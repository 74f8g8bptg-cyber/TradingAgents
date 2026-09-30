"""Phase 6b Trade Proposal Builder (P1) on synthetic setups.

Nothing here is a real market fact: bars, quotes, ratings and thresholds are fixtures.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from research_helpers import AS_OF
from stellar.journal import StellarJournal
from stellar.marketdata.contracts import FreshnessStatus, StaleReason
from stellar.proposals import (
    ApprovalSource,
    LevelSelection,
    ProposalFailure,
    ProposalStatus,
    SelectionSource,
    build_proposal,
)
from stellar.reasoning import Stance
from stellar.schemas.common import Direction
from stellar.schemas.proposal import EntryType, Rating
from stellar.setups import OptionKind, StopBuffer, evaluate_setup
from stellar.technical.numeric import calc
from trader_helpers import (
    LONG_CLOSES,
    SETUP_CONFIG,
    SHORT_CLOSES,
    H,
    approve,
    decision_support,
    decision_variant,
    market,
    option_of,
    owner_selection,
    technical,
)

pytestmark = pytest.mark.unit

DOWN = {"specialist": Stance.SUPPORTS_DOWNSIDE, "research_manager": Stance.SUPPORTS_DOWNSIDE}


@pytest.fixture(scope="module")
def long_inputs():
    with StellarJournal() as j:
        analysis = technical(LONG_CLOSES)
        return analysis, decision_support(j, analysis)


@pytest.fixture(scope="module")
def long_setup(long_inputs):
    analysis, decision = long_inputs
    return evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF,
                          config=SETUP_CONFIG)


@pytest.fixture(scope="module")
def short_setup():
    with StellarJournal() as j:
        analysis = technical(SHORT_CLOSES)
        decision = decision_support(j, analysis, stances=DOWN)
    return evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF,
                          config=SETUP_CONFIG)


LONG_MARKET = market(LONG_CLOSES, bid="122.0", ask="122.2")
SHORT_MARKET = market(SHORT_CLOSES, bid="127.8", ask="128.0")


_OWN = object()


def build(setup, *, selection=None, approval=_OWN, mkt=LONG_MARKET, config=SETUP_CONFIG,
          created_at=AS_OF, **selection_kw):
    selection = selection or owner_selection(setup, **selection_kw)
    approval = approve(setup) if approval is _OWN else approval
    return build_proposal(setup=setup, selection=selection, approval=approval, market=mkt,
                          config=config, created_at=created_at)


# ------------------------------------------------------------------- clean builds --


def test_clean_long_market_proposal(long_setup):
    out = build(long_setup, targets=(OptionKind.PRIOR_SWING_TARGET, OptionKind.ZONE_TARGET))
    assert out.status is ProposalStatus.BUILT and out.failure is None
    p = out.proposal
    assert p.direction is Direction.LONG and p.setup_id == long_setup.setup_id
    assert p.entry.type is EntryType.MARKET and p.entry.price == Decimal("122.2")  # the ask
    assert p.stop_loss.price == Decimal("109.0")
    assert [t.price for t in p.take_profits] == [Decimal("126.5"), Decimal("130.0")]
    assert p.source_rating is Rating.BUY and p.size_factor == 1
    assert p.reward_risk is None and p.llm_levels_advisory is None  # nothing invented
    assert p.valid_until == long_setup.valid_until and p.created_at == AS_OF
    assert p.snapshot_id == LONG_MARKET.snapshot_id and p.run_id == long_setup.evidence.run_id
    assert p.provenance.produced_by == "trade_proposal_builder"
    assert p.provenance.config_hash == SETUP_CONFIG.config_hash()
    assert long_setup.setup_id in p.provenance.input_ids
    assert long_setup.fingerprint in p.report_hashes
    assert long_setup.evidence.decision_outputs_hash in p.report_hashes
    assert out.reference_basis == "quote_ask"


def test_zone_entry_stays_a_zone_and_is_a_limit(long_setup):
    out = build(long_setup, entry=OptionKind.LIMIT_AT_ZONE)
    assert out.status is ProposalStatus.BUILT
    entry = out.proposal.entry
    assert entry.type is EntryType.LIMIT and entry.price is None
    assert (entry.zone_low, entry.zone_high) == (Decimal("115.0"), Decimal("116.0"))


def test_clean_short_proposal(short_setup):
    out = build(short_setup, mkt=SHORT_MARKET,
                targets=(OptionKind.PRIOR_SWING_TARGET, OptionKind.ZONE_TARGET))
    assert out.status is ProposalStatus.BUILT
    p = out.proposal
    assert p.direction is Direction.SHORT and p.entry.price == Decimal("127.8")  # the bid
    assert p.stop_loss.price == Decimal("141.0") > p.entry.price
    assert [t.price for t in p.take_profits] == [Decimal("123.5"), Decimal("120.0")]


def test_atr_stop_is_measured_from_the_entry_far_edge(long_inputs):
    analysis, decision = long_inputs
    config = SETUP_CONFIG.model_copy(update={"atr_stop_multiple": Decimal("2")})
    setup = evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF, config=config)
    out = build(setup, config=config, entry=OptionKind.LIMIT_AT_ZONE, stop=OptionKind.ATR_STOP)
    with calc():
        expected = Decimal("115.0") - Decimal("2") * analysis.volatility.atr.value
    assert out.proposal.stop_loss.price == expected
    assert out.proposal.stop_loss.basis == "atr_multiple_from_entry"


def test_same_inputs_same_proposal_and_changed_evidence_a_new_one(long_inputs, long_setup):
    a, b = build(long_setup), build(long_setup)
    assert a == b and a.proposal.proposal_id == b.proposal.proposal_id
    assert a.proposal_hash == b.proposal_hash
    analysis, decision = long_inputs
    changed = evaluate_setup(technical=analysis,
                             decision=decision_variant(decision, outputs_hash="3" * 64),
                             as_of=AS_OF, config=SETUP_CONFIG)
    assert build(changed).proposal.proposal_id != a.proposal.proposal_id
    later = build(long_setup, created_at=AS_OF + H)
    assert later.proposal.proposal_id != a.proposal.proposal_id


def test_proposal_is_immutable(long_setup):
    p = build(long_setup).proposal
    with pytest.raises(ValidationError):
        p.stop_loss = p.take_profits[0]


# ------------------------------------------------------------------------ geometry --


def test_invalid_stop_geometry_is_refused(long_setup):
    below_stop = market(LONG_CLOSES, bid="108.6", ask="108.8")
    out = build(long_setup, mkt=below_stop)
    assert out.status is ProposalStatus.REFUSED
    assert out.failure is ProposalFailure.INVALID_STOP_GEOMETRY and out.proposal is None


def test_invalid_target_geometry_is_refused(long_setup):
    above_target = market(LONG_CLOSES, bid="126.8", ask="127.0")
    out = build(long_setup, mkt=above_target)
    assert out.failure is ProposalFailure.INVALID_TARGET_GEOMETRY


def test_short_geometry_is_reversed(short_setup):
    out = build(short_setup, mkt=market(SHORT_CLOSES, bid="141.5", ask="141.7"))
    assert out.failure is ProposalFailure.INVALID_STOP_GEOMETRY


def test_marketable_limit_zone_is_refused(long_setup):
    inside = market(LONG_CLOSES, bid="115.3", ask="115.5")
    out = build(long_setup, mkt=inside, entry=OptionKind.LIMIT_AT_ZONE)
    assert out.failure is ProposalFailure.LIMIT_WOULD_BE_MARKETABLE


def test_market_entry_without_a_quote_is_unresolved(long_setup):
    out = build(long_setup, mkt=market(LONG_CLOSES, bid="1", ask="1", with_quote=False))
    assert out.failure is ProposalFailure.NO_QUOTE


def test_missing_target_cannot_be_selected(long_setup):
    with pytest.raises(ValidationError):
        LevelSelection(setup_id=long_setup.setup_id, setup_fingerprint=long_setup.fingerprint,
                       entry_option_id=option_of(long_setup, OptionKind.MARKET_AT_QUOTE).option_id,
                       stop_option_id=option_of(long_setup, OptionKind.STRUCTURE_STOP).option_id,
                       target_option_ids=(), source=SelectionSource.OWNER)


def test_unknown_or_misused_option_is_refused(long_setup):
    good = owner_selection(long_setup)
    unknown = good.model_copy(update={"stop_option_id": "opt_0000000000000000"})
    assert build(long_setup, selection=unknown).failure is ProposalFailure.UNKNOWN_OPTION
    swapped = good.model_copy(update={"stop_option_id": good.target_option_ids[0]})
    assert build(long_setup, selection=swapped).failure is ProposalFailure.OPTION_ROLE_MISMATCH


def test_selection_for_other_evidence_is_refused(long_inputs, long_setup):
    analysis, decision = long_inputs
    changed = evaluate_setup(technical=analysis,
                             decision=decision_variant(decision, outputs_hash="4" * 64),
                             as_of=AS_OF, config=SETUP_CONFIG)
    out = build(changed, selection=owner_selection(long_setup))
    assert out.failure is ProposalFailure.SELECTION_FOR_OTHER_EVIDENCE


def test_no_selection_is_refused(long_setup):
    out = build_proposal(setup=long_setup, selection=None, approval=approve(long_setup), market=LONG_MARKET,
                         config=SETUP_CONFIG, created_at=AS_OF)
    assert out.failure is ProposalFailure.SELECTION_REQUIRED


# ------------------------------------------------------------------------ approval --


def test_no_approval_no_proposal(long_setup):
    assert build(long_setup, approval=None).failure is ProposalFailure.APPROVAL_REQUIRED


def test_overweight_is_d9_no_trade(long_setup):
    ow = approve(long_setup, Rating.OVERWEIGHT)
    assert build(long_setup, approval=ow).failure is ProposalFailure.OVERWEIGHT_D9_UNRESOLVED


@pytest.mark.parametrize("rating", [Rating.HOLD, Rating.UNDERWEIGHT, Rating.SELL, Rating.REVIEW])
def test_hold_underweight_sell_review_never_propose(long_setup, rating):
    out = build(long_setup, approval=approve(long_setup, rating,
                                             source=ApprovalSource.PORTFOLIO_MANAGER))
    assert out.failure is ProposalFailure.RATING_DOES_NOT_APPROVE and out.proposal is None


def test_sell_on_a_long_setup_is_not_a_short(long_setup):
    out = build(long_setup, approval=approve(long_setup, Rating.SELL))
    assert out.proposal is None  # never re-read as "go short" (R-1, L8)


# ----------------------------------------------------------- config, time, data --


def test_profile_unset_refuses(long_inputs):
    analysis, decision = long_inputs
    config = SETUP_CONFIG.model_copy(update={"profile": None})
    setup = evaluate_setup(technical=analysis, decision=decision, as_of=AS_OF, config=config)
    assert build(setup, config=config).failure is ProposalFailure.PROFILE_NOT_CONFIGURED


def test_config_mismatch_refuses(long_setup):
    other = SETUP_CONFIG.model_copy(update={"stop_buffer": StopBuffer(price=Decimal("1"))})
    assert build(long_setup, config=other).failure is ProposalFailure.CONFIG_MISMATCH


def test_expired_setup_is_refused_at_build(long_setup):
    out = build(long_setup, created_at=long_setup.valid_until)
    assert out.failure is ProposalFailure.SETUP_EXPIRED


def test_not_ready_setup_is_refused(long_inputs):
    analysis, decision = long_inputs
    candidate = evaluate_setup(technical=analysis,
                               decision=decision_variant(decision, final_stance=Stance.NEUTRAL),
                               as_of=AS_OF, config=SETUP_CONFIG)
    out = build_proposal(setup=candidate, selection=None, approval=approve(candidate), market=LONG_MARKET,
                         config=SETUP_CONFIG, created_at=AS_OF)
    assert out.failure is ProposalFailure.SETUP_NOT_READY and out.detail == "CANDIDATE"


def test_stale_market_data_is_refused(long_setup):
    stale = LONG_MARKET.model_copy(update={"freshness": LONG_MARKET.freshness.model_copy(
        update={"status": FreshnessStatus.STALE,
                "stale_reason": StaleReason.OLDER_THAN_MAX_INTERVALS})})
    assert build(long_setup, mkt=stale).failure is ProposalFailure.MARKET_DATA_STALE


def test_future_market_data_is_refused(long_setup):
    future = market(LONG_CLOSES, bid="122.0", ask="122.2", end=AS_OF + H)
    assert build(long_setup, mkt=future).failure is ProposalFailure.FUTURE_MARKET_DATA


def test_market_data_older_than_the_evidence_is_refused(long_setup):
    old = market(LONG_CLOSES, bid="122.0", ask="122.2", end=AS_OF - H)
    out = build(long_setup, mkt=old)
    assert out.failure is ProposalFailure.MARKET_DATA_OLDER_THAN_EVIDENCE


def test_market_data_for_another_instrument_is_refused(long_setup):
    eur = market(LONG_CLOSES, bid="122.0", ask="122.2", instrument="EURUSD")
    assert build(long_setup, mkt=eur).failure is ProposalFailure.MARKET_DATA_MISMATCH


def test_targets_are_ordered_nearest_first_whatever_the_selection_order(long_setup):
    out = build(long_setup, targets=(OptionKind.ZONE_TARGET, OptionKind.PRIOR_SWING_TARGET))
    assert [t.price for t in out.proposal.take_profits] == [Decimal("126.5"), Decimal("130.0")]


def test_the_approval_is_part_of_the_proposal_identity(long_setup):
    owner = build(long_setup)
    pm = build(long_setup, approval=approve(long_setup,
                                            source=ApprovalSource.PORTFOLIO_MANAGER))
    assert owner.proposal.proposal_id != pm.proposal.proposal_id

