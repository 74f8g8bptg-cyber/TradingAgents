"""Claim corroboration across sources: what a claim's evidence status is, and why.

``ClaimValidation`` (Phase 1) says whether one claim passed V1–V4. ``ClaimAssessment`` adds
the cross-source view. Statuses:

| Status | Rule |
|---|---|
| REJECTED | V1–V4 rejected it (not stale) |
| STALE | V2 found it outside the role's freshness window |
| CONFLICTING | another *independent* accepted claim on the same subject and period has a different value |
| VALIDATED | an accepted FACT from an OFFICIAL (tier 1) source, or an accepted FACT/REACTION agreeing with one |
| PARTIALLY_SUPPORTED | an accepted FACT or REACTION from a tier 2–3 source with no official agreement, or a tier 4 claim agreeing with an official one |
| UNVERIFIED | any accepted INTERPRETATION (an opinion is never a fact), or a tier 4 claim on its own |

**Independence.** An item that repeats or syndicates another (``derived_from``) shares that
item's root. Claims with the same root are one source, however many copies exist. Agreement
between models or between copies never counts as corroboration.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from stellar.research.sources import SourceAllowlist, SourceTier
from stellar.schemas.common import (
    ClaimId,
    Label,
    ResearchItemId,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.research import (
    CheckOutcome,
    ClaimLabel,
    ClaimValidation,
    ResearchItem,
    ValidationStatus,
)


class EvidenceStatus(StrEnum):
    VALIDATED = "VALIDATED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"
    REJECTED = "REJECTED"


class ClaimAssessment(StellarModel):
    claim_id: ClaimId
    item_id: ResearchItemId
    root_item_id: ResearchItemId
    label: ClaimLabel | None = None
    status: EvidenceStatus
    supporting_claim_ids: tuple[ClaimId, ...] = ()
    contradicting_claim_ids: tuple[ClaimId, ...] = ()
    source_tier: int | None = None
    validator: Label = "claim_corroboration"
    as_of: UtcDatetime
    limitations: tuple[Label, ...] = ()


def root_of(item: ResearchItem, by_id: dict[str, ResearchItem]) -> str:
    """The earliest item this one derives from (following ``derived_from``)."""
    seen = {item.item_id}
    current = item
    while current.derived_from:
        parent_id = current.derived_from[0]
        parent = by_id.get(parent_id)
        if parent is None or parent_id in seen:
            return parent_id
        seen.add(parent_id)
        current = parent
    return current.item_id


def assess_claims(items: Sequence[ResearchItem], validations: Sequence[ClaimValidation], *,
                  allowlist: SourceAllowlist, as_of: datetime) -> list[ClaimAssessment]:
    by_id = {i.item_id: i for i in items}
    claims = {(i.item_id, c.claim_id): c for i in items for c in i.claims}
    tier = {i.item_id: (s.tier if (s := allowlist.get(i.source_id)) else None) for i in items}
    accepted = [v for v in validations if v.status is ValidationStatus.ACCEPTED]
    out = []
    for v in validations:
        item = by_id[v.item_id]
        root = root_of(item, by_id)
        claim = claims[(v.item_id, v.claim_id)]
        limitations = tuple(c.reason for c in v.checks
                            if c.outcome is CheckOutcome.ACCEPTED and c.reason is not None)
        common = {"claim_id": v.claim_id, "item_id": v.item_id, "root_item_id": root,
                  "label": v.label, "source_tier": tier[v.item_id], "as_of": as_of,
                  "limitations": limitations}
        if v.status is not ValidationStatus.ACCEPTED:
            stale = any(c.outcome is CheckOutcome.STALE for c in v.checks)
            out.append(ClaimAssessment(**common, status=EvidenceStatus.STALE if stale
                                       else EvidenceStatus.REJECTED))
            continue
        if v.label is ClaimLabel.INTERPRETATION:
            out.append(ClaimAssessment(**common, status=EvidenceStatus.UNVERIFIED))
            continue
        peers = []
        for other in accepted:
            if other is v or other.label is ClaimLabel.INTERPRETATION:
                continue
            other_item = by_id[other.item_id]
            if root_of(other_item, by_id) == root:
                continue  # the same source, repeated: not independent
            oc = claims[(other.item_id, other.claim_id)]
            if claim.subject is not None and oc.subject == claim.subject and \
                    oc.period == claim.period:
                peers.append((other, oc))
        conflicts = [o.claim_id for o, oc in peers if claim.value is not None
                     and oc.value is not None and oc.value != claim.value]
        agree = [(o, oc) for o, oc in peers if o.claim_id not in conflicts]
        official_agrees = any(tier[o.item_id] is SourceTier.OFFICIAL
                              and o.label is ClaimLabel.FACT for o, _ in agree)
        own_tier = tier[v.item_id]
        if conflicts:
            status = EvidenceStatus.CONFLICTING
        elif own_tier is SourceTier.OFFICIAL and v.label is ClaimLabel.FACT or official_agrees \
                and own_tier is not SourceTier.COMMUNITY:
            status = EvidenceStatus.VALIDATED
        elif own_tier in (SourceTier.PROFESSIONAL, SourceTier.AGGREGATOR) or official_agrees:
            status = EvidenceStatus.PARTIALLY_SUPPORTED
        else:
            status = EvidenceStatus.UNVERIFIED
        out.append(ClaimAssessment(
            **common, status=status,
            supporting_claim_ids=tuple(sorted(o.claim_id for o, _ in agree)),
            contradicting_claim_ids=tuple(sorted(conflicts))))
    return out
