"""Candle measurements and rule-based descriptors (Foundation §4.10).

Measurements (always computed; ratios are None for a zero-range bar):
- range = high - low; body = |close - open|; signed_body = close - open;
- upper_wick = high - max(open, close); lower_wick = min(open, close) - low;
- body / upper-wick / lower-wick ratio = value / range; close_location = (close - low) / range;
- gap = open - previous close (None for the first bar);
- true range = max(high - low, |high - previous close|, |low - previous close|), and
  high - low for the first bar (flagged ``true_range_uses_previous_close = False``);
- relative_range = range / mean range of the preceding ``relative_range_lookback`` bars.

Descriptors. Definitional ones need no threshold:
- BULLISH (close > open), BEARISH (close < open), NEUTRAL (close == open);
- INSIDE_BAR: high < previous high **and** low > previous low (strict);
- OUTSIDE_BAR: high > previous high **and** low < previous low (strict);
- BULLISH_ENGULFING: previous bar BEARISH, this bar BULLISH, and this body contains the
  previous body (open <= previous close, close >= previous open) and is larger;
- BEARISH_ENGULFING: the mirror image.

Threshold descriptors are evaluated only when configured; otherwise they are listed as
unevaluated (``threshold_unset``):
- DOJI_LIKE, SMALL_BODY and LARGE_BODY compare ``body_ratio``;
- UPPER_REJECTION and LOWER_REJECTION compare the wick ratios;
- EXPANSION_BAR and CONTRACTION_BAR compare ``relative_range``.

A descriptor is an observation of geometry. None of them implies a direction to trade.
"""

from __future__ import annotations

from collections.abc import Sequence

from stellar.schemas.market import Candle
from stellar.technical.config import CandleConfig
from stellar.technical.models import (
    BarDirection,
    CandleEvidence,
    CandleFeatures,
    CandleLabel,
    Unevaluated,
)
from stellar.technical.numeric import mean, ratio


def candle_features(candles: Sequence[Candle], config: CandleConfig) -> list[CandleFeatures]:
    out: list[CandleFeatures] = []
    lookback = config.relative_range_lookback
    for i, c in enumerate(candles):
        prev = candles[i - 1] if i > 0 else None
        rng = c.high - c.low
        top, bottom = max(c.open, c.close), min(c.open, c.close)
        direction = BarDirection.UP if c.close > c.open else (
            BarDirection.DOWN if c.close < c.open else BarDirection.FLAT)
        if prev is None:
            true_range = rng
        else:
            true_range = max(rng, abs(c.high - prev.close), abs(c.low - prev.close))
        relative = None
        if lookback is not None and i >= lookback:
            relative = ratio(rng, mean([x.high - x.low for x in candles[i - lookback:i]]))
        out.append(CandleFeatures(
            index=i, open_time=c.open_time, close_time=c.close_time, open=c.open, high=c.high,
            low=c.low, close=c.close, direction=direction, range=rng, body=top - bottom,
            signed_body=c.close - c.open, upper_wick=c.high - top, lower_wick=bottom - c.low,
            body_ratio=ratio(top - bottom, rng), upper_wick_ratio=ratio(c.high - top, rng),
            lower_wick_ratio=ratio(bottom - c.low, rng),
            close_location=ratio(c.close - c.low, rng),
            gap=None if prev is None else c.open - prev.close,
            true_range=true_range, true_range_uses_previous_close=prev is not None,
            relative_range=relative))
    return out


def _threshold(labels: list[CandleLabel], missing: list[Unevaluated], label: CandleLabel,
               threshold, value, *, at_most: bool) -> None:
    if threshold is None:
        missing.append(Unevaluated(item=label.value.lower(), reason="threshold_unset"))
    elif value is None:
        missing.append(Unevaluated(item=label.value.lower(), reason="not_computable"))
    elif (value <= threshold) if at_most else (value >= threshold):
        labels.append(label)


def classify(features: Sequence[CandleFeatures], config: CandleConfig) -> list[CandleEvidence]:
    out: list[CandleEvidence] = []
    for i, f in enumerate(features):
        labels: list[CandleLabel] = [{BarDirection.UP: CandleLabel.BULLISH,
                                      BarDirection.DOWN: CandleLabel.BEARISH,
                                      BarDirection.FLAT: CandleLabel.NEUTRAL}[f.direction]]
        missing: list[Unevaluated] = []
        _threshold(labels, missing, CandleLabel.DOJI_LIKE, config.doji_max_body_ratio,
                   f.body_ratio, at_most=True)
        _threshold(labels, missing, CandleLabel.SMALL_BODY, config.small_body_max_ratio,
                   f.body_ratio, at_most=True)
        _threshold(labels, missing, CandleLabel.LARGE_BODY, config.large_body_min_ratio,
                   f.body_ratio, at_most=False)
        _threshold(labels, missing, CandleLabel.UPPER_REJECTION, config.rejection_wick_min_ratio,
                   f.upper_wick_ratio, at_most=False)
        _threshold(labels, missing, CandleLabel.LOWER_REJECTION, config.rejection_wick_min_ratio,
                   f.lower_wick_ratio, at_most=False)
        _threshold(labels, missing, CandleLabel.EXPANSION_BAR,
                   config.expansion_min_relative_range, f.relative_range, at_most=False)
        _threshold(labels, missing, CandleLabel.CONTRACTION_BAR,
                   config.contraction_max_relative_range, f.relative_range, at_most=True)
        if i > 0:
            p = features[i - 1]
            if f.high < p.high and f.low > p.low:
                labels.append(CandleLabel.INSIDE_BAR)
            if f.high > p.high and f.low < p.low:
                labels.append(CandleLabel.OUTSIDE_BAR)
            if p.direction is BarDirection.DOWN and f.direction is BarDirection.UP and \
                    f.open <= p.close and f.close >= p.open and f.body > p.body:
                labels.append(CandleLabel.BULLISH_ENGULFING)
            if p.direction is BarDirection.UP and f.direction is BarDirection.DOWN and \
                    f.open >= p.close and f.close <= p.open and f.body > p.body:
                labels.append(CandleLabel.BEARISH_ENGULFING)
        out.append(CandleEvidence(features=f, labels=tuple(labels), unevaluated=tuple(missing)))
    return out
