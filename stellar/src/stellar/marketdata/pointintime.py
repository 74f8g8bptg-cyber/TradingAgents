"""Point-in-time (no look-ahead) helpers.

A bar is known at ``as_of`` only once it has closed: ``close_time <= as_of``. A
bar that opened before ``as_of`` but closes after it is still forming, and its
final OHLC contains later information, so it is excluded. A quote is known when
``ts <= as_of``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from stellar.schemas.market import Candle, Quote


class LookAheadError(ValueError):
    """Data from after ``as_of`` reached a point-in-time consumer."""


def known_at(candles: Iterable[Candle], as_of: datetime) -> tuple[Candle, ...]:
    """Bars closed at or before ``as_of``, in their original order."""
    return tuple(c for c in candles if c.close_time <= as_of)


def in_window(
    candles: Iterable[Candle], start: datetime | None, end: datetime | None
) -> tuple[Candle, ...]:
    """Bars whose ``open_time`` lies in ``[start, end]`` (either bound optional)."""
    return tuple(
        c for c in candles
        if (start is None or c.open_time >= start) and (end is None or c.open_time <= end)
    )


def assert_no_look_ahead(candles: Sequence[Candle], as_of: datetime) -> None:
    late = [c.open_time.isoformat() for c in candles if c.close_time > as_of]
    if late:
        raise LookAheadError(f"{len(late)} bar(s) close after as_of {as_of.isoformat()}: {late[:3]}")


def latest_quote_at(quotes: Iterable[Quote], as_of: datetime) -> Quote | None:
    """The newest quote stamped at or before ``as_of``, or ``None``."""
    known = [q for q in quotes if q.ts <= as_of]
    return max(known, key=lambda q: q.ts) if known else None
