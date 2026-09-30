"""True range, ATR and range statistics. No warm-up value is ever filled in.

ATR(n) (Wilder), with n = ``atr_period``:
- TR_0 = high - low (no previous close); TR_i = max(high - low, |high - prev close|,
  |low - prev close|);
- ATR is first defined at index n - 1, as the mean of TR_0 .. TR_{n-1};
- after that, ATR_i = (ATR_{i-1} * (n - 1) + TR_i) / n;
- before index n - 1 the ATR is None (warm-up: n bars).

Range statistics use the ``range_lookback`` bars *before* the latest bar, so the latest
bar's own range is compared with a baseline that does not include it.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from stellar.technical.models import CandleFeatures, IndicatorKind, IndicatorValue, Volatility
from stellar.technical.numeric import mean, ratio


def atr_series(features: Sequence[CandleFeatures], period: int) -> list[Decimal | None]:
    out: list[Decimal | None] = [None] * len(features)
    if len(features) < period:
        return out
    tr = [f.true_range for f in features]
    atr = mean(tr[:period])
    out[period - 1] = atr
    for i in range(period, len(features)):
        atr = (atr * (period - 1) + tr[i]) / period
        out[i] = atr
    return out


def atr_value(series: Sequence[Decimal | None], period: int) -> IndicatorValue:
    latest = series[-1] if series else None
    previous = series[-2] if len(series) > 1 else None
    return IndicatorValue(
        name=f"atr_{period}", kind=IndicatorKind.ATR, parameters={"period": str(period),
                                                                  "smoothing": "wilder"},
        warmup_bars=period, bars_available=len(series), ready=latest is not None,
        value=latest, previous=previous,
        slope=None if latest is None or previous is None else latest - previous)


def volatility(features: Sequence[CandleFeatures], *, atr_period: int | None,
               range_lookback: int | None,
               atr: Sequence[Decimal | None] | None) -> Volatility:
    latest = features[-1]
    stats: dict = {}
    if range_lookback is not None and len(features) > range_lookback:
        window = [f.range for f in features[-1 - range_lookback:-1]]
        stats = {"range_lookback": range_lookback, "mean_range": mean(window),
                 "min_range": min(window), "max_range": max(window),
                 "latest_relative_range": ratio(latest.range, mean(window))}
    elif range_lookback is not None:
        stats = {"range_lookback": range_lookback}
    return Volatility(true_range=latest.true_range,
                      atr=None if atr_period is None or atr is None else atr_value(atr, atr_period),
                      **stats)
