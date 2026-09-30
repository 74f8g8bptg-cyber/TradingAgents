"""Structured ``TradeProposal`` (Foundation §4.13).

Setup-first (R-1): the direction comes from the deterministic Setup; the
Portfolio Manager's rating is the approval strength for that Setup. Only a Buy
or Overweight rating produces a proposal (Foundation §8.2 rule 4); Hold,
Underweight, Sell and REVIEW never do.

Every execution value is typed: entry, stop-loss and take-profits are
``Decimal`` prices on the correct side of each other. The Trader's levels are
kept only as advisory values. This module validates structure, not risk policy:
minimum reward:risk, stop distance and sizing are Risk Engine rules (Phase 3).

Reward:risk is **not** computed or checked here. How it is measured (which
target, which entry price for a zone) is a trading-methodology decision that
has not been made; until it is, ``reward_risk`` is only a typed, provisional
value stated by the builder, and no rule may rely on it.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    Direction,
    InstrumentId,
    Label,
    Price,
    ProfileId,
    ProposalId,
    Provenance,
    RunId,
    SchemaVersion,
    SetupId,
    Sha256Hex,
    ShortText,
    SnapshotId,
    StellarModel,
    UtcDatetime,
    strict_number,
)


class Rating(StrEnum):
    """The Portfolio Manager's typed rating; values equal upstream's strings."""

    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"
    REVIEW = "REVIEW"


PROPOSAL_RATINGS = frozenset({Rating.BUY, Rating.OVERWEIGHT})
"""Ratings that may produce a proposal. All others mean no proposal (R-1)."""


class EntryType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class EntrySpec(StellarModel):
    """Entry: a single price or a zone, never both (Foundation §4.13)."""

    type: EntryType
    price: Price | None = None
    zone_low: Price | None = None
    zone_high: Price | None = None

    @model_validator(mode="after")
    def _price_or_zone(self) -> EntrySpec:
        has_zone = self.zone_low is not None or self.zone_high is not None
        if self.price is not None and has_zone:
            raise ValueError("entry has either a price or a zone, not both")
        if self.price is None and not has_zone:
            raise ValueError("entry needs a price or a zone")
        if has_zone:
            if self.zone_low is None or self.zone_high is None:
                raise ValueError("a zone needs both zone_low and zone_high")
            if self.zone_low >= self.zone_high:
                raise ValueError("zone_low must be below zone_high")
        return self

    def bounds(self) -> tuple[Decimal, Decimal]:
        """Lowest and highest entry price (equal for a single price)."""
        if self.price is not None:
            return self.price, self.price
        assert self.zone_low is not None and self.zone_high is not None
        return self.zone_low, self.zone_high


class PriceLevel(StellarModel):
    """A stop or target price with the label of the rule that produced it."""

    price: Price
    basis: Label


class AdvisoryLevels(StellarModel):
    """Levels parsed from the upstream Trader's text. Advisory only, never used for orders."""

    entry: Price | None = None
    stop: Price | None = None


class Contradiction(StellarModel):
    code: Label
    detail: ShortText | None = None


SizeFactor = Annotated[
    Decimal, BeforeValidator(strict_number), Field(gt=0, le=1, allow_inf_nan=False)
]


class TradeProposal(StellarModel):
    """A typed proposal built by the Trade Proposal Builder (P1)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    proposal_id: ProposalId
    run_id: RunId
    snapshot_id: SnapshotId
    setup_id: SetupId
    instrument: InstrumentId
    profile: ProfileId
    direction: Direction
    source_rating: Rating
    size_factor: SizeFactor
    entry: EntrySpec
    stop_loss: PriceLevel
    take_profits: tuple[PriceLevel, ...] = Field(min_length=1)
    reward_risk: Annotated[
        Decimal, BeforeValidator(strict_number), Field(gt=0, allow_inf_nan=False)
    ] | None = Field(
        default=None,
        description=(
            "PROVISIONAL, non-canonical: as stated by the builder; not recomputed or "
            "checked, because the measurement method is not decided. No rule may use it."
        ),
    )
    valid_until: UtcDatetime
    llm_levels_advisory: AdvisoryLevels | None = None
    contradictions: tuple[Contradiction, ...] = ()
    report_hashes: tuple[Sha256Hex, ...] = ()
    created_at: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _rating_levels_and_times(self) -> TradeProposal:
        if self.source_rating not in PROPOSAL_RATINGS:
            raise ValueError(
                f"rating {self.source_rating.value} never produces a proposal (R-1)"
            )
        if self.source_rating is Rating.BUY and self.size_factor != 1:
            raise ValueError("a Buy rating takes the setup at size factor 1")
        if self.provenance.produced_by != "trade_proposal_builder":
            raise ValueError("proposals are built only by trade_proposal_builder (P1)")
        stop = self.stop_loss.price
        long = self.direction is Direction.LONG
        low_edge, high_edge = self.entry.bounds()
        if long and not stop < low_edge:
            raise ValueError("a LONG stop-loss must be below the entry")
        if not long and not stop > high_edge:
            raise ValueError("a SHORT stop-loss must be above the entry")
        targets = [tp.price for tp in self.take_profits]
        for target in targets:
            if long and not target > high_edge:
                raise ValueError("a LONG take-profit must be above the entry")
            if not long and not target < low_edge:
                raise ValueError("a SHORT take-profit must be below the entry")
        ordered = sorted(targets) if long else sorted(targets, reverse=True)
        if targets != ordered or len(set(targets)) != len(targets):
            raise ValueError("take-profits must be distinct and ordered nearest first")
        if self.valid_until <= self.created_at:
            raise ValueError("valid_until must be after created_at")
        return self
