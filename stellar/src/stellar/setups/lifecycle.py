"""The Setup lifecycle (Foundation §4.12), journaled as ``setup.state.changed``.

The journal is the only store: the current state of a setup is the ``to`` state of its latest
``setup.state.changed`` event. Nothing is overwritten.

**Transitions** (anything else is refused and journals nothing):

| From | To |
|---|---|
| (none), NO_SETUP, WATCHING, ARMED | NO_SETUP, WATCHING, ARMED, INVALIDATED, EXPIRED |
| ARMED | PROPOSED (only through ``mark_proposed``, when the builder has built a proposal) |
| PROPOSED | INVALIDATED, EXPIRED (APPROVED / REJECTED belong to the Risk Engine) |
| APPROVED | FILLED, INVALIDATED, EXPIRED (broker and Risk Engine; never set here) |
| INVALIDATED, EXPIRED, REJECTED, FILLED | none (terminal) |

A PROPOSED setup keeps its proposal: a later evaluation that finds it WATCHING, ARMED or
NO_SETUP does not move it back (the proposal expires or is invalidated instead).

**Idempotency.** An evaluation with the same state and the same fingerprint as the latest
event journals nothing. The same state with a new fingerprint journals one event with rule
``evidence_changed``, so the journal always holds the evidence behind the current state.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from stellar.journal import StellarJournal
from stellar.schemas.common import Label, StellarModel
from stellar.setups.models import Setup, SetupState
from stellar.telemetry import EventBus, new_event

SOURCE = "stellar.setups"
AGENT = "pullback_setup"
EVENT = "setup.state.changed"

_OPEN = {SetupState.NO_SETUP, SetupState.WATCHING, SetupState.ARMED}
_EVALUATED = _OPEN | {SetupState.INVALIDATED, SetupState.EXPIRED}
ALLOWED: dict[SetupState | None, frozenset[SetupState]] = {
    None: frozenset(_EVALUATED),
    SetupState.NO_SETUP: frozenset(_EVALUATED),
    SetupState.WATCHING: frozenset(_EVALUATED),
    SetupState.ARMED: frozenset(_EVALUATED | {SetupState.PROPOSED}),
    SetupState.PROPOSED: frozenset({SetupState.APPROVED, SetupState.REJECTED,
                                    SetupState.INVALIDATED, SetupState.EXPIRED}),
    SetupState.APPROVED: frozenset({SetupState.FILLED, SetupState.INVALIDATED,
                                    SetupState.EXPIRED}),
    SetupState.REJECTED: frozenset(),
    SetupState.FILLED: frozenset(),
    SetupState.EXPIRED: frozenset(),
    SetupState.INVALIDATED: frozenset(),
}
TERMINAL = frozenset(s for s, targets in ALLOWED.items() if s is not None and not targets)


class LifecycleResult(StellarModel):
    setup_id: str
    previous: SetupState | None = None
    state: SetupState
    changed: bool
    """True when an event was journaled."""
    refused: bool = False
    rule: Label | None = None


class SetupBook:
    """Reads and appends the lifecycle of setups in one journal."""

    def __init__(self, journal: StellarJournal, *, station_id: str,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._journal = journal
        self._bus = EventBus(journal)
        self._station = station_id
        self._clock = clock or (lambda: datetime.now(UTC))

    def latest(self, setup_id: str) -> dict[str, Any] | None:
        for event in reversed(self._journal.read(types=[EVENT])):
            if event.payload.get("setup_id") == setup_id:
                return event.payload
        return None

    def state(self, setup_id: str) -> SetupState | None:
        latest = self.latest(setup_id)
        return SetupState(latest["to"]) if latest else None

    def record(self, setup: Setup) -> LifecycleResult:
        """Journal the state an evaluation found, if the transition is allowed."""
        latest = self.latest(setup.setup_id)
        previous = SetupState(latest["to"]) if latest else None
        target = setup.state
        if previous is target:
            if latest and latest.get("fingerprint") == setup.fingerprint or previous in TERMINAL:
                return LifecycleResult(setup_id=setup.setup_id, previous=previous,
                                       state=target, changed=False)
            return self._emit(setup, previous, target, "evidence_changed")
        if previous is SetupState.PROPOSED and target in _OPEN:
            return LifecycleResult(setup_id=setup.setup_id, previous=previous, state=previous,
                                   changed=False, rule="already_proposed")
        if target not in ALLOWED[previous]:
            return LifecycleResult(setup_id=setup.setup_id, previous=previous,
                                   state=previous or target, changed=False, refused=True,
                                   rule=f"illegal_{(previous or target).value.lower()}_to_"
                                        f"{target.value.lower()}")
        rule = setup.reasons[0] if setup.reasons else {
            SetupState.WATCHING: "candidate_found",
            SetupState.ARMED: "ready_for_proposal"}.get(target, target.value.lower())
        return self._emit(setup, previous, target, rule)

    def mark_proposed(self, setup: Setup, proposal_id: str) -> LifecycleResult:
        """ARMED → PROPOSED, once a proposal for this exact setup evaluation was built."""
        latest = self.latest(setup.setup_id)
        previous = SetupState(latest["to"]) if latest else None
        if previous is SetupState.PROPOSED and latest and \
                latest.get("proposal_id") == proposal_id:
            return LifecycleResult(setup_id=setup.setup_id, previous=previous, state=previous,
                                   changed=False)
        if previous is not SetupState.ARMED or latest is None or \
                latest.get("fingerprint") != setup.fingerprint:
            return LifecycleResult(setup_id=setup.setup_id, previous=previous,
                                   state=previous or setup.state, changed=False, refused=True,
                                   rule="not_armed_with_this_evidence")
        return self._emit(setup, previous, SetupState.PROPOSED, "proposal_built",
                          proposal_id=proposal_id)

    def _emit(self, setup: Setup, previous: SetupState | None, target: SetupState, rule: str,
              **extra: Any) -> LifecycleResult:
        self._bus.publish(new_event(
            EVENT, station_id=self._station, source=SOURCE, agent_id=AGENT,
            instrument=setup.instrument, correlation_id=setup.evidence.run_id,
            ts=self._clock(),
            payload={"setup_id": setup.setup_id, "from": previous.value if previous else None,
                     "to": target.value, "rule": rule, "status": setup.status.value,
                     "direction": setup.direction.value, "fingerprint": setup.fingerprint,
                     "as_of": setup.as_of.isoformat(), "setup": setup.model_dump(mode="json"),
                     **extra}))
        return LifecycleResult(setup_id=setup.setup_id, previous=previous, state=target,
                               changed=True, rule=rule)
