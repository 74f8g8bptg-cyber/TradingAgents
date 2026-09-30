"""Research validation V1–V4 (Foundation §4.29.2), deterministic given the claim labels.

Per item:
- **V1 Source Validator** (``source_validator``): the source is on the owner allowlist
  (else ``source_not_allowlisted``), and its type is allowed for the item's role (else
  ``source_type_mismatch``).
- **V2 Freshness Checker** (``freshness_checker``):
  - ``published_at`` or ``retrieved_at`` after ``as_of`` → FUTURE (no look-ahead);
  - older than the role's configured freshness window → STALE;
  - if no window is configured, the item is accepted with reason ``freshness_window_unset``
    and the analysis records the limitation.
- **V3 Duplicate Detector** (``duplicate_detector``): the same ``content_hash`` as an earlier
  item (by publication time, then id) → DUPLICATE. A syndicated item (``derived_from``) is
  kept but is not an independent source (see ``corroboration``).

Per claim:
- **V4 Classifier** (``claim_classifier``): the claim must carry a label. Labels come from
  the V4 LLM step or from owner-declared labels; a claim without one is rejected
  (``label_unavailable``). A FACT with a value is cross-checked against a structured
  calendar value for the same subject and period when one exists; a mismatch is rejected
  (``calendar_mismatch``).

A claim is ACCEPTED only when every check accepts (the Phase 1 ``ClaimValidation`` rule).
Validators never repair data and never ask a model to supply a missing value.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from stellar.research.sources import ROLE_SOURCE_TYPES, SourceAllowlist
from stellar.schemas.common import (
    FiniteDecimal,
    Label,
    Provenance,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.research import (
    CheckOutcome,
    ClaimLabel,
    ClaimValidation,
    ResearchItem,
    ResearchRole,
    ValidationCheck,
    ValidationStatus,
)
from stellar.serialization import content_hash, sha256_hex


class ValidationConfig(StellarModel):
    """Freshness windows per role in seconds. None of them is a default (UNSET)."""

    freshness_seconds: dict[ResearchRole, int] = {}
    test_only: bool = False

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class CalendarValue(StellarModel):
    """A structured calendar value used to cross-check numeric FACT claims."""

    subject: Label
    period: ShortText
    value: FiniteDecimal
    source_id: Label
    published_at: UtcDatetime


def _check(validator: str, outcome: CheckOutcome, reason: str | None = None) -> ValidationCheck:
    return ValidationCheck(validator=validator, outcome=outcome, reason=reason)


def item_checks(items: Sequence[ResearchItem], *, allowlist: SourceAllowlist,
                config: ValidationConfig, as_of: datetime) -> dict[str, list[ValidationCheck]]:
    out: dict[str, list[ValidationCheck]] = {}
    seen_hashes: set[str] = set()
    for item in sorted(items, key=lambda i: (i.published_at, i.item_id)):
        checks = []
        source = allowlist.get(item.source_id)
        if source is None:
            checks.append(_check("source_validator", CheckOutcome.REJECTED,
                                 "source_not_allowlisted"))
        elif source.source_type not in ROLE_SOURCE_TYPES[item.role]:
            checks.append(_check("source_validator", CheckOutcome.REJECTED,
                                 "source_type_mismatch"))
        else:
            checks.append(_check("source_validator", CheckOutcome.ACCEPTED))
        window = config.freshness_seconds.get(item.role)
        if item.published_at > as_of or item.retrieved_at > as_of:
            checks.append(_check("freshness_checker", CheckOutcome.FUTURE, "after_as_of"))
        elif window is not None and (as_of - item.published_at).total_seconds() > window:
            checks.append(_check("freshness_checker", CheckOutcome.STALE, "outside_window"))
        else:
            checks.append(_check("freshness_checker", CheckOutcome.ACCEPTED,
                                 None if window is not None else "freshness_window_unset"))
        if item.content_hash in seen_hashes:
            checks.append(_check("duplicate_detector", CheckOutcome.DUPLICATE, "same_content"))
        else:
            seen_hashes.add(item.content_hash)
            checks.append(_check("duplicate_detector", CheckOutcome.ACCEPTED))
        out[item.item_id] = checks
    return out


def validate_claims(items: Sequence[ResearchItem], *, allowlist: SourceAllowlist,
                    config: ValidationConfig, as_of: datetime,
                    labels: Mapping[str, ClaimLabel],
                    calendar: Sequence[CalendarValue] = ()) -> list[ClaimValidation]:
    checks_by_item = item_checks(items, allowlist=allowlist, config=config, as_of=as_of)
    config_hash = content_hash({"allowlist": allowlist.allowlist_hash(),
                                "config": config.config_hash()})
    known = {(c.subject, c.period): c for c in calendar if c.published_at <= as_of}
    out = []
    for item in sorted(items, key=lambda i: (i.published_at, i.item_id)):
        for claim in item.claims:
            label = labels.get(claim.claim_id)
            if label is None:
                v4 = _check("claim_classifier", CheckOutcome.REJECTED, "label_unavailable")
            else:
                ref = known.get((claim.subject, claim.period))
                mismatch = (label is ClaimLabel.FACT and claim.value is not None
                            and ref is not None and ref.value != claim.value)
                v4 = _check("claim_classifier", CheckOutcome.REJECTED, "calendar_mismatch") \
                    if mismatch else _check("claim_classifier", CheckOutcome.ACCEPTED)
            checks = (*checks_by_item[item.item_id], v4)
            accepted = all(c.outcome is CheckOutcome.ACCEPTED for c in checks)
            out.append(ClaimValidation(
                validation_id="val_" + sha256_hex(f"{item.item_id}|{claim.claim_id}|"
                                                  f"{as_of.isoformat()}|{config_hash}")[:40],
                item_id=item.item_id, claim_id=claim.claim_id, label=label, checks=checks,
                status=ValidationStatus.ACCEPTED if accepted else ValidationStatus.REJECTED,
                validated_at=as_of,
                provenance=Provenance(produced_by="claim_classifier", config_hash=config_hash,
                                      input_ids=(item.item_id, claim.claim_id))))
    return out
