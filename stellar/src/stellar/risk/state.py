"""Inputs to a risk evaluation: ``RiskContext`` and the state it carries.

Broker-independent and explicit. Nothing here assumes a contract size, pip
value, leverage, margin formula or currency conversion: a value the engine needs
must be given, with its source, or the rule that needs it reports a missing
input. ``None`` always means *unknown*; an empty tuple means *known to be none*
(for example, no open positions).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from stellar.marketdata import QuoteResponse, VerifiedMarketSnapshot
from stellar.risk.breaker import CircuitBreakerState
from stellar.schemas.common import (
    CurrencyCode,
    FiniteDecimal,
    InstrumentId,
    Label,
    OrderSide,
    PositiveDecimal,
    Price,
    Sha256Hex,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.proposal import TradeProposal

InputSource = Literal["broker", "paper_broker", "owner", "journal", "test_fixture"]


class AccountRiskState(StellarModel):
    """Account figures in the account currency, as of ``as_of``."""

    currency: CurrencyCode
    equity: PositiveDecimal
    balance: PositiveDecimal | None = None
    peak_equity: PositiveDecimal | None = None
    """Highest equity on record (for drawdown); None if not tracked."""
    as_of: UtcDatetime
    source: InputSource

    @model_validator(mode="after")
    def _peak(self) -> AccountRiskState:
        if self.peak_equity is not None and self.peak_equity < self.equity:
            raise ValueError("peak_equity cannot be below current equity")
        return self


class DailyRiskState(StellarModel):
    """Today's P&L in the account currency. The trading day's definition is the caller's."""

    trading_day: date
    start_equity: PositiveDecimal
    realised_pnl: FiniteDecimal
    unrealised_pnl: FiniteDecimal | None = None
    as_of: UtcDatetime
    source: InputSource


class PositionState(StellarModel):
    """An open position. ``open_risk`` is the loss at its stop, in the account currency,
    if known; it is never estimated here."""

    instrument: InstrumentId
    side: OrderSide
    volume: PositiveDecimal
    open_price: Price
    stop_loss: Price | None = None
    open_risk: FiniteDecimal | None = Field(default=None, ge=0)
    idempotency_key: Sha256Hex | None = None
    source: InputSource


class PendingOrderState(StellarModel):
    instrument: InstrumentId
    side: OrderSide
    volume: PositiveDecimal
    idempotency_key: Sha256Hex
    open_risk: FiniteDecimal | None = Field(default=None, ge=0)
    source: InputSource


class CooldownState(StellarModel):
    """An active cooldown produced elsewhere (a later phase), consumed here."""

    instrument: InstrumentId | None = None
    """None: applies to every instrument."""
    until: UtcDatetime
    reason: Label
    source: InputSource


class EventRestrictionState(StellarModel):
    """A validated, externally supplied event/news restriction for one instrument.

    No calendar or news feed exists yet; this is the hook a later phase fills.
    ``restricted`` is what the upstream validator decided; the engine does not guess.
    """

    instrument: InstrumentId
    restricted: bool
    window_start: UtcDatetime | None = None
    window_end: UtcDatetime | None = None
    event_ref: ShortText | None = None
    evaluated_at: UtcDatetime
    source: Label


class InstrumentRiskMetadata(StellarModel):
    """Broker or owner-declared figures needed for sizing. Never defaulted."""

    instrument: InstrumentId
    account_currency: CurrencyCode
    value_per_price_unit_per_lot: PositiveDecimal
    """Account-currency value of a 1.0 price move for 1 lot (tick value / tick size)."""
    lot_step: PositiveDecimal
    min_volume: PositiveDecimal
    max_volume: PositiveDecimal | None = None
    min_stop_distance: PositiveDecimal | None = None
    """Broker stops level in price units, if known."""
    source: InputSource

    @model_validator(mode="after")
    def _bounds(self) -> InstrumentRiskMetadata:
        if self.max_volume is not None and self.max_volume < self.min_volume:
            raise ValueError("max_volume cannot be below min_volume")
        return self


class ExecutionModeInput(StellarModel):
    """The execution mode as configured (PAPER / DEMO / LIVE are all representable here
    so that the rule, not only the config loader, refuses LIVE and gates DEMO)."""

    mode: Literal["PAPER", "DEMO", "LIVE"]
    demo_gate_open: Literal[False] = False
    """DEMO needs the Phase 8 gate; it cannot be opened in Phase 3."""


class RiskContext(StellarModel):
    """Everything one evaluation may use. Its canonical hash identifies the input."""

    as_of: UtcDatetime
    proposal: TradeProposal
    execution: ExecutionModeInput
    breaker: CircuitBreakerState
    account: AccountRiskState | None = None
    daily: DailyRiskState | None = None
    positions: tuple[PositionState, ...] | None = None
    pending_orders: tuple[PendingOrderState, ...] | None = None
    snapshot: VerifiedMarketSnapshot | None = None
    quote: QuoteResponse | None = None
    metadata: InstrumentRiskMetadata | None = None
    requested_volume: PositiveDecimal | None = None
    cooldowns: tuple[CooldownState, ...] | None = None
    event_restriction: EventRestrictionState | None = None
    enabled_instruments: tuple[InstrumentId, ...] = tuple(InstrumentId)
    """Instruments the station trades (from config); others are unsupported."""
    prior_idempotency_keys: tuple[Sha256Hex, ...] = ()
    """Keys of orders already created from earlier approvals (journal)."""
