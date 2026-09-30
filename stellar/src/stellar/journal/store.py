"""The Stellar Journal: the canonical, append-only record of Stellar runtime events.

Separate from upstream's ``TradingMemoryLog`` (a markdown decision log that
Stellar may read later, D-10); nothing here reads or writes upstream memory.

Guarantees:
- **Append-only.** SQLite triggers abort any UPDATE or DELETE of stored events.
- **Ordered.** The journal assigns ``seq`` = previous + 1 inside one write
  transaction, so sequence numbers are contiguous from 1.
- **Validated.** Only well-formed ``StellarEvent`` objects (or JSON that parses
  into one) are stored; the stored copy's body hash is checked on every read.
- **Idempotent.** Appending an event whose ``event_id`` is already stored with
  the same content returns the stored copy and writes nothing; the same id with
  different content is refused.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import ValidationError

from stellar.serialization import sha256_hex
from stellar.telemetry.events import StellarEvent

JOURNAL_FORMAT = "stellar-journal"
JOURNAL_FORMAT_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS journal_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    ts TEXT NOT NULL,
    run_id TEXT,
    correlation_id TEXT,
    content_key TEXT NOT NULL,
    body TEXT NOT NULL,
    body_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_run ON events (run_id, seq);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'the Stellar journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'the Stellar journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS meta_no_update BEFORE UPDATE ON journal_meta
BEGIN SELECT RAISE(ABORT, 'journal metadata is immutable'); END;
"""


class JournalError(Exception):
    """Base class for journal errors."""


class JournalWriteError(JournalError):
    """The event could not be persisted."""


class MalformedEventError(JournalError):
    """The input is not a valid Stellar event."""


class DuplicateEventConflict(JournalError):
    """A different event reuses an ``event_id`` that is already stored."""


class JournalIntegrityError(JournalError):
    """Stored data fails its integrity checks."""


class StellarJournal:
    def __init__(self, path: str | Path = ":memory:") -> None:
        target = str(path)
        if target != ":memory:":
            Path(target).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(target, check_same_thread=False, isolation_level=None)
        self._db.executescript(_SCHEMA)
        self._db.execute(
            "INSERT OR IGNORE INTO journal_meta (key, value) VALUES ('format', ?), ('version', ?)",
            (JOURNAL_FORMAT, JOURNAL_FORMAT_VERSION),
        )
        meta = dict(self._db.execute("SELECT key, value FROM journal_meta"))
        if meta.get("format") != JOURNAL_FORMAT or meta.get("version") != JOURNAL_FORMAT_VERSION:
            self._db.close()
            raise JournalIntegrityError(f"{target} is not a version-1 Stellar journal")

    # -------------------------------------------------------------- write --

    def append(self, event: StellarEvent) -> StellarEvent:
        """Store ``event`` and return the stored copy (with ``seq``)."""
        return self.append_new(event)[0]

    def append_json(self, text: str) -> StellarEvent:
        """Parse, validate and store one event given as JSON."""
        try:
            event = StellarEvent.from_json(text)
        except ValidationError as exc:
            raise MalformedEventError(str(exc)) from exc
        return self.append(event)

    def append_new(self, event: StellarEvent) -> tuple[StellarEvent, bool]:
        """Store ``event``; returns ``(stored, is_new)``. ``is_new`` is False for a replayed duplicate."""
        event = self._revalidated(event)
        key = event.content_key()
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT content_key, seq, body, body_sha256 FROM events WHERE event_id = ?",
                    (event.event_id,),
                ).fetchone()
                if row is not None:
                    self._db.execute("ROLLBACK")
                    if row[0] != key:
                        raise DuplicateEventConflict(
                            f"event_id {event.event_id} is already stored with different content"
                        )
                    return self._parse(*row[1:]), False
                (last,) = self._db.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
                stored = event.with_seq(last + 1)
                body = stored.to_json()
                self._db.execute(
                    "INSERT INTO events (seq, event_id, type, ts, run_id, correlation_id,"
                    " content_key, body, body_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        stored.seq,
                        stored.event_id,
                        stored.type,
                        stored.model_dump(mode="json")["ts"],
                        stored.run_id,
                        stored.correlation_id,
                        key,
                        body,
                        sha256_hex(body),
                    ),
                )
                self._db.execute("COMMIT")
            except sqlite3.Error as exc:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise JournalWriteError(str(exc)) from exc
        return stored, True

    @staticmethod
    def _revalidated(event: StellarEvent) -> StellarEvent:
        if not isinstance(event, StellarEvent):
            raise MalformedEventError(f"expected a StellarEvent, got {type(event).__name__}")
        if event.seq is not None:
            raise MalformedEventError("seq is assigned by the journal; append an event without it")
        try:
            # Re-validate from data so an object built with model_construct cannot slip through.
            return StellarEvent.model_validate(event.model_dump())
        except ValidationError as exc:
            raise MalformedEventError(str(exc)) from exc

    # --------------------------------------------------------------- read --

    def last_seq(self) -> int:
        with self._lock:
            (last,) = self._db.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
        return last

    def get(self, event_id: str) -> StellarEvent | None:
        with self._lock:
            row = self._db.execute(
                "SELECT seq, body, body_sha256 FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return None if row is None else self._parse(*row)

    def read(
        self,
        since_seq: int = 0,
        *,
        run_id: str | None = None,
        types: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[StellarEvent]:
        """Events with ``seq > since_seq`` in order, optionally filtered."""
        sql = "SELECT seq, body, body_sha256 FROM events WHERE seq > ?"
        args: list[object] = [since_seq]
        if run_id is not None:
            sql += " AND run_id = ?"
            args.append(run_id)
        wanted = list(types) if types is not None else None
        if wanted is not None:
            sql += f" AND type IN ({','.join('?' * len(wanted))})" if wanted else " AND 0"
            args.extend(wanted)
        sql += " ORDER BY seq"
        if limit is not None:
            sql += " LIMIT ?"
            args.append(limit)
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [self._parse(*row) for row in rows]

    def replay(self, since_seq: int = 0) -> Iterator[StellarEvent]:
        """Yield every stored event after ``since_seq`` in journal order."""
        yield from self.read(since_seq)

    def verify(self) -> int:
        """Check contiguity and body hashes of the whole journal; returns the event count."""
        events = self.read()
        for expected, event in enumerate(events, start=1):
            if event.seq != expected:
                raise JournalIntegrityError(f"sequence gap: expected {expected}, found {event.seq}")
        return len(events)

    @staticmethod
    def _parse(seq: int, body: str, body_sha256: str) -> StellarEvent:
        if sha256_hex(body) != body_sha256:
            raise JournalIntegrityError(f"event at seq {seq} fails its body hash")
        try:
            event = StellarEvent.from_json(body)
        except ValidationError as exc:
            raise JournalIntegrityError(f"event at seq {seq} is not a valid event") from exc
        if event.seq != seq:
            raise JournalIntegrityError(f"event at seq {seq} records seq {event.seq}")
        return event

    # ------------------------------------------------------------ lifetime --

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> StellarJournal:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
