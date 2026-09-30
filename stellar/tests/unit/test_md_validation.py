"""Candle and series validation, gaps and freshness. All data is SYNTHETIC."""

from datetime import timedelta
from decimal import Decimal

import pytest
from md_helpers import FIXED_NOW, T0, H, bar
from pydantic import ValidationError
from stellar.marketdata import (
    DuplicatePolicy,
    FreshnessStatus,
    IssueCode,
    IssueSeverity,
    OrderPolicy,
    StaleReason,
    evaluate_freshness,
    find_gaps,
    validate_series,
)
from stellar.schemas.market import Candle, DataQualityFlag, Timeframe

pytestmark = pytest.mark.unit


def codes(result, severity=None):
    return {i.code for i in result.issues if severity is None or i.severity is severity}


def validate(candles, **kw):
    return validate_series(candles, instrument="XAUUSD", timeframe=Timeframe.H1, **kw)


# --- bar-level rules (Candle contract) -------------------------------------------


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"high": Decimal("2380")}, "high"),
        ({"low": Decimal("2390")}, "low"),
        ({"open": "NaN"}, "finite"),
        ({"close": "Infinity"}, "finite"),
        ({"open": True}, "boolean"),
        ({"high": 2388.5}, "floats"),
        ({"volume": Decimal("-1")}, "greater than or equal"),
        ({"open_time": T0.replace(tzinfo=None)}, "timezone-aware"),
        ({"close_time": T0}, "close_time"),
    ],
)
def test_invalid_bars_are_rejected_at_construction(overrides, message):
    with pytest.raises(ValidationError, match=message):
        bar(0, **overrides)


def test_volume_is_optional_but_must_agree_with_volume_kind():
    no_volume = bar(0, volume=None, volume_kind="none")
    assert no_volume.volume is None
    with pytest.raises(ValidationError, match="volume is absent"):
        bar(0, volume=None)  # kind still "tick"
    with pytest.raises(ValidationError, match="volume is absent"):
        bar(0, volume_kind="none")  # volume still present
    both = bar(0, volume=Decimal("5"), volume_kind="real", tick_volume=Decimal("140"))
    assert both.tick_volume == Decimal("140")


def test_phase1_candles_remain_valid():
    # The Phase 1 shape (volume given, kind tick, no new fields) still validates.
    legacy = {k: v for k, v in bar(0).model_dump().items()
              if k not in {"tick_volume", "quality_flags"}}
    assert Candle.model_validate(legacy).tick_volume is None


# --- series rules -------------------------------------------------------------------


def test_a_clean_series_has_no_issues():
    result = validate([bar(i) for i in range(4)])
    assert result.issues == () and result.flags == () and not result.has_errors
    assert result.observed_price_decimals == 2


def test_instrument_timeframe_and_closure_consistency():
    mixed = [bar(0), bar(1, instrument="EURUSD", base=Decimal("1.08512"))]
    assert IssueCode.INSTRUMENT_MISMATCH in codes(validate(mixed), IssueSeverity.ERROR)
    assert IssueCode.NOT_CLOSED in codes(validate([bar(0, is_closed=False)]))
    wrong = bar(0, close_time=T0 + timedelta(minutes=59))
    assert IssueCode.WRONG_DURATION in codes(validate([wrong]), IssueSeverity.ERROR)


def test_out_of_order_is_rejected_unless_sorting_is_explicit():
    bars = [bar(1), bar(0), bar(2)]
    rejected = validate(bars)
    assert IssueCode.OUT_OF_ORDER in codes(rejected, IssueSeverity.ERROR)
    sorted_ = validate(bars, order_policy=OrderPolicy.SORT)
    assert not sorted_.has_errors
    assert [c.open_time for c in sorted_.candles] == [T0, T0 + H, T0 + 2 * H]
    assert DataQualityFlag.OUT_OF_ORDER in sorted_.flags


def test_duplicates_are_rejected_unless_identical_ones_are_explicitly_dropped():
    bars = [bar(0), bar(1), bar(1), bar(2)]
    assert IssueCode.DUPLICATE_BAR in codes(validate(bars), IssueSeverity.ERROR)
    dropped = validate(bars, duplicate_policy=DuplicatePolicy.DROP_IDENTICAL)
    assert not dropped.has_errors and len(dropped.candles) == 3
    assert DataQualityFlag.DUPLICATE_BAR in dropped.flags
    conflicting = [bar(0), bar(1), bar(1, close=Decimal("2386.50")), bar(2)]
    result = validate(conflicting, duplicate_policy=DuplicatePolicy.DROP_IDENTICAL)
    assert IssueCode.CONFLICTING_DUPLICATE in codes(result, IssueSeverity.ERROR)


def test_overlapping_bars_are_rejected():
    overlap = bar(1, open_time=T0 + timedelta(minutes=30), close_time=T0 + timedelta(minutes=90))
    result = validate_series([bar(0), overlap], instrument="XAUUSD", timeframe=Timeframe.D1)
    assert IssueCode.OVERLAPPING_BARS in codes(result, IssueSeverity.ERROR)


def test_gaps_are_reported_not_filled():
    bars = [bar(0), bar(1), bar(4), bar(5)]
    result = validate(bars)
    assert not result.has_errors
    assert len(result.candles) == 4  # nothing inserted
    assert DataQualityFlag.GAP_DETECTED in result.flags
    assert [(g.previous_open_time, g.next_open_time, g.missing_intervals) for g in result.gaps] \
        == [(T0 + H, T0 + 4 * H, 2)]
    assert find_gaps([bar(0), bar(1)], Timeframe.H1) == ()


def test_missing_volume_is_flagged():
    result = validate([bar(0), bar(1, volume=None, volume_kind="none")])
    assert DataQualityFlag.MISSING_VOLUME in result.flags and not result.has_errors


def test_precision_beyond_the_declared_precision_is_an_error():
    result = validate([bar(0, close=Decimal("2386.125"), high=Decimal("2387.62"))],
                      declared_price_decimals=2)
    assert IssueCode.PRECISION_EXCEEDS_DECLARED in codes(result, IssueSeverity.ERROR)
    assert validate([bar(0)], declared_price_decimals=2).issues == ()


def test_source_precision_loss_is_flagged_when_the_instrument_precision_is_known():
    result = validate([bar(0)], declared_price_decimals=2, instrument_price_decimals=3)
    assert DataQualityFlag.SOURCE_PRECISION_LOSS in result.flags
    assert validate([bar(0)], declared_price_decimals=2, instrument_price_decimals=2).flags == ()


# --- freshness ---------------------------------------------------------------------


def test_freshness_is_unknown_without_a_configured_threshold():
    fresh = evaluate_freshness(as_of=FIXED_NOW, retrieved_at=FIXED_NOW,
                               source_timestamp=FIXED_NOW - 3 * H, timeframe=Timeframe.H1,
                               max_staleness_intervals=None)
    assert fresh.status is FreshnessStatus.UNKNOWN and fresh.intervals_behind == 3
    assert fresh.expected_interval_seconds == 3600


def test_freshness_against_a_configured_threshold():
    kw = {"as_of": FIXED_NOW, "retrieved_at": FIXED_NOW, "timeframe": Timeframe.H1,
          "max_staleness_intervals": 2}
    assert evaluate_freshness(source_timestamp=FIXED_NOW - 2 * H, **kw).status \
        is FreshnessStatus.FRESH
    stale = evaluate_freshness(source_timestamp=FIXED_NOW - 3 * H, **kw)
    assert stale.status is FreshnessStatus.STALE
    assert stale.stale_reason is StaleReason.OLDER_THAN_MAX_INTERVALS
    assert evaluate_freshness(source_timestamp=None, **kw).status is FreshnessStatus.NO_DATA


def test_freshness_refuses_a_source_timestamp_after_as_of():
    with pytest.raises(ValidationError, match="look-ahead"):
        evaluate_freshness(as_of=FIXED_NOW, retrieved_at=FIXED_NOW,
                           source_timestamp=FIXED_NOW + H, timeframe=Timeframe.H1,
                           max_staleness_intervals=None)
