"""Analysis contract: the common record of every analysis output.

One ``AnalysisReport`` is written per output of M1, S1–S4 and T2–T8, matching
the ``analysis.created`` event (Foundation §10.1; layer design §4.3). It links
the output to its inputs, states research coverage, and keeps any narrative as a
bounded excerpt plus a hash. It carries **no** entry, stop, target or size:
those exist only in typed proposals and orders.

The kind-specific typed bodies (``MacroAssessment``, ``MarketAssessment``,
``StructureAssessment``, …) are defined with their producers in Phases 5–6.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import StringConstraints, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    AnalysisId,
    ClaimId,
    InstrumentId,
    Provenance,
    ResearchSnapshotId,
    RunId,
    SchemaVersion,
    Sha256Hex,
    SnapshotId,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.research import ResearchRole


class AnalysisKind(StrEnum):
    MACRO = "macro"
    MARKET = "market"
    STRUCTURE = "structure"
    MOMENTUM = "momentum"
    PRICE_ACTION = "price_action"
    SESSION = "session"
    REPORT = "report"


_NEEDS_INSTRUMENT = {
    AnalysisKind.MARKET,
    AnalysisKind.STRUCTURE,
    AnalysisKind.MOMENTUM,
    AnalysisKind.PRICE_ACTION,
    AnalysisKind.SESSION,
    AnalysisKind.REPORT,
}
_NEEDS_COVERAGE = {AnalysisKind.MACRO, AnalysisKind.MARKET}
_NEEDS_MARKET_SNAPSHOT = {
    AnalysisKind.STRUCTURE,
    AnalysisKind.MOMENTUM,
    AnalysisKind.PRICE_ACTION,
    AnalysisKind.REPORT,
}


class Coverage(StellarModel):
    """Which research roles contributed and which were missing (Foundation §4.29.5)."""

    contributed: tuple[ResearchRole, ...] = ()
    missing: tuple[ResearchRole, ...] = ()

    @model_validator(mode="after")
    def _disjoint(self) -> Coverage:
        if set(self.contributed) & set(self.missing):
            raise ValueError("a role cannot both contribute and be missing")
        if len(set(self.contributed)) != len(self.contributed) or len(set(self.missing)) != len(
            self.missing
        ):
            raise ValueError("coverage roles must be unique")
        return self


class AnalysisReport(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    analysis_id: AnalysisId
    kind: AnalysisKind
    run_id: RunId | None = None
    instrument: InstrumentId | None = None
    snapshot_id: SnapshotId | None = None
    research_snapshot_id: ResearchSnapshotId | None = None
    as_of: UtcDatetime
    created_at: UtcDatetime
    coverage: Coverage | None = None
    cited_claim_ids: tuple[ClaimId, ...] = ()
    excerpt: Annotated[str, StringConstraints(max_length=2000)] | None = None
    chars: int | None = None
    sha256: Sha256Hex | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def _links_for_kind(self) -> AnalysisReport:
        if self.kind in _NEEDS_INSTRUMENT and self.instrument is None:
            raise ValueError(f"a {self.kind} analysis must name its instrument")
        if self.kind in _NEEDS_COVERAGE and self.coverage is None:
            raise ValueError(f"a {self.kind} analysis must state its research coverage")
        if self.kind in _NEEDS_MARKET_SNAPSHOT and self.snapshot_id is None:
            raise ValueError(f"a {self.kind} analysis must reference its market snapshot")
        if self.kind in _NEEDS_COVERAGE and self.research_snapshot_id is None:
            raise ValueError(f"a {self.kind} analysis must reference its research snapshot")
        if self.created_at < self.as_of:
            raise ValueError("created_at cannot be before as_of")
        if (self.excerpt is None) != (self.sha256 is None) or (self.sha256 is None) != (
            self.chars is None
        ):
            raise ValueError("excerpt, chars and sha256 are given together or not at all")
        if self.chars is not None and self.chars < 0:
            raise ValueError("chars cannot be negative")
        if len(set(self.cited_claim_ids)) != len(self.cited_claim_ids):
            raise ValueError("cited claim ids must be unique")
        return self
