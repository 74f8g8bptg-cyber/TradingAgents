"""Phase 5: point-in-time guarantees, determinism, quality, multi-timeframe evidence and
publishing. All bars are synthetic constructed shapes (tests/technical_helpers.py)."""

from datetime import timedelta
from decimal import Decimal, getcontext, localcontext

import pytest
from stellar.journal import StellarJournal
from stellar.schemas.market import Timeframe
from stellar.technical import (
    Alignment,
    Limitation,
    SnapshotMismatch,
    StructureState,
    TechnicalAnalysis,
    TechnicalConfig,
    TechnicalInputError,
    analyse,
    analyse_mtf,
    publish_technical_analysis,
    verify,
)
from stellar.telemetry import EVENT_TYPES
from technical_helpers import (
    DOWN_ZIGZAG,
    T0,
    TEST_CONFIG,
    UP_ZIGZAG,
    config,
    from_closes,
    response,
    snapshot,
)

pytestmark = pytest.mark.unit
H = timedelta(hours=1)
SOURCE_ONLY = {"analysis_id": True, "content_hash": True, "provenance": True,
               "source": {"response_as_of": True, "response_series_hash": True}}


def run(bars, cfg=TEST_CONFIG, as_of=None, **kw):
    resp = response(bars, **kw)
    return analyse(resp, as_of=as_of or resp.request.as_of, config=cfg)


# --- point in time --------------------------------------------------------------------------------


def test_an_analysis_at_t_never_depends_on_bars_after_t():
    bars = from_closes(UP_ZIGZAG + [114, 108, 111])
    full = response(bars)
    for k in range(2, len(bars)):
        as_of = bars[k].close_time
        with_future = analyse(full, as_of=as_of, config=TEST_CONFIG)
        without = analyse(response(bars[:k + 1]), as_of=as_of, config=TEST_CONFIG)
        assert with_future.model_dump(exclude=SOURCE_ONLY) == \
            without.model_dump(exclude=SOURCE_ONLY), k


def test_unclosed_and_future_bars_are_never_used():
    bars = from_closes(UP_ZIGZAG)
    mid_bar = bars[5].open_time + timedelta(minutes=30)
    a = analyse(response(bars), as_of=mid_bar, config=TEST_CONFIG)
    assert a.source.bar_count == 5 and a.source.last_bar_close_time == bars[4].close_time


def test_as_of_after_the_data_is_refused():
    bars = from_closes(UP_ZIGZAG)
    with pytest.raises(TechnicalInputError, match="later bars are unknown"):
        analyse(response(bars), as_of=bars[-1].close_time + H, config=TEST_CONFIG)


def test_evidence_dated_after_as_of_cannot_be_constructed():
    a = run(from_closes(UP_ZIGZAG))
    data = a.model_dump()
    data["as_of"] = a.as_of - H
    with pytest.raises(ValueError, match="look-ahead"):
        TechnicalAnalysis.model_validate(data)


# --- determinism ----------------------------------------------------------------------------------


def test_same_input_same_analysis_and_hash():
    bars = from_closes(UP_ZIGZAG)
    first, second = run(bars), run(bars)
    assert first == second and first.content_hash == second.content_hash
    assert first.analysis_id == f"an_{first.content_hash[:40]}" and verify(first)


def test_the_callers_decimal_context_does_not_change_results():
    bars = from_closes(UP_ZIGZAG)
    reference = run(bars)
    with localcontext() as ctx:
        ctx.prec = 6
        assert getcontext().prec == 6
        assert run(bars).content_hash == reference.content_hash


def test_config_changes_the_hash_and_tampering_is_detected():
    bars = from_closes(UP_ZIGZAG)
    a, b = run(bars), run(bars, cfg=config(atr_period=4))
    assert a.content_hash != b.content_hash and a.config_hash != b.config_hash
    tampered = a.model_copy(update={"structure": a.structure.model_copy(
        update={"state": StructureState.DOWN})})
    assert not verify(tampered)


# --- quality / limitations ------------------------------------------------------------------------


def test_default_config_measures_everything_and_classifies_nothing_it_cannot():
    a = run(from_closes(UP_ZIGZAG), cfg=TechnicalConfig())
    assert len(a.candles) == len(UP_ZIGZAG) and a.candles[-1].features.range > 0
    assert {Limitation.THRESHOLD_UNSET, Limitation.PIVOT_WINDOW_UNSET,
            Limitation.CALENDAR_NAIVE_CONTEXT, Limitation.SYNTHETIC_SOURCE} <= set(a.limitations)
    assert a.indicators == () and a.zones == () and a.volatility.atr is None
    assert {u.item for u in a.unevaluated} >= {"pivots", "atr", "zones", "indicators",
                                               "consolidation", "doji_like"}


def test_proxy_data_is_refused_unless_allowed_and_then_labelled():
    bars = from_closes(UP_ZIGZAG)
    with pytest.raises(TechnicalInputError, match="refused"):
        run(bars, proxy=True)
    a = run(bars, cfg=config(allow_substitute_data=True), proxy=True)
    assert Limitation.PROXY_SOURCE in a.limitations
    assert a.source.mapping_kind.value == "PROXY"


# --- multi-timeframe ------------------------------------------------------------------------------


def h4_and_h1(h4_closes=UP_ZIGZAG, h1_closes=UP_ZIGZAG):
    h4 = from_closes(h4_closes, tf=Timeframe.H4, start=T0 - 16 * 4 * H)
    forming = from_closes([h4_closes[-1], h4_closes[-1] + 30], tf=Timeframe.H4, start=T0)[1:]
    forming = [forming[0].model_copy(update={"open_time": T0, "close_time": T0 + 4 * H})]
    h1 = from_closes(h1_closes, tf=Timeframe.H1, start=T0 - 16 * H)
    as_of = T0 + H
    return ({Timeframe.H4: response(h4 + forming, as_of=T0 + 4 * H),
             Timeframe.H1: response(h1, as_of=as_of)}, as_of)


def test_a_higher_timeframe_bar_is_used_only_after_it_closes():
    responses, as_of = h4_and_h1()
    m = analyse_mtf("XAUUSD", responses, timeframes=[Timeframe.H1, Timeframe.H4], as_of=as_of,
                    config=TEST_CONFIG)
    h4 = next(r for r in m.readings if r.timeframe is Timeframe.H4)
    assert h4.last_closed_bar_close_time == T0  # the H4 bar closing at T0 + 4h is excluded
    analysis = next(a for a in m.analyses if a.timeframe is Timeframe.H4)
    assert analysis.source.bar_count == 16
    assert h4.intervals_since_last_close == Decimal("0.25")


def test_agreement_and_disagreement():
    responses, as_of = h4_and_h1()
    agree = analyse_mtf("XAUUSD", responses, timeframes=[Timeframe.H4, Timeframe.H1],
                        as_of=as_of, config=TEST_CONFIG)
    assert agree.alignment is Alignment.AGREE_UP
    assert [r.timeframe for r in agree.readings] == [Timeframe.H4, Timeframe.H1]
    responses, as_of = h4_and_h1(h1_closes=DOWN_ZIGZAG)
    disagree = analyse_mtf("XAUUSD", responses, timeframes=[Timeframe.H4, Timeframe.H1],
                           as_of=as_of, config=TEST_CONFIG)
    assert disagree.alignment is Alignment.DISAGREE


def test_missing_timeframe_is_reported_not_synthesised():
    responses, as_of = h4_and_h1()
    m = analyse_mtf("XAUUSD", responses,
                    timeframes=[Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15],
                    as_of=as_of, config=TEST_CONFIG)
    assert set(m.missing_timeframes) == {Timeframe.D1, Timeframe.M15}
    assert Limitation.MISSING_TIMEFRAME in m.limitations
    assert {r.timeframe for r in m.readings if not r.available} == {Timeframe.D1,
                                                                   Timeframe.M15}
    assert m.alignment is Alignment.AGREE_UP  # the two available timeframes agree


def test_mtf_is_deterministic():
    responses, as_of = h4_and_h1()
    kwargs = {"timeframes": [Timeframe.H4, Timeframe.H1], "as_of": as_of, "config": TEST_CONFIG}
    assert analyse_mtf("XAUUSD", responses, **kwargs).content_hash == \
        analyse_mtf("XAUUSD", responses, **kwargs).content_hash


# --- publishing -----------------------------------------------------------------------------------


def test_publishing_uses_the_existing_analysis_created_event():
    bars = from_closes(UP_ZIGZAG)
    resp = response(bars)
    a = analyse(resp, as_of=resp.request.as_of, config=TEST_CONFIG)
    with StellarJournal() as journal:
        events = publish_technical_analysis(journal, a, snapshot(resp), station_id="stellar-test",
                                            created_at=a.as_of)
        assert [e.type for e in events] == ["analysis.created"] * 3
        assert {e.type for e in journal.read()} <= EVENT_TYPES
    assert [e.payload["kind"] for e in events] == ["structure", "momentum", "price_action"]
    assert [e.agent_id for e in events] == ["market_structure", "technical_indicator",
                                           "price_action"]
    assert all(e.payload["technical_analysis_id"] == a.analysis_id
               and e.payload["content_hash"] == a.content_hash for e in events)
    assert all(e.payload["report"]["snapshot_id"] == "snap_tech_01" for e in events)


def test_publishing_refuses_a_snapshot_of_another_series():
    bars = from_closes(UP_ZIGZAG)
    a = run(bars)
    other = response(from_closes(DOWN_ZIGZAG))
    with StellarJournal() as journal, pytest.raises(SnapshotMismatch):
        publish_technical_analysis(journal, a, snapshot(other), station_id="stellar-test",
                                   created_at=a.as_of)


# --- scope ----------------------------------------------------------------------------------------

FORBIDDEN_WORDS = ("buy", "sell", "long", "short", "entry", "stop", "target", "signal", "bias",
                   "profit", "probab", "opportunit", "recommend", "should")


def _names(model, seen=None):
    seen = seen if seen is not None else set()
    if model in seen:
        return set()
    seen.add(model)
    names = set(getattr(model, "model_fields", {}))
    for field in getattr(model, "model_fields", {}).values():
        for arg in _types(field.annotation):
            if hasattr(arg, "model_fields"):
                names |= _names(arg, seen)
            elif isinstance(arg, type) and hasattr(arg, "__members__"):
                names |= {m.lower() for m in arg.__members__}
    return names


def _types(annotation):
    args = getattr(annotation, "__args__", None)
    if not args:
        return [annotation]
    return [t for a in args for t in _types(a)]


def test_the_contract_has_no_trading_vocabulary():
    names = _names(TechnicalAnalysis)
    assert names  # the walk found the nested records
    # "signal" is allowed only as the MACD signal-line period (MacdSpec.signal), the
    # indicator's standard name; it is a moving average, not a trading signal.
    allowed = {"signal"}
    offenders = sorted(n for n in names - allowed if any(w in n for w in FORBIDDEN_WORDS))
    assert offenders == []
