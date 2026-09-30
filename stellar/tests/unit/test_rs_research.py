"""Phase 6 research layer: sources, collection, V1–V4 validation, corroboration, snapshots.
All sources, items and values are synthetic fixtures (tests/research_helpers.py)."""

import pytest
from research_helpers import (
    ALLOWLIST,
    AS_OF,
    CB_DECISION,
    CPI_CALENDAR,
    CPI_CONFLICT,
    CPI_OFFICIAL,
    DECLARED,
    DUPLICATE_NEWS,
    FORUM,
    FUTURE_NEWS,
    NEWS,
    STALE_NEWS,
    STATION,
    SYNDICATED,
    VALIDATION,
    H,
    collections,
    item,
)
from stellar.journal import StellarJournal
from stellar.research import (
    CalendarValue,
    CollectionResult,
    CollectionStatus,
    EvidenceStatus,
    SourceAllowlist,
    StaticCollector,
    ValidationConfig,
    assess_claims,
    build_snapshot,
    publish_snapshot,
    validate_claims,
)
from stellar.schemas.research import ClaimLabel, ResearchRole, ValidationStatus

pytestmark = pytest.mark.unit


def validate(*items, allowlist=ALLOWLIST, config=VALIDATION, labels=DECLARED, calendar=()):
    return {v.claim_id: v for v in validate_claims(items, allowlist=allowlist, config=config,
                                                   as_of=AS_OF, labels=labels,
                                                   calendar=calendar)}


def reasons(v):
    return {c.reason for c in v.checks if c.reason}


def assess(*items, labels=DECLARED):
    vals = validate_claims(items, allowlist=ALLOWLIST, config=VALIDATION, as_of=AS_OF,
                           labels=labels)
    return {a.claim_id: a for a in assess_claims(items, vals, allowlist=ALLOWLIST, as_of=AS_OF)}


# --- collection ---------------------------------------------------------------------------------


def test_absence_is_explicit_never_filled():
    empty = StaticCollector(ResearchRole.RATES_BONDS).collect(AS_OF)
    assert empty.status is CollectionStatus.NO_DATA and empty.items == ()
    down = StaticCollector(ResearchRole.RATES_BONDS, unavailable_reason="source_down").collect(AS_OF)
    assert down.status is CollectionStatus.UNAVAILABLE and down.reason == "source_down"
    with pytest.raises(ValueError):
        CollectionResult(role=ResearchRole.RATES_BONDS, as_of=AS_OF,
                         status=CollectionStatus.NO_DATA, items=(CB_DECISION,), reason="x")


# --- V1–V4 -------------------------------------------------------------------------------------


def test_empty_allowlist_accepts_nothing():
    v = validate(CB_DECISION, allowlist=SourceAllowlist())["clm_cb_rate"]
    assert v.status is ValidationStatus.REJECTED and "source_not_allowlisted" in reasons(v)


def test_source_type_must_match_the_role():
    wrong = item("ri_wrong", ResearchRole.CENTRAL_BANK, "synthetic_newswire", "Synthetic text.",
                 [{"claim_id": "clm_wrong", "statement": "Synthetic statement."}])
    v = validate(wrong, labels={"clm_wrong": ClaimLabel.FACT})["clm_wrong"]
    assert "source_type_mismatch" in reasons(v)


def test_future_and_stale_items_are_rejected():
    vs = validate(FUTURE_NEWS, STALE_NEWS)
    assert "after_as_of" in reasons(vs["clm_future"])
    assert "outside_window" in reasons(vs["clm_old"])


def test_unset_freshness_window_is_reported_not_assumed():
    v = validate(CB_DECISION, config=ValidationConfig())["clm_cb_rate"]
    assert v.status is ValidationStatus.ACCEPTED and "freshness_window_unset" in reasons(v)


def test_exact_duplicate_is_rejected_and_the_earliest_kept():
    vs = validate(NEWS, DUPLICATE_NEWS)
    assert vs["clm_news_reaction"].status is ValidationStatus.ACCEPTED
    assert "same_content" in reasons(vs["clm_dup"])


def test_unlabelled_claims_and_calendar_mismatches_are_rejected():
    assert "label_unavailable" in reasons(validate(CB_DECISION, labels={})["clm_cb_rate"])
    ref = CalendarValue(subject="synthetic_cpi_yoy", period="2026-08", value="3.1",
                        source_id="synthetic_calendar", published_at=AS_OF - 3 * H)
    vs = validate(CPI_OFFICIAL, CPI_CONFLICT, calendar=[ref])
    assert vs["clm_cpi_off"].status is ValidationStatus.ACCEPTED
    assert "calendar_mismatch" in reasons(vs["clm_cpi_news"])


# --- corroboration -------------------------------------------------------------------------------


def test_official_fact_is_validated_and_secondary_agreement_too():
    a = assess(CPI_OFFICIAL, CPI_CALENDAR, CB_DECISION)
    assert a["clm_cpi_off"].status is EvidenceStatus.VALIDATED
    assert a["clm_cpi_cal"].status is EvidenceStatus.VALIDATED  # agrees with the official one
    assert a["clm_cb_rate"].status is EvidenceStatus.VALIDATED


def test_secondary_alone_is_partially_supported_and_interpretation_unverified():
    a = assess(NEWS)
    assert a["clm_news_reaction"].status is EvidenceStatus.PARTIALLY_SUPPORTED
    assert a["clm_news_view"].status is EvidenceStatus.UNVERIFIED


def test_conflicting_official_and_secondary_claims():
    a = assess(CPI_OFFICIAL, CPI_CONFLICT)
    assert a["clm_cpi_off"].status is EvidenceStatus.CONFLICTING
    assert a["clm_cpi_news"].contradicting_claim_ids == ("clm_cpi_off",)


def test_syndicated_copies_are_not_independent_sources():
    a = assess(CB_DECISION, SYNDICATED)
    assert a["clm_synd"].root_item_id == "ri_cb_01"
    assert a["clm_cb_rate"].supporting_claim_ids == ()  # the copy does not corroborate


def test_community_source_alone_is_unverified():
    assert assess(FORUM)["clm_forum"].status is EvidenceStatus.UNVERIFIED


def test_stale_and_rejected_statuses():
    a = assess(STALE_NEWS, FUTURE_NEWS)
    assert a["clm_old"].status is EvidenceStatus.STALE
    assert a["clm_future"].status is EvidenceStatus.REJECTED


# --- snapshots ---------------------------------------------------------------------------------


def snapshot(*items):
    vals = validate_claims(items, allowlist=ALLOWLIST, config=VALIDATION, as_of=AS_OF,
                           labels=DECLARED)
    return build_snapshot(collections(*items), vals,
                          assess_claims(items, vals, allowlist=ALLOWLIST, as_of=AS_OF),
                          as_of=AS_OF, allowlist_hash=ALLOWLIST.allowlist_hash(),
                          validation_config_hash=VALIDATION.config_hash())


def test_snapshot_is_deterministic_and_reports_coverage():
    a, b = snapshot(CB_DECISION, NEWS), snapshot(CB_DECISION, NEWS)
    assert a == b and a.research_snapshot_id == f"rsnap_{a.content_hash[:40]}"
    assert set(a.contributed_roles()) == {ResearchRole.CENTRAL_BANK, ResearchRole.MARKET_NEWS}
    assert a.missing_roles([ResearchRole.ECONOMIC_DATA]) == (ResearchRole.ECONOMIC_DATA,)
    assert snapshot(CB_DECISION).content_hash != a.content_hash


def test_claim_ids_must_be_unique_across_a_snapshot():
    clash = item("ri_clash", ResearchRole.MARKET_NEWS, "synthetic_newswire", "Synthetic clash.",
                 [{"claim_id": "clm_cb_rate", "statement": "Same id."}])
    with pytest.raises(ValueError, match="unique"):
        snapshot(CB_DECISION, clash)


def test_publishing_uses_existing_research_events():
    snap = snapshot(CB_DECISION, FUTURE_NEWS)
    with StellarJournal() as journal:
        publish_snapshot(journal, snap, station_id=STATION, ts=AS_OF)
        types = [e.type for e in journal.read()]
    assert types.count("research.item.collected") == 2
    assert "research.item.accepted" in types and "research.item.rejected" in types
    assert types[-1] == "research.snapshot.created"
