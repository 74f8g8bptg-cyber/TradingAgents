"""Descriptive market structure from CONFIRMED swings (Foundation §4.11; T3).

Swing labels. Each confirmed swing is compared with the previous confirmed swing of the
same kind, with tolerance t:
- highs: **HH** if higher by more than t, **LH** if lower by more than t, **EQH** otherwise;
- lows: **HL** if higher by more than t, **LL** if lower by more than t, **EQL** otherwise.

The tolerance t is exact (0) when unset, a price amount, or a multiple of the ATR *at the
swing's confirmation bar*. If an ATR-based t cannot be computed yet, the swing is left
unlabelled (never guessed).

State, from the latest labelled high and low:
- **UP**: HH and HL;
- **DOWN**: LH and LL;
- **RANGE**: EQH and EQL;
- **MIXED**: any other combination;
- **INSUFFICIENT**: either label missing.

It describes the swing sequence. It is not a trading bias, and no rule here calls
anything a "reversal".

Structure events, for the latest confirmed swing high (and low):
- the first bar that *closes* above it (below it) after the swing was confirmed is
  STRUCTURE_BREAK_UP (STRUCTURE_BREAK_DOWN);
- wicks alone do not count;
- ``break_against_state`` marks the latest event when it runs opposite to the state.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from stellar.technical.config import ToleranceConfig
from stellar.technical.models import (
    CandleFeatures,
    MarketStructure,
    Pivot,
    PivotKind,
    StructureEvent,
    StructureEventKind,
    StructureState,
    SwingLabel,
    SwingPoint,
)

_LABELS = {PivotKind.HIGH: (SwingLabel.HH, SwingLabel.LH, SwingLabel.EQH),
           PivotKind.LOW: (SwingLabel.HL, SwingLabel.LL, SwingLabel.EQL)}


def tolerance_method(config: ToleranceConfig) -> str:
    if config.price is not None:
        return "price"
    if config.atr_multiple is not None:
        return "atr_multiple"
    return "exact"


def tolerance_at(config: ToleranceConfig, index: int,
                 atr: Sequence[Decimal | None] | None) -> Decimal | None:
    if config.price is not None:
        return config.price
    if config.atr_multiple is not None:
        value = atr[index] if atr is not None else None
        return None if value is None else config.atr_multiple * value
    return Decimal(0)


def _confirmation_index(pivot: Pivot) -> int:
    return pivot.index + pivot.right


def market_structure(features: Sequence[CandleFeatures], pivots: Sequence[Pivot],
                     tolerance: ToleranceConfig,
                     atr: Sequence[Decimal | None] | None) -> MarketStructure:
    swings: list[SwingPoint] = []
    previous: dict[PivotKind, Pivot] = {}
    for p in pivots:  # confirmed, in the order they became known
        before = previous.get(p.kind)
        label = difference = tol = None
        if before is not None:
            difference = p.price - before.price
            tol = tolerance_at(tolerance, _confirmation_index(p), atr)
            if tol is not None:
                up, down, equal = _LABELS[p.kind]
                label = up if difference > tol else down if difference < -tol else equal
        swings.append(SwingPoint(pivot_id=p.evidence_id, kind=p.kind, label=label, price=p.price,
                                 previous_price=None if before is None else before.price,
                                 difference=difference, tolerance=tol,
                                 confirmed_at=p.confirmed_at))
        previous[p.kind] = p
    last_high = next((s for s in reversed(swings) if s.kind is PivotKind.HIGH), None)
    last_low = next((s for s in reversed(swings) if s.kind is PivotKind.LOW), None)
    state = _state(last_high, last_low)
    events = []
    for pivot in previous.values():
        event = _break(features, pivot)
        if event is not None:
            events.append(event)
    events.sort(key=lambda e: (e.bar_close_time, e.kind.value))
    against = bool(events) and (
        (state is StructureState.UP and events[-1].kind is StructureEventKind.STRUCTURE_BREAK_DOWN)
        or (state is StructureState.DOWN
            and events[-1].kind is StructureEventKind.STRUCTURE_BREAK_UP))
    return MarketStructure(swings=tuple(swings), state=state, last_swing_high=last_high,
                           last_swing_low=last_low, events=tuple(events),
                           break_against_state=against,
                           equal_tolerance_method=tolerance_method(tolerance))


def _state(high: SwingPoint | None, low: SwingPoint | None) -> StructureState:
    if high is None or low is None or high.label is None or low.label is None:
        return StructureState.INSUFFICIENT
    pair = (high.label, low.label)
    if pair == (SwingLabel.HH, SwingLabel.HL):
        return StructureState.UP
    if pair == (SwingLabel.LH, SwingLabel.LL):
        return StructureState.DOWN
    if pair == (SwingLabel.EQH, SwingLabel.EQL):
        return StructureState.RANGE
    return StructureState.MIXED


def _break(features: Sequence[CandleFeatures], pivot: Pivot) -> StructureEvent | None:
    assert pivot.confirmed_at is not None
    for f in features:
        if f.close_time <= pivot.confirmed_at:
            continue
        if pivot.kind is PivotKind.HIGH and f.close > pivot.price:
            kind = StructureEventKind.STRUCTURE_BREAK_UP
        elif pivot.kind is PivotKind.LOW and f.close < pivot.price:
            kind = StructureEventKind.STRUCTURE_BREAK_DOWN
        else:
            continue
        return StructureEvent(kind=kind, reference_pivot_id=pivot.evidence_id, level=pivot.price,
                              bar_index=f.index, bar_close_time=f.close_time, close=f.close)
    return None
