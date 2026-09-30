"""Moving averages, RSI, MACD and Bollinger Bands on closes, in Decimal.

No period is a default: each indicator exists only when its parameters are configured.
Values before the warm-up are None, never partial averages (the audited upstream
``min_periods=1`` behaviour is not reproduced).

Formulas:
- **SMA(n)** = mean of the last n closes. Warm-up: n bars.
- **EMA(n)**: seeded with SMA(n) at index n - 1, then EMA_i = EMA_{i-1} + a * (close_i -
  EMA_{i-1}) with a = 2 / (n + 1). Warm-up: n bars. No ``adjust=True`` reweighting.
- **RSI(n)** (Wilder):
  - changes d_i = close_i - close_{i-1};
  - the first average gain and loss are the means of d_1..d_n (gains = max(d, 0),
    losses = max(-d, 0));
  - then avg_i = (avg_{i-1} * (n - 1) + x_i) / n;
  - RSI = 100 - 100 / (1 + avg_gain / avg_loss); it is 100 when avg_loss = 0 < avg_gain,
    and **undefined (None)** when both are 0 (no invented 50);
  - warm-up: n + 1 bars.
- **MACD(f, s, g)**:
  - MACD line = EMA(f) - EMA(s), defined from index s - 1;
  - signal = EMA(g) of the MACD line, seeded with the SMA of its first g values;
  - histogram = MACD - signal;
  - warm-up: s + g - 1 bars for the signal and histogram.
- **Bollinger(n, k)**:
  - middle = SMA(n); sd = **population** standard deviation of the last n closes (divide
    by n);
  - upper / lower = middle +/- k * sd;
  - bandwidth = (upper - lower) / middle;
  - %B = (close - lower) / (upper - lower), None when the bands coincide;
  - warm-up: n bars.

Labels are descriptive comparisons (``close_above``, ``rsi_above_upper`` when levels are
configured, ``macd_above_signal``). None is a signal.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from stellar.technical.config import BollingerSpec, IndicatorConfig, MacdSpec
from stellar.technical.models import IndicatorKind, IndicatorValue
from stellar.technical.numeric import ZERO, mean, ratio

Series = list[Decimal | None]


def sma_series(values: Sequence[Decimal], n: int) -> Series:
    out: Series = [None] * len(values)
    for i in range(n - 1, len(values)):
        out[i] = mean(values[i - n + 1:i + 1])
    return out


def ema_series(values: Sequence[Decimal | None], n: int) -> Series:
    """EMA of a series that may start with None (e.g. a MACD line); seeded with an SMA."""
    out: Series = [None] * len(values)
    start = next((i for i, v in enumerate(values) if v is not None), None)
    if start is None or len(values) - start < n:
        return out
    alpha = Decimal(2) / (n + 1)
    ema = mean(list(values[start:start + n]))  # type: ignore[arg-type]
    out[start + n - 1] = ema
    for i in range(start + n, len(values)):
        ema = ema + alpha * (values[i] - ema)  # type: ignore[operator]
        out[i] = ema
    return out


def rsi_series(closes: Sequence[Decimal], n: int) -> Series:
    out: Series = [None] * len(closes)
    if len(closes) < n + 1:
        return out
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gain = mean([max(d, ZERO) for d in changes[:n]])
    loss = mean([max(-d, ZERO) for d in changes[:n]])
    out[n] = _rsi(gain, loss)
    for i in range(n + 1, len(closes)):
        d = changes[i - 1]
        gain = (gain * (n - 1) + max(d, ZERO)) / n
        loss = (loss * (n - 1) + max(-d, ZERO)) / n
        out[i] = _rsi(gain, loss)
    return out


def _rsi(gain: Decimal, loss: Decimal) -> Decimal | None:
    if loss == 0:
        return None if gain == 0 else Decimal(100)
    return 100 - 100 / (1 + gain / loss)


def _latest(series: Series) -> tuple[Decimal | None, Decimal | None]:
    latest = series[-1] if series else None
    previous = series[-2] if len(series) > 1 else None
    return latest, previous


def _value(name: str, kind: IndicatorKind, parameters: dict[str, str], warmup: int,
           series: Series, *, components: dict | None = None,
           labels: Sequence[str] = ()) -> IndicatorValue:
    latest, previous = _latest(series)
    return IndicatorValue(
        name=name, kind=kind, parameters=parameters, warmup_bars=warmup,
        bars_available=len(series), ready=latest is not None, value=latest, previous=previous,
        slope=None if latest is None or previous is None else latest - previous,
        components=components or {}, labels=tuple(labels))


def _position(close: Decimal, value: Decimal | None) -> list[str]:
    if value is None:
        return []
    return ["close_above" if close > value else "close_below" if close < value else "close_at"]


def moving_averages(closes: Sequence[Decimal], config: IndicatorConfig) -> list[IndicatorValue]:
    out = []
    for n in config.sma_periods:
        series = sma_series(closes, n)
        out.append(_value(f"sma_{n}", IndicatorKind.SMA, {"period": str(n)}, n, series,
                          labels=_position(closes[-1], series[-1])))
    for n in config.ema_periods:
        series = ema_series(closes, n)
        out.append(_value(f"ema_{n}", IndicatorKind.EMA, {"period": str(n), "seed": "sma"}, n,
                          series, labels=_position(closes[-1], series[-1])))
    return out


def ma_ordering(values: Sequence[IndicatorValue]) -> tuple[str, ...] | None:
    """Names of the ready moving averages from highest to lowest value; None unless all are
    ready (ties keep configuration order)."""
    mas = [v for v in values if v.kind in (IndicatorKind.SMA, IndicatorKind.EMA)]
    if not mas or any(v.value is None for v in mas):
        return None
    return tuple(v.name for v in sorted(mas, key=lambda v: -v.value))  # type: ignore[operator]


def rsi(closes: Sequence[Decimal], config: IndicatorConfig) -> IndicatorValue | None:
    n = config.rsi_period
    if n is None:
        return None
    series = rsi_series(closes, n)
    labels = []
    latest = series[-1]
    if latest is not None and config.rsi_upper is not None and config.rsi_lower is not None:
        labels = ["rsi_above_upper" if latest > config.rsi_upper else
                  "rsi_below_lower" if latest < config.rsi_lower else "rsi_between_levels"]
    params = {"period": str(n), "smoothing": "wilder"}
    if config.rsi_upper is not None:
        params |= {"upper": str(config.rsi_upper), "lower": str(config.rsi_lower)}
    return _value(f"rsi_{n}", IndicatorKind.RSI, params, n + 1, series, labels=labels)


def macd(closes: Sequence[Decimal], spec: MacdSpec) -> IndicatorValue:
    fast, slow = ema_series(closes, spec.fast), ema_series(closes, spec.slow)
    line: Series = [None if f is None or s is None else f - s for f, s in zip(fast, slow,
                                                                            strict=True)]
    signal = ema_series(line, spec.signal)
    latest_signal = signal[-1] if signal else None
    ready_line = line if latest_signal is not None else [None] * len(line)
    histogram = None if latest_signal is None else line[-1] - latest_signal  # type: ignore[operator]
    labels = []
    if histogram is not None:
        labels = ["macd_above_signal" if histogram > 0 else
                  "macd_below_signal" if histogram < 0 else "macd_at_signal"]
    name = f"macd_{spec.fast}_{spec.slow}_{spec.signal}"
    value = _value(name, IndicatorKind.MACD,
                   {"fast": str(spec.fast), "slow": str(spec.slow), "signal": str(spec.signal)},
                   spec.slow + spec.signal - 1, ready_line,
                   components={"line": line[-1] if line else None, "signal": latest_signal,
                               "histogram": histogram},
                   labels=labels)
    return value


def bollinger(closes: Sequence[Decimal], spec: BollingerSpec) -> IndicatorValue:
    n, k = spec.period, spec.deviations
    middle = sma_series(closes, n)
    components: dict[str, Decimal | None] = {"upper": None, "lower": None, "bandwidth": None,
                                              "percent_b": None}
    labels: list[str] = []
    if middle[-1] is not None:
        window = closes[-n:]
        sd = (sum(((c - middle[-1]) ** 2 for c in window), ZERO) / n).sqrt()
        upper, lower = middle[-1] + k * sd, middle[-1] - k * sd
        components = {"upper": upper, "lower": lower,
                      "bandwidth": ratio(upper - lower, middle[-1]),
                      "percent_b": ratio(closes[-1] - lower, upper - lower)}
        close = closes[-1]
        labels = ["close_above_upper" if close > upper else
                  "close_below_lower" if close < lower else "close_inside_bands"]
    return _value(f"bollinger_{n}_{str(k).replace('.', 'p')}", IndicatorKind.BOLLINGER,
                  {"period": str(n), "deviations": str(k), "sd": "population"}, n, middle,
                  components=components, labels=labels)


def indicators(closes: Sequence[Decimal], config: IndicatorConfig) -> list[IndicatorValue]:
    out = moving_averages(closes, config)
    value = rsi(closes, config)
    if value is not None:
        out.append(value)
    if config.macd is not None:
        out.append(macd(closes, config.macd))
    if config.bollinger is not None:
        out.append(bollinger(closes, config.bollinger))
    return out
