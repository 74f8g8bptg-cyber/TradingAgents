"""``OrderIntent`` (Foundation §4.14): built only by the Risk Engine from an APPROVED decision.

The intent carries every value an execution needs, typed, including its risk
metadata: a stop-loss is mandatory and ``max_slippage`` cannot be omitted. The
account mode is PAPER or DEMO only; LIVE cannot be expressed on an order.
Cross-checks against the proposal and decision are in ``stellar.validation``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    DecisionId,
    InstrumentId,
    IntentId,
    NonNegativeDecimal,
    OrderSide,
    PositiveDecimal,
    Price,
    ProposalId,
    Provenance,
    SchemaVersion,
    Sha256Hex,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.risk import RISK_ENGINE_ID
from stellar.serialization import sha256_hex


class AccountMode(StrEnum):
    PAPER = "PAPER"
    DEMO = "DEMO"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


def idempotency_key_for(proposal_id: str) -> str:
    """Idempotency key = hash(proposal_id) (Foundation §8.1, duplicate order prevention)."""
    return sha256_hex(proposal_id)


class OrderIntent(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    intent_id: IntentId
    proposal_id: ProposalId
    decision_id: DecisionId
    account_mode: AccountMode
    instrument: InstrumentId
    broker_symbol: ShortText
    side: OrderSide
    volume: PositiveDecimal
    order_type: OrderType
    price: Price | None = None
    stop_loss: Price
    take_profit: Price | None = None
    max_slippage: NonNegativeDecimal
    idempotency_key: Sha256Hex
    expires_at: UtcDatetime
    created_at: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _structure(self) -> OrderIntent:
        if self.provenance.produced_by != RISK_ENGINE_ID:
            raise ValueError("order intents are built only by risk_engine (P3)")
        if self.idempotency_key != idempotency_key_for(self.proposal_id):
            raise ValueError("idempotency_key must be the hash of proposal_id")
        if self.order_type is OrderType.LIMIT and self.price is None:
            raise ValueError("a limit order needs a price")
        buy = self.side is OrderSide.BUY
        reference = self.price
        if reference is not None:
            if buy and not self.stop_loss < reference:
                raise ValueError("a BUY stop-loss must be below the price")
            if not buy and not self.stop_loss > reference:
                raise ValueError("a SELL stop-loss must be above the price")
        if self.take_profit is not None:
            anchor = reference if reference is not None else self.stop_loss
            if buy and not self.take_profit > anchor:
                raise ValueError("a BUY take-profit must be above the price and stop")
            if not buy and not self.take_profit < anchor:
                raise ValueError("a SELL take-profit must be below the price and stop")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self
