"""Impulse legs, the current pullback, and consolidation measurements (Foundation §4.11).

**Legs (impulse measurements).**
- *Construction:*
  - built between consecutive *alternating* confirmed swings (low → high = UP leg,
    high → low = DOWN leg);
  - when two confirmed swings of the same kind follow each other, the more extreme one
    is kept (the higher high / the lower low; the earlier on a tie);
  - a leg is known from its end swing's confirmation time.
- *Measurements*, over the bars after the start swing up to and including the end swing:
  - bars, net move, and path length (sum of |close change|);
  - efficiency (|net| / path) and cumulative signed body;
  - mean range, and range expansion (mean range / mean range of the preceding
    ``relative_range_lookback`` bars);
  - net move / ATR at the end bar.
- *Role:*
  - WITH_STRUCTURE / COUNTER_STRUCTURE relative to the structure state at ``as_of``
    (UP: up legs are with it; DOWN: down legs are);
  - otherwise UNCLASSIFIED.

**Pullback.**
- Measures the bars after the end of the last completed leg (the reference leg), up to
  ``as_of``:
  - depth against the leg, and retracement ratio = depth / |leg net move|;
  - the current retracement from the latest close;
  - counts and body totals of bars moving against and with the leg's direction;
  - the mean close location.
- It is a measurement of what happened after a leg, whatever the count of
  counter-direction bars. No count of candles is treated as a signal.

**Consolidation** (``consolidation.lookback`` recent bars):
- measurements: window high/low/range, net displacement, path, efficiency, overlap ratio,
  mean range and range / ATR;
- it is classified ``is_consolidation`` only when both ``max_range_atr`` and
  ``min_overlap_ratio`` are configured and ATR is ready. Otherwise the classification is
  None (unevaluated).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from stellar.technical.config import ConsolidationConfig
from stellar.technical.models import (
    BarDirection,
    CandleFeatures,
    Consolidation,
    LegDirection,
    LegRole,
    Pivot,
    PivotKind,
    Pullback,
    StructureLeg,
    StructureState,
)
from stellar.technical.numeric import ZERO, mean, ratio, total
from stellar.technical.pivots import evidence_id


def alternating(pivots: Sequence[Pivot]) -> list[Pivot]:
    """Confirmed swings in bar order, with runs of one kind reduced to their extreme."""
    out: list[Pivot] = []
    for p in sorted(pivots, key=lambda p: p.index):
        if out and out[-1].kind is p.kind:
            last = out[-1]
            more_extreme = p.price > last.price if p.kind is PivotKind.HIGH else \
                p.price < last.price
            if more_extreme:
                out[-1] = p
            continue
        out.append(p)
    return out


def _path(features: Sequence[CandleFeatures], start: int, end: int) -> Decimal:
    return total(abs(features[j].close - features[j - 1].close) for j in range(start + 1, end + 1))


def legs(features: Sequence[CandleFeatures], pivots: Sequence[Pivot], state: StructureState,
         *, lookback: int | None, atr: Sequence[Decimal | None] | None) -> list[StructureLeg]:
    swings = alternating(pivots)
    out: list[StructureLeg] = []
    for a, b in zip(swings, swings[1:], strict=False):
        bars = features[a.index + 1:b.index + 1]
        direction = LegDirection.UP if b.kind is PivotKind.HIGH else LegDirection.DOWN
        role = LegRole.UNCLASSIFIED
        if state is StructureState.UP:
            role = LegRole.WITH_STRUCTURE if direction is LegDirection.UP else \
                LegRole.COUNTER_STRUCTURE
        elif state is StructureState.DOWN:
            role = LegRole.WITH_STRUCTURE if direction is LegDirection.DOWN else \
                LegRole.COUNTER_STRUCTURE
        net = b.price - a.price
        path = _path(features, a.index, b.index)
        mean_range = mean([f.range for f in bars])
        expansion = None
        if lookback is not None and a.index + 1 >= lookback:
            expansion = ratio(mean_range, mean([f.range for f in
                                                features[a.index + 1 - lookback:a.index + 1]]))
        end_atr = atr[b.index] if atr is not None else None
        out.append(StructureLeg(
            evidence_id=evidence_id("leg", a.evidence_id, b.evidence_id), direction=direction,
            role=role, start_pivot_id=a.evidence_id, end_pivot_id=b.evidence_id,
            start_time=a.bar_open_time, end_time=b.bar_close_time, start_price=a.price,
            end_price=b.price, bars=len(bars), net_move=net, path_length=path,
            efficiency=ratio(abs(net), path), cumulative_body=total(f.signed_body for f in bars),
            mean_range=mean_range, range_expansion=expansion,
            atr_normalised_move=None if end_atr is None else ratio(net, end_atr),
            confirmed_at=b.confirmed_at))
    return out


def pullback(features: Sequence[CandleFeatures], legs_: Sequence[StructureLeg],
             pivots: Sequence[Pivot]) -> Pullback | None:
    if not legs_:
        return None
    ref = legs_[-1]
    end = next(p for p in pivots if p.evidence_id == ref.end_pivot_id)
    bars = features[end.index + 1:]
    up = ref.direction is LegDirection.UP
    counter_dir = BarDirection.DOWN if up else BarDirection.UP
    with_dir = BarDirection.UP if up else BarDirection.DOWN
    size = abs(ref.net_move)
    adverse = depth = retracement = current = None
    if bars:
        adverse = min(f.low for f in bars) if up else max(f.high for f in bars)
        depth = max(ref.end_price - adverse, ZERO) if up else max(adverse - ref.end_price, ZERO)
        retracement = ratio(depth, size)
        last = bars[-1].close
        current = ratio(ref.end_price - last if up else last - ref.end_price, size)
    locations = [f.close_location for f in bars if f.close_location is not None]
    return Pullback(
        reference_leg_id=ref.evidence_id, reference_direction=ref.direction,
        started_at=end.bar_close_time, bars=len(bars), max_adverse_price=adverse, depth=depth,
        retracement_ratio=retracement, current_retracement_ratio=current,
        counter_direction_bars=sum(f.direction is counter_dir for f in bars),
        with_direction_bars=sum(f.direction is with_dir for f in bars),
        counter_body_total=total(f.body for f in bars if f.direction is counter_dir),
        with_body_total=total(f.body for f in bars if f.direction is with_dir),
        mean_close_location=mean(locations) if locations else None)


def consolidation(features: Sequence[CandleFeatures], config: ConsolidationConfig,
                  atr_latest: Decimal | None) -> Consolidation | None:
    n = config.lookback
    if n is None or len(features) < n:
        return None
    window = features[-n:]
    high, low = max(f.high for f in window), min(f.low for f in window)
    path = total(abs(window[j].close - window[j - 1].close) for j in range(1, n))
    net = window[-1].close - window[0].open
    pairs = list(zip(window, window[1:], strict=False))
    overlap = ratio(Decimal(sum(max(a.low, b.low) <= min(a.high, b.high) for a, b in pairs)),
                    Decimal(len(pairs))) if pairs else None
    range_atr = None if atr_latest is None else ratio(high - low, atr_latest)
    classified = None
    if config.max_range_atr is not None and config.min_overlap_ratio is not None and \
            range_atr is not None and overlap is not None:
        classified = range_atr <= config.max_range_atr and overlap >= config.min_overlap_ratio
    return Consolidation(lookback=n, window_start=window[0].open_time,
                         window_end=window[-1].close_time, high=high, low=low, range=high - low,
                         net_displacement=net, path_length=path,
                         efficiency=ratio(abs(net), path), overlap_ratio=overlap,
                         mean_range=mean([f.range for f in window]), range_atr=range_atr,
                         is_consolidation=classified)
