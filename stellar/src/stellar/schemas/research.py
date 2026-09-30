"""Research contracts (Foundation §4.29).

``ResearchItem`` is the collector output of §4.29.1 (the "research finding").
``ClaimValidation`` records the V1–V4 verdict on one claim of one item
(§4.29.2): an accepted claim with label FACT is what later stages treat as a
validated fact. Collectors and validators themselves are later phases.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    ClaimId,
    ClaimValidationId,
    FiniteDecimal,
    Label,
    Provenance,
    ResearchItemId,
    ResearchSnapshotId,
    SchemaVersion,
    Sha256Hex,
    ShortText,
    StellarModel,
    TechnicalId,
    UnitInterval,
    UtcDatetime,
)


class ResearchRole(StrEnum):
    """Research collector roles R1–R6; values are the roles' technical ids."""

    CENTRAL_BANK = "research_central_bank"
    ECONOMIC_DATA = "research_economic_data"
    MARKET_NEWS = "research_market_news"
    GEOPOLITICAL = "research_geopolitical"
    RATES_BONDS = "research_rates_bonds"
    CORPORATE_EARNINGS = "research_corporate_earnings"


class Claim(StellarModel):
    """One statement extracted from a research item."""

    claim_id: ClaimId
    statement: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    value: FiniteDecimal | None = None
    unit: ShortText | None = None
    period: ShortText | None = None
    subject: Label | None = None
    """Phase 6 (additive): what the claim is about (e.g. ``us_cpi_yoy``), so independent
    sources on the same subject and period can be compared. None: not comparable."""


_AFFECTED = r"^(?:[A-Z]{3}|XAUUSD|EURUSD|USDJPY|NAS100)$"


class ResearchItem(StellarModel):
    """A collected research item (Foundation §4.29.1 ``ResearchItem`` fields)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    item_id: ResearchItemId
    role: ResearchRole
    source_id: Label
    source_ref: ShortText
    published_at: UtcDatetime
    retrieved_at: UtcDatetime
    affected: tuple[Annotated[str, StringConstraints(pattern=_AFFECTED)], ...] = Field(
        min_length=1
    )
    excerpt: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    content_hash: Sha256Hex
    claims: tuple[Claim, ...] = ()
    # Phase 6 additions (optional, so earlier records stay valid):
    topic: Label | None = None
    derived_from: tuple[ResearchItemId, ...] = ()
    """Items this one repeats or syndicates. A derived item is never an independent source."""
    revision_of: ResearchItemId | None = None
    """A later revision of an earlier item (vintage). Both stay in the store."""

    @model_validator(mode="after")
    def _times_and_claims(self) -> ResearchItem:
        if self.retrieved_at < self.published_at:
            raise ValueError("retrieved_at cannot be before published_at")
        ids = [c.claim_id for c in self.claims]
        if len(set(ids)) != len(ids):
            raise ValueError("claim ids must be unique within an item")
        if self.item_id in self.derived_from or self.revision_of == self.item_id:
            raise ValueError("an item cannot derive from or revise itself")
        return self


ResearchFinding = ResearchItem
"""Alias: the project brief's "ResearchFinding" is the documented ``ResearchItem``."""


class ClaimLabel(StrEnum):
    """V4 classification (Foundation §4.29.2)."""

    FACT = "FACT"
    REACTION = "REACTION"
    INTERPRETATION = "INTERPRETATION"


class CheckOutcome(StrEnum):
    """Outcome of one validator on one item or claim (Foundation §4.29.2)."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STALE = "stale"
    FUTURE = "future"
    DUPLICATE = "duplicate"


class ValidationCheck(StellarModel):
    validator: TechnicalId
    outcome: CheckOutcome
    reason: Label | None = None

    @model_validator(mode="after")
    def _reason_when_not_accepted(self) -> ValidationCheck:
        if self.outcome is not CheckOutcome.ACCEPTED and self.reason is None:
            raise ValueError("a check that does not accept must give a reason")
        return self


class ValidationStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ClaimValidation(StellarModel):
    """The validators' verdict on one claim.

    ACCEPTED requires every check to accept. Only accepted, labelled claims
    reach analysis (Foundation §4.29.2).
    """

    schema_version: SchemaVersion = SCHEMA_VERSION
    validation_id: ClaimValidationId
    item_id: ResearchItemId
    claim_id: ClaimId
    label: ClaimLabel | None = None
    label_confidence: UnitInterval | None = None
    checks: tuple[ValidationCheck, ...] = Field(min_length=1)
    status: ValidationStatus
    research_snapshot_id: ResearchSnapshotId | None = None
    validated_at: UtcDatetime
    provenance: Provenance

    @field_validator("checks")
    @classmethod
    def _one_check_per_validator(
        cls, value: tuple[ValidationCheck, ...]
    ) -> tuple[ValidationCheck, ...]:
        names = [c.validator for c in value]
        if len(set(names)) != len(names):
            raise ValueError("at most one check per validator")
        return value

    @model_validator(mode="after")
    def _status_matches_checks(self) -> ClaimValidation:
        all_accept = all(c.outcome is CheckOutcome.ACCEPTED for c in self.checks)
        if self.status is ValidationStatus.ACCEPTED:
            if not all_accept:
                raise ValueError("ACCEPTED requires every check to accept")
            if self.label is None:
                raise ValueError("an accepted claim must carry a label")
        elif all_accept:
            raise ValueError("REJECTED requires at least one check that does not accept")
        return self

    @property
    def is_validated_fact(self) -> bool:
        return self.status is ValidationStatus.ACCEPTED and self.label is ClaimLabel.FACT


ValidatedFact = ClaimValidation
"""Alias: the project brief's "ValidatedFact"; see ``ClaimValidation.is_validated_fact``."""

__all__ = [
    "Claim",
    "ClaimLabel",
    "ClaimValidation",
    "CheckOutcome",
    "ResearchFinding",
    "ResearchItem",
    "ResearchRole",
    "ValidatedFact",
    "ValidationCheck",
    "ValidationStatus",
]
