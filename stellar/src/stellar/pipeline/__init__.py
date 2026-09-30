"""The Phase 6 research / debate pipeline: deterministic orchestration of the research chain,
LLM analysts and debate, producing typed decision support. No proposal, risk or execution."""

from stellar.pipeline.challenger import challenge, check_output, technical_direction
from stellar.pipeline.config import (
    DETERMINISTIC_ROLES,
    LLM_ROLES,
    SPECIALISTS,
    LlmBudget,
    WorkflowConfig,
)
from stellar.pipeline.evidence import (
    RELEVANCE,
    EvidenceItem,
    EvidenceKind,
    EvidencePool,
    TechnicalAfterAsOf,
    build_pool,
)
from stellar.pipeline.orchestrator import PipelineInputs, ResearchPipeline
from stellar.pipeline.quality import evidence_quality, guard_stance
from stellar.pipeline.records import (
    ChallengeFinding,
    ChallengeKind,
    ChallengeReport,
    DecisionSupport,
    EvidenceGrade,
    EvidenceQuality,
    MacroAssessment,
    MarketView,
    RunStatus,
    StepRecord,
    StepStatus,
    Synthesis,
)

__all__ = [
    "DETERMINISTIC_ROLES",
    "LLM_ROLES",
    "RELEVANCE",
    "SPECIALISTS",
    "ChallengeFinding",
    "ChallengeKind",
    "ChallengeReport",
    "DecisionSupport",
    "EvidenceGrade",
    "EvidenceItem",
    "EvidenceKind",
    "EvidencePool",
    "EvidenceQuality",
    "LlmBudget",
    "MacroAssessment",
    "MarketView",
    "PipelineInputs",
    "ResearchPipeline",
    "RunStatus",
    "StepRecord",
    "StepStatus",
    "Synthesis",
    "TechnicalAfterAsOf",
    "WorkflowConfig",
    "build_pool",
    "challenge",
    "check_output",
    "evidence_quality",
    "guard_stance",
    "technical_direction",
]
