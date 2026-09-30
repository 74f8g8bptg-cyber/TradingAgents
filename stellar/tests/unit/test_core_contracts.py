"""Valid construction and malformed rejection for every core contract."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from factories import (
    T0,
    analysis_data,
    candle_data,
    make_analysis,
    make_decision,
    make_intent,
    make_proposal,
    make_research_item,
    make_result,
    make_series,
    make_snapshot,
    make_validation,
    research_item_data,
    snapshot_data,
    validation_data,
)
from pydantic import ValidationError
from stellar.schemas import (
    SCHEMA_VERSION,
    AnalysisReport,
    Candle,
    ClaimValidation,
    InstrumentId,
    MarketSnapshot,
    ResearchFinding,
    ResearchItem,
    ValidatedFact,
)

pytestmark = pytest.mark.unit


def test_every_core_contract_builds_from_valid_data():
    records = [
        make_research_item(),
        make_validation(),
        make_snapshot(),
        make_analysis(),
        make_proposal(),
        make_decision(),
        make_intent(),
        make_result(),
    ]
    for record in records:
        assert record.schema_version == SCHEMA_VERSION
        # Round trip through JSON gives an equal record.
        assert type(record).model_validate_json(record.model_dump_json()) == record


def test_brief_names_are_aliases_of_the_documented_contracts():
    assert ResearchFinding is ResearchItem
    assert ValidatedFact is ClaimValidation
    assert make_validation().is_validated_fact
    assert not make_validation(label="INTERPRETATION").is_validated_fact


def test_records_are_immutable_and_closed():
    proposal = make_proposal()
    with pytest.raises(ValidationError):
        proposal.direction = "LONG"
    with pytest.raises(ValidationError, match="Extra inputs"):
        make_proposal(notes="enter at 2400")


def test_other_schema_major_versions_are_rejected():
    with pytest.raises(ValidationError):
        make_proposal(schema_version="2.0")
    assert make_proposal(schema_version="1.3").schema_version == "1.3"


def test_timestamps_must_be_timezone_aware_and_are_stored_in_utc():
    with pytest.raises(ValidationError, match="timezone-aware"):
        make_proposal(created_at=datetime(2026, 9, 29, 14, 0))
    from datetime import timezone

    plus_two = timezone(timedelta(hours=2))
    proposal = make_proposal(created_at=T0.astimezone(plus_two))
    assert proposal.created_at.utcoffset() == timedelta(0)
    assert proposal.created_at == T0


@pytest.mark.parametrize("value", ["XAU/USD", "xauusd", "GC=F", "BTCUSD"])
def test_instruments_use_canonical_ids_only(value):
    with pytest.raises(ValidationError):
        make_proposal(instrument=value)


def test_canonical_instrument_ids():
    assert [i.value for i in InstrumentId] == ["XAUUSD", "EURUSD", "USDJPY", "NAS100"]


@pytest.mark.parametrize(
    "field,value",
    [("proposal_id", "dec_01"), ("proposal_id", "prop_"), ("snapshot_id", "prop_01"),
     ("setup_id", "01"), ("run_id", "run id with spaces")],
)
def test_ids_must_carry_their_record_prefix(field, value):
    with pytest.raises(ValidationError):
        make_proposal(**{field: value})


# --- market ---------------------------------------------------------------


def test_candle_rejects_inconsistent_ohlc():
    with pytest.raises(ValidationError, match="high"):
        Candle.model_validate(candle_data(1, high="2399.00"))
    with pytest.raises(ValidationError, match="low"):
        Candle.model_validate(candle_data(1, low="2402.00"))
    with pytest.raises(ValidationError, match="close_time"):
        Candle.model_validate(candle_data(1, close_time=T0 - timedelta(hours=2)))


def test_series_rejects_duplicates_disorder_and_a_wrong_hash():
    with pytest.raises(ValidationError, match="strictly increasing"):
        make_series(candle_data(1), candle_data(2))
    series = make_series()
    with pytest.raises(ValidationError, match="content_hash"):
        type(series).model_validate({**series.model_dump(), "content_hash": "0" * 64})


def test_snapshot_refuses_look_ahead():
    with pytest.raises(ValidationError, match="look-ahead"):
        make_snapshot(as_of=T0 - timedelta(minutes=30))
    quote = snapshot_data()["quote"] | {"ts": T0 + timedelta(seconds=1)}
    with pytest.raises(ValidationError, match="look-ahead"):
        make_snapshot(quote=quote)


def test_snapshot_rejects_a_crossed_quote_and_mixed_instruments():
    quote = snapshot_data()["quote"] | {"bid": "2401", "ask": "2400"}
    with pytest.raises(ValidationError, match="ask"):
        make_snapshot(quote=quote)
    with pytest.raises(ValidationError, match="instrument"):
        MarketSnapshot.model_validate(snapshot_data(instrument="EURUSD", quote=None))


# --- research ---------------------------------------------------------------


def test_research_item_rejects_retrieval_before_publication_and_duplicate_claims():
    with pytest.raises(ValidationError, match="retrieved_at"):
        make_research_item(retrieved_at=T0 - timedelta(hours=4))
    claims = research_item_data()["claims"] * 2
    with pytest.raises(ValidationError, match="unique"):
        make_research_item(claims=claims)


def test_research_item_rejects_unknown_affected_symbols():
    with pytest.raises(ValidationError):
        make_research_item(affected=["XAU/USD"])


def test_claim_validation_status_must_match_its_checks():
    rejecting = validation_data()["checks"][:3] + [
        {"validator": "claim_classifier", "outcome": "rejected", "reason": "calendar_mismatch"}
    ]
    with pytest.raises(ValidationError, match="ACCEPTED requires"):
        make_validation(checks=rejecting)
    rejected = make_validation(checks=rejecting, status="REJECTED")
    assert not rejected.is_validated_fact
    with pytest.raises(ValidationError, match="REJECTED requires"):
        make_validation(status="REJECTED")
    with pytest.raises(ValidationError, match="reason"):
        make_validation(checks=[{"validator": "freshness_checker", "outcome": "stale"}],
                        status="REJECTED")
    with pytest.raises(ValidationError, match="label"):
        ClaimValidation.model_validate(validation_data(label=None))


# --- analysis ---------------------------------------------------------------


def test_analysis_report_requires_the_links_its_kind_needs():
    with pytest.raises(ValidationError, match="coverage"):
        make_analysis(coverage=None)
    with pytest.raises(ValidationError, match="instrument"):
        make_analysis(kind="market")
    with pytest.raises(ValidationError, match="market snapshot"):
        make_analysis(kind="structure", instrument="XAUUSD", coverage=None)
    report = make_analysis(kind="structure", instrument="XAUUSD", snapshot_id="snap_01",
                           coverage=None, research_snapshot_id=None)
    assert report.kind == "structure"


def test_analysis_report_rejects_overlapping_coverage_and_partial_excerpts():
    coverage = {"contributed": ["research_central_bank"], "missing": ["research_central_bank"]}
    with pytest.raises(ValidationError, match="both"):
        make_analysis(coverage=coverage)
    with pytest.raises(ValidationError, match="together"):
        AnalysisReport.model_validate(analysis_data(sha256=None))


# --- numbers ----------------------------------------------------------------


@pytest.mark.parametrize("value", [1.5, True, "NaN", "Infinity", "-1", "0", "abc"])
def test_prices_reject_floats_booleans_non_finite_and_non_positive(value):
    with pytest.raises(ValidationError):
        make_intent(stop_loss=value)


def test_decimal_values_survive_serialization_exactly():
    intent = make_intent(max_slippage="0.10000")
    again = type(intent).model_validate_json(intent.model_dump_json())
    assert again.max_slippage == Decimal("0.10000")
    assert isinstance(again.volume, Decimal)
