"""Phase 5: pivots, structure, impulse/pullback/consolidation, zones, breaks and retests.

All bars are synthetic constructed shapes (tests/technical_helpers.py).
"""

from decimal import Decimal

import pytest
from stellar.technical import (
    LegDirection,
    LegRole,
    Limitation,
    PivotKind,
    PivotStatus,
    StructureEventKind,
    StructureState,
    SwingLabel,
    ZoneEventKind,
    ZoneKind,
    analyse,
)
from stellar.technical.numeric import calc
from technical_helpers import (
    DOWN_ZIGZAG,
    TEST_CONFIG,
    UP_ZIGZAG,
    D,
    config,
    from_closes,
    from_ohlc,
    response,
)

pytestmark = pytest.mark.unit


def q(a, b):
    """a / b in the engine's explicit decimal context (34 digits)."""
    with calc():
        return Decimal(a) / Decimal(b)


def run(bars, cfg=TEST_CONFIG, as_of=None):
    resp = response(bars)
    return analyse(resp, as_of=as_of or resp.request.as_of, config=cfg)


# --- pivots -------------------------------------------------------------------------------------


def test_swing_high_and_low_are_found_with_their_window():
    a = run(from_closes(UP_ZIGZAG))
    confirmed = [p for p in a.pivots if p.status is PivotStatus.CONFIRMED]
    assert [(p.kind, p.price) for p in confirmed][:2] == [(PivotKind.HIGH, D("108.5")),
                                                          (PivotKind.LOW, D("102.5"))]
    assert all(p.left == 2 and p.right == 2 for p in a.pivots)


def test_a_pivot_is_confirmed_only_when_its_right_window_has_closed():
    bars = from_closes(UP_ZIGZAG)
    first_high = 2  # the bar closing at 108 (high 108.5)
    before = run(bars, as_of=bars[first_high + 1].close_time)
    candidate = [p for p in before.pivots if p.index == first_high]
    assert candidate and candidate[0].status is PivotStatus.CANDIDATE
    assert candidate[0].confirmed_at is None and candidate[0].right_bars_seen == 1
    assert Limitation.UNCONFIRMED_PIVOT in before.limitations
    assert before.structure.swings == ()  # candidates never feed structure
    after = run(bars, as_of=bars[first_high + 2].close_time)
    (confirmed,) = [p for p in after.pivots if p.index == first_high]
    assert confirmed.status is PivotStatus.CONFIRMED
    assert confirmed.confirmed_at == bars[first_high + 2].close_time


def test_equal_extremes_are_not_pivots():
    rows = [(10, 11, 9, 10.5), (10.5, 12, 10, 11), (11, 13, 10.5, 12), (12, 13, 11, 11.5),
            (11.5, 12, 10.8, 11), (11, 11.5, 10.5, 11)]
    assert [p for p in run(from_ohlc(rows)).pivots if p.kind is PivotKind.HIGH] == []


def test_without_a_pivot_window_nothing_structural_is_guessed():
    a = run(from_closes(UP_ZIGZAG), cfg=config(pivots={}))
    assert a.pivots == () and a.structure.state is StructureState.INSUFFICIENT
    assert Limitation.PIVOT_WINDOW_UNSET in a.limitations and a.legs == () and a.zones == ()


# --- structure ----------------------------------------------------------------------------------


def test_up_structure_labels_hh_hl():
    a = run(from_closes(UP_ZIGZAG))
    labels = [s.label for s in a.structure.swings if s.label is not None]
    assert labels == [SwingLabel.HH, SwingLabel.HL, SwingLabel.HH]
    assert a.structure.state is StructureState.UP


def test_down_structure_labels_lh_ll():
    a = run(from_closes(DOWN_ZIGZAG))
    labels = [s.label for s in a.structure.swings if s.label is not None]
    assert labels == [SwingLabel.LL, SwingLabel.LH, SwingLabel.LL]
    assert a.structure.state is StructureState.DOWN


def test_equal_swings_make_a_range():
    closes = [100, 104, 108, 104, 100, 104, 108, 104, 100, 104, 108, 104, 100]
    a = run(from_closes(closes))
    assert {s.label for s in a.structure.swings if s.label} == {SwingLabel.EQH, SwingLabel.EQL}
    assert a.structure.state is StructureState.RANGE


def test_near_equal_needs_an_explicit_tolerance():
    closes = [100, 104, 108, 104, 100, 104, 108.2, 104, 100.1, 104, 108, 104, 100]
    exact = run(from_closes(closes), cfg=config(equal_tolerance={}))
    tolerant = run(from_closes(closes), cfg=config(equal_tolerance={"price": "0.5"}))
    assert SwingLabel.HH in {s.label for s in exact.structure.swings}
    assert exact.structure.equal_tolerance_method == "exact"
    assert {s.label for s in tolerant.structure.swings if s.label} <= {SwingLabel.EQH,
                                                                       SwingLabel.EQL}
    assert tolerant.structure.state is StructureState.RANGE


def test_break_down_against_an_up_structure_is_described_not_interpreted():
    a = run(from_closes(UP_ZIGZAG + [114, 108]))
    (event,) = [e for e in a.structure.events
                if e.kind is StructureEventKind.STRUCTURE_BREAK_DOWN]
    assert event.level == D("109.5") and event.close < event.level
    assert a.structure.state is StructureState.UP and a.structure.break_against_state


def test_break_up_by_close_not_by_wick():
    wick_only = UP_ZIGZAG[:-1] + [122.4]  # high 122.9 > 122.5 but close below
    a = run(from_closes(wick_only, wick="0.5"))
    assert not [e for e in a.structure.events if e.kind is StructureEventKind.STRUCTURE_BREAK_UP]
    a = run(from_closes(UP_ZIGZAG + [123]))
    assert [e for e in a.structure.events if e.kind is StructureEventKind.STRUCTURE_BREAK_UP]


def test_too_few_swings_is_insufficient():
    a = run(from_closes([100, 104, 108, 105, 103, 104]))
    assert a.structure.state is StructureState.INSUFFICIENT
    assert Limitation.INSUFFICIENT_HISTORY in a.limitations


# --- impulse / pullback / consolidation ---------------------------------------------------------


def test_legs_measure_impulses_between_confirmed_swings():
    a = run(from_closes(UP_ZIGZAG))
    up = [leg for leg in a.legs if leg.direction is LegDirection.UP]
    first = up[0]
    assert first.net_move == D(13) and first.role is LegRole.WITH_STRUCTURE
    assert first.bars == 3 and first.path_length == D(12)  # closes 103 -> 107, 111, 115
    assert first.efficiency == q(13, 12)
    assert first.cumulative_body == D(12)
    assert first.atr_normalised_move is not None
    assert all(leg.role is LegRole.COUNTER_STRUCTURE for leg in a.legs
               if leg.direction is LegDirection.DOWN)


def test_pullback_depth_duration_and_ratio_against_the_last_leg():
    a = run(from_closes(UP_ZIGZAG))
    p = a.pullback
    assert p.reference_direction is LegDirection.UP and p.bars == 3
    assert p.max_adverse_price == D("116.5") and p.depth == D(6)
    assert p.retracement_ratio == q(6, 13)
    assert (p.counter_direction_bars, p.with_direction_bars) == (2, 1)
    assert p.counter_body_total == D(5) and p.with_body_total == D(4)


def test_pullback_after_a_down_leg_is_measured_upwards():
    p = run(from_closes(DOWN_ZIGZAG)).pullback
    assert p.reference_direction is LegDirection.DOWN
    assert p.max_adverse_price == D("183.5") and p.depth == D(6)  # 183.5 - 177.5
    assert p.retracement_ratio == q(6, 13)
    assert (p.counter_direction_bars, p.with_direction_bars) == (2, 1)


def test_consolidation_is_measured_and_only_classified_with_thresholds():
    tight = [100, 104, 108, 112, 116, 115.8, 116.1, 115.9, 116.0]
    a = run(from_closes(tight, wick="0.2"))
    c = a.consolidation
    assert c.lookback == 4 and c.overlap_ratio == 1 and c.is_consolidation is True
    unset = run(from_closes(tight, wick="0.2"),
                cfg=config(consolidation={"lookback": 4}))
    assert unset.consolidation.is_consolidation is None
    assert any(u.item == "consolidation_classification" for u in unset.unevaluated)


# --- zones, breakouts, retests ----------------------------------------------------------------

BREAK_RETEST = [
    (100, 101, 99, 100.5), (100.5, 103, 100, 102.5), (102.5, 110, 102, 108),
    (108, 108.5, 105, 106), (106, 107, 104, 105), (105, 109, 104.5, 108.8),
    (108.8, 110.2, 108.5, 110.0), (110, 111.5, 109.8, 111.2), (111.2, 111.4, 110.3, 111.0),
    (111, 111.2, 109.9, 110.1), (110.1, 110.8, 109.7, 110.2),
]


def zone_at(a, price):
    return next(z for z in a.zones if z.lower <= D(price) <= z.upper)


def test_zone_from_a_confirmed_swing_with_its_derivation():
    a = run(from_ohlc(BREAK_RETEST))
    z = zone_at(a, 110)
    assert z.kind is ZoneKind.RESISTANCE and (z.lower, z.upper) == (D("109.5"), D("110.5"))
    assert z.derivation == "confirmed_pivot_cluster" and z.tolerance == D("0.5")
    assert z.tolerance_method == "price" and len(z.source_pivot_ids) == 1
    assert z.first_known_at == from_ohlc(BREAK_RETEST)[4].close_time


def test_break_then_retest_held_then_failed():
    a = run(from_ohlc(BREAK_RETEST))
    kinds = [e.kind for e in zone_at(a, 110).events]
    assert kinds == [ZoneEventKind.CLOSE_ABOVE, ZoneEventKind.RETEST_ATTEMPT,
                     ZoneEventKind.RETEST_HELD, ZoneEventKind.RETEST_ATTEMPT,
                     ZoneEventKind.RETEST_FAILED, ZoneEventKind.WICK_ABOVE]
    assert zone_at(a, 110).state == "inside"


def test_zone_strength_never_uses_future_touches():
    bars = from_ohlc(BREAK_RETEST)
    early = run(bars, as_of=bars[7].close_time)
    late = run(bars)
    assert zone_at(early, 110).interactions == 2 < zone_at(late, 110).interactions
    assert zone_at(early, 110).last_tested_at == bars[7].close_time
    assert [e.kind for e in zone_at(early, 110).events] == [ZoneEventKind.CLOSE_ABOVE]


def test_repeated_swings_cluster_into_one_zone():
    closes = [100, 104, 108, 104, 100, 104, 108.2, 104, 100.1, 104, 108, 104, 100]
    a = run(from_closes(closes), cfg=config(zone_tolerance={"price": "0.5"}))
    top = zone_at(a, "108.6")
    assert len(top.source_pivot_ids) == 3 and top.kind is ZoneKind.RESISTANCE


def test_no_zones_without_a_tolerance():
    a = run(from_closes(UP_ZIGZAG), cfg=config(zone_tolerance={}))
    assert a.zones == () and any(u.item == "zones" and u.reason == "tolerance_unset"
                                 for u in a.unevaluated)
