"""Circuit-breaker persistence: the state is derived from the Stellar Journal.

The breaker's state is never stored as a mutable flag. It is replayed from
journaled ``circuit_breaker.tripped`` and ``circuit_breaker.reset`` events, so a
restart reconstructs exactly the state before it, and restarting can never
imply an owner approval (Foundation §4.27: "persisted, so a restart does not
re-arm it").

- Trips are sticky: once TRIPPED, later trips are not recorded as new trips.
- A reset counts only if it came from the owner command: source
  ``stellar.owner`` and payload ``by == "owner"`` with a reason. Any other
  ``circuit_breaker.reset`` event in the journal is ignored and counted in
  ``ignored_resets``.
- This module has **no reset operation**. Resetting is ``stellar.owner`` only.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from stellar.journal import StellarJournal
from stellar.risk.breaker import BreakerStatus, BreakerTrip, CircuitBreakerState, OwnerReset
from stellar.telemetry import StellarEvent, new_event

OWNER_SOURCE = "stellar.owner"
NEVER = datetime(1970, 1, 1, tzinfo=UTC)
BREAKER_EVENTS = ("circuit_breaker.tripped", "circuit_breaker.reset")


def is_owner_reset(event: StellarEvent) -> bool:
    payload = event.payload
    return (event.type == "circuit_breaker.reset" and event.source == OWNER_SOURCE
            and payload.get("by") == "owner" and bool(str(payload.get("reason") or "").strip()))


def replay_breaker(events) -> tuple[CircuitBreakerState, int]:
    """Fold breaker events (journal order) into a state; returns (state, ignored resets)."""
    state = CircuitBreakerState(updated_at=NEVER)
    ignored = 0
    for event in events:
        if event.type == "circuit_breaker.tripped":
            state = state.tripped(BreakerTrip.from_event(event))
        elif event.type == "circuit_breaker.reset":
            if not is_owner_reset(event) or state.status is not BreakerStatus.TRIPPED:
                ignored += 1
                continue
            reset = OwnerReset(by="owner", reason=str(event.payload["reason"]),
                               reset_at=event.ts, event_id=event.event_id)
            state = CircuitBreakerState(status=BreakerStatus.ARMED, last_reset=reset,
                                        updated_at=max(state.updated_at, event.ts))
    return state, ignored


class BreakerLedger:
    def __init__(self, journal: StellarJournal, *, station_id: str,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._journal = journal
        self._station_id = station_id
        self._clock = clock or (lambda: datetime.now(UTC))

    def state(self) -> CircuitBreakerState:
        return replay_breaker(self._journal.read(types=BREAKER_EVENTS))[0]

    def ignored_resets(self) -> int:
        return replay_breaker(self._journal.read(types=BREAKER_EVENTS))[1]

    def trip(self, trip: BreakerTrip) -> CircuitBreakerState:
        """Record a trip if the breaker is armed; a tripped breaker keeps its first trip."""
        current = self.state()
        if current.status is BreakerStatus.TRIPPED:
            return current
        self._journal.append(new_event(
            "circuit_breaker.tripped", station_id=self._station_id, source="stellar.risk",
            agent_id=trip.tripped_by if trip.tripped_by != "owner" else None,
            payload=trip.to_event_payload(), ts=max(trip.tripped_at, self._clock()),
        ))
        return self.state()
