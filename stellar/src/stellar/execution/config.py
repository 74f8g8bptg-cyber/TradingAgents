"""Paper Broker configuration (Foundation §4.15, D-8).

Nothing here has a market default:
- **Account (D-8).** ``account_currency`` and ``starting_balance`` are required; the
  broker cannot be built without them.
- **Spread.** ``QUOTE_ONLY`` uses only real bid/ask from quotes (and the native
  side of a bar); ``SYNTHETIC_FIXED`` adds an owner-given spread per instrument,
  labelled synthetic on every fill. There is no spread per market built in.
- **Slippage.** ``ZERO`` or ``FIXED`` per instrument, always adverse, never random.
  The owner chooses one explicitly; there is no default.
- **Economics.** Money P&L needs an owner-declared value of a 1.0 price move per
  lot and its currency; without it, P&L stays unknown.
- **Intrabar policy.** ``STOP_FIRST``: when one bar reaches both the stop and the
  target, the stop is taken (Foundation §4.15, the conservative assumption).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stellar.schemas.common import (
    CurrencyCode,
    InstrumentId,
    Label,
    NonNegativeDecimal,
    PositiveDecimal,
    StellarModel,
)
from stellar.serialization import content_hash


class SpreadMode(StrEnum):
    QUOTE_ONLY = "QUOTE_ONLY"
    SYNTHETIC_FIXED = "SYNTHETIC_FIXED"


class SpreadModel(StellarModel):
    mode: SpreadMode
    synthetic: dict[InstrumentId, NonNegativeDecimal] = Field(default_factory=dict)
    """Owner-given synthetic spread in price units (SYNTHETIC_FIXED only)."""

    @model_validator(mode="after")
    def _consistent(self) -> SpreadModel:
        if self.mode is SpreadMode.QUOTE_ONLY and self.synthetic:
            raise ValueError("QUOTE_ONLY takes no synthetic spreads")
        if self.mode is SpreadMode.SYNTHETIC_FIXED and not self.synthetic:
            raise ValueError("SYNTHETIC_FIXED needs at least one explicit spread")
        return self


class SlippageMode(StrEnum):
    ZERO = "ZERO"
    FIXED = "FIXED"


class SlippageModel(StellarModel):
    mode: SlippageMode
    fixed: dict[InstrumentId, NonNegativeDecimal] = Field(default_factory=dict)
    """Adverse slippage in price units per instrument (FIXED only)."""

    @model_validator(mode="after")
    def _consistent(self) -> SlippageModel:
        if self.mode is SlippageMode.ZERO and self.fixed:
            raise ValueError("ZERO takes no fixed slippage values")
        if self.mode is SlippageMode.FIXED and not self.fixed:
            raise ValueError("FIXED needs at least one explicit slippage value")
        return self


class IntrabarPolicy(StrEnum):
    STOP_FIRST = "STOP_FIRST"


class InstrumentEconomics(StellarModel):
    """Owner-declared money value of price moves. Never defaulted."""

    instrument: InstrumentId
    pnl_currency: CurrencyCode
    """The currency the instrument's P&L is produced in."""
    value_per_price_unit_per_lot: PositiveDecimal
    """Value in ``pnl_currency`` of a 1.0 price move for 1 lot."""
    source: Label


class PaperBrokerConfig(StellarModel):
    account_id: Label
    account_currency: CurrencyCode
    starting_balance: PositiveDecimal
    spread: SpreadModel
    slippage: SlippageModel
    intrabar_policy: IntrabarPolicy = IntrabarPolicy.STOP_FIRST
    economics: tuple[InstrumentEconomics, ...] = ()
    max_quote_age_seconds: int | None = Field(default=None, ge=1)
    """Optional: refuse fills from quotes older than this. None: not checked (P4-3)."""

    @model_validator(mode="after")
    def _unique_economics(self) -> PaperBrokerConfig:
        instruments = [e.instrument for e in self.economics]
        if len(set(instruments)) != len(instruments):
            raise ValueError("economics may be given once per instrument")
        return self

    def economics_for(self, instrument: InstrumentId) -> InstrumentEconomics | None:
        return next((e for e in self.economics if e.instrument is instrument), None)

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
