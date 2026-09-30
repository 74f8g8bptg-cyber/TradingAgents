"""Phase 6b setup evaluation and lifecycle on synthetic evidence.

Nothing here is a real market fact: bars, quotes, research and thresholds are fixtures.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from research_helpers import AS_OF, STATION
from stellar.journal import StellarJournal
from stellar.pipeline.records import (
    ChallengeFinding,
    ChallengeKind,
    ChallengeReport,
    EvidenceGrade,
    RunStatus,
)
from stellar.reasoning import Stance
from stellar.schemas.market import Timeframe
from stellar.setups import (
    NumericSource,
    OptionKind,
    SetupBook,
    SetupConfig,
    SetupDirection,
    SetupInputError,
    SetupState,
    SetupStatus,
    StopBuffer,
    evaluate_setup,
    verify_setup,
)
from stellar.technical import PivotStatus, analyse_mtf
from stellar.technical.mtf import Alignment
from stellar.technical.numeric import calc
from technical_helpers import TEST_CONFIG, response
from trader_helpers import (
    INVALIDATED_CLOSES,
    LONG_CLOSES,
    RANGE_CLOSES,
    SETUP_CONFIG,
    SHORT_CLOSES,
    SINGLE_CLOSES,
    WICK_BREACH_CLOSES,
    H,
    bars_for,
    decision_support,
    decision_variant,
    reviewed,
    technical,
)

pytestmark = pytest.mark.unit

DOWN = {"specialist": Stance.SUPPORTS_DOWNSIDE, "research_manager": Stance.SUPPORTS_DOWNSIDE}


@pytest.fixture(scope="module")
def long_case():
    with StellarJournal() as j:
        analysis = technical(LONG_CLOSES)
        return analysis, decision_support(j, analysis)


@pytest.fixture(scope="module")
def short_case():
    with StellarJournal() as j:
        analysis = technical(SHORT_CLOSES)
        return analysis, decision_support(j, analysis, stances=DOWN)


def evaluate(case, *, config=SETUP_CONFIG, as_of=AS_OF, **decision_update):
    analysis, decision = case
    if decision_update:
        decision = decision_variant(decision, **decision_update)
    return evaluate_setup(technical=analysis, decision=decision, as_of=as_of, config=config)


# ------------------------------------------------------------------ clean candidates --


def test_clean_long_setup_is_ready_with_sourced_options(long_case):
    setup = evaluate(long_case)
    assert setup.status is SetupStatus.READY_FOR_PROPOSAL
    assert setup.state is SetupState.ARMED
    assert setup.direction is SetupDirection.LONG and setup.reasons == ()
    # invalidation is the reference leg's start swing (a CONFIRMED Phase 5 pivot)
    assert setup.invalidation_level == Decimal("109.0")
    kinds = {o.kind: o for o in setup.options}
    assert kinds[OptionKind.STRUCTURE_STOP].price == Decimal("109.0")
    assert kinds[OptionKind.STRUCTURE_STOP].basis == "structure_swing_low_no_buffer"
    zone = kinds[OptionKind.LIMIT_AT_ZONE]
    assert (zone.zone_low, zone.zone_high, zone.price) == (Decimal("115.0"), Decimal("116.0"),
                                                         None)  # a zone, not a midpoint
    targets = [o.price for o in setup.options if o.kind in (OptionKind.PRIOR_SWING_TARGET,
                                                            OptionKind.ZONE_TARGET)]
    assert targets == [Decimal("126.5"), Decimal("130.0")]
    assert kinds[OptionKind.MARKET_AT_QUOTE].price is None  # read from the quote at build time
    assert verify_setup(setup)


def test_every_option_number_names_a_non_llm_source_and_phase5_evidence(long_case):
    analysis, _ = long_case
    setup = evaluate(long_case)
    known = {p.evidence_id for p in analysis.pivots} | {z.evidence_id for z in analysis.zones} \
        | {g.evidence_id for g in analysis.legs}
    for o in setup.options:
        assert set(o.sources) <= set(NumericSource)
        if o.kind is not OptionKind.MARKET_AT_QUOTE:
            assert o.evidence_ids and set(o.evidence_ids) <= known


def test_clean_short_setup_is_the_mirror(short_case):
    setup = evaluate(short_case)
    assert setup.status is SetupStatus.READY_FOR_PROPOSAL
    assert setup.direction is SetupDirection.SHORT
    assert setup.invalidation_level == Decimal("141.0")
    stop = next(o for o in setup.options if o.kind is OptionKind.STRUCTURE_STOP)
    assert stop.price == Decimal("141.0") and stop.basis == "structure_swing_high_no_buffer"
    targets = [o.price for o in setup.options if o.role.value == "TARGET"]
    assert targets == [Decimal("123.5"), Decimal("120.0")]  # nearest first, below the entry


# ---------------------------------------------------------------- no setup / evidence --


def test_range_structure_is_no_setup(long_case):
    _, decision = long_case
    analysis = technical(RANGE_CLOSES)
    setup = evaluate_setup(technical=analysis, decision=reviewed(decision, analysis),
                           as_of=AS_OF, config=SETUP_CONFIG)
    assert setup.status is SetupStatus.NO_SETUP and setup.state is SetupState.NO_SETUP
    assert setup.direction is SetupDirection.NONE and setup.options == ()
    assert setup.reasons == ("structure_range",)


def test_insufficient_technical_history_is_insufficient_evidence(long_case):
    _, decision = long_case
    analysis = technical(LONG_CLOSES[:4])
    setup = evaluate_setup(technical=analysis, decision=reviewed(decision, analysis),
                           as_of=AS_OF, config=SETUP_CONFIG)
    assert setup.status is SetupStatus.INSUFFICIENT_EVIDENCE
    assert setup.reasons == ("technical_structure_insufficient",)


def test_counter_structure_last_leg_is_no_setup_whatever_the_red_candle_count(long_case):
    """A confirmed pullback low completes a counter-structure leg: no pullback setup, even
    though the bars since the high are 'red'. Candle counts are never a rule."""
    _, decision = long_case
    analysis = technical(LONG_CLOSES[:21] + [118, 120, 122])
    assert analysis.structure.state.value == "UP"
    setup = evaluate_setup(technical=analysis, decision=reviewed(decision, analysis),
                           as_of=AS_OF, config=SETUP_CONFIG)
    assert setup.status is SetupStatus.NO_SETUP
    assert setup.reasons == ("last_leg_not_with_structure",)


@pytest.mark.parametrize("update, reason", [
    ({"final_stance": Stance.INSUFFICIENT_EVIDENCE}, "research_stance_insufficient"),
    ({"status": RunStatus.FAILED}, "research_run_failed"),
])
def test_research_that_cannot_support_is_insufficient_evidence(long_case, update, reason):
    setup = evaluate(long_case, **update)
    assert setup.status is SetupStatus.INSUFFICIENT_EVIDENCE
    assert setup.direction is SetupDirection.LONG and reason in setup.reasons
    assert setup.options == ()


def test_insufficient_evidence_grade_blocks_the_setup(long_case):
    _, decision = long_case
    quality = decision.quality.model_copy(update={"grade": EvidenceGrade.INSUFFICIENT})
    setup = evaluate(long_case, quality=quality)
    assert setup.status is SetupStatus.INSUFFICIENT_EVIDENCE
    assert "evidence_grade_insufficient" in setup.reasons


def test_technical_macro_conflict_from_the_real_pipeline_is_conflicting_evidence():
    """UP structure, downside research: the Phase 6 guard makes it MIXED; the setup layer
    keeps the disagreement instead of averaging it."""
    with StellarJournal() as j:
        analysis = technical(LONG_CLOSES)
        decision = decision_support(j, analysis, stances=DOWN)
    setup = evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF,
                           config=SETUP_CONFIG)
    assert decision.final_stance is Stance.MIXED
    assert setup.status is SetupStatus.CONFLICTING_EVIDENCE
    assert setup.state is SetupState.NO_SETUP
    assert "research_stance_mixed" in setup.reasons
    assert "technical_macro_disagreement" in setup.reasons


@pytest.mark.parametrize("update, reason", [
    ({"final_stance": Stance.SUPPORTS_DOWNSIDE}, "research_stance_opposes_direction"),
    ({"challenge": ChallengeReport(findings=(ChallengeFinding(
        finding_id="chk_0123456789abcdef", kind=ChallengeKind.TECHNICAL_MACRO_DISAGREEMENT,
        subject="research_manager", detail="fixture"),))}, "technical_macro_disagreement"),
])
def test_opposing_research_is_conflicting_evidence(long_case, update, reason):
    setup = evaluate(long_case, **update)
    assert setup.status is SetupStatus.CONFLICTING_EVIDENCE and reason in setup.reasons


@pytest.mark.parametrize("alignment", [Alignment.DISAGREE, Alignment.AGREE_DOWN])
def test_multi_timeframe_disagreement_is_conflicting_evidence(long_case, alignment):
    analysis, decision = long_case
    mtf = analyse_mtf("XAUUSD", {Timeframe.H1: response(bars_for(LONG_CLOSES))},
                      timeframes=[Timeframe.H1], as_of=AS_OF, config=TEST_CONFIG)
    mtf = mtf.model_copy(update={"alignment": alignment})  # SYNTHETIC variant
    setup = evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF,
                           config=SETUP_CONFIG, mtf=mtf)
    assert setup.status is SetupStatus.CONFLICTING_EVIDENCE
    assert f"mtf_{alignment.value.lower()}" in setup.reasons


def test_neutral_research_keeps_a_candidate_but_not_ready(long_case):
    setup = evaluate(long_case, final_stance=Stance.NEUTRAL)
    assert setup.status is SetupStatus.CANDIDATE and setup.state is SetupState.WATCHING
    assert setup.reasons == ("research_does_not_support_direction",)


# -------------------------------------------------------------------- unset config --


def test_unset_configuration_invents_nothing_and_never_reaches_ready(long_case):
    setup = evaluate(long_case, config=SetupConfig())
    assert setup.status is SetupStatus.CANDIDATE
    assert setup.valid_until is None  # no expiry default
    assert set(setup.reasons) == {"ready_evidence_grades_unset", "setup_validity_unset",
                                  "no_entry_option"}
    assert {"entry_models_unset", "setup_validity_unset",
            "retracement_bounds_unset"} <= set(setup.unevaluated)
    kinds = {o.kind for o in setup.options}
    assert OptionKind.ATR_STOP not in kinds  # ATR only when configured
    stop = next(o for o in setup.options if o.kind is OptionKind.STRUCTURE_STOP)
    assert stop.buffer is None and stop.price == setup.invalidation_level  # no pip default


def test_evidence_grade_outside_the_configured_set_is_not_ready(long_case):
    config = SETUP_CONFIG.model_copy(update={"ready_evidence_grades": (EvidenceGrade.LIMITED,)})
    setup = evaluate(long_case, config=config)
    assert setup.status is SetupStatus.CANDIDATE
    assert setup.reasons == ("evidence_grade_not_ready",)


def test_configured_retracement_bounds_are_applied(long_case):
    ratio = long_case[0].pullback.retracement_ratio
    config = SETUP_CONFIG.model_copy(update={"min_retracement_ratio": Decimal("0.5")})
    assert ratio < Decimal("0.5")
    assert evaluate(long_case, config=config).reasons == ("retracement_below_min",)
    config = SETUP_CONFIG.model_copy(update={"max_retracement_ratio": Decimal("0.3")})
    assert evaluate(long_case, config=config).reasons == ("retracement_above_max",)


def test_configured_buffer_and_atr_stop_use_phase5_atr(long_case):
    analysis, _ = long_case
    atr = analysis.volatility.atr.value
    config = SETUP_CONFIG.model_copy(update={
        "stop_buffer": StopBuffer(atr_multiple=Decimal("0.5")),
        "atr_stop_multiple": Decimal("2")})
    setup = evaluate(long_case, config=config)
    stop = next(o for o in setup.options if o.kind is OptionKind.STRUCTURE_STOP)
    with calc():
        assert stop.price == Decimal("109.0") - Decimal("0.5") * atr
        assert_distance = Decimal("2") * atr
    assert stop.basis == "structure_swing_low_buffered"
    assert NumericSource.PHASE5_ATR in stop.sources and NumericSource.SETUP_CONFIG in stop.sources
    atr_stop = next(o for o in setup.options if o.kind is OptionKind.ATR_STOP)
    assert atr_stop.atr_distance == assert_distance and atr_stop.price is None


def test_config_rejects_inconsistent_bounds_and_overlapping_buffers():
    with pytest.raises(ValidationError):
        SetupConfig(min_retracement_ratio=Decimal("0.6"), max_retracement_ratio=Decimal("0.4"))
    with pytest.raises(ValidationError):
        StopBuffer(price=Decimal("1"), atr_multiple=Decimal("1"))
    with pytest.raises(ValidationError):
        SetupConfig(setup_validity_bars=1.5)


# ----------------------------------------------------------- invalidation and expiry --


def test_breach_of_the_invalidation_level_invalidates(long_case):
    _, decision = long_case
    analysis = technical(INVALIDATED_CLOSES)
    setup = evaluate_setup(technical=analysis, decision=reviewed(decision, analysis),
                           as_of=AS_OF, config=SETUP_CONFIG)
    assert setup.status is SetupStatus.INVALIDATED and setup.state is SetupState.INVALIDATED
    assert setup.options == ()
    assert setup.reasons == ("structure_break_against_state",)


def test_a_wick_through_the_invalidation_level_invalidates(long_case):
    _, decision = long_case
    analysis = technical(WICK_BREACH_CLOSES)
    assert not analysis.structure.break_against_state
    assert analysis.pullback.max_adverse_price < Decimal("109.0")
    setup = evaluate_setup(technical=analysis, decision=reviewed(decision, analysis),
                           as_of=AS_OF, config=SETUP_CONFIG)
    assert setup.status is SetupStatus.INVALIDATED
    assert setup.reasons == ("invalidation_level_breached",)


def test_setup_expires_at_valid_until(long_case):
    ready = evaluate(long_case)
    assert ready.valid_until == ready.valid_from + 4 * H  # test-only validity of 4 bars
    expired = evaluate(long_case, as_of=ready.valid_until)
    assert expired.status is SetupStatus.EXPIRED and expired.reasons == ("valid_until_reached",)
    assert expired.setup_id == ready.setup_id  # the same setup, a later state
    assert evaluate(long_case, as_of=ready.valid_until - H).status is \
        SetupStatus.READY_FOR_PROPOSAL


# ------------------------------------------------------------ identity / idempotency --


def test_same_evidence_gives_the_identical_setup(long_case):
    assert evaluate(long_case) == evaluate(long_case)


def test_changed_evidence_gives_a_new_fingerprint_and_a_new_leg_a_new_setup(long_case):
    base = evaluate(long_case)
    new_research = evaluate(long_case, outputs_hash="1" * 64)
    assert new_research.setup_id == base.setup_id
    assert new_research.fingerprint != base.fingerprint
    _, decision = long_case
    other = technical(SINGLE_CLOSES)
    other_setup = evaluate_setup(technical=other, decision=reviewed(decision, other),
                                 as_of=AS_OF, config=SETUP_CONFIG)
    assert other_setup.setup_id != base.setup_id
    changed_config = evaluate(long_case, config=SETUP_CONFIG.model_copy(
        update={"setup_validity_bars": 5}))
    assert changed_config.setup_id != base.setup_id


def test_setup_is_immutable_and_tamper_evident(long_case):
    setup = evaluate(long_case)
    with pytest.raises(ValidationError):
        setup.status = SetupStatus.CANDIDATE
    tampered = setup.model_copy(update={"invalidation_level": Decimal("100")})
    assert not verify_setup(tampered)


# ------------------------------------------------------------------- point in time --


def test_future_technical_evidence_is_refused(long_case):
    _, decision = long_case
    with pytest.raises(SetupInputError) as err:
        evaluate(long_case, as_of=AS_OF - H)
    assert err.value.code == "future_technical"
    later = technical(LONG_CLOSES, end=AS_OF + H)
    with pytest.raises(SetupInputError):
        evaluate_setup(technical=later, decision=reviewed(decision, later), as_of=AS_OF,
                       config=SETUP_CONFIG)


def test_future_research_is_refused(long_case):
    analysis, decision = long_case
    with pytest.raises(SetupInputError) as err:
        evaluate_setup(technical=analysis, decision=decision_variant(decision, as_of=AS_OF + H),
                       as_of=AS_OF, config=SETUP_CONFIG)
    assert err.value.code == "future_research"


def test_unconfirmed_pivot_is_never_a_level(long_case):
    """The latest pullback low (120.5) is a CANDIDATE pivot at as_of: no option uses it."""
    analysis, _ = long_case
    candidates = [p for p in analysis.pivots if p.status is PivotStatus.CANDIDATE]
    setup = evaluate(long_case)
    used = {e for o in setup.options for e in o.evidence_ids}
    prices = {o.price for o in setup.options} | {o.zone_low for o in setup.options}
    assert Decimal("120.5") not in prices
    assert not {p.evidence_id for p in candidates} & used
    confirmed = {p.evidence_id for p in analysis.pivots if p.status is PivotStatus.CONFIRMED}
    assert {e for e in used if e.startswith("piv_")} <= confirmed


def test_the_decision_support_must_have_reviewed_this_analysis(long_case):
    _, decision = long_case
    other = technical(SINGLE_CLOSES)
    with pytest.raises(SetupInputError) as err:
        evaluate_setup(technical=other, decision=decision, as_of=AS_OF, config=SETUP_CONFIG)
    assert err.value.code == "technical_not_reviewed"


def test_a_tampered_technical_analysis_is_refused(long_case):
    analysis, decision = long_case
    tampered = analysis.model_copy(update={"pullback": analysis.pullback.model_copy(
        update={"depth": Decimal("99")})})
    with pytest.raises(SetupInputError) as err:
        evaluate_setup(technical=tampered, decision=decision, as_of=AS_OF, config=SETUP_CONFIG)
    assert err.value.code == "technical_hash_mismatch"


def test_instrument_mismatch_is_refused(long_case):
    analysis, decision = long_case
    with pytest.raises(SetupInputError):
        evaluate_setup(technical=analysis, decision=decision_variant(decision,
                                                                     instrument="EURUSD"),
                       as_of=AS_OF, config=SETUP_CONFIG)


# ----------------------------------------------------------------------- lifecycle --


def test_lifecycle_journals_transitions_once(long_case):
    with StellarJournal() as j:
        book = SetupBook(j, station_id=STATION, clock=lambda: AS_OF)
        neutral = evaluate(long_case, final_stance=Stance.NEUTRAL)
        first = book.record(neutral)
        assert first.changed and first.previous is None and first.state is SetupState.WATCHING
        assert first.rule == "research_does_not_support_direction"
        assert not book.record(neutral).changed  # same evidence: nothing journaled
        ready = evaluate(long_case)
        armed = book.record(ready)
        assert armed.changed and armed.previous is SetupState.WATCHING
        assert armed.state is SetupState.ARMED and armed.rule == "ready_for_proposal"
        events = j.read(types=["setup.state.changed"])
        assert [(e.payload["from"], e.payload["to"]) for e in events] == [
            (None, "WATCHING"), ("WATCHING", "ARMED")]
        assert events[-1].payload["fingerprint"] == ready.fingerprint
        assert events[-1].correlation_id == ready.evidence.run_id


def test_terminal_states_refuse_to_reopen(long_case):
    with StellarJournal() as j:
        book = SetupBook(j, station_id=STATION, clock=lambda: AS_OF)
        ready = evaluate(long_case)
        book.record(ready)
        expired = evaluate(long_case, as_of=ready.valid_until)
        assert book.record(expired).state is SetupState.EXPIRED
        back = book.record(ready)
        assert back.refused and back.state is SetupState.EXPIRED and not back.changed
        assert book.state(ready.setup_id) is SetupState.EXPIRED


def test_proposed_is_set_only_for_the_armed_evidence(long_case):
    with StellarJournal() as j:
        book = SetupBook(j, station_id=STATION, clock=lambda: AS_OF)
        ready = evaluate(long_case)
        refused = book.mark_proposed(ready, "prop_x")
        assert refused.refused  # never armed in this journal
        book.record(ready)
        other = evaluate(long_case, outputs_hash="2" * 64)
        assert book.mark_proposed(other, "prop_x").refused  # other evidence
        done = book.mark_proposed(ready, "prop_x")
        assert done.changed and done.state is SetupState.PROPOSED
        assert not book.mark_proposed(ready, "prop_x").changed  # idempotent
        # a later evaluation does not move a proposed setup back
        kept = book.record(evaluate(long_case, final_stance=Stance.NEUTRAL))
        assert kept.state is SetupState.PROPOSED and kept.rule == "already_proposed"
        assert not kept.refused and not kept.changed
