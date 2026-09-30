"""Records of a pipeline run: steps, findings, evidence quality, synthesis, decision support.

``DecisionSupport`` is the run's output. It is descriptive decision support for a later
Trader / proposal layer. It contains no proposal, direction to trade, size, level, approval
or order, and nothing in it can instantiate one.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from stellar.reasoning.contracts import (
    DebateCaseOutput,
    MacroAssessmentOutput,
    MarketViewOutput,
    Stance,
    SynthesisOutput,
)
from stellar.reasoning.provider import FailureKind
from stellar.reasoning.structured import AgentCallRecord
from stellar.schemas.analysis import Coverage
from stellar.schemas.common import (
    InstrumentId,
    Label,
    ResearchSnapshotId,
    RunId,
    Sha256Hex,
    StellarModel,
    TechnicalId,
    UtcDatetime,
)
from stellar.schemas.market import Timeframe


class StepStatus(StrEnum):
    COMPLETED = "COMPLETED"
    REUSED = "REUSED"
    """A completed result with the exact same fingerprint was found in the journal."""
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StepRecord(StellarModel):
    role: TechnicalId
    status: StepStatus
    reason: Label | None = None
    failure: FailureKind | None = None
    fingerprint: Sha256Hex | None = None
    call: AgentCallRecord | None = None
    output_hash: Sha256Hex | None = None


class MacroAssessment(StellarModel):
    """M1 output plus deterministic driver ids (the model never names ids itself)."""

    driver_ids: tuple[str, ...]
    output: MacroAssessmentOutput
    coverage: Coverage


class MarketView(StellarModel):
    instrument: InstrumentId
    specialist: TechnicalId
    output: MarketViewOutput
    coverage: Coverage


class ChallengeKind(StrEnum):
    INTERPRETATION_AS_FACT = "INTERPRETATION_AS_FACT"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    OUT_OF_AS_OF = "OUT_OF_AS_OF"
    TECHNICAL_MACRO_DISAGREEMENT = "TECHNICAL_MACRO_DISAGREEMENT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    DUPLICATE_COUNTED = "DUPLICATE_COUNTED"
    OVERCONFIDENT_LANGUAGE = "OVERCONFIDENT_LANGUAGE"


class ChallengeFinding(StellarModel):
    finding_id: str = Field(pattern=r"^chk_[0-9a-f]{16}$")
    kind: ChallengeKind
    subject: Label
    """Which output the finding is about (a role id, or ``inputs``)."""
    evidence_ids: tuple[str, ...] = ()
    detail: Label


class ChallengeReport(StellarModel):
    findings: tuple[ChallengeFinding, ...] = ()

    def kinds(self) -> set[ChallengeKind]:
        return {f.kind for f in self.findings}


class EvidenceGrade(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    LIMITED = "LIMITED"
    ADEQUATE = "ADEQUATE"


class EvidenceQuality(StellarModel):
    """Evidence quality from the evidence itself, never from a model's self-assessment."""

    grade: EvidenceGrade
    validated_facts: int = Field(ge=0)
    partially_supported: int = Field(ge=0)
    conflicting: int = Field(ge=0)
    unverified: int = Field(ge=0)
    interpretations: int = Field(ge=0)
    independent_sources: int = Field(ge=0)
    technical_items: int = Field(ge=0)
    excluded_stale: int = Field(ge=0)
    excluded_rejected: int = Field(ge=0)
    missing_research_roles: tuple[Label, ...] = ()
    technical_limitations: tuple[Label, ...] = ()
    reasons: tuple[Label, ...] = ()


class Synthesis(StellarModel):
    output: SynthesisOutput
    model_stance: Stance
    final_stance: Stance
    guard_adjustments: tuple[Label, ...] = ()
    post_findings: tuple[ChallengeFinding, ...] = ()


class RunStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DETERMINISTIC_ONLY = "DETERMINISTIC_ONLY"


class TechnicalRef(StellarModel):
    analysis_id: str
    content_hash: Sha256Hex
    timeframe: Timeframe | None = None


class DecisionSupport(StellarModel):
    run_id: RunId
    instrument: InstrumentId
    as_of: UtcDatetime
    research_snapshot_id: ResearchSnapshotId
    technical: tuple[TechnicalRef, ...]
    evidence_pool_hash: Sha256Hex
    workflow_config_hash: Sha256Hex
    prompt_registry_hash: Sha256Hex
    steps: tuple[StepRecord, ...]
    macro: MacroAssessment | None = None
    market_view: MarketView | None = None
    bull_cases: tuple[DebateCaseOutput, ...] = ()
    bear_cases: tuple[DebateCaseOutput, ...] = ()
    challenge: ChallengeReport
    quality: EvidenceQuality
    synthesis: Synthesis | None = None
    final_stance: Stance
    status: RunStatus
    limitations: tuple[Label, ...] = ()
    outputs_hash: Sha256Hex
    """Hash of the analytical outputs only (unchanged when a run is resumed from checkpoints)."""
