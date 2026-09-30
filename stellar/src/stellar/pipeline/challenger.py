"""P2 Contradiction Checker (deterministic): the challenger pass over every model output.

It never decides a stance. It records findings (kind, subject, evidence ids, detail):
- **INTERPRETATION_AS_FACT:** a statement, argument or driver with basis FACT cites no
  VALIDATED or PARTIALLY_SUPPORTED fact (only interpretations, reactions, unverified or
  conflicting claims).
- **UNSUPPORTED_CLAIM:** a directional stance (SUPPORTS_UPSIDE / SUPPORTS_DOWNSIDE) with no
  cited validated or partially supported fact and no technical evidence.
- **CONFLICTING_EVIDENCE:** an output cites a claim whose sources conflict.
- **OUT_OF_AS_OF:** cited evidence observed after ``as_of``. The pool already excludes it, so
  this is a guard.
- **TECHNICAL_MACRO_DISAGREEMENT:** the specialist's stance points one way while the Phase 5
  structure (or multi-timeframe alignment) for the instrument points the other.
- **MISSING_EVIDENCE:** a required research role contributed nothing, a collector reported
  NO_DATA / UNAVAILABLE, or there is no technical evidence.
- **DUPLICATE_COUNTED:** one output cites several claims from the same root source (copies or
  syndications counted as if independent).
- **OVERCONFIDENT_LANGUAGE:** certainty words in model text ("certain", "guaranteed",
  "definitely", "no doubt", "risk-free", ...), which no evidence grade justifies.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import datetime

from stellar.pipeline.evidence import EvidenceItem, EvidenceKind
from stellar.pipeline.records import ChallengeFinding, ChallengeKind
from stellar.reasoning.contracts import (
    Basis,
    DebateCaseOutput,
    MacroAssessmentOutput,
    MarketViewOutput,
    Stance,
    SynthesisOutput,
)
from stellar.research.corroboration import EvidenceStatus
from stellar.serialization import sha256_hex

SUPPORTED = {EvidenceStatus.VALIDATED, EvidenceStatus.PARTIALLY_SUPPORTED}
CERTAINTY = re.compile(r"\b(certain(ly)?|guarantee(d|s)?|definitely|no doubt|risk[- ]free|"
                       r"cannot fail|will surely|sure thing|100 ?%)\b", re.IGNORECASE)
DIRECTIONAL = {Stance.SUPPORTS_UPSIDE: "UP", Stance.SUPPORTS_DOWNSIDE: "DOWN"}


def finding(kind: ChallengeKind, subject: str, detail: str,
            evidence_ids: Iterable[str] = ()) -> ChallengeFinding:
    ids = tuple(sorted(set(evidence_ids)))
    return ChallengeFinding(finding_id="chk_" + sha256_hex(f"{kind}|{subject}|{detail}|{ids}")[:16],
                            kind=kind, subject=subject, evidence_ids=ids, detail=detail)


def technical_direction(pool: Sequence[EvidenceItem]) -> str | None:
    hints = {e.direction_hint for e in pool if e.kind is EvidenceKind.TECHNICAL
             and e.direction_hint is not None}
    return hints.pop() if len(hints) == 1 else None


def _fact_supported(ids: Iterable[str], by_id: dict[str, EvidenceItem]) -> bool:
    return any((e := by_id.get(i)) is not None and e.kind is EvidenceKind.FACT
               and e.status in SUPPORTED for i in ids)


def _statements(subject: str, output) -> list[tuple[Basis, tuple[str, ...], str]]:
    """(basis, evidence ids, text) for every claim-bearing statement of an output."""
    if isinstance(output, MacroAssessmentOutput):
        return [(d.basis, d.evidence_ids, d.mechanism_hypothesis) for d in output.drivers]
    if isinstance(output, MarketViewOutput):
        return [(s.basis, s.evidence_ids, s.statement) for s in output.reasoning]
    if isinstance(output, DebateCaseOutput):
        return [(a.basis, a.evidence_ids, a.point) for a in output.arguments]
    return []


def _texts(output) -> list[str]:
    if isinstance(output, SynthesisOutput):
        return [output.summary, *output.unresolved_contradictions]
    if isinstance(output, MacroAssessmentOutput):
        return [output.regime_description, *(d.mechanism_hypothesis for d in output.drivers)]
    if isinstance(output, MarketViewOutput):
        return [s.statement for s in output.reasoning]
    if isinstance(output, DebateCaseOutput):
        return [a.point for a in output.arguments] + [r.response for r in output.rebuttals]
    return []


def check_output(subject: str, output, pool: Sequence[EvidenceItem], *,
                 as_of: datetime) -> list[ChallengeFinding]:
    by_id = {e.evidence_id: e for e in pool}
    out: list[ChallengeFinding] = []
    cited = output.cited_evidence_ids()
    for basis, ids, _text in _statements(subject, output):
        if basis is Basis.FACT and not _fact_supported(ids, by_id):
            out.append(finding(ChallengeKind.INTERPRETATION_AS_FACT, subject,
                               "fact_without_supported_fact", ids))
    conflicting = [i for i in cited if (e := by_id.get(i)) and
                   e.status is EvidenceStatus.CONFLICTING]
    if conflicting:
        out.append(finding(ChallengeKind.CONFLICTING_EVIDENCE, subject, "cites_conflicting",
                           conflicting))
    late = [i for i in cited if (e := by_id.get(i)) and e.observed_at > as_of]
    if late:
        out.append(finding(ChallengeKind.OUT_OF_AS_OF, subject, "evidence_after_as_of", late))
    roots: dict[str, list[str]] = {}
    for i in cited:
        e = by_id.get(i)
        if e is not None and e.root_item_id is not None:
            roots.setdefault(e.root_item_id, []).append(i)
    for ids in roots.values():
        items = {by_id[i].item_id for i in ids}
        if len(items) > 1:
            out.append(finding(ChallengeKind.DUPLICATE_COUNTED, subject, "same_root_source", ids))
    stance = getattr(output, "stance", None)
    if stance in DIRECTIONAL:
        technical = any(by_id[i].kind is EvidenceKind.TECHNICAL for i in cited if i in by_id)
        if not _fact_supported(cited, by_id) and not technical:
            out.append(finding(ChallengeKind.UNSUPPORTED_CLAIM, subject,
                               "directional_stance_without_support", cited))
    if any(CERTAINTY.search(t) for t in _texts(output)):
        out.append(finding(ChallengeKind.OVERCONFIDENT_LANGUAGE, subject, "certainty_wording"))
    return out


def challenge(*, pool: Sequence[EvidenceItem], as_of: datetime, macro=None, view=None,
              bull: Sequence[DebateCaseOutput] = (), bear: Sequence[DebateCaseOutput] = (),
              missing_roles: Sequence[str] = (), absent_collections: Sequence[str] = ()
              ) -> list[ChallengeFinding]:
    out: list[ChallengeFinding] = []
    for subject, output in (("causal_macro_analyst", macro), ("market_specialist", view),
                            *(("bull_researcher", b) for b in bull),
                            *(("bear_researcher", b) for b in bear)):
        if output is not None:
            out.extend(check_output(subject, output, pool, as_of=as_of))
    direction = technical_direction(pool)
    if view is not None and direction is not None and \
            DIRECTIONAL.get(view.stance) not in (None, direction):
        technical_ids = [e.evidence_id for e in pool if e.direction_hint == direction]
        out.append(finding(ChallengeKind.TECHNICAL_MACRO_DISAGREEMENT, "market_specialist",
                           f"view_{view.stance.value.lower()}_technical_{direction.lower()}",
                           technical_ids))
    for role in missing_roles:
        out.append(finding(ChallengeKind.MISSING_EVIDENCE, "inputs", f"missing_{role}"))
    for role in absent_collections:
        out.append(finding(ChallengeKind.MISSING_EVIDENCE, "inputs", f"absent_{role}"))
    if not any(e.kind is EvidenceKind.TECHNICAL for e in pool):
        out.append(finding(ChallengeKind.MISSING_EVIDENCE, "inputs", "no_technical_evidence"))
    unique = {f.finding_id: f for f in out}
    return sorted(unique.values(), key=lambda f: (f.kind.value, f.subject, f.finding_id))
