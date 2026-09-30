"""Research chain R → V (Foundation Phase 6a): sources, collection results, validation V1–V4,
cross-source corroboration and research snapshots. Deterministic; no model output is ever
turned into a validated fact here."""

from stellar.research.collect import (
    CollectionResult,
    CollectionStatus,
    ResearchCollector,
    StaticCollector,
)
from stellar.research.corroboration import ClaimAssessment, EvidenceStatus, assess_claims, root_of
from stellar.research.snapshot import ResearchSnapshot, build_snapshot, publish_snapshot
from stellar.research.sources import (
    ROLE_SOURCE_TYPES,
    SourceAllowlist,
    SourceRecord,
    SourceTier,
    SourceType,
)
from stellar.research.validation import (
    CalendarValue,
    ValidationConfig,
    item_checks,
    validate_claims,
)

__all__ = [
    "ROLE_SOURCE_TYPES",
    "CalendarValue",
    "ClaimAssessment",
    "CollectionResult",
    "CollectionStatus",
    "EvidenceStatus",
    "ResearchCollector",
    "ResearchSnapshot",
    "SourceAllowlist",
    "SourceRecord",
    "SourceTier",
    "SourceType",
    "StaticCollector",
    "ValidationConfig",
    "assess_claims",
    "build_snapshot",
    "item_checks",
    "publish_snapshot",
    "root_of",
    "validate_claims",
]
