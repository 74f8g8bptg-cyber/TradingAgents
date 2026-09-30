"""Series-level validation. Problems are reported, never silently repaired.

Bar-level rules (OHLC relations, finite Decimals, no booleans, non-negative
volume, timezone-aware times) are enforced when a ``Candle`` is constructed.
This module adds the rules that need the whole series:

| Rule | Default | Explicit alternative |
|---|---|---|
| Instrument / timeframe consistency | ERROR | — |
| Bar not closed | ERROR | — |
| Wrong bar duration (M1–H4) | ERROR | — |
| Out-of-order bars | ERROR | ``OrderPolicy.SORT``: sorted, WARNING + ``OUT_OF_ORDER`` |
| Identical duplicate bars | ERROR | ``DuplicatePolicy.DROP_IDENTICAL``: dropped, WARNING + ``DUPLICATE_BAR`` |
| Conflicting duplicates (same time, different values) | ERROR | — |
| Overlapping bars | ERROR | — |
| Gaps | WARNING + ``GAP_DETECTED`` | — |
| Missing volume | WARNING + ``MISSING_VOLUME`` | — |
| Price decimals beyond the declared precision | ERROR | — |
| Declared precision below the instrument's precision | WARNING + ``SOURCE_PRECISION_LOSS`` | — |

D1/W1 durations are not checked: their boundaries are provider-specific
(Foundation §4.7) and no session calendar exists yet.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import Field

from stellar.marketdata.contracts import (
    DataIssue,
    IssueCode,
    IssueSeverity,
    decimal_places,
    sorted_flags,
)
from stellar.marketdata.freshness import Gap, find_gaps
from stellar.marketdata.timeframes import duration
from stellar.schemas.common import InstrumentId, StellarModel
from stellar.schemas.market import Candle, DataQualityFlag, Timeframe

_FIXED_DURATION = {Timeframe.M1, Timeframe.M5, Timeframe.M15, Timeframe.M30, Timeframe.H1,
                   Timeframe.H4}


class DuplicatePolicy(StrEnum):
    REJECT = "REJECT"
    DROP_IDENTICAL = "DROP_IDENTICAL"


class OrderPolicy(StrEnum):
    REJECT = "REJECT"
    SORT = "SORT"


class SeriesValidation(StellarModel):
    candles: tuple[Candle, ...]
    """The bars after any explicitly permitted handling (sorting, dropping identical duplicates)."""
    issues: tuple[DataIssue, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()
    gaps: tuple[Gap, ...] = ()
    observed_price_decimals: int | None = Field(default=None, ge=0)

    @property
    def has_errors(self) -> bool:
        return any(i.severity is IssueSeverity.ERROR for i in self.issues)


def _issue(code, severity, message, candle=None, row=None) -> DataIssue:
    return DataIssue(code=code, severity=severity, message=message, row=row,
                     open_time=candle.open_time if candle is not None else None)


def observed_price_decimals(candles: Sequence[Candle]) -> int | None:
    places = [decimal_places(v) for c in candles for v in (c.open, c.high, c.low, c.close)]
    return max(places) if places else None


def validate_series(
    candles: Sequence[Candle],
    *,
    instrument: InstrumentId,
    timeframe: Timeframe,
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.REJECT,
    order_policy: OrderPolicy = OrderPolicy.REJECT,
    declared_price_decimals: int | None = None,
    instrument_price_decimals: int | None = None,
    rows: Sequence[int] | None = None,
) -> SeriesValidation:
    """Validate ``candles`` as one series. ``rows`` (same length) names source rows in issues."""
    issues: list[DataIssue] = []
    flags: set[DataQualityFlag] = set()
    row_of = dict(zip((id(c) for c in candles), rows, strict=True)) if rows is not None else {}
    E, W = IssueSeverity.ERROR, IssueSeverity.WARNING

    step = duration(timeframe)
    for c in candles:
        row = row_of.get(id(c))
        if c.instrument != instrument:
            issues.append(_issue(IssueCode.INSTRUMENT_MISMATCH, E,
                                 f"bar is {c.instrument}, series is {instrument}", c, row))
        if c.timeframe != timeframe:
            issues.append(_issue(IssueCode.TIMEFRAME_MISMATCH, E,
                                 f"bar is {c.timeframe}, series is {timeframe}", c, row))
        if not c.is_closed:
            issues.append(_issue(IssueCode.NOT_CLOSED, E, "bar is not closed", c, row))
        if timeframe in _FIXED_DURATION and c.close_time - c.open_time != step:
            issues.append(_issue(IssueCode.WRONG_DURATION, E,
                                 f"bar lasts {c.close_time - c.open_time}, {timeframe} is {step}",
                                 c, row))

    # Ordering: detect before any handling.
    ordered = list(candles)
    out_of_order = any(b.open_time < a.open_time
                       for a, b in zip(candles, candles[1:], strict=False))
    if out_of_order:
        if order_policy is OrderPolicy.SORT:
            ordered.sort(key=lambda c: c.open_time)
            flags.add(DataQualityFlag.OUT_OF_ORDER)
            issues.append(_issue(IssueCode.OUT_OF_ORDER, W, "bars were out of order; sorted"))
        else:
            first = next(b for a, b in zip(candles, candles[1:], strict=False)
                         if b.open_time < a.open_time)
            issues.append(_issue(IssueCode.OUT_OF_ORDER, E, "bars are out of order", first,
                                 row_of.get(id(first))))

    # Duplicates (same open_time).
    kept: list[Candle] = []
    for c in ordered:
        if kept and c.open_time == kept[-1].open_time:
            row = row_of.get(id(c))
            if c != kept[-1]:
                issues.append(_issue(IssueCode.CONFLICTING_DUPLICATE, E,
                                     "two different bars share this open_time", c, row))
            elif duplicate_policy is DuplicatePolicy.DROP_IDENTICAL:
                flags.add(DataQualityFlag.DUPLICATE_BAR)
                issues.append(_issue(IssueCode.DUPLICATE_BAR, W,
                                     "identical duplicate bar dropped", c, row))
                continue
            else:
                issues.append(_issue(IssueCode.DUPLICATE_BAR, E, "duplicate bar", c, row))
            continue
        kept.append(c)

    # Overlaps (checked on the ordered, de-duplicated series).
    if not out_of_order or order_policy is OrderPolicy.SORT:
        for a, b in zip(kept, kept[1:], strict=False):
            if b.open_time < a.close_time:
                issues.append(_issue(IssueCode.OVERLAPPING_BARS, E,
                                     f"bar opens before the previous bar closes ({a.close_time})",
                                     b, row_of.get(id(b))))

    gaps = find_gaps(kept, timeframe) if not out_of_order or order_policy is OrderPolicy.SORT \
        else ()
    if gaps:
        flags.add(DataQualityFlag.GAP_DETECTED)
        issues.append(_issue(IssueCode.GAP_DETECTED, W,
                             f"{len(gaps)} gap(s); not filled (weekends and holidays included, "
                             "no session calendar)"))

    missing_volume = sum(1 for c in kept if c.volume is None)
    if missing_volume:
        flags.add(DataQualityFlag.MISSING_VOLUME)
        issues.append(_issue(IssueCode.MISSING_VOLUME, W, f"{missing_volume} bar(s) without volume"))

    observed = observed_price_decimals(kept)
    if declared_price_decimals is not None:
        for c in kept:
            if observed_price_decimals([c]) > declared_price_decimals:
                issues.append(_issue(IssueCode.PRECISION_EXCEEDS_DECLARED, E,
                                     f"price has more than the declared "
                                     f"{declared_price_decimals} decimals", c, row_of.get(id(c))))
                break
        if instrument_price_decimals is not None and \
                declared_price_decimals < instrument_price_decimals:
            flags.add(DataQualityFlag.SOURCE_PRECISION_LOSS)
            issues.append(_issue(IssueCode.SOURCE_PRECISION_LOSS, W,
                                 f"source declares {declared_price_decimals} decimals; the "
                                 f"instrument uses {instrument_price_decimals}"))

    return SeriesValidation(candles=tuple(kept), issues=tuple(issues), flags=sorted_flags(flags),
                            gaps=gaps, observed_price_decimals=observed)
