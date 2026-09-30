"""In-process event bus (layer design §4.5). No network transport in Phase 1.

Publishing journals the event first, then delivers the stored copy (with its
``seq``) to subscribers. An event already in the journal is not delivered again.

Failure rules (layer design §4.5):
- a subscriber that raises is logged and skipped; it never fails the publisher;
- if a **decision or order** event cannot be written to the journal, the error
  propagates so execution halts; for other events the write failure is logged
  and ``None`` returned;
- a malformed event, or a different event reusing a stored ``event_id``, always
  raises: those are programming errors, not storage failures.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

# Module import (not ``from … import``): stellar.journal.store imports
# stellar.telemetry, so names are resolved at call time to keep either import
# order working.
import stellar.journal.store as journal_store
from stellar.telemetry.catalogue import is_critical
from stellar.telemetry.events import StellarEvent

log = logging.getLogger(__name__)

Subscriber = Callable[[StellarEvent], None]


class EventBus:
    def __init__(self, journal: journal_store.StellarJournal) -> None:
        self._journal = journal
        self._subscribers: list[Subscriber] = []
        self._lock = threading.Lock()

    def subscribe(self, handler: Subscriber) -> Callable[[], None]:
        """Register ``handler``; returns a function that unsubscribes it."""
        with self._lock:
            self._subscribers.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._subscribers:
                    self._subscribers.remove(handler)

        return unsubscribe

    def publish(self, event: StellarEvent) -> StellarEvent | None:
        """Journal ``event`` and deliver it once. Returns the stored event."""
        try:
            stored, is_new = self._journal.append_new(event)
        except journal_store.JournalWriteError:
            if is_critical(event.type):
                raise
            log.exception("could not journal non-critical event %s", event.type)
            return None
        if is_new:
            with self._lock:
                subscribers = list(self._subscribers)
            for handler in subscribers:
                try:
                    handler(stored)
                except Exception:
                    log.exception("event subscriber failed on %s", stored.type)
        return stored
