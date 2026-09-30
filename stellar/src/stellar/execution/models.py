"""Paper Broker records: orders, fills, positions, trades, P&L and the account state.

Every money figure is ``Decimal``; ``None`` always means **unknown** (never zero),
and a ``PnL`` states why it is unknown. Records are immutable: a transition is a
new record, journaled in an event, never an edit of an old one.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from stellar.schemas.common import (
    CurrencyCode,
    DecisionId,
    FillId,
    FiniteDecimal,
    InstrumentId,
    IntentId,
    Label,
    NonNegativeDecimal,
    OrderId,
    OrderSide,
    PositionId,
    PositiveDecimal,
    Price,
    ProposalId,
    Provenance,
    Sha256Hex,
    ShortText,
    StellarModel,
    TradeId,
    UtcDatetime,
)
from stellar.schemas.order import OrderIntent
from stellar.serialization import sha256_hex

PAPER_EXECUTION_ID = "paper_execution"


# ------------------------------------------------------------------------ ids --


def order_id_for(intent_id: str) -> str:
    return "ord_" + sha256_hex(intent_id)[:40]


def position_id_for(order_id: str) -> str:
    return "pos_" + sha256_hex(order_id)[:40]


def trade_id_for(position_id: str) -> str:
    return "trade_" + sha256_hex(position_id)[:40]


def entry_fill_id_for(order_id: str) -> str:
    return "fill_" + sha256_hex(order_id + ":entry")[:40]


def exit_fill_id_for(position_id: str) -> str:
    return "fill_" + sha256_hex(position_id + ":exit")[:40]


# ---------------------------------------------------------------- vocabulary --


class PaperOrderStatus(StrEnum):
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    """Refused before acceptance. Does not use up the proposal's idempotency key."""
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    """Accepted and working, but its approval is no longer current: when it became
    executable, no fill-time authorisation passed. It cannot fill until a current
    authorised intent for the same terms is supplied. Never filled by default."""
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    """Accepted, then the fill was refused (for example slippage above the maximum)."""
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


WORKING_ORDER_STATUSES = frozenset({PaperOrderStatus.PENDING, PaperOrderStatus.BLOCKED})
FINAL_ORDER_STATUSES = frozenset(set(PaperOrderStatus) - WORKING_ORDER_STATUSES)

INTENT_TERMS = ("proposal_id", "account_mode", "instrument", "broker_symbol", "side", "volume",
                "order_type", "price", "stop_loss", "take_profit", "max_slippage",
                "idempotency_key")
"""The economic terms a fill-time authorisation must repeat exactly (only the intent and
decision ids, and the intent's own times, may differ)."""


class PriceSource(StrEnum):
    QUOTE = "quote"
    BAR = "bar"


class SpreadSource(StrEnum):
    QUOTE = "quote"
    """Real bid and ask from a quote."""
    BAR_SIDE = "bar_side"
    """The bar is already on the executing side; no spread applied."""
    SYNTHETIC = "synthetic_config"
    """The owner's explicit synthetic spread."""


class SlippageSource(StrEnum):
    ZERO = "zero"
    FIXED = "config_fixed"
    NOT_APPLIED = "not_applied"
    """Limit entries and take-profits fill at their level; no slippage."""


class FillKind(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class CloseReason(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    MANUAL = "MANUAL"


class PositionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AuthorisationStage(StrEnum):
    SUBMISSION = "SUBMISSION"
    FILL = "FILL"


class PnlStatus(StrEnum):
    KNOWN = "KNOWN"
    MISSING_ECONOMICS = "MISSING_ECONOMICS"
    MISSING_CONVERSION = "MISSING_CONVERSION"
    MISSING_PRICE = "MISSING_PRICE"


# ------------------------------------------------------------------ records --


class ConversionRate(StellarModel):
    """An explicit rate: 1 ``base`` = ``rate`` ``quote``. Never inverted or chained."""

    base: CurrencyCode
    quote: CurrencyCode
    rate: PositiveDecimal
    as_of: UtcDatetime
    source: ShortText

    @model_validator(mode="after")
    def _distinct(self) -> ConversionRate:
        if self.base == self.quote:
            raise ValueError("a conversion rate needs two different currencies")
        return self


class PnL(StellarModel):
    """P&L of one position. ``price_change`` (signed, in the position's favour, per
    unit) is always known; money is known only with economics (and a rate)."""

    price_change: FiniteDecimal
    status: PnlStatus
    currency: CurrencyCode
    """The account currency."""
    amount: FiniteDecimal | None = None
    instrument_currency: CurrencyCode | None = None
    instrument_amount: FiniteDecimal | None = None
    conversion: ConversionRate | None = None

    @model_validator(mode="after")
    def _known_iff_amount(self) -> PnL:
        if (self.status is PnlStatus.KNOWN) != (self.amount is not None):
            raise ValueError("amount is given exactly when the P&L is KNOWN")
        return self


class FillAuthorisation(StellarModel):
    """Proof that a fill was confirmed current by Phase 3 (``RiskService.confirm_intent``)
    at the moment it happened. Built only by the Execution Checker."""

    stage: AuthorisationStage
    intent_id: IntentId
    decision_id: DecisionId
    evaluation_fingerprint: Sha256Hex
    context_as_of: UtcDatetime
    confirmed_at: UtcDatetime

    @model_validator(mode="after")
    def _not_from_the_future(self) -> FillAuthorisation:
        if self.context_as_of > self.confirmed_at:
            raise ValueError("an authorisation cannot use a context after its confirmation")
        return self


class PaperFill(StellarModel):
    """One simulated execution with everything that priced it."""

    fill_id: FillId
    kind: FillKind
    instrument: InstrumentId
    side: OrderSide
    volume: PositiveDecimal
    price_source: PriceSource
    source_price: Price
    """The executing-side market price that triggered or priced the fill."""
    level: Price | None = None
    """The limit, stop or target level, when one applied."""
    execution_price: Price
    spread: NonNegativeDecimal | None = None
    spread_source: SpreadSource
    slippage: NonNegativeDecimal
    slippage_source: SlippageSource
    gap: bool = False
    """The market opened beyond the level; the fill uses the (worse) market price."""
    slippage_breach: bool = False
    """A protective exit slipped more than the order's ``max_slippage`` (Foundation §8.1
    "breach after fill"). The exit is still executed; the breach is recorded."""
    intrabar_ambiguous: bool = False
    intrabar_resolution: Label | None = None
    source_ts: UtcDatetime
    source: ShortText
    provider_symbol: ShortText
    as_of: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _consistent(self) -> PaperFill:
        if self.source_ts > self.as_of:
            raise ValueError("a fill cannot use a price stamped after as_of")
        if self.intrabar_ambiguous != (self.intrabar_resolution is not None):
            raise ValueError("an ambiguous fill states its resolution")
        return self


class PaperOrder(StellarModel):
    order_id: OrderId
    account_id: Label
    intent: OrderIntent
    status: PaperOrderStatus
    reason: Label | None = None
    evaluation_fingerprint: Sha256Hex | None = None
    """The Phase 3 evaluation confirmed current at submission."""
    created_at: UtcDatetime
    updated_at: UtcDatetime
    fill: PaperFill | None = None
    position_id: PositionId | None = None
    fill_authorisation: FillAuthorisation | None = None
    """The current authorisation the fill was executed under."""

    @model_validator(mode="after")
    def _consistent(self) -> PaperOrder:
        if self.order_id != order_id_for(self.intent.intent_id):
            raise ValueError("order_id must be derived from the intent id")
        filled = self.status is PaperOrderStatus.FILLED
        if filled != (self.fill is not None) or filled != (self.position_id is not None) or \
                filled != (self.fill_authorisation is not None):
            raise ValueError("a FILLED order has exactly one fill, position and authorisation")
        if self.status in {PaperOrderStatus.PREFLIGHT_FAILED, PaperOrderStatus.REJECTED,
                           PaperOrderStatus.BLOCKED} and self.reason is None:
            raise ValueError(f"a {self.status.value} order gives a reason")
        if self.status is not PaperOrderStatus.PREFLIGHT_FAILED and \
                self.evaluation_fingerprint is None:
            raise ValueError("an accepted order references its confirmed evaluation")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")
        return self


class Position(StellarModel):
    """One open (or closed) paper position. No netting: one filled order, one position."""

    position_id: PositionId
    account_id: Label
    order_id: OrderId
    intent_id: IntentId
    authorised_intent_id: IntentId
    """The intent whose fill-time authorisation opened the position."""
    proposal_id: ProposalId
    decision_id: DecisionId
    """The decision of that authorisation."""
    idempotency_key: Sha256Hex
    instrument: InstrumentId
    side: OrderSide
    volume: PositiveDecimal
    entry_price: Price
    stop_loss: Price
    take_profit: Price | None = None
    max_slippage: NonNegativeDecimal
    entry_fill_id: FillId
    entry_window_start: UtcDatetime
    entry_window_end: UtcDatetime
    """When the entry could have happened: a quote's instant, or a bar's interval."""
    opened_at: UtcDatetime
    updated_at: UtcDatetime
    mark_price: Price | None = None
    mark_ts: UtcDatetime | None = None
    unrealised: PnL | None = None
    status: PositionStatus = PositionStatus.OPEN

    @model_validator(mode="after")
    def _consistent(self) -> Position:
        if self.position_id != position_id_for(self.order_id):
            raise ValueError("position_id must be derived from the order id")
        if self.entry_window_end < self.entry_window_start:
            raise ValueError("the entry window ends before it starts")
        if (self.mark_price is None) != (self.mark_ts is None):
            raise ValueError("a mark has a price and a time")
        return self


class TradeRecord(StellarModel):
    """The settled history of one position (Foundation §11 Phase 4 settlement)."""

    trade_id: TradeId
    account_id: Label
    position_id: PositionId
    proposal_id: ProposalId
    decision_id: DecisionId
    evaluation_fingerprint: Sha256Hex
    """The evaluation confirmed current when the entry filled."""
    intent_id: IntentId
    authorised_intent_id: IntentId
    order_id: OrderId
    instrument: InstrumentId
    side: OrderSide
    volume: PositiveDecimal
    stop_loss: Price
    take_profit: Price | None = None
    entry_fill: PaperFill
    exit_fill: PaperFill
    close_reason: CloseReason
    realised: PnL
    opened_at: UtcDatetime
    closed_at: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _consistent(self) -> TradeRecord:
        if self.trade_id != trade_id_for(self.position_id):
            raise ValueError("trade_id must be derived from the position id")
        if self.entry_fill.kind is not FillKind.ENTRY or self.exit_fill.kind is not FillKind.EXIT:
            raise ValueError("a trade has one entry fill and one exit fill")
        if self.exit_fill.side is self.side:
            raise ValueError("the exit fill is on the opposite side")
        if self.closed_at < self.opened_at:
            raise ValueError("a trade cannot close before it opened")
        return self


class PaperStats(StellarModel):
    """Counts only. No performance scoring in Phase 4."""

    submitted: int
    preflight_failed: int
    accepted: int
    pending: int
    blocked: int
    filled: int
    rejected: int
    cancelled: int
    expired: int
    open_positions: int
    closed_trades: int


class PaperAccountState(StellarModel):
    """The account as reconstructed from the journal. ``None`` is unknown, never zero."""

    account_id: Label
    currency: CurrencyCode
    starting_balance: PositiveDecimal
    balance: FiniteDecimal | None
    realised_pnl: FiniteDecimal | None
    unrealised_pnl: FiniteDecimal | None
    equity: FiniteDecimal | None
    peak_equity: FiniteDecimal | None
    unsettled_trade_ids: tuple[TradeId, ...]
    """Closed trades whose money P&L is unknown; while any exist, balance is unknown."""
    unvalued_position_ids: tuple[PositionId, ...]
    """Open positions whose unrealised P&L is unknown; while any exist, equity is unknown."""
    open_positions: tuple[Position, ...]
    pending_orders: tuple[PaperOrder, ...]
    """Working orders: PENDING and BLOCKED."""
    closed_trades: tuple[TradeRecord, ...]
    open_risk: FiniteDecimal | None
    """Loss at every open stop, in the account currency, if every one is calculable."""
    version: int
    """Number of broker events applied."""
    seq: int
    """Journal sequence of the last event applied."""
    as_of: UtcDatetime | None
    config_hash: Sha256Hex
