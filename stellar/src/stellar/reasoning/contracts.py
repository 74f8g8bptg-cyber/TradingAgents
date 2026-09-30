"""Typed LLM output schemas (structured output only; Foundation §4.29.3–4.29.4).

Every output:
- is closed (unknown fields are rejected);
- cites evidence only by id. ``cited_evidence_ids()`` lists every id it uses, so the caller
  can refuse ids that were not offered;
- keeps FACT / REACTION / INTERPRETATION apart through an explicit ``basis`` on each
  statement;
- reports model confidence only as ``self_reported_confidence``, which is metadata, never
  evidence quality.

**Stances are descriptive:** SUPPORTS_UPSIDE, SUPPORTS_DOWNSIDE, MIXED, NEUTRAL,
INSUFFICIENT_EVIDENCE. None is a buy or sell decision. There is no field for an order,
size, entry, stop, target or approval.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from stellar.schemas.common import ClaimId, InstrumentId, StellarModel
from stellar.schemas.research import ClaimLabel

EvidenceRef = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,6}_[A-Za-z0-9_.\-]{1,128}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=1000)]
Refs = Annotated[tuple[EvidenceRef, ...], Field(max_length=64)]


class Stance(StrEnum):
    SUPPORTS_UPSIDE = "SUPPORTS_UPSIDE"
    SUPPORTS_DOWNSIDE = "SUPPORTS_DOWNSIDE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Basis(StrEnum):
    FACT = "FACT"
    REACTION = "REACTION"
    INTERPRETATION = "INTERPRETATION"
    TECHNICAL = "TECHNICAL"
    """Deterministic Phase 5 evidence, read as given."""


class ModelConfidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


def _unique(refs) -> None:
    if len(set(refs)) != len(refs):
        raise ValueError("evidence ids must not repeat")


# ------------------------------------------------------------------ V4 claim labels --


class ClaimLabelOutput(StellarModel):
    claim_id: ClaimId
    label: ClaimLabel
    rationale: Text


class ClaimLabelling(StellarModel):
    labels: tuple[ClaimLabelOutput, ...]

    def cited_evidence_ids(self) -> set[str]:
        return {x.claim_id for x in self.labels}


# ------------------------------------------------------------------------ M1 macro --


class DriverKind(StrEnum):
    RATES_YIELDS = "RATES_YIELDS"
    INFLATION = "INFLATION"
    EMPLOYMENT = "EMPLOYMENT"
    GROWTH = "GROWTH"
    LIQUIDITY = "LIQUIDITY"
    CENTRAL_BANK_POLICY = "CENTRAL_BANK_POLICY"
    CURRENCY_STRENGTH = "CURRENCY_STRENGTH"
    RISK_SENTIMENT = "RISK_SENTIMENT"
    GEOPOLITICS = "GEOPOLITICS"
    EARNINGS_GUIDANCE = "EARNINGS_GUIDANCE"


class ObservedChange(StrEnum):
    RISING = "RISING"
    FALLING = "FALLING"
    UNCHANGED = "UNCHANGED"
    UNCLEAR = "UNCLEAR"


class MacroDriverOutput(StellarModel):
    driver: DriverKind
    observed_change: ObservedChange
    affected: tuple[InstrumentId, ...] = Field(min_length=1)
    evidence_ids: Refs = Field(min_length=1)
    basis: Basis
    """What the observed change rests on: FACT, REACTION or INTERPRETATION evidence."""
    mechanism_hypothesis: Text
    """A causal *hypothesis*, never presented as a fact."""
    alternative_explanations: tuple[Text, ...] = ()
    uncertainties: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _refs(self) -> MacroDriverOutput:
        _unique(self.evidence_ids)
        return self


class MacroAssessmentOutput(StellarModel):
    drivers: tuple[MacroDriverOutput, ...]
    regime_description: Text
    event_risks: tuple[Text, ...] = ()
    uncertainties: tuple[Text, ...] = ()
    self_reported_confidence: ModelConfidence | None = None

    def cited_evidence_ids(self) -> set[str]:
        return {e for d in self.drivers for e in d.evidence_ids}


# ------------------------------------------------------------------- S1–S4 market view --


class ReasoningStep(StellarModel):
    statement: Text
    basis: Basis
    evidence_ids: Refs = Field(min_length=1)


class MarketViewOutput(StellarModel):
    instrument: InstrumentId
    stance: Stance
    reasoning: tuple[ReasoningStep, ...]
    supporting_evidence_ids: Refs = ()
    contradicting_evidence_ids: Refs = ()
    technical_evidence_ids: Refs = ()
    macro_driver_ids: Refs = ()
    event_risks: tuple[Text, ...] = ()
    invalidation_conditions: tuple[Text, ...] = ()
    missing_information: tuple[Text, ...] = ()
    self_reported_confidence: ModelConfidence | None = None

    @model_validator(mode="after")
    def _consistent(self) -> MarketViewOutput:
        if self.stance not in (Stance.INSUFFICIENT_EVIDENCE, Stance.NEUTRAL) and \
                not self.reasoning:
            raise ValueError("a directional or mixed stance must show its reasoning")
        if set(self.supporting_evidence_ids) & set(self.contradicting_evidence_ids):
            raise ValueError("evidence cannot both support and contradict the view")
        return self

    def cited_evidence_ids(self) -> set[str]:
        return ({e for s in self.reasoning for e in s.evidence_ids}
                | set(self.supporting_evidence_ids) | set(self.contradicting_evidence_ids)
                | set(self.technical_evidence_ids) | set(self.macro_driver_ids))


# ------------------------------------------------------------------------ U1/U2 debate --


class DebateSide(StrEnum):
    BULL = "BULL"
    BEAR = "BEAR"


class Argument(StellarModel):
    point: Text
    basis: Basis
    evidence_ids: Refs = Field(min_length=1)


class Rebuttal(StellarModel):
    rebutted_evidence_ids: Refs = Field(min_length=1)
    response: Text
    evidence_ids: Refs = ()


class DebateCaseOutput(StellarModel):
    side: DebateSide
    arguments: tuple[Argument, ...] = Field(min_length=1)
    own_weaknesses: tuple[Text, ...] = Field(min_length=1)
    """A case must name its own weaknesses."""
    rebuttals: tuple[Rebuttal, ...] = ()
    self_reported_confidence: ModelConfidence | None = None

    def cited_evidence_ids(self) -> set[str]:
        return ({e for a in self.arguments for e in a.evidence_ids}
                | {e for r in self.rebuttals for e in (*r.rebutted_evidence_ids, *r.evidence_ids)})


# --------------------------------------------------------------------- U3 synthesis --


class SynthesisOutput(StellarModel):
    summary: Text
    stance: Stance
    upside_evidence_ids: Refs = ()
    downside_evidence_ids: Refs = ()
    unresolved_contradictions: tuple[Text, ...] = ()
    missing_information: tuple[Text, ...] = ()
    self_reported_confidence: ModelConfidence | None = None

    def cited_evidence_ids(self) -> set[str]:
        return set(self.upside_evidence_ids) | set(self.downside_evidence_ids)


SCHEMAS: dict[str, type[StellarModel]] = {
    "claim_labelling": ClaimLabelling,
    "macro_assessment": MacroAssessmentOutput,
    "market_view": MarketViewOutput,
    "debate_case": DebateCaseOutput,
    "synthesis": SynthesisOutput,
}
