"""Evidence quality and stance guards. Deterministic, and never taken from a model.

**Evidence quality** counts, for the focus instrument:
- validated, partially supported, conflicting and unverified claims, and interpretations;
- independent sources (distinct roots among supported claims), technical items, and
  stale / rejected exclusions;
- missing required research roles and the Phase 5 limitations.

Grades are rules, not a numeric score:
- **INSUFFICIENT:** no supported claim and no technical evidence;
- **LIMITED:** any of:
  - no validated fact;
  - a conflicting claim;
  - a missing required research role;
  - no technical evidence;
  - a Phase 5 ``insufficient_history`` limitation;
  - a challenger finding of kind INTERPRETATION_AS_FACT, UNSUPPORTED_CLAIM,
    TECHNICAL_MACRO_DISAGREEMENT, DUPLICATE_COUNTED or OUT_OF_AS_OF;
- **ADEQUATE:** otherwise.

A model's ``self_reported_confidence`` plays no part.

**Guards** on the Research Manager's stance (the model stance is kept; the final stance is
what the guards allow):
- INSUFFICIENT evidence → INSUFFICIENT_EVIDENCE;
- a directional stance with no cited evidence on its side → INSUFFICIENT_EVIDENCE;
- a technical / macro disagreement with a directional stance → MIXED. Disagreement is kept,
  never averaged away.
"""

from __future__ import annotations

from collections.abc import Sequence

from stellar.pipeline.evidence import EvidenceItem, EvidenceKind, EvidencePool
from stellar.pipeline.records import (
    ChallengeFinding,
    ChallengeKind,
    EvidenceGrade,
    EvidenceQuality,
)
from stellar.reasoning.contracts import Stance, SynthesisOutput
from stellar.research.corroboration import EvidenceStatus

LIMITING_FINDINGS = {ChallengeKind.INTERPRETATION_AS_FACT, ChallengeKind.UNSUPPORTED_CLAIM,
                     ChallengeKind.TECHNICAL_MACRO_DISAGREEMENT, ChallengeKind.DUPLICATE_COUNTED,
                     ChallengeKind.OUT_OF_AS_OF}


def evidence_quality(items: Sequence[EvidenceItem], pool: EvidencePool, *,
                     missing_roles: Sequence[str],
                     findings: Sequence[ChallengeFinding]) -> EvidenceQuality:
    claims = [e for e in items if e.kind is not EvidenceKind.TECHNICAL]
    technical = [e for e in items if e.kind is EvidenceKind.TECHNICAL]

    def count(status: EvidenceStatus, kind: EvidenceKind | None = None) -> int:
        return sum(e.status is status and (kind is None or e.kind is kind) for e in claims)

    validated = count(EvidenceStatus.VALIDATED, EvidenceKind.FACT)
    partial = count(EvidenceStatus.PARTIALLY_SUPPORTED)
    supported = [e for e in claims if e.status in (EvidenceStatus.VALIDATED,
                                                   EvidenceStatus.PARTIALLY_SUPPORTED)]
    tech_limits = sorted({x for e in technical for x in e.limitations})
    reasons = []
    if not supported and not technical:
        grade = EvidenceGrade.INSUFFICIENT
        reasons.append("no_supported_evidence")
    else:
        if validated == 0:
            reasons.append("no_validated_fact")
        if count(EvidenceStatus.CONFLICTING):
            reasons.append("conflicting_claims")
        if missing_roles:
            reasons.append("missing_research_roles")
        if not technical:
            reasons.append("no_technical_evidence")
        if "insufficient_history" in tech_limits:
            reasons.append("technical_insufficient_history")
        reasons += sorted({f"finding_{f.kind.value.lower()}" for f in findings
                           if f.kind in LIMITING_FINDINGS})
        grade = EvidenceGrade.LIMITED if reasons else EvidenceGrade.ADEQUATE
    return EvidenceQuality(
        grade=grade, validated_facts=validated, partially_supported=partial,
        conflicting=count(EvidenceStatus.CONFLICTING),
        unverified=count(EvidenceStatus.UNVERIFIED),
        interpretations=sum(e.kind is EvidenceKind.INTERPRETATION for e in claims),
        independent_sources=len({e.root_item_id for e in supported}),
        technical_items=len(technical), excluded_stale=pool.excluded_stale,
        excluded_rejected=pool.excluded_rejected, missing_research_roles=tuple(missing_roles),
        technical_limitations=tuple(tech_limits), reasons=tuple(reasons))


def guard_stance(output: SynthesisOutput, quality: EvidenceQuality,
                 findings: Sequence[ChallengeFinding]) -> tuple[Stance, tuple[str, ...]]:
    stance = output.stance
    if quality.grade is EvidenceGrade.INSUFFICIENT:
        return Stance.INSUFFICIENT_EVIDENCE, ("insufficient_evidence",) if \
            stance is not Stance.INSUFFICIENT_EVIDENCE else ()
    side = {Stance.SUPPORTS_UPSIDE: output.upside_evidence_ids,
            Stance.SUPPORTS_DOWNSIDE: output.downside_evidence_ids}.get(stance)
    if side is not None and not side:
        return Stance.INSUFFICIENT_EVIDENCE, ("stance_without_evidence",)
    if side is not None and any(f.kind is ChallengeKind.TECHNICAL_MACRO_DISAGREEMENT
                                for f in findings):
        return Stance.MIXED, ("technical_macro_disagreement",)
    return stance, ()
