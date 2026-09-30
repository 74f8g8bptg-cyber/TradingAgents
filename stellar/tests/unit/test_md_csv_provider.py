"""Local CSV provider: format, timezones, ordering, duplicates, malformed rows, precision.

All files are SYNTHETIC (see tests/fixtures and the md_helpers labels).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from md_helpers import (
    FIXED_NOW,
    FIXTURES,
    T0,
    H,
    csv_provider,
    fixture_provider,
    request,
    write_csv,
)
from stellar.marketdata import (
    ErrorCode,
    IssueCode,
    MarketDataError,
    MarketDataSource,
    OrderPolicy,
    decimal_places,
)
from stellar.marketdata.providers import CsvFileSpec
from stellar.marketdata.validation import DuplicatePolicy
from stellar.schemas.market import DataQualityFlag, Timeframe
from stellar.serialization import canonical_json

pytestmark = pytest.mark.unit

HEADER = "timestamp,open,high,low,close,volume\n"
ROW = "2030-01-07T{h:02d}:00:00Z,1.08512,1.08561,1.08497,1.08537,1450\n"


def rows(*hours):
    return HEADER + "".join(ROW.format(h=h) for h in hours)


def fail_codes(provider, **req):
    with pytest.raises(MarketDataError) as err:
        provider.candles(request(**req))
    assert err.value.code is ErrorCode.VALIDATION_FAILED
    return {i.code for i in err.value.issues}, err.value


# --- fixtures and protocol ---------------------------------------------------------


def test_fixtures_are_labelled_synthetic():
    for path in FIXTURES.glob("*.csv"):
        assert path.read_text(encoding="utf-8").startswith("# SYNTHETIC TEST DATA"), path
    provider = fixture_provider()
    assert provider.info().synthetic
    assert any("SYNTHETIC" in note for note in provider.read("EURUSD", Timeframe.H1).notes)


def test_provider_implements_the_protocol_and_reports_capabilities():
    provider = fixture_provider()
    assert isinstance(provider, MarketDataSource)
    assert provider.instruments() == ("EURUSD", "NAS100", "USDJPY", "XAUUSD")
    assert provider.timeframes("EURUSD") == (Timeframe.H1,)
    assert provider.timeframes("EURUSD") != (Timeframe.M5,)
    assert provider.mapping("XAUUSD").kind == "EXACT"
    assert provider.metadata("NAS100").display_name == "NAS100"
    with pytest.raises(MarketDataError) as err:
        provider.candles(request(timeframe="M5"))
    assert err.value.code is ErrorCode.UNSUPPORTED_TIMEFRAME
    with pytest.raises(MarketDataError) as err:
        provider.quote("EURUSD", FIXED_NOW)
    assert err.value.code is ErrorCode.UNSUPPORTED_OPERATION


def test_instrument_is_declared_by_the_spec_not_inferred_from_the_file_name(tmp_path):
    path = write_csv(tmp_path, rows(8, 9), name="XAUUSD_H1.csv")  # misleading name
    provider = csv_provider(path, instrument="EURUSD", symbol="EURUSD")
    response = provider.candles(request("EURUSD"))
    assert {c.instrument for c in response.series.candles} == {"EURUSD"}
    with pytest.raises(MarketDataError) as err:
        provider.candles(request("XAUUSD"))
    assert err.value.code is ErrorCode.UNSUPPORTED_INSTRUMENT


# --- precision -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "instrument,first_close,places",
    [("EURUSD", "1.08537", 5), ("USDJPY", "149.872", 3), ("XAUUSD", "2386.35", 2),
     ("NAS100", "18477.00", 2)],
)
def test_source_precision_is_preserved_exactly(instrument, first_close, places):
    response = fixture_provider().candles(request(instrument))
    close = response.series.candles[0].close
    assert close == Decimal(first_close)
    assert str(close) == first_close  # same digits, trailing zeros included
    assert decimal_places(close) == places
    dumped = response.model_dump(mode="json")["series"]["candles"][0]["close"]
    assert dumped == first_close
    assert first_close in canonical_json(response)


def test_eurusd_1_08537_survives_file_parse_validation_serialization_and_reload():
    response = fixture_provider().candles(request("EURUSD"))
    first = response.series.candles[0]
    assert first.close == Decimal("1.08537") and str(first.close) == "1.08537"
    reloaded = type(response).model_validate_json(response.model_dump_json())
    assert str(reloaded.series.candles[0].close) == "1.08537"
    assert reloaded == response
    assert response.quality.observed_price_decimals == 5


def test_no_global_rounding_of_other_instruments_either(tmp_path):
    path = write_csv(tmp_path, HEADER + "2030-01-07T08:00:00Z,149.8125,149.9051,149.7880,"
                                        "149.87215,10\n")
    response = csv_provider(path, instrument="USDJPY", symbol="USDJPY").candles(
        request("USDJPY"))
    assert str(response.series.candles[0].close) == "149.87215"


# --- timezones --------------------------------------------------------------------------


def test_offsets_are_normalised_to_utc(tmp_path):
    body = HEADER + ("2030-01-07T03:00:00-05:00,1.08512,1.08561,1.08497,1.08537,1\n"
                     "2030-01-07T10:00:00+01:00,1.08537,1.08590,1.08520,1.08574,1\n")
    candles = csv_provider(write_csv(tmp_path, body)).candles(request()).series.candles
    assert [c.open_time for c in candles] == [T0, T0 + H]
    assert all(c.open_time.utcoffset() == timedelta(0) for c in candles)


def test_naive_timestamps_need_a_declared_timezone(tmp_path):
    body = HEADER + "2030-01-07T08:00:00,1.08512,1.08561,1.08497,1.08537,1\n"
    found, _ = fail_codes(csv_provider(write_csv(tmp_path, body)))
    assert IssueCode.NAIVE_TIMESTAMP in found
    provider = csv_provider(write_csv(tmp_path, body, "ny.csv"), naive_timezone="America/New_York")
    first = provider.candles(request()).series.candles[0]
    assert first.open_time == datetime(2030, 1, 7, 13, 0, tzinfo=UTC)  # EST = UTC-5


def test_ambiguous_and_nonexistent_local_times_are_rejected(tmp_path):
    # 2030-11-03 01:30 happens twice in New York; 2030-03-10 02:30 never happens.
    ambiguous = HEADER + "2030-11-03T01:30:00,1.08512,1.08561,1.08497,1.08537,1\n"
    missing = HEADER + "2030-03-10T02:30:00,1.08512,1.08561,1.08497,1.08537,1\n"
    for body, code in ((ambiguous, IssueCode.AMBIGUOUS_LOCAL_TIME),
                       (missing, IssueCode.NONEXISTENT_LOCAL_TIME)):
        provider = csv_provider(write_csv(tmp_path, body), naive_timezone="America/New_York")
        found, _ = fail_codes(provider)
        assert code in found


def test_unknown_timezone_is_rejected_in_the_spec(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        CsvFileSpec(path=tmp_path / "x.csv", instrument="EURUSD", timeframe="H1",
                    provider_symbol="EURUSD", naive_timezone="Mars/Olympus")


# --- malformed files and rows -------------------------------------------------------------


@pytest.mark.parametrize(
    "body,code",
    [
        ("timestamp,open,high,low\n", IssueCode.MISSING_COLUMN),
        ("timestamp,open,high,low,close,adj_close\n", IssueCode.MALFORMED_ROW),
        (HEADER + "2030-01-07T08:00:00Z,1.08512,1.08561,1.08497\n", IssueCode.MALFORMED_ROW),
        (HEADER + "yesterday,1.08512,1.08561,1.08497,1.08537,1\n", IssueCode.INVALID_TIMESTAMP),
        (HEADER + "2030-01-07T08:00:00Z,abc,1.08561,1.08497,1.08537,1\n", IssueCode.INVALID_NUMBER),
        (HEADER + "2030-01-07T08:00:00Z,NaN,1.08561,1.08497,1.08537,1\n", IssueCode.INVALID_NUMBER),
        (HEADER + "2030-01-07T08:00:00Z,1.08512,inf,1.08497,1.08537,1\n", IssueCode.INVALID_NUMBER),
        (HEADER + "2030-01-07T08:00:00Z,true,1.08561,1.08497,1.08537,1\n",
         IssueCode.INVALID_NUMBER),
        (HEADER + "2030-01-07T08:00:00Z,1.08512,1.08400,1.08497,1.08537,1\n",
         IssueCode.INVALID_PRICE_RELATION),
        (HEADER + "2030-01-07T08:00:00Z,1.08512,1.08561,1.08497,1.08537,-5\n",
         IssueCode.MALFORMED_ROW),
        (HEADER + "2030-01-07T08:00:00Z,,1.08561,1.08497,1.08537,1\n", IssueCode.INVALID_NUMBER),
    ],
)
def test_malformed_input_is_rejected_with_a_typed_issue(tmp_path, body, code):
    found, err = fail_codes(csv_provider(write_csv(tmp_path, body)))
    assert code in found
    assert err.to_record()["code"] == "VALIDATION_FAILED"


def test_issues_name_the_file_line(tmp_path):
    body = rows(8) + "2030-01-07T09:00:00Z,1.08537,1.08400,1.08520,1.08574,1\n"
    _, err = fail_codes(csv_provider(write_csv(tmp_path, body)))
    bad = [i for i in err.issues if i.code is IssueCode.INVALID_PRICE_RELATION]
    assert bad[0].row == 4  # comment line 1, header line 2, rows 3-4


def test_empty_volume_means_no_volume_not_zero(tmp_path):
    body = HEADER + "2030-01-07T08:00:00Z,1.08512,1.08561,1.08497,1.08537,\n"
    response = csv_provider(write_csv(tmp_path, body)).candles(request())
    candle = response.series.candles[0]
    assert candle.volume is None and candle.volume_kind == "none"
    assert DataQualityFlag.MISSING_VOLUME in response.quality.flags


def test_missing_volume_column_is_flagged_for_nas100():
    response = fixture_provider().candles(request("NAS100"))
    assert all(c.volume is None for c in response.series.candles)
    assert DataQualityFlag.MISSING_VOLUME in response.quality.flags


# --- ordering and duplicates ------------------------------------------------------------------


def test_out_of_order_file_is_rejected_by_default(tmp_path):
    found, _ = fail_codes(csv_provider(write_csv(tmp_path, rows(9, 8, 10))))
    assert IssueCode.OUT_OF_ORDER in found


def test_out_of_order_file_can_be_sorted_explicitly_and_is_flagged(tmp_path):
    provider = csv_provider(write_csv(tmp_path, rows(9, 8, 10)), order_policy=OrderPolicy.SORT)
    response = provider.candles(request())
    assert [c.open_time.hour for c in response.series.candles] == [8, 9, 10]
    assert DataQualityFlag.OUT_OF_ORDER in response.quality.flags


def test_duplicate_rows_are_rejected_by_default_and_can_be_dropped_explicitly(tmp_path):
    path = write_csv(tmp_path, rows(8, 9, 9, 10))
    found, _ = fail_codes(csv_provider(path))
    assert IssueCode.DUPLICATE_BAR in found
    response = csv_provider(path, duplicate_policy=DuplicatePolicy.DROP_IDENTICAL).candles(
        request())
    assert response.quality.bar_count == 3
    assert DataQualityFlag.DUPLICATE_BAR in response.quality.flags


def test_conflicting_duplicates_are_always_rejected(tmp_path):
    body = rows(8, 9) + "2030-01-07T09:00:00Z,1.08512,1.08561,1.08497,1.08540,1450\n"
    path = write_csv(tmp_path, body)
    found, _ = fail_codes(csv_provider(path, duplicate_policy=DuplicatePolicy.DROP_IDENTICAL))
    assert IssueCode.CONFLICTING_DUPLICATE in found


def test_gaps_in_a_file_are_flagged_not_filled(tmp_path):
    response = csv_provider(write_csv(tmp_path, rows(8, 9, 12))).candles(request())
    assert response.quality.bar_count == 3 and response.quality.gap_count == 1
    assert DataQualityFlag.GAP_DETECTED in response.quality.flags


def test_declared_precision_is_enforced(tmp_path):
    body = HEADER + "2030-01-07T08:00:00Z,1.085121,1.08561,1.08497,1.08537,1\n"
    found, _ = fail_codes(csv_provider(write_csv(tmp_path, body), declared_price_decimals=5))
    assert IssueCode.PRECISION_EXCEEDS_DECLARED in found


def test_two_files_for_the_same_series_are_refused(tmp_path):
    from stellar.marketdata.providers import CsvFileProvider

    spec = CsvFileSpec(path=tmp_path / "a.csv", instrument="EURUSD", timeframe="H1",
                       provider_symbol="EURUSD")
    with pytest.raises(ValueError, match="two files"):
        CsvFileProvider(provider_id="p", name="p", files=[spec, spec], price_side="mid",
                        volume_kind="tick")


def test_unreadable_file_is_a_source_error(tmp_path):
    with pytest.raises(MarketDataError) as err:
        csv_provider(tmp_path / "missing.csv").candles(request())
    assert err.value.code is ErrorCode.SOURCE_UNAVAILABLE
