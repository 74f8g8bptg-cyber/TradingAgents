"""``python -m stellar.owner reset-breaker --journal PATH --station-id ID`` (owner only)."""

from __future__ import annotations

import argparse
import sys

from stellar.journal import StellarJournal
from stellar.owner.breaker_reset import CONFIRMATION_PHRASE, ResetOutcome, owner_reset_breaker
from stellar.risk.ledger import BreakerLedger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m stellar.owner")
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset-breaker", help="reset a tripped circuit breaker (owner only)")
    reset.add_argument("--journal", required=True)
    reset.add_argument("--station-id", required=True)
    args = parser.parse_args(argv)

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    with StellarJournal(args.journal) as journal:
        state = BreakerLedger(journal, station_id=args.station_id).state()
        print(f"Circuit breaker: {state.status.value}")
        if state.trip is not None:
            trip = state.trip
            print(f"Tripped at {trip.tripped_at.isoformat()} by {trip.tripped_by}: "
                  f"{trip.cause.value} {trip.rule.value if trip.rule else ''}".rstrip())
        typed = input(f'Type "{CONFIRMATION_PHRASE}" to reset: ') if interactive else ""
        reason = input("Reason for the reset: ") if interactive else ""
        outcome = owner_reset_breaker(journal, station_id=args.station_id,
                                      interactive=interactive, typed_confirmation=typed,
                                      reason=reason)
    print(outcome.value)
    return 0 if outcome is ResetOutcome.RESET else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
