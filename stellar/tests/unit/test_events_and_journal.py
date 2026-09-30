"""Event envelope, catalogue, serialization, journal and bus."""

import random
import sqlite3
from datetime import timedelta

import pytest
from factories import T0, event_data, make_event
from pydantic import ValidationError
from stellar.ids import IdKind, new_id, new_ulid
from stellar.journal import (
    DuplicateEventConflict,
    JournalIntegrityError,
    JournalWriteError,
    MalformedEventError,
    StellarJournal,
)
from stellar.telemetry import EVENT_TYPES, MINIMUM_V1_EVENT_TYPES, EventBus, StellarEvent, new_event
from stellar.telemetry.catalogue import EVENT_NAME_PATTERN, REQUIRED_PAYLOAD_KEYS, is_critical

pytestmark = pytest.mark.unit


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


# --- ids --------------------------------------------------------------------


def test_ulids_are_reproducible_with_injected_time_and_randomness_and_sort_by_time():
    a = new_ulid(T0, random.Random(7))
    assert a == new_ulid(T0, random.Random(7))
    later = new_ulid(T0 + timedelta(milliseconds=1), random.Random(7))
    assert len(a) == 26 and later > a
    assert new_id(IdKind.PROPOSAL, T0, random.Random(1)).startswith("prop_")


# --- catalogue --------------------------------------------------------------


def test_catalogue_names_are_canonical_and_include_the_minimum_v1_set():
    assert MINIMUM_V1_EVENT_TYPES <= EVENT_TYPES
    assert len(MINIMUM_V1_EVENT_TYPES) == 29
    for name in EVENT_TYPES:
        assert EVENT_NAME_PATTERN.match(name), name
    assert set(REQUIRED_PAYLOAD_KEYS) <= EVENT_TYPES


@pytest.mark.parametrize(
    "name",
    ["agent.state_changed", "risk.breaker_tripped", "signal.intent_created", "order.fill",
     "Agent.State.Changed", "trade", "custom.thing.happened"],
)
def test_non_canonical_or_legacy_event_names_are_rejected(name):
    with pytest.raises(ValidationError, match="canonical"):
        make_event(type=name)


def test_critical_domains():
    assert is_critical("risk.approved") and is_critical("order.filled")
    assert is_critical("circuit_breaker.reset") and is_critical("trade.proposed")
    assert not is_critical("agent.state.changed") and not is_critical("analysis.created")


# --- envelope ---------------------------------------------------------------


def test_event_envelope_fields_and_validation():
    event = make_event(run_id="run_x1", instrument="XAUUSD", correlation_id="prop_7f3a",
                       room="command_deck")
    assert event.seq is None and event.schema_version == "1.0"
    with pytest.raises(ValidationError):
        make_event(event_id="not-a-ulid")
    with pytest.raises(ValidationError, match="correlation_id"):
        make_event(correlation_id="7f3a")
    with pytest.raises(ValidationError):
        make_event(source="somewhere")
    with pytest.raises(ValidationError):
        make_event(ts=T0.replace(tzinfo=None))


def test_decision_critical_events_require_their_documented_payload_keys():
    with pytest.raises(ValidationError, match="missing"):
        make_event(type="risk.approved", payload={"proposal_id": "prop_01"})
    event = make_event(type="risk.approved",
                       payload={"proposal_id": "prop_01", "decision_id": "dec_01"})
    assert event.type == "risk.approved"


@pytest.mark.parametrize("key", ["api_key", "password", "backend_url", "API_KEY"])
def test_secrets_never_enter_events(key):
    with pytest.raises(ValidationError, match="not allowed"):
        make_event(payload={"nested": {key: "x"}})


def test_payload_rejects_non_finite_numbers():
    with pytest.raises(ValidationError):
        make_event(payload={"value": float("nan")})


def test_serialization_is_deterministic_and_round_trips():
    a = make_event(payload={"b": 1, "a": [1, 2], "c": {"z": "1", "y": None}})
    b = StellarEvent.model_validate(event_data(payload={"c": {"y": None, "z": "1"}, "a": [1, 2],
                                                        "b": 1}))
    assert a.to_json() == b.to_json()
    assert a.content_key() == b.content_key()
    assert " " not in a.to_json()
    assert StellarEvent.from_json(a.to_json()) == a


def test_new_event_helper_is_reproducible():
    one = new_event("system.paused", station_id="stellar-01", source="stellar.system",
                    payload={"reason": "owner"}, ts=T0, rng=random.Random(3))
    two = new_event("system.paused", station_id="stellar-01", source="stellar.system",
                    payload={"reason": "owner"}, ts=T0, rng=random.Random(3))
    assert one == two


# --- journal ----------------------------------------------------------------


def test_journal_appends_in_order_with_contiguous_sequence_numbers(journal):
    stored = [journal.append(make_event(n)) for n in range(5)]
    assert [e.seq for e in stored] == [1, 2, 3, 4, 5]
    assert [e.event_id for e in journal.replay()] == [e.event_id for e in stored]
    assert journal.last_seq() == 5
    assert journal.verify() == 5


def test_journal_orders_by_append_not_by_timestamp(journal):
    journal.append(make_event(0, ts=T0 + timedelta(seconds=10)))
    journal.append(make_event(1, ts=T0))
    assert [e.seq for e in journal.read()] == [1, 2]
    assert [e.event_id for e in journal.read()] == [make_event(0).event_id,
                                                    make_event(1).event_id]


def test_journal_read_filters(journal):
    journal.append(make_event(0, run_id="run_a"))
    journal.append(make_event(1, run_id="run_b"))
    journal.append(make_event(2, run_id="run_a", type="system.paused",
                              payload={"reason": "x"}))
    assert [e.seq for e in journal.read(since_seq=1)] == [2, 3]
    assert [e.seq for e in journal.read(run_id="run_a")] == [1, 3]
    assert [e.seq for e in journal.read(types=["system.paused"])] == [3]
    assert journal.read(types=[]) == []
    assert [e.seq for e in journal.read(limit=2)] == [1, 2]


def test_duplicate_event_is_stored_once(journal):
    first = journal.append(make_event(0))
    again, is_new = journal.append_new(make_event(0))
    assert not is_new and again == first
    assert journal.last_seq() == 1


def test_same_event_id_with_different_content_is_refused(journal):
    journal.append(make_event(0))
    with pytest.raises(DuplicateEventConflict):
        journal.append(make_event(0, payload={"from": "IDLE", "to": "ERROR", "reason": "x"}))
    assert journal.last_seq() == 1


def test_journal_rejects_malformed_input(journal):
    with pytest.raises(MalformedEventError):
        journal.append({"type": "agent.state.changed"})
    with pytest.raises(MalformedEventError, match="seq"):
        journal.append(make_event(0).with_seq(9))
    bypass = StellarEvent.model_construct(**{**event_data(0), "type": "not.a.real_event"})
    with pytest.raises(MalformedEventError):
        journal.append(bypass)
    with pytest.raises(MalformedEventError):
        journal.append_json('{"event_id": "x"}')
    assert journal.last_seq() == 0


def test_journal_accepts_valid_json_and_replays_it(journal):
    stored = journal.append_json(make_event(0).to_json())
    assert stored.seq == 1 and journal.get(stored.event_id) == stored


def test_old_records_cannot_be_updated_or_deleted(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        j.append(make_event(0))
    raw = sqlite3.connect(path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("UPDATE events SET type = 'system.paused'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("DELETE FROM events")
    raw.close()


def test_journal_persists_and_detects_tampering(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        j.append(make_event(0))
        j.append(make_event(1))
    with StellarJournal(path) as j:
        assert j.verify() == 2
        assert j.append(make_event(2)).seq == 3
    raw = sqlite3.connect(path)
    raw.execute("DROP TRIGGER events_no_update")
    raw.execute("UPDATE events SET body = replace(body, 'supervisor', 'risk_engine') WHERE seq=1")
    raw.commit()
    raw.close()
    with StellarJournal(path) as j, pytest.raises(JournalIntegrityError):
        j.verify()


def test_journal_refuses_a_foreign_database(tmp_path):
    path = tmp_path / "other.sqlite3"
    raw = sqlite3.connect(path)
    raw.execute("CREATE TABLE journal_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    raw.execute("INSERT INTO journal_meta VALUES ('format', 'something-else')")
    raw.commit()
    raw.close()
    with pytest.raises(JournalIntegrityError):
        StellarJournal(path)


# --- bus --------------------------------------------------------------------


def test_bus_journals_then_delivers_once(journal):
    bus = EventBus(journal)
    seen = []
    bus.subscribe(seen.append)
    stored = bus.publish(make_event(0))
    assert stored.seq == 1 and seen == [stored]
    assert bus.publish(make_event(0)) == stored  # duplicate: not delivered again
    assert seen == [stored]


def test_a_failing_subscriber_never_fails_the_publisher(journal):
    bus = EventBus(journal)
    seen = []

    def broken(_):
        raise RuntimeError("renderer crashed")

    bus.subscribe(broken)
    bus.subscribe(seen.append)
    bus.publish(make_event(0))
    assert len(seen) == 1


def test_unsubscribe(journal):
    bus = EventBus(journal)
    seen = []
    unsubscribe = bus.subscribe(seen.append)
    unsubscribe()
    bus.publish(make_event(0))
    assert seen == []


class _BrokenJournal(StellarJournal):
    def append_new(self, event):
        raise JournalWriteError("disk full")


def test_journal_write_failure_halts_critical_events_only():
    bus = EventBus(_BrokenJournal())
    assert bus.publish(make_event(0)) is None
    critical = make_event(1, type="risk.approved",
                          payload={"proposal_id": "prop_01", "decision_id": "dec_01"})
    with pytest.raises(JournalWriteError):
        bus.publish(critical)


def test_bus_never_swallows_malformed_events(journal):
    bus = EventBus(journal)
    bypass = StellarEvent.model_construct(**{**event_data(0), "type": "not.a.real_event"})
    with pytest.raises(MalformedEventError):
        bus.publish(bypass)
