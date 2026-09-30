"""Phase 6b setups: the deterministic Setup contract, evaluator and lifecycle (T6).

Reads Phase 5 technical evidence and Phase 6 decision support as given. Calls no model, and
cannot build a proposal, a risk decision, an order intent or an order.
"""

from stellar.setups.config import (
    ORDER_TYPE_FOR_ENTRY,
    EntryModelKind,
    SetupConfig,
    StopBuffer,
)
from stellar.setups.evaluate import SetupInputError, evaluate_setup, indicator_ref, verify_setup
from stellar.setups.lifecycle import ALLOWED, TERMINAL, LifecycleResult, SetupBook
from stellar.setups.models import (
    STATE_FOR_STATUS,
    LevelOption,
    LevelRole,
    NumericSource,
    OptionKind,
    Setup,
    SetupDirection,
    SetupEvidence,
    SetupState,
    SetupStatus,
    SetupType,
)

__all__ = [
    "ALLOWED",
    "ORDER_TYPE_FOR_ENTRY",
    "STATE_FOR_STATUS",
    "TERMINAL",
    "EntryModelKind",
    "LevelOption",
    "LevelRole",
    "LifecycleResult",
    "NumericSource",
    "OptionKind",
    "Setup",
    "SetupBook",
    "SetupConfig",
    "SetupDirection",
    "SetupEvidence",
    "SetupInputError",
    "SetupState",
    "SetupStatus",
    "SetupType",
    "StopBuffer",
    "evaluate_setup",
    "indicator_ref",
    "verify_setup",
]
