"""Support / resistance zones from confirmed swings, with break and retest observations.

**Zones.**
- *Tolerance* t = ``zone_tolerance.price``, or ``zone_tolerance.atr_multiple`` × the ATR at
  ``as_of``. Without a tolerance (or with an ATR not yet ready) no zone is built.
- *Clustering:*
  - confirmed swings are taken in the order they became known;
  - each joins the first existing zone whose member prices, widened by t, contain its
    price; otherwise it starts a new zone.
- *Bounds:* [lowest member - t, highest member + t]. A zone is never narrower than its
  tolerance allows, so no single price is presented as exact.
- *Kind:* SUPPORT (swing lows only), RESISTANCE (swing highs only) or MIXED.
- *Recorded:* the derivation, tolerance and method, source swing ids, and
  ``first_known_at`` (the first member's confirmation time).
- *Interactions:* bars closed after ``first_known_at`` whose high-low range overlaps the
  zone; ``last_tested_at`` is the latest such bar. Only bars at or before ``as_of``
  exist here, so a later touch can never strengthen a zone in an earlier query.

**Breaks and retests** (per zone, over the bars after ``first_known_at``). The starting
position is where the confirming bar closed (above, below or inside). Then, per bar:
- **CLOSE_ABOVE / CLOSE_BELOW:** the close crosses outside the zone from inside or from
  the other side (a break);
- **WICK_ABOVE / WICK_BELOW:** a bar starting inside the zone trades beyond it but
  closes back inside;
- after a break, **RETEST_ATTEMPT:** a bar trades back into the zone. It is then
  **RETEST_HELD** if it closes outside again on the break side, else **RETEST_FAILED**.

These record what price did. None of them is a trade instruction.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from stellar.technical.config import ToleranceConfig
from stellar.technical.models import (
    CandleFeatures,
    Pivot,
    PivotKind,
    PriceZone,
    ZoneEvent,
    ZoneEventKind,
    ZoneKind,
)
from stellar.technical.pivots import evidence_id
from stellar.technical.structure import tolerance_method


def zone_tolerance(config: ToleranceConfig, latest_atr: Decimal | None) -> Decimal | None:
    if config.price is not None:
        return config.price
    if config.atr_multiple is not None and latest_atr is not None:
        return config.atr_multiple * latest_atr
    return None


def zones(features: Sequence[CandleFeatures], pivots: Sequence[Pivot], tolerance: Decimal,
          method: ToleranceConfig) -> list[PriceZone]:
    clusters: list[list[Pivot]] = []
    for p in pivots:  # confirmed, in the order they became known
        for members in clusters:
            lo, hi = min(m.price for m in members), max(m.price for m in members)
            if lo - tolerance <= p.price <= hi + tolerance:
                members.append(p)
                break
        else:
            clusters.append([p])
    out = []
    for members in clusters:
        lower = min(m.price for m in members) - tolerance
        upper = max(m.price for m in members) + tolerance
        if lower <= 0:
            continue  # a zone cannot extend to a non-positive price
        kinds = {m.kind for m in members}
        kind = ZoneKind.MIXED if len(kinds) == 2 else (
            ZoneKind.SUPPORT if PivotKind.LOW in kinds else ZoneKind.RESISTANCE)
        first = members[0].confirmed_at
        assert first is not None
        after = [f for f in features if f.close_time > first]
        touching = [f for f in after if f.low <= upper and f.high >= lower]
        start = next((f for f in features if f.close_time == first), None)
        events, state = _events(after, lower, upper, start.close if start else None)
        out.append(PriceZone(
            evidence_id=evidence_id("zone", *(m.evidence_id for m in members), tolerance),
            kind=kind, lower=lower, upper=upper, derivation="confirmed_pivot_cluster",
            tolerance=tolerance, tolerance_method=tolerance_method(method),
            source_pivot_ids=tuple(m.evidence_id for m in members), first_known_at=first,
            interactions=len(touching),
            last_tested_at=touching[-1].close_time if touching else None,
            events=tuple(events), state=state))
    return out


def _side(close: Decimal | None, lower: Decimal, upper: Decimal) -> str | None:
    if close is None:
        return None
    return "above" if close > upper else "below" if close < lower else "inside"


def _events(bars: Sequence[CandleFeatures], lower: Decimal, upper: Decimal,
            start_close: Decimal | None) -> tuple[list[ZoneEvent], str]:
    side = _side(start_close, lower, upper) or "inside"
    broken = False
    events: list[ZoneEvent] = []

    def add(kind: ZoneEventKind, f: CandleFeatures) -> None:
        events.append(ZoneEvent(kind=kind, bar_index=f.index, bar_close_time=f.close_time))

    for f in bars:
        if broken and side == "above" and f.low <= upper:
            add(ZoneEventKind.RETEST_ATTEMPT, f)
            if f.close > upper:
                add(ZoneEventKind.RETEST_HELD, f)
                continue
            add(ZoneEventKind.RETEST_FAILED, f)
            broken, side = False, _side(f.close, lower, upper)
            if side == "below":
                add(ZoneEventKind.CLOSE_BELOW, f)
                broken = True
            continue
        if broken and side == "below" and f.high >= lower:
            add(ZoneEventKind.RETEST_ATTEMPT, f)
            if f.close < lower:
                add(ZoneEventKind.RETEST_HELD, f)
                continue
            add(ZoneEventKind.RETEST_FAILED, f)
            broken, side = False, _side(f.close, lower, upper)
            if side == "above":
                add(ZoneEventKind.CLOSE_ABOVE, f)
                broken = True
            continue
        new_side = _side(f.close, lower, upper)
        if new_side == "above" and side != "above":
            add(ZoneEventKind.CLOSE_ABOVE, f)
            side, broken = "above", True
        elif new_side == "below" and side != "below":
            add(ZoneEventKind.CLOSE_BELOW, f)
            side, broken = "below", True
        elif new_side == "inside":
            if side == "inside":
                if f.high > upper:
                    add(ZoneEventKind.WICK_ABOVE, f)
                if f.low < lower:
                    add(ZoneEventKind.WICK_BELOW, f)
            side, broken = "inside", False
    state = side if not broken else f"{side}_after_break"
    return events, state
