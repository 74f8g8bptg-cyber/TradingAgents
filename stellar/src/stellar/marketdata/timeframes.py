"""Timeframe durations and parsing (Foundation §4.7).

The canonical set is ``stellar.schemas.market.Timeframe``. Adding a timeframe is
additive: one enum member plus one duration here. Not every provider serves every
timeframe; each source declares what it supports.

Bar alignment (which wall-clock minute an H4 or D1 bar starts on) differs by
provider and broker server time, so it is declared by the source, not assumed
here. Only durations are canonical.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from stellar.schemas.market import Timeframe

DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.M30: timedelta(minutes=30),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(weeks=1),
}

_ALIASES: dict[str, Timeframe] = {
    "1m": Timeframe.M1,
    "5m": Timeframe.M5,
    "15m": Timeframe.M15,
    "30m": Timeframe.M30,
    "1h": Timeframe.H1,
    "4h": Timeframe.H4,
    "1d": Timeframe.D1,
    "1w": Timeframe.W1,
}


def _check_complete() -> None:
    missing = set(Timeframe) - set(DURATIONS)
    if missing:  # pragma: no cover - guarded by tests
        raise RuntimeError(f"timeframes without a duration: {sorted(missing)}")


_check_complete()


def parse_timeframe(value: str | Timeframe) -> Timeframe:
    """``"H1"``, ``"h1"`` or ``"1h"`` → ``Timeframe.H1``. Anything else raises ``ValueError``."""
    if isinstance(value, Timeframe):
        return value
    text = str(value).strip()
    upper = text.upper()
    if upper in Timeframe.__members__:
        return Timeframe(upper)
    alias = _ALIASES.get(text.lower())
    if alias is None:
        raise ValueError(f"unknown timeframe {value!r}; expected one of {[t.value for t in Timeframe]}")
    return alias


def duration(timeframe: Timeframe) -> timedelta:
    return DURATIONS[timeframe]


def intervals_between(earlier: datetime, later: datetime, timeframe: Timeframe) -> int:
    """Whole timeframe intervals from ``earlier`` to ``later`` (0 if ``later`` is not after it)."""
    if later <= earlier:
        return 0
    return int((later - earlier) // DURATIONS[timeframe])
