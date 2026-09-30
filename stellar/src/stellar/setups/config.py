"""Setup and proposal-level configuration. Every threshold is UNSET by default.

No canonical document approves a setup threshold, a validity window, a stop buffer, an ATR
multiple, a minimum reward:risk or a timeframe profile (Foundation D-7, D-12; Phase 5 P5-12).
So:
- a value left ``None`` (or an empty tuple) is **UNSET**, and the step that needs it is not
  performed. It is reported, never replaced by a guess;
- UNSET never loosens a rule. It keeps a setup at CANDIDATE or refuses a proposal:
  - no ``setup_validity_bars``: the setup has no expiry, so it never becomes
    READY_FOR_PROPOSAL (a proposal needs ``valid_until``);
  - no ``ready_evidence_grades``: READY_FOR_PROPOSAL is not reachable;
  - no ``entry_models``: there is no entry option;
  - no ``profile``: the builder refuses (``TradeProposal.profile`` is required).
- ``stop_buffer`` UNSET means *no buffer*: the stop sits exactly on the evidence level, and its
  basis says so (``no_buffer``). No percent or pip distance is ever assumed.

Tests use labelled synthetic configurations (``test_only``); none of their values is a
default or a recommendation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stellar.pipeline.records import EvidenceGrade
from stellar.schemas.common import (
    Label,
    NonNegativeDecimal,
    PositiveDecimal,
    ProfileId,
    StellarModel,
    UnitInterval,
)
from stellar.serialization import content_hash


class EntryModelKind(StrEnum):
    """How an entry is expressed. The order type follows from the kind, never from text."""

    MARKET_AT_QUOTE = "MARKET_AT_QUOTE"
    """Order type ``market``. The entry reference is the current quote at build time (ask for
    LONG, bid for SHORT); no quote means no entry."""
    LIMIT_AT_ZONE = "LIMIT_AT_ZONE"
    """Order type ``limit``. The entry is a Phase 5 price zone, kept as a zone (never collapsed
    to a midpoint); a zone of zero width is a single limit price."""


ORDER_TYPE_FOR_ENTRY: dict[EntryModelKind, str] = {
    EntryModelKind.MARKET_AT_QUOTE: "market",
    EntryModelKind.LIMIT_AT_ZONE: "limit",
}


class StopBuffer(StellarModel):
    """Distance beyond an evidence level: in price units or as an ATR multiple (at most one)."""

    price: NonNegativeDecimal | None = None
    atr_multiple: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def _one(self) -> StopBuffer:
        if self.price is not None and self.atr_multiple is not None:
            raise ValueError("give the buffer in price units or as an ATR multiple, not both")
        return self

    @property
    def configured(self) -> bool:
        return self.price is not None or self.atr_multiple is not None


class SetupConfig(StellarModel):
    version: Label = "unset"
    test_only: bool = False
    setup_validity_bars: int | None = Field(default=None, ge=1, le=100_000)
    """Setup / proposal validity in bars of the setup timeframe, counted from the moment the
    reference leg became known (Foundation §7.1 ``setup_validity``). UNSET: no expiry is
    claimed, so the setup cannot become READY_FOR_PROPOSAL."""
    ready_evidence_grades: tuple[EvidenceGrade, ...] = ()
    """Phase 6 evidence grades that may reach READY_FOR_PROPOSAL. UNSET: none may."""
    min_retracement_ratio: UnitInterval | None = None
    """Optional: the pullback must have retraced at least this fraction of the leg."""
    max_retracement_ratio: UnitInterval | None = None
    """Optional: the pullback must not have retraced more than this fraction of the leg."""
    entry_models: tuple[EntryModelKind, ...] = ()
    stop_buffer: StopBuffer = StopBuffer()
    atr_stop_multiple: PositiveDecimal | None = None
    """Optional ATR stop (distance = multiple × Phase 5 ATR). UNSET: no ATR stop option."""
    profile: ProfileId | None = None
    """The timeframe profile a proposal is filed under (D-7 undecided). UNSET: no proposal."""

    @model_validator(mode="after")
    def _consistent(self) -> SetupConfig:
        if self.min_retracement_ratio is not None and self.max_retracement_ratio is not None \
                and self.min_retracement_ratio > self.max_retracement_ratio:
            raise ValueError("min_retracement_ratio cannot exceed max_retracement_ratio")
        if len(set(self.entry_models)) != len(self.entry_models):
            raise ValueError("entry models must not repeat")
        if len(set(self.ready_evidence_grades)) != len(self.ready_evidence_grades):
            raise ValueError("evidence grades must not repeat")
        return self

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
