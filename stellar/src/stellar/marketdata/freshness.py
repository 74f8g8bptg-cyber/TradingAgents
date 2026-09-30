"""Freshness evaluation and gap detection (deterministic, no session calendar).

Freshness compares the newest bar's close time with ``as_of`` in whole timeframe
intervals. No staleness threshold is built in: without a configured
``max_staleness_intervals`` the status is UNKNOWN, never a guess.

Gaps are reported, never filled. Without session calendars (not implemented in
Phase 2) a weekend or holiday gap is indistinguishable from a missing bar, so
every gap is reported and none is judged.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import Field

from stellar.marketdata.contracts import Freshness, FreshnessStatus, StaleReason
from stellar.marketdata.timeframes import duration, intervals_between
from stellar.schemas.common import StellarModel, UtcDatetime
from stellar.schemas.market import Candle, Timeframe


class Gap(StellarModel):
    """Missing time between two consecutive bars."""

    previous_open_time: UtcDatetime
    next_open_time: UtcDatetime
    missing_intervals: int = Field(ge=1)


def find_gaps(candles: Sequence[Candle], timeframe: Timeframe) -> tuple[Gap, ...]:
    """Gaps in a series already ordered by ``open_time``."""
    step = duration(timeframe)
    gaps = []
    for previous, current in zip(candles, candles[1:], strict=False):
        delta = current.open_time - previous.open_time
        if delta > step:
            gaps.append(Gap(previous_open_time=previous.open_time,
                            next_open_time=current.open_time,
                            missing_intervals=int(delta // step) - 1 or 1))
    return tuple(gaps)


def evaluate_freshness(
    *,
    as_of: datetime,
    retrieved_at: datetime,
    source_timestamp: datetime | None,
    timeframe: Timeframe | None,
    max_staleness_intervals: int | None,
) -> Freshness:
    """Freshness of data whose newest timestamp is ``source_timestamp``."""
    interval = int(duration(timeframe).total_seconds()) if timeframe is not None else None
    if source_timestamp is None:
        return Freshness(as_of=as_of, retrieved_at=retrieved_at,
                         expected_interval_seconds=interval,
                         max_staleness_intervals=max_staleness_intervals,
                         status=FreshnessStatus.NO_DATA)
    behind = intervals_between(source_timestamp, as_of, timeframe) if timeframe else None
    if max_staleness_intervals is None or behind is None:
        status, reason = FreshnessStatus.UNKNOWN, None
    elif behind > max_staleness_intervals:
        status, reason = FreshnessStatus.STALE, StaleReason.OLDER_THAN_MAX_INTERVALS
    else:
        status, reason = FreshnessStatus.FRESH, None
    return Freshness(as_of=as_of, retrieved_at=retrieved_at, source_timestamp=source_timestamp,
                     expected_interval_seconds=interval, intervals_behind=behind,
                     max_staleness_intervals=max_staleness_intervals, status=status,
                     stale_reason=reason)
