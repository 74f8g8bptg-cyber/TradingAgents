"""Phase 5: true range, ATR, SMA, EMA, RSI, MACD, Bollinger and volume.

Expected values are hand-computed from the formulas in the module docstrings, on
synthetic closes 1, 2, 3, 4, 5, 4, 3 (a constructed shape, not market data).
"""

from decimal import Decimal

import pytest
from stellar.technical import IndicatorKind, Limitation, analyse
from stellar.technical.candles import candle_features
from stellar.technical.config import BollingerSpec, IndicatorConfig, MacdSpec
from stellar.technical.indicators import (
    bollinger,
    ema_series,
    macd,
    rsi_series,
    sma_series,
)
from stellar.technical.numeric import calc
from stellar.technical.volatility import atr_series
from technical_helpers import TEST_CONFIG, D, config, from_closes, from_ohlc, response

pytestmark = pytest.mark.unit
CLOSES = [D(x) for x in (1, 2, 3, 4, 5, 4, 3)]
EPS = Decimal("1e-30")


def q(a, b):
    with calc():
        return Decimal(a) / Decimal(b)


def close(a, b):
    return a is not None and abs(a - b) < EPS


# --- volatility ---------------------------------------------------------------------------------

TR_ROWS = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 12.5, 11.5, 12), (15, 16, 14.5, 15.5)]


def test_true_range_and_wilder_atr_with_warmup():
    with calc():
        features = candle_features(from_ohlc(TR_ROWS), TEST_CONFIG.candles)
        atr = atr_series(features, 3)
    assert [f.true_range for f in features] == [D(3), D(3), D(1), D(4)]
    assert atr[:2] == [None, None]  # warm-up: no early value
    assert atr[2] == q(7, 3)
    assert close(atr[3], q(26, 9))


def test_atr_in_the_analysis_states_period_and_readiness():
    a = analyse(response(from_ohlc(TR_ROWS)), as_of=from_ohlc(TR_ROWS)[-1].close_time,
                config=TEST_CONFIG)
    atr = a.volatility.atr
    assert atr.parameters == {"period": "3", "smoothing": "wilder"} and atr.warmup_bars == 3
    assert atr.ready and close(atr.value, q(26, 9))
    short = analyse(response(from_ohlc(TR_ROWS[:2])), as_of=from_ohlc(TR_ROWS)[1].close_time,
                    config=TEST_CONFIG)
    assert not short.volatility.atr.ready and short.volatility.atr.value is None
    assert Limitation.INSUFFICIENT_HISTORY in short.limitations


def test_range_expansion_against_a_prior_baseline():
    rows = [(10, 11, 9, 10.5)] * 3 + [(10.5, 14, 9, 13)]
    a = analyse(response(from_ohlc(rows)), as_of=from_ohlc(rows)[-1].close_time,
                config=TEST_CONFIG)
    v = a.volatility
    assert v.mean_range == D(2) and v.latest_relative_range == D("2.5")


# --- moving averages ----------------------------------------------------------------------------


def test_sma_and_ema_are_none_before_warmup_and_exact_after():
    with calc():
        sma, ema = sma_series(CLOSES, 3), ema_series(CLOSES, 3)
    assert sma[:2] == [None, None] and sma[2] == D(2) and sma[6] == D(4)
    assert ema[:2] == [None, None]
    assert ema[2:] == [D(2), D(3), D(4), D(4), D("3.5")]  # seeded with SMA, alpha = 1/2


def test_moving_average_evidence_has_slope_position_and_ordering():
    bars = from_closes([1, 2, 3, 4, 5, 4, 3])
    a = analyse(response(bars), as_of=bars[-1].close_time, config=TEST_CONFIG)
    sma = next(v for v in a.indicators if v.name == "sma_3")
    ema = next(v for v in a.indicators if v.name == "ema_3")
    assert sma.value == D(4) and close(sma.slope, q(-1, 3))  # previous SMA (4+5+4)/3
    assert sma.labels == ("close_below",)
    assert ema.value == D("3.5") and ema.slope == D("-0.5")
    assert a.ma_ordering == ("sma_3", "ema_3")


# --- RSI --------------------------------------------------------------------------------------


def test_rsi_wilder_values_and_warmup():
    with calc():
        rsi = rsi_series(CLOSES, 3)
    assert rsi[:3] == [None, None, None]  # needs n + 1 bars
    assert rsi[3] == 100 and rsi[4] == 100
    with calc():  # RS 2 then 0.8, evaluated in the engine's context
        assert close(rsi[5], 100 - Decimal(100) / 3)
        assert close(rsi[6], 100 - Decimal(100) / Decimal("1.8"))


def test_rsi_is_undefined_not_fifty_when_price_never_moves():
    with calc():
        assert rsi_series([D(5)] * 6, 3)[-1] is None


def test_rsi_zone_labels_only_when_levels_are_configured():
    bars = from_closes([1, 2, 3, 4, 5, 4, 3])
    plain = analyse(response(bars), as_of=bars[-1].close_time, config=TEST_CONFIG)
    rsi = next(v for v in plain.indicators if v.kind is IndicatorKind.RSI)
    assert rsi.labels == ()
    zoned = analyse(response(bars), as_of=bars[-1].close_time,
                    config=config(indicators={**TEST_CONFIG.indicators.model_dump(),
                                              "rsi_upper": "70", "rsi_lower": "30"}))
    rsi = next(v for v in zoned.indicators if v.kind is IndicatorKind.RSI)
    assert rsi.labels == ("rsi_between_levels",)


# --- MACD / Bollinger ---------------------------------------------------------------------------


def test_macd_line_signal_histogram():
    with calc():
        value = macd(CLOSES, MacdSpec(fast=2, slow=3, signal=2))
    assert value.warmup_bars == 4 and value.ready
    assert close(value.value, q(-1, 9))
    assert close(value.components["signal"], q(1, 54))
    assert close(value.components["histogram"], q(-7, 54))
    assert value.labels == ("macd_below_signal",)
    with calc():
        early = macd(CLOSES[:3], MacdSpec(fast=2, slow=3, signal=2))
    assert not early.ready and early.value is None and early.components["signal"] is None


def test_bollinger_population_sd():
    with calc():
        value = bollinger(CLOSES, BollingerSpec(period=3, deviations=D(2)))
        sd = (Decimal(2) / 3).sqrt()
        upper, lower = 4 + 2 * sd, 4 - 2 * sd
    assert value.value == D(4)
    assert close(value.components["upper"], upper)
    assert close(value.components["lower"], lower)
    assert value.labels == ("close_inside_bands",)
    assert value.parameters["sd"] == "population"


def test_no_indicator_without_configuration():
    bars = from_closes([1, 2, 3, 4, 5])
    a = analyse(response(bars), as_of=bars[-1].close_time,
                config=config(indicators=IndicatorConfig()))
    assert a.indicators == () and a.ma_ordering is None
    assert any(u.item == "indicators" for u in a.unevaluated)


def test_indicators_keep_fx_precision():
    bars = from_closes(["1.08231", "1.08254", "1.08219", "1.08247", "1.08262"], wick="0.00005",
                       instrument="EURUSD")
    a = analyse(response(bars, instrument="EURUSD"), as_of=bars[-1].close_time,
                config=TEST_CONFIG)
    sma = next(v for v in a.indicators if v.name == "sma_3")
    with calc():
        assert sma.value == (D("1.08219") + D("1.08247") + D("1.08262")) / 3
    assert sma.value != 0 and str(a.candles[-1].features.close) == "1.08262"


# --- volume -------------------------------------------------------------------------------------


def test_missing_volume_is_unavailable_not_zero():
    bars = from_closes([1, 2, 3, 4])
    a = analyse(response(bars), as_of=bars[-1].close_time, config=TEST_CONFIG)
    assert not a.volume.available and a.volume.latest is None
    assert Limitation.MISSING_VOLUME in a.limitations


@pytest.mark.parametrize("kind,limitation", [("real", None), ("tick", Limitation.TICK_VOLUME_ONLY)])
def test_real_and_tick_volume_stay_distinct(kind, limitation):
    rows = [(10, 11, 9, 10.5, 100), (10.5, 11, 10, 10.8, 100), (10.8, 11, 10.2, 10.3, 100),
            (10.3, 10.6, 10.1, 10.2, 300)]
    bars = from_ohlc(rows, volume_kind=kind)
    a = analyse(response(bars, volume_kind=kind), as_of=bars[-1].close_time, config=TEST_CONFIG)
    assert a.volume.kind.value == kind and a.volume.relative_volume == D(3)
    assert (limitation in a.limitations) if limitation else \
        Limitation.TICK_VOLUME_ONLY not in a.limitations


def test_relative_volume_needs_enough_history():
    rows = [(10, 11, 9, 10.5, 100), (10.5, 11, 10, 10.8, 200)]
    bars = from_ohlc(rows, volume_kind="real")
    a = analyse(response(bars, volume_kind="real"), as_of=bars[-1].close_time,
                config=TEST_CONFIG)
    assert a.volume.available and a.volume.relative_volume is None
