"""``ExecutionResult``: the outcome of one order at one point in its lifecycle.

Statuses follow the order events of layer design §4.3 (``order.created``,
``order.preflight.failed``, ``order.sent``, ``order.acknowledged``,
``order.partially_filled``, ``order.filled``, ``order.rejected``). Closing a
position is a trade record (``trade.closed``), defined with settlement in Phase 4.
Phase 4 adds, additively, ``cancelled`` and ``expired`` for working orders that end
without a fill (``order.cancelled``, ``order.expired``).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    FillId,
    FiniteDecimal,
    InstrumentId,
    IntentId,
    Label,
    NonNegativeDecimal,
    OrderId,
    OrderSide,
    PositiveDecimal,
    Price,
    Provenance,
    SchemaVersion,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.order import AccountMode

EXECUTION_AGENT_IDS = frozenset({"execution_checker", "paper_execution", "mt5_execution"})


class ExecutionStatus(StrEnum):
    CREATED = "created"
    PREFLIGHT_FAILED = "preflight_failed"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    # Phase 4 additions: a working (pending) order can end without a fill.
    CANCELLED = "cancelled"
    EXPIRED = "expired"


_NO_FILL = {
    ExecutionStatus.CREATED,
    ExecutionStatus.PREFLIGHT_FAILED,
    ExecutionStatus.SENT,
    ExecutionStatus.ACKNOWLEDGED,
    ExecutionStatus.REJECTED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.EXPIRED,
}
_NEEDS_REASON = {ExecutionStatus.PREFLIGHT_FAILED, ExecutionStatus.REJECTED}


class ExecutionResult(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    order_id: OrderId
    intent_id: IntentId
    instrument: InstrumentId
    account_mode: AccountMode
    side: OrderSide
    status: ExecutionStatus
    requested_volume: PositiveDecimal
    filled_volume: NonNegativeDecimal
    fill_id: FillId | None = None
    fill_price: Price | None = None
    slippage: FiniteDecimal | None = None
    reason: Label | None = None
    broker_ticket: ShortText | None = None
    ts: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _lifecycle_consistent(self) -> ExecutionResult:
        if self.provenance.produced_by not in EXECUTION_AGENT_IDS:
            raise ValueError("execution results come only from the execution agents (P4, E1, E2)")
        if self.provenance.produced_by == "mt5_execution" and self.account_mode is not (
            AccountMode.DEMO
        ):
            raise ValueError("the MT5 execution agent runs demo accounts only")
        if self.broker_ticket is not None and self.account_mode is not AccountMode.DEMO:
            raise ValueError("a broker ticket exists only for broker (DEMO) orders")
        if self.status in _NO_FILL:
            if self.filled_volume != 0 or self.fill_price is not None or self.fill_id is not None:
                raise ValueError(f"status {self.status.value} carries no fill")
            if self.slippage is not None:
                raise ValueError(f"status {self.status.value} carries no slippage")
        else:
            if self.fill_price is None or self.fill_id is None:
                raise ValueError("a fill needs fill_price and fill_id")
            if self.status is ExecutionStatus.FILLED and self.filled_volume != self.requested_volume:
                raise ValueError("filled means the whole requested volume was filled")
            if self.status is ExecutionStatus.PARTIALLY_FILLED and not (
                0 < self.filled_volume < self.requested_volume
            ):
                raise ValueError("a partial fill is more than zero and less than requested")
        if self.status in _NEEDS_REASON and self.reason is None:
            raise ValueError(f"status {self.status.value} must give a reason")
        if self.status not in _NEEDS_REASON and self.reason is not None:
            raise ValueError(f"status {self.status.value} carries no failure reason")
        return self
