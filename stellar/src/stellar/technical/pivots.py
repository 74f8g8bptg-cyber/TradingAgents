"""Swing pivots with explicit confirmation (no look-ahead).

Definition (``left`` = L, ``right`` = R, both required configuration):
- bar i is a **swing high** when its high is strictly greater than the highs of the
  L bars before it and of the R bars after it;
- a **swing low** is the mirror image (strictly lower lows);
- ties are not pivots: equal highs on either side prevent a swing (a deterministic,
  conservative choice).

Confirmation:
- a swing is **CONFIRMED** only when bar i+R has closed; ``confirmed_at`` is that bar's
  close time;
- at ``as_of``, a bar whose right window is incomplete but which beats every bar seen
  so far is a **CANDIDATE**; it is reported but never used by structure, legs or zones;
- the engine only ever sees bars closed at or before ``as_of``, so no pivot can be
  confirmed by a bar that had not closed yet.
"""

from __future__ import annotations

from collections.abc import Sequence

from stellar.schemas.market import Candle
from stellar.serialization import sha256_hex
from stellar.technical.models import Pivot, PivotKind, PivotStatus


def evidence_id(prefix: str, *parts: object) -> str:
    return f"{prefix}_{sha256_hex('|'.join(str(p) for p in parts))[:16]}"


def find_pivots(candles: Sequence[Candle], left: int, right: int) -> list[Pivot]:
    pivots: list[Pivot] = []
    n = len(candles)
    for i in range(left, n):
        before = candles[i - left:i]
        after = candles[i + 1:i + 1 + right]
        c = candles[i]
        for kind in (PivotKind.HIGH, PivotKind.LOW):
            if kind is PivotKind.HIGH:
                price = c.high
                beats = all(price > b.high for b in before) and all(price > a.high for a in after)
            else:
                price = c.low
                beats = all(price < b.low for b in before) and all(price < a.low for a in after)
            if not beats:
                continue
            confirmed = len(after) == right
            pivots.append(Pivot(
                evidence_id=evidence_id("piv", kind.value, c.open_time.isoformat(), left, right),
                kind=kind, status=PivotStatus.CONFIRMED if confirmed else PivotStatus.CANDIDATE,
                index=i, bar_open_time=c.open_time, bar_close_time=c.close_time, price=price,
                left=left, right=right,
                confirmed_at=after[-1].close_time if confirmed else None,
                right_bars_seen=len(after)))
    return pivots


def confirmed(pivots: Sequence[Pivot]) -> list[Pivot]:
    """Confirmed pivots in the order they became known (confirmation, then bar time)."""
    return sorted((p for p in pivots if p.status is PivotStatus.CONFIRMED),
                  key=lambda p: (p.confirmed_at, p.bar_open_time, p.kind.value))
