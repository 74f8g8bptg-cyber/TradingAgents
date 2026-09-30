"""The evidence pool: everything an agent may cite in one run, with its status and origin.

Evidence comes from exactly two places:
- **Research claims** from the research snapshot whose assessment is VALIDATED,
  PARTIALLY_SUPPORTED, CONFLICTING or UNVERIFIED. STALE and REJECTED claims never enter, and
  are counted only as exclusions. The evidence id is the claim id; the kind is its V4 label
  (FACT / REACTION / INTERPRETATION).
- **Phase 5 technical evidence**, read as given. Nothing is recomputed:
  - each ``TechnicalAnalysis`` contributes its structure state, its structure events and its
    pullback measurement;
  - a ``MultiTimeframeAnalysis`` contributes its alignment;
  - every item keeps the analysis id, content hash, timeframe and limitations. Evidence ids are
    ``tev_`` + a hash.

**Point in time:** claims come only from items published and retrieved at or before
``as_of`` (V2), and a technical analysis dated after ``as_of`` is refused.

**Relevance (not direction):** an instrument sees claims that affect it or its currencies
(XAUUSD: XAU, USD; EURUSD: EUR, USD; USDJPY: USD, JPY; NAS100: USD) and its own technical
evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import StringConstraints

from stellar.research.corroboration import EvidenceStatus
from stellar.research.snapshot import ResearchSnapshot
from stellar.schemas.common import (
    FiniteDecimal,
    InstrumentId,
    Label,
    ResearchItemId,
    Sha256Hex,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import Timeframe
from stellar.schemas.research import ClaimLabel, ResearchRole
from stellar.serialization import content_hash, sha256_hex
from stellar.technical import MultiTimeframeAnalysis, StructureState, TechnicalAnalysis
from stellar.technical.mtf import Alignment

RELEVANCE: dict[InstrumentId, frozenset[str]] = {
    InstrumentId.XAUUSD: frozenset({"XAUUSD", "XAU", "USD"}),
    InstrumentId.EURUSD: frozenset({"EURUSD", "EUR", "USD"}),
    InstrumentId.USDJPY: frozenset({"USDJPY", "USD", "JPY"}),
    InstrumentId.NAS100: frozenset({"NAS100", "USD"}),
}
USABLE = frozenset({EvidenceStatus.VALIDATED, EvidenceStatus.PARTIALLY_SUPPORTED,
                    EvidenceStatus.CONFLICTING, EvidenceStatus.UNVERIFIED})


class EvidenceKind(StrEnum):
    FACT = "FACT"
    REACTION = "REACTION"
    INTERPRETATION = "INTERPRETATION"
    TECHNICAL = "TECHNICAL"


class EvidenceItem(StellarModel):
    evidence_id: Annotated[str, StringConstraints(pattern=r"^(clm|tev)_[A-Za-z0-9_.\-]{1,128}$")]
    kind: EvidenceKind
    status: EvidenceStatus | None = None
    """Research claims only; technical evidence is deterministic and has no status."""
    statement: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    affected: tuple[str, ...] = ()
    observed_at: UtcDatetime
    role: ResearchRole | None = None
    item_id: ResearchItemId | None = None
    root_item_id: ResearchItemId | None = None
    source_id: Label | None = None
    source_tier: int | None = None
    subject: Label | None = None
    value: FiniteDecimal | None = None
    unit: ShortText | None = None
    period: ShortText | None = None
    technical_analysis_id: str | None = None
    technical_content_hash: Sha256Hex | None = None
    timeframe: Timeframe | None = None
    direction_hint: Literal["UP", "DOWN"] | None = None
    """Technical structure only: UP / DOWN state as Phase 5 labelled it."""
    limitations: tuple[Label, ...] = ()


class EvidencePool(StellarModel):
    as_of: UtcDatetime
    items: tuple[EvidenceItem, ...]
    excluded_stale: int
    excluded_rejected: int
    pool_hash: Sha256Hex

    def by_id(self) -> dict[str, EvidenceItem]:
        return {e.evidence_id: e for e in self.items}

    def for_instrument(self, instrument: InstrumentId) -> tuple[EvidenceItem, ...]:
        keys = RELEVANCE[instrument]
        return tuple(e for e in self.items
                     if (e.kind is EvidenceKind.TECHNICAL and instrument.value in e.affected)
                     or (e.kind is not EvidenceKind.TECHNICAL and set(e.affected) & keys))


class TechnicalAfterAsOf(ValueError):
    """A technical analysis dated after the run's as_of was supplied."""


def _tev(*parts: object) -> str:
    return "tev_" + sha256_hex("|".join(str(p) for p in parts))[:16]


def technical_evidence(analysis: TechnicalAnalysis) -> list[EvidenceItem]:
    base = {"kind": EvidenceKind.TECHNICAL, "affected": (analysis.instrument.value,),
            "observed_at": analysis.as_of, "technical_analysis_id": analysis.analysis_id,
            "technical_content_hash": analysis.content_hash,
            "timeframe": analysis.timeframe,
            "limitations": tuple(x.value for x in analysis.limitations)}
    s = analysis.structure
    hint = {StructureState.UP: "UP", StructureState.DOWN: "DOWN"}.get(s.state)
    high = s.last_swing_high.label.value if s.last_swing_high and s.last_swing_high.label else None
    low = s.last_swing_low.label.value if s.last_swing_low and s.last_swing_low.label else None
    out = [EvidenceItem(evidence_id=_tev(analysis.analysis_id, "structure"),
                        statement=f"Phase 5 {analysis.timeframe.value} structure state "
                                  f"{s.state.value} (last swing high {high}, last swing low "
                                  f"{low}).", direction_hint=hint, **base)]
    for event in s.events:
        out.append(EvidenceItem(
            evidence_id=_tev(analysis.analysis_id, "event", event.reference_pivot_id,
                             event.kind.value),
            statement=f"Phase 5 {analysis.timeframe.value} {event.kind.value}: close "
                      f"{event.close} beyond swing level {event.level} (bar closed "
                      f"{event.bar_close_time.isoformat()}).", **base))
    p = analysis.pullback
    if p is not None:
        out.append(EvidenceItem(
            evidence_id=_tev(analysis.analysis_id, "pullback"),
            statement=f"Phase 5 {analysis.timeframe.value} pullback after a "
                      f"{p.reference_direction.value} leg: {p.bars} bars, retracement ratio "
                      f"{p.retracement_ratio}, {p.counter_direction_bars} counter-direction bars.",
            **base))
    return out


def mtf_evidence(mtf: MultiTimeframeAnalysis) -> EvidenceItem:
    hint = {Alignment.AGREE_UP: "UP", Alignment.AGREE_DOWN: "DOWN"}.get(mtf.alignment)
    states = ", ".join(f"{r.timeframe.value}={r.structure_state.value if r.structure_state else 'n/a'}"
                       for r in mtf.readings)
    return EvidenceItem(
        evidence_id=_tev("mtf", mtf.content_hash), kind=EvidenceKind.TECHNICAL,
        statement=f"Phase 5 multi-timeframe alignment {mtf.alignment.value} ({states}).",
        affected=(mtf.instrument.value,), observed_at=mtf.as_of, direction_hint=hint,
        technical_content_hash=mtf.content_hash,
        limitations=tuple(x.value for x in mtf.limitations))


def build_pool(snapshot: ResearchSnapshot, technical: Sequence[TechnicalAnalysis], *,
               as_of: datetime, mtf: MultiTimeframeAnalysis | None = None) -> EvidencePool:
    if snapshot.as_of != as_of:
        raise ValueError("the research snapshot is for another as_of")
    claims = {c.claim_id: (i, c) for i in snapshot.items for c in i.claims}
    out: list[EvidenceItem] = []
    stale = rejected = 0
    for a in snapshot.assessments:
        if a.status is EvidenceStatus.STALE:
            stale += 1
            continue
        if a.status not in USABLE:
            rejected += 1
            continue
        item, claim = claims[a.claim_id]
        assert item.published_at <= as_of  # V2 rejects anything later
        out.append(EvidenceItem(
            evidence_id=a.claim_id, kind=EvidenceKind(a.label.value if a.label else
                                                      ClaimLabel.INTERPRETATION.value),
            status=a.status, statement=claim.statement, affected=item.affected,
            observed_at=item.published_at, role=item.role, item_id=item.item_id,
            root_item_id=a.root_item_id, source_id=item.source_id, source_tier=a.source_tier,
            subject=claim.subject, value=claim.value, unit=claim.unit, period=claim.period,
            limitations=a.limitations))
    for analysis in technical:
        if analysis.as_of > as_of:
            raise TechnicalAfterAsOf(f"{analysis.analysis_id} is dated after as_of")
        out.extend(technical_evidence(analysis))
    if mtf is not None:
        if mtf.as_of > as_of:
            raise TechnicalAfterAsOf("the multi-timeframe analysis is dated after as_of")
        out.append(mtf_evidence(mtf))
    body = {"as_of": as_of.isoformat(), "items": [e.model_dump(mode="json") for e in out]}
    return EvidencePool(as_of=as_of, items=tuple(out), excluded_stale=stale,
                        excluded_rejected=rejected, pool_hash=content_hash(body))
