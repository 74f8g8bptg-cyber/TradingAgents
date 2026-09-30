"""The owner's circuit-breaker reset (Foundation §8.3; owner decision Q6).

This is the **only** code that writes ``circuit_breaker.reset``. It is meant to be
run by the owner, by hand, on the local machine:

    python -m stellar.owner reset-breaker --journal PATH --station-id ID

Requirements before a reset is recorded:
1. an interactive terminal (standard input and output are TTYs), so no
   scheduler, script, agent or UI can drive it;
2. the owner types the exact confirmation phrase;
3. the owner gives a non-empty reason;
4. the breaker is actually TRIPPED.

Any failed attempt is journaled as ``circuit_breaker.reset_refused``. A reset is
journaled with source ``stellar.owner`` and ``by: owner``; the breaker ledger
accepts no other reset.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum

from stellar.journal import StellarJournal
from stellar.risk.breaker import BreakerStatus
from stellar.risk.ledger import OWNER_SOURCE, BreakerLedger
from stellar.telemetry import new_event

CONFIRMATION_PHRASE = "RESET CIRCUIT BREAKER"


class ResetOutcome(StrEnum):
    RESET = "RESET"
    REFUSED_NOT_INTERACTIVE = "REFUSED_NOT_INTERACTIVE"
    REFUSED_CONFIRMATION = "REFUSED_CONFIRMATION"
    REFUSED_NO_REASON = "REFUSED_NO_REASON"
    REFUSED_NOT_TRIPPED = "REFUSED_NOT_TRIPPED"


def owner_reset_breaker(
    journal: StellarJournal,
    *,
    station_id: str,
    interactive: bool,
    typed_confirmation: str,
    reason: str,
    clock: Callable[[], datetime] | None = None,
) -> ResetOutcome:
    now = (clock or (lambda: datetime.now(UTC)))()

    def refuse(outcome: ResetOutcome, why: str) -> ResetOutcome:
        journal.append(new_event("circuit_breaker.reset_refused", station_id=station_id,
                                 source=OWNER_SOURCE, ts=now,
                                 payload={"source": "owner_command", "reason": why}))
        return outcome

    if not interactive:
        return refuse(ResetOutcome.REFUSED_NOT_INTERACTIVE, "not_an_interactive_terminal")
    if typed_confirmation != CONFIRMATION_PHRASE:
        return refuse(ResetOutcome.REFUSED_CONFIRMATION, "confirmation_phrase_mismatch")
    if not reason.strip():
        return refuse(ResetOutcome.REFUSED_NO_REASON, "no_reason_given")
    ledger = BreakerLedger(journal, station_id=station_id)
    if ledger.state().status is not BreakerStatus.TRIPPED:
        return refuse(ResetOutcome.REFUSED_NOT_TRIPPED, "breaker_not_tripped")
    journal.append(new_event("circuit_breaker.reset", station_id=station_id, source=OWNER_SOURCE,
                             ts=now, payload={"by": "owner", "reason": reason.strip()}))
    return ResetOutcome.RESET
