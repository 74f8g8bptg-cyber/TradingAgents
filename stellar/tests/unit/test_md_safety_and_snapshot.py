"""Proxy safety, point-in-time access, response guards, serialization and snapshots.

All data is SYNTHETIC.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from md_helpers import (
    FIXED_NOW,
    T0,
    H,
    bar,
    csv_provider,
    fixture_provider,
    memory_provider,
    quote,
    request,
    write_csv,
)
from pydantic import ValidationError
from stellar.marketdata import (
    ErrorCode,
    FreshnessStatus,
    LookAheadError,
    MappingKind,
    MarketDataError,
    MarketDataResponse,
    SubstitutionPolicy,
    VerifiedMarketSnapshot,
    assert_no_look_ahead,
    build_verified_snapshot,
    candle_columns,
    known_at,
)
from stellar.schemas.market import DataQualityFlag
from stellar.serialization import canonical_json, sha256_hex

pytestmark = pytest.mark.unit

ALLOW_PROXY = SubstitutionPolicy(allow_proxy=True)
GC_F = {"symbol": "GC=F", "kind": MappingKind.PROXY,
        "description": "COMEX gold futures (front month), not spot XAU/USD"}
NDX = {"symbol": "^NDX", "kind": MappingKind.PROXY,
       "description": "Nasdaq-100 cash index, not the NAS100 CFD"}
CONFIG_HASH = sha256_hex("synthetic-test-config")


# --- no silent proxy substitution ----------------------------------------------------------


def _proxy_memory(instrument, spec, n=3):
    base = Decimal("2385.12") if instrument == "XAUUSD" else Decimal("18456.25")
    bars = [bar(i, instrument=instrument, symbol=spec["symbol"], proxy=True, base=base)
            for i in range(n)]
    return memory_provider(instrument, symbol=spec["symbol"], kind=spec["kind"],
                           description=spec["description"], bars=bars)


@pytest.mark.parametrize("instrument,spec", [("XAUUSD", GC_F), ("NAS100", NDX)])
def test_proxy_data_is_refused_by_default(instrument, spec):
    provider = _proxy_memory(instrument, spec)
    with pytest.raises(MarketDataError) as err:
        provider.candles(request(instrument))
    assert err.value.code is ErrorCode.PROXY_NOT_ALLOWED
    assert spec["symbol"] in err.value.detail


def test_xauusd_request_never_silently_returns_gc_f(tmp_path):
    body = ("timestamp,open,high,low,close,volume\n"
            "2030-01-07T08:00:00Z,2395.10,2398.40,2393.80,2396.70,10\n")
    provider = csv_provider(write_csv(tmp_path, body), instrument="XAUUSD", symbol="GC=F",
                            kind=MappingKind.PROXY, description=GC_F["description"])
    with pytest.raises(MarketDataError) as err:
        provider.candles(request("XAUUSD"))
    assert err.value.code is ErrorCode.PROXY_NOT_ALLOWED


def test_nas100_request_never_silently_returns_ndx(tmp_path):
    body = ("timestamp,open,high,low,close\n"
            "2030-01-07T14:00:00Z,18460.10,18480.00,18455.00,18470.25\n")
    provider = csv_provider(write_csv(tmp_path, body), instrument="NAS100", symbol="^NDX",
                            kind=MappingKind.PROXY, description=NDX["description"])
    with pytest.raises(MarketDataError) as err:
        provider.candles(request("NAS100"))
    assert err.value.code is ErrorCode.PROXY_NOT_ALLOWED


@pytest.mark.parametrize("instrument,spec", [("XAUUSD", GC_F), ("NAS100", NDX)])
def test_explicitly_allowed_proxy_is_labelled_everywhere(instrument, spec):
    response = _proxy_memory(instrument, spec).candles(request(instrument, substitution=ALLOW_PROXY))
    assert response.request.instrument == instrument  # canonical identity unchanged
    assert response.mapping.kind is MappingKind.PROXY
    assert response.mapping.provider_symbol == spec["symbol"]  # provenance of what was used
    assert DataQualityFlag.PROXY_SOURCE in response.quality.flags
    assert all(c.proxy and c.provider_symbol == spec["symbol"] and c.instrument == instrument
               for c in response.series.candles)


def test_derived_data_needs_its_own_opt_in():
    bars = [bar(i, proxy=True, symbol="SYNTH_XAU") for i in range(3)]
    provider = memory_provider(symbol="SYNTH_XAU", kind=MappingKind.DERIVED,
                               description="synthetic cross of two series", bars=bars)
    with pytest.raises(MarketDataError) as err:
        provider.candles(request("XAUUSD", substitution=ALLOW_PROXY))
    assert err.value.code is ErrorCode.DERIVED_NOT_ALLOWED
    response = provider.candles(request("XAUUSD",
                                        substitution=SubstitutionPolicy(allow_derived=True)))
    assert DataQualityFlag.DERIVED_SOURCE in response.quality.flags


def test_mislabelled_source_bars_are_rejected():
    # A provider whose bars claim to be exact while its mapping says proxy.
    bars = [bar(i, symbol="GC=F", proxy=False) for i in range(2)]
    provider = memory_provider(symbol="GC=F", kind=MappingKind.PROXY,
                               description=GC_F["description"], bars=bars)
    with pytest.raises(MarketDataError) as err:
        provider.candles(request("XAUUSD", substitution=ALLOW_PROXY))
    assert err.value.code is ErrorCode.MALFORMED_SOURCE


def test_unknown_or_unsupported_instruments():
    with pytest.raises(ValidationError):
        request("GOLD")  # not a canonical id: refused before any provider is asked
    with pytest.raises(MarketDataError) as err:
        memory_provider().candles(request("EURUSD"))  # canonical, but this provider lacks it
    assert err.value.code is ErrorCode.UNSUPPORTED_INSTRUMENT


# --- point in time ----------------------------------------------------------------------------


def test_no_bar_after_as_of_is_returned():
    provider = memory_provider(n=10)
    as_of = T0 + 4 * H  # bars 0-3 have closed; bar 4 opens exactly at as_of
    response = provider.candles(request("XAUUSD", as_of=as_of))
    assert [c.open_time for c in response.series.candles] == [T0 + i * H for i in range(4)]
    assert all(c.close_time <= as_of for c in response.series.candles)


def test_a_bar_still_forming_at_as_of_is_excluded():
    provider = memory_provider(n=10)
    response = provider.candles(request("XAUUSD", as_of=T0 + 4 * H + timedelta(minutes=59)))
    assert response.series.candles[-1].open_time == T0 + 3 * H  # bar 4 has not closed


def test_as_of_exactly_at_a_close_includes_that_bar():
    response = memory_provider(n=10).candles(request("XAUUSD", as_of=T0 + 5 * H))
    assert response.series.candles[-1].close_time == T0 + 5 * H


def test_as_of_before_all_data_returns_no_data_not_future_bars():
    response = memory_provider(n=3).candles(request("XAUUSD", as_of=T0))
    assert response.series is None and response.quality.bar_count == 0
    assert response.freshness.status is FreshnessStatus.NO_DATA


def test_window_bounds_and_end_after_as_of():
    provider = memory_provider(n=10)
    response = provider.candles(request("XAUUSD", as_of=T0 + 6 * H, start=T0 + 2 * H,
                                        end=T0 + 9 * H))
    assert [c.open_time for c in response.series.candles] == [T0 + i * H for i in range(2, 6)]


def test_csv_provider_is_point_in_time_too():
    response = fixture_provider().candles(request("EURUSD", as_of=T0 + 2 * H))
    assert [c.close for c in response.series.candles] == [Decimal("1.08537"), Decimal("1.08574")]


def test_helpers_detect_look_ahead():
    bars = [bar(i) for i in range(5)]
    assert len(known_at(bars, T0 + 3 * H)) == 3
    assert_no_look_ahead(bars[:3], T0 + 3 * H)
    with pytest.raises(LookAheadError):
        assert_no_look_ahead(bars, T0 + 3 * H)


def test_quotes_are_point_in_time():
    quotes = [quote(T0 + i * H) for i in range(5)]
    provider = memory_provider(quotes={"XAUUSD": quotes})
    answer = provider.quote("XAUUSD", T0 + 2 * H + timedelta(minutes=30))
    assert answer.quote.ts == T0 + 2 * H
    with pytest.raises(MarketDataError) as err:
        provider.quote("XAUUSD", T0 - H)
    assert err.value.code is ErrorCode.NO_DATA


def test_a_response_cannot_be_built_with_look_ahead_or_unlabelled_proxies():
    good = memory_provider(n=5).candles(request("XAUUSD", as_of=T0 + 3 * H))
    data = good.model_dump()
    data["request"]["as_of"] = T0 + 2 * H
    data["freshness"]["as_of"] = T0 + 2 * H
    data["freshness"]["source_timestamp"] = T0 + 2 * H
    with pytest.raises(ValidationError, match="look-ahead"):
        MarketDataResponse.model_validate(data)
    proxy = _proxy_memory("XAUUSD", GC_F).candles(request("XAUUSD", substitution=ALLOW_PROXY))
    data = proxy.model_dump()
    data["quality"]["flags"] = []
    with pytest.raises(ValidationError, match="PROXY_SOURCE"):
        MarketDataResponse.model_validate(data)
    data = proxy.model_dump()
    data["request"]["substitution"] = {"allow_proxy": False, "allow_derived": False}
    with pytest.raises(ValidationError, match="not allowed"):
        MarketDataResponse.model_validate(data)


# --- quality, freshness and partial coverage -----------------------------------------------------


def test_freshness_and_stale_flag_use_the_requested_threshold():
    provider = memory_provider(n=3)  # last bar closes at T0 + 3H
    stale = provider.candles(request("XAUUSD", as_of=T0 + 8 * H, max_staleness_intervals=2))
    assert stale.freshness.status is FreshnessStatus.STALE
    assert stale.freshness.intervals_behind == 5
    assert DataQualityFlag.STALE in stale.quality.flags
    fresh = provider.candles(request("XAUUSD", as_of=T0 + 4 * H, max_staleness_intervals=2))
    assert fresh.freshness.status is FreshnessStatus.FRESH
    unknown = provider.candles(request("XAUUSD", as_of=T0 + 8 * H))
    assert unknown.freshness.status is FreshnessStatus.UNKNOWN
    assert DataQualityFlag.STALE not in unknown.quality.flags
    assert unknown.freshness.retrieved_at == FIXED_NOW
    assert unknown.freshness.source_timestamp == T0 + 3 * H


def test_partial_series_is_flagged_when_the_range_is_not_covered():
    provider = memory_provider(n=3)
    partial = provider.candles(request("XAUUSD", as_of=T0 + 10 * H, start=T0 - 5 * H,
                                       end=T0 + 8 * H))
    assert DataQualityFlag.PARTIAL_SERIES in partial.quality.flags
    full = provider.candles(request("XAUUSD", as_of=T0 + 3 * H, start=T0, end=T0 + 2 * H))
    assert DataQualityFlag.PARTIAL_SERIES not in full.quality.flags


def test_gaps_reported_for_the_returned_slice_only():
    bars = [bar(0), bar(1), bar(5), bar(6)]
    provider = memory_provider(bars=bars)
    before_gap = provider.candles(request("XAUUSD", as_of=T0 + 2 * H))
    assert DataQualityFlag.GAP_DETECTED not in before_gap.quality.flags
    with_gap = provider.candles(request("XAUUSD", as_of=T0 + 7 * H))
    assert with_gap.quality.gap_count == 1 and DataQualityFlag.GAP_DETECTED in \
        with_gap.quality.flags


# --- deterministic serialization and research access --------------------------------------------


def test_serialization_is_deterministic():
    one = fixture_provider().candles(request("EURUSD"))
    two = fixture_provider().candles(request("EURUSD"))
    assert canonical_json(one) == canonical_json(two)
    assert one.series.content_hash == two.series.content_hash
    assert type(one).model_validate_json(one.model_dump_json()) == one


def test_candle_columns_preserve_values_and_order():
    response = fixture_provider().candles(request("USDJPY"))
    columns = candle_columns(response.series.candles)
    assert columns["close"] == (Decimal("149.872"), Decimal("149.943"), Decimal("149.901"))
    assert list(columns["open_time"]) == sorted(columns["open_time"])


# --- verified snapshot --------------------------------------------------------------------------


def test_snapshot_contains_only_values_from_the_validated_input():
    response = fixture_provider().candles(request("EURUSD"))
    snap = build_verified_snapshot(response, snapshot_id="snap_eurusd_1", created_at=FIXED_NOW,
                                   config_hash=CONFIG_HASH)
    last = response.series.candles[-1]
    assert snap.latest_bar == last  # the very same values, no recomputation
    assert str(snap.latest_bar.close) == "1.08510"
    assert snap.bar_count == 5 and snap.series_hash == response.series.content_hash
    assert snap.first_bar_open_time == response.series.candles[0].open_time
    assert snap.last_bar_close_time == last.close_time
    assert snap.provenance.produced_by == "data_validator"
    assert snap.source.synthetic and snap.mapping.kind == "EXACT"
    assert snap.freshness == response.freshness and snap.quality == response.quality
    # No indicator or other computed price appears anywhere in the snapshot.
    prices = {str(v) for c in response.series.candles for v in (c.open, c.high, c.low, c.close)}
    dumped = snap.model_dump(mode="json")["latest_bar"]
    assert {dumped[k] for k in ("open", "high", "low", "close")} <= prices
    assert not {"rsi", "ema", "sma", "atr", "macd"} & set(snap.model_dump())


def test_snapshot_with_a_point_in_time_quote():
    provider = memory_provider(quotes={"XAUUSD": [quote(T0 + i * H) for i in range(6)]})
    as_of = T0 + 4 * H
    response = provider.candles(request("XAUUSD", as_of=as_of))
    snap = build_verified_snapshot(response, snapshot_id="snap_xau_1", created_at=FIXED_NOW,
                                   config_hash=CONFIG_HASH,
                                   quote=provider.quote("XAUUSD", as_of))
    assert snap.latest_quote.ts == as_of and str(snap.latest_quote.bid) == "2390.11"
    assert snap.quote_mapping.provider_symbol == "XAUUSD"


def test_snapshot_keeps_proxy_labels():
    response = _proxy_memory("NAS100", NDX).candles(request("NAS100", substitution=ALLOW_PROXY))
    snap = build_verified_snapshot(response, snapshot_id="snap_nas_1", created_at=FIXED_NOW,
                                   config_hash=CONFIG_HASH)
    assert snap.latest_bar.proxy and snap.mapping.provider_symbol == "^NDX"
    assert DataQualityFlag.PROXY_SOURCE in snap.quality.flags


def test_snapshot_refuses_empty_data_and_look_ahead():
    empty = memory_provider(n=3).candles(request("XAUUSD", as_of=T0))
    with pytest.raises(MarketDataError) as err:
        build_verified_snapshot(empty, snapshot_id="snap_x", created_at=FIXED_NOW,
                                config_hash=CONFIG_HASH)
    assert err.value.code is ErrorCode.NO_DATA
    response = memory_provider(n=3).candles(request("XAUUSD", as_of=T0 + 3 * H))
    snap = build_verified_snapshot(response, snapshot_id="snap_y", created_at=FIXED_NOW,
                                   config_hash=CONFIG_HASH)
    data = snap.model_dump()
    data["as_of"] = T0 + 2 * H
    data["freshness"]["as_of"] = T0 + 2 * H
    with pytest.raises(ValidationError):
        VerifiedMarketSnapshot.model_validate(data)
    later_quote = memory_provider(quotes={"XAUUSD": [quote(T0 + 5 * H)]}).quote(
        "XAUUSD", T0 + 5 * H)
    with pytest.raises(MarketDataError):
        build_verified_snapshot(response, snapshot_id="snap_z", created_at=FIXED_NOW,
                                config_hash=CONFIG_HASH, quote=later_quote)
