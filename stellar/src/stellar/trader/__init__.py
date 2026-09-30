"""Phase 6b trader layer: the U4 Trader's level selection and the desk that runs
setup → selection → Trade Proposal. It never reaches risk approval, order intents, the broker,
the breaker, account state or configuration.
"""

from stellar.trader.contracts import (
    TRADER_ROLE,
    TRADER_TEMPLATE,
    TraderConfig,
    TraderDecision,
    TraderSelectionOutput,
)
from stellar.trader.desk import (
    DeskFailure,
    OutcomeKind,
    TraderDesk,
    TraderInputs,
    TraderOutcome,
    check_selection,
    single_option_selection,
    trader_task,
)

__all__ = [
    "TRADER_ROLE",
    "TRADER_TEMPLATE",
    "DeskFailure",
    "OutcomeKind",
    "TraderConfig",
    "TraderDecision",
    "TraderDesk",
    "TraderInputs",
    "TraderOutcome",
    "TraderSelectionOutput",
    "check_selection",
    "single_option_selection",
    "trader_task",
]
