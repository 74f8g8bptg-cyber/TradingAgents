"""Phase 5: candle measurements, rule-based descriptors and sequences (synthetic bars)."""

from decimal import Decimal

import pytest
from stellar.technical import BarDirection, CandleConfig, CandleLabel
from stellar.technical.candles import candle_features, classify
from stellar.technical.numeric import calc
from stellar.technical.sequences import has_run, run_length, sequences
from technical_helpers import TEST_CONFIG, D, candle, from_ohlc

pytestmark = pytest.mark.unit
CFG = TEST_CONFIG.candles


def features(rows, cfg=CFG):
    with calc():
        return candle_features(from_ohlc(rows), cfg)


def labels(rows, cfg=CFG):
    with calc():
        return [e.labels for e in classify(candle_features(from_ohlc(rows), cfg), cfg)]


def test_body_wicks_range_and_ratios_are_exact():
    (f,) = features([(10, 14, 9, 13)])
    assert (f.range, f.body, f.signed_body, f.upper_wick, f.lower_wick) == (
        D(5), D(3), D(3), D(1), D(1))
    assert (f.body_ratio, f.upper_wick_ratio, f.lower_wick_ratio, f.close_location) == (
        D("0.6"), D("0.2"), D("0.2"), D("0.8"))
    assert f.direction is BarDirection.UP and f.gap is None
    assert f.true_range == D(5) and not f.true_range_uses_previous_close


def test_gap_and_true_range_use_the_previous_close():
    _, f = features([(10, 12, 9, 11), (15, 16, 14.5, 15.5)])
    assert f.gap == D(4) and f.true_range == D(5) and f.true_range_uses_previous_close


def test_zero_range_bar_is_safe():
    (f,) = features([(10, 10, 10, 10)])
    assert f.range == 0 and f.direction is BarDirection.FLAT
    assert f.body_ratio is f.upper_wick_ratio is f.lower_wick_ratio is f.close_location is None
    (lab,) = labels([(10, 10, 10, 10)])
    assert CandleLabel.NEUTRAL in lab and CandleLabel.DOJI_LIKE not in lab


def test_source_precision_is_preserved():
    bar = candle("1.08231", "1.08254", "1.08219", "1.08247", i=0, instrument="EURUSD")
    with calc():
        (f,) = candle_features([bar], CFG)
    assert f.range == Decimal("0.00035") and f.body == Decimal("0.00016")
    assert str(f.upper_wick) == "0.00007"


@pytest.mark.parametrize("row,label", [
    ((10, 12, 9, 11.5), CandleLabel.BULLISH),
    ((11.5, 12, 9, 10), CandleLabel.BEARISH),
    ((10, 12, 9, 10), CandleLabel.NEUTRAL),
])
def test_direction_labels(row, label):
    assert label in labels([row])[0]


def test_threshold_labels_follow_configured_ratios():
    doji, big, upper, lower = labels([(10, 11, 9, 10.1), (9, 11, 9, 11), (10, 14, 9.5, 10.5),
                                      (13, 13.5, 9, 13.2)])
    assert CandleLabel.DOJI_LIKE in doji and CandleLabel.SMALL_BODY in doji
    assert CandleLabel.LARGE_BODY in big and CandleLabel.DOJI_LIKE not in big
    assert CandleLabel.UPPER_REJECTION in upper and CandleLabel.LOWER_REJECTION not in upper
    assert CandleLabel.LOWER_REJECTION in lower


def test_unset_thresholds_are_reported_not_guessed():
    (evidence,) = classify(candle_features(from_ohlc([(10, 11, 9, 10.05)]), CandleConfig()),
                           CandleConfig())
    assert set(evidence.labels) == {CandleLabel.BULLISH}
    unevaluated = {u.item: u.reason for u in evidence.unevaluated}
    assert unevaluated["doji_like"] == "threshold_unset"
    assert unevaluated["upper_rejection"] == "threshold_unset"
    assert unevaluated["expansion_bar"] == "threshold_unset"
    assert evidence.features.body_ratio == Decimal("0.025")  # the raw measurement still exists


def test_inside_outside_and_engulfing_definitions():
    rows = [(10, 12, 8, 11), (11, 11.5, 9, 10), (9.5, 13, 7.5, 12), (12, 12.5, 11, 11.2)]
    lab = labels(rows)
    assert CandleLabel.INSIDE_BAR in lab[1]
    assert CandleLabel.OUTSIDE_BAR in lab[2] and CandleLabel.BULLISH_ENGULFING in lab[2]
    assert CandleLabel.INSIDE_BAR in lab[3]
    bearish = labels([(10, 11, 9.5, 10.8), (11, 11.2, 9, 9.8)])[1]
    assert CandleLabel.BEARISH_ENGULFING in bearish


def test_equal_extremes_are_neither_inside_nor_outside():
    lab = labels([(10, 12, 8, 11), (11, 12, 9, 10)])[1]  # same high
    assert CandleLabel.INSIDE_BAR not in lab and CandleLabel.OUTSIDE_BAR not in lab


def test_expansion_and_contraction_need_a_baseline():
    rows = [(10, 11, 9, 10.5)] * 3 + [(10.5, 14, 9, 13), (13, 13.4, 12.8, 13.1)]
    fs = features(rows)
    assert fs[2].relative_range is None  # fewer than 3 earlier bars
    assert fs[3].relative_range == D("2.5")
    lab = labels(rows)
    assert CandleLabel.EXPANSION_BAR in lab[3] and CandleLabel.CONTRACTION_BAR in lab[4]


def test_sequences_count_runs_without_assuming_n():
    rows = [(10, 11, 9, 10.5), (10.5, 11, 10, 10.8), (10.8, 10.9, 10.2, 10.3),
            (10.3, 10.6, 10.1, 10.2), (10.2, 10.4, 10.15, 10.18)]
    with calc():
        evidence = classify(candle_features(from_ohlc(rows), CFG), CFG)
    seq = sequences(evidence, rejection_configured=True)
    assert (seq.consecutive_down, seq.consecutive_up) == (3, 0)
    # ranges 2, 1, 0.7, 0.5, 0.25; highs 11, 11, 10.9, 10.6, 10.4; lows ... 10.2, 10.1, 10.15
    assert seq.shrinking_bodies == 2 and seq.shrinking_ranges == 4
    assert seq.lower_highs == 3 and seq.higher_lows == 1 and seq.alternating == 1
    assert seq.upper_rejections is not None
    assert sequences(evidence, rejection_configured=False).upper_rejections is None


def test_a_counter_sequence_is_a_count_not_a_signal():
    rows = [(10, 11, 9.8, 10.9), (10.9, 12, 10.8, 11.9), (11.9, 12.1, 11.4, 11.5),
            (11.5, 11.6, 11.1, 11.2)]
    feats = features(rows)
    assert run_length(feats, lambda f: f.direction is BarDirection.DOWN) == 2
    assert has_run(feats, lambda f: f.direction is BarDirection.DOWN, 2)
    assert not has_run(feats, lambda f: f.direction is BarDirection.DOWN, 3)


def test_alternating_run_and_flat_bar():
    rows = [(10, 11, 9, 11), (11, 11.5, 10, 10.2), (10.2, 11, 10, 10.9), (10.9, 11, 10.5, 10.6)]
    with calc():
        ev = classify(candle_features(from_ohlc(rows), CFG), CFG)
    assert sequences(ev, rejection_configured=False).alternating == 4
    flat = rows + [(10.6, 10.8, 10.4, 10.6)]
    with calc():
        ev = classify(candle_features(from_ohlc(flat), CFG), CFG)
    assert sequences(ev, rejection_configured=False).alternating == 0
