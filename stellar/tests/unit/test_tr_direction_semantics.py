"""LONG / SHORT semantics of Phase 6b proposals (Foundation §4.13, R-1, L8).

- ``TradeProposal.direction`` (LONG / SHORT) is the only field that says which way a position
  opens, and it is copied from the setup.
- ``source_rating`` is approval strength for that setup. Buy means "take this setup", in
  either direction; it is never a side.
- The upstream "Sell" rating means "exit or avoid the position". It never approves a proposal,
  and nothing translates it into a SHORT.

Nothing here is a real market fact: bars, quotes and ratings are synthetic fixtures.
"""

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from research_helpers import AS_OF, STATION
from stellar.journal import StellarJournal
from stellar.proposals import ApprovalSource, ProposalFailure, ProposalStatus, build_proposal
from stellar.reasoning import Stance
from stellar.schemas.common import SIDE_FOR_DIRECTION, Direction, OrderSide
from stellar.schemas.proposal import PROPOSAL_RATINGS, Rating, TradeProposal
from stellar.setups import OptionKind, SetupDirection, SetupStatus, evaluate_setup
from stellar.trader import OutcomeKind, TraderDesk, TraderInputs
from trader_helpers import (
    LONG_CLOSES,
    SETUP_CONFIG,
    SHORT_CLOSES,
    TRADER_CONFIG,
    approve,
    approve_for,
    decision_support,
    market,
    owner_selection,
    technical,
    trader_provider,
)

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "stellar"
DOWN = {"specialist": Stance.SUPPORTS_DOWNSIDE, "research_manager": Stance.SUPPORTS_DOWNSIDE}
LONG_MARKET = market(LONG_CLOSES, bid="122.0", ask="122.2")
SHORT_MARKET = market(SHORT_CLOSES, bid="127.8", ask="128.0")


@pytest.fixture(scope="module")
def cases():
    with StellarJournal() as j:
        long_t, short_t = technical(LONG_CLOSES), technical(SHORT_CLOSES)
        long_d = decision_support(j, long_t)
        short_d = decision_support(j, short_t, stances=DOWN)
    long_s = evaluate_setup(technical=long_t, decision=long_d, as_of=AS_OF, config=SETUP_CONFIG)
    short_s = evaluate_setup(technical=short_t, decision=short_d, as_of=AS_OF,
                             config=SETUP_CONFIG)
    assert long_s.status is short_s.status is SetupStatus.READY_FOR_PROPOSAL
    return {"LONG": (long_s, LONG_MARKET, (long_t, long_d)),
            "SHORT": (short_s, SHORT_MARKET, (short_t, short_d))}


def build(setup, mkt, approval):
    return build_proposal(setup=setup, selection=owner_selection(setup), approval=approval,
                          market=mkt, config=SETUP_CONFIG, created_at=AS_OF)


# ------------------------------------------------------------------ exact semantics --


def test_long_semantics_are_unambiguous(cases):
    setup, mkt, _ = cases["LONG"]
    p = build(setup, mkt, approve(setup)).proposal
    assert setup.direction is SetupDirection.LONG
    assert p.direction is Direction.LONG  # opens a long position
    assert p.source_rating is Rating.BUY  # approval strength for this setup, not a side
    assert SIDE_FOR_DIRECTION[p.direction] is OrderSide.BUY  # Phase 3 intent side
    assert p.entry.price == mkt.latest_quote.ask  # a long enters at the ask
    assert p.stop_loss.price < p.entry.price < min(t.price for t in p.take_profits)


def test_short_semantics_are_supported_and_unambiguous(cases):
    """A READY SHORT setup does produce a proposal: ``direction=SHORT`` opens the short. The
    Buy rating is the approval of *that* SHORT setup and carries no side of its own."""
    setup, mkt, _ = cases["SHORT"]
    p = build(setup, mkt, approve(setup)).proposal
    assert setup.direction is SetupDirection.SHORT
    assert p.direction is Direction.SHORT  # opens a short position
    assert p.source_rating is Rating.BUY  # "take this setup" (R-1), not "buy the instrument"
    assert SIDE_FOR_DIRECTION[p.direction] is OrderSide.SELL  # Phase 3 intent side
    assert p.entry.price == mkt.latest_quote.bid  # a short enters at the bid
    assert p.stop_loss.price > p.entry.price > max(t.price for t in p.take_profits)


def test_the_order_side_is_derived_from_direction_only():
    """Phase 3 builds the intent side from ``proposal.direction`` via SIDE_FOR_DIRECTION;
    neither it nor Phase 6b reads a side from the rating."""
    intents = (SRC / "risk" / "intents.py").read_text(encoding="utf-8")
    assert "side=SIDE_FOR_DIRECTION[proposal.direction]" in intents
    assert "source_rating" not in intents
    assert SIDE_FOR_DIRECTION == {Direction.LONG: OrderSide.BUY, Direction.SHORT: OrderSide.SELL}
    assert set(Direction) == {Direction.LONG, Direction.SHORT}  # no third, ambiguous value


# ------------------------------------------------------------- every rating × side --


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("rating", list(Rating))
def test_only_buy_builds_and_the_direction_is_always_the_setups(cases, side, rating):
    setup, mkt, _ = cases[side]
    out = build(setup, mkt, approve(setup, rating))
    if rating is Rating.BUY:
        assert out.status is ProposalStatus.BUILT
        assert out.proposal.direction.value == setup.direction.value
    else:
        assert out.status is ProposalStatus.REFUSED and out.proposal is None
        assert out.failure in (ProposalFailure.RATING_DOES_NOT_APPROVE,
                               ProposalFailure.OVERWEIGHT_D9_UNRESOLVED)


# ------------------------------------------------------------- no Sell-as-short --


def test_sell_never_opens_a_short(cases):
    setup, mkt, _ = cases["SHORT"]
    out = build(setup, mkt, approve(setup, Rating.SELL))
    assert out.failure is ProposalFailure.RATING_DOES_NOT_APPROVE and out.proposal is None
    out = build(setup, mkt, approve(setup, Rating.UNDERWEIGHT))
    assert out.failure is ProposalFailure.RATING_DOES_NOT_APPROVE


def test_sell_on_a_long_setup_never_becomes_a_short(cases):
    long_setup, mkt, _ = cases["LONG"]
    for direction in Direction:
        out = build(long_setup, mkt, approve(long_setup, Rating.SELL, direction=direction))
        assert out.proposal is None


def test_no_code_maps_a_rating_to_a_direction_or_a_side():
    """The trader layer never names Sell / Underweight / an order side, and no mapping keyed
    by Rating exists (the only rating comparisons are the Buy / Overweight gates)."""
    for pkg in ("setups", "proposals", "trader"):
        for path in (SRC / pkg).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    assert (node.value.id, node.attr) not in {
                        ("Rating", "SELL"), ("Rating", "UNDERWEIGHT"), ("Rating", "HOLD")}, path
                    assert node.value.id not in ("OrderSide",), path
                if isinstance(node, ast.ImportFrom):
                    assert not {a.name for a in node.names} & {"OrderSide",
                                                               "SIDE_FOR_DIRECTION"}, path
                if isinstance(node, ast.Name):
                    assert node.id not in ("SIDE_FOR_DIRECTION", "OrderSide"), path
                if isinstance(node, ast.Dict):
                    keys = {getattr(k, "value", None) and getattr(k.value, "id", None)
                            for k in node.keys if k is not None}
                    assert "Rating" not in keys, path


def test_the_rating_vocabulary_that_may_propose_is_buy_or_overweight_only():
    assert {Rating.BUY, Rating.OVERWEIGHT} == PROPOSAL_RATINGS  # Phase 1 schema (R-1)
    assert Rating.SELL not in PROPOSAL_RATINGS


# ------------------------------------------------- no SHORT → LONG by accident --


def test_a_long_approval_cannot_turn_a_short_setup_into_a_long_proposal(cases):
    setup, mkt, _ = cases["SHORT"]
    out = build(setup, mkt, approve(setup, direction=Direction.LONG))
    assert out.failure is ProposalFailure.APPROVAL_DIRECTION_MISMATCH and out.proposal is None


def test_a_short_approval_cannot_turn_a_long_setup_into_a_short_proposal(cases):
    setup, mkt, _ = cases["LONG"]
    out = build(setup, mkt, approve(setup, direction=Direction.SHORT))
    assert out.failure is ProposalFailure.APPROVAL_DIRECTION_MISMATCH


def test_an_approval_for_another_setup_is_refused(cases):
    long_setup, _, _ = cases["LONG"]
    short_setup, mkt, _ = cases["SHORT"]
    borrowed = approve(long_setup).model_copy(update={"direction": Direction.SHORT})
    out = build(short_setup, mkt, borrowed)
    assert out.failure is ProposalFailure.APPROVAL_FOR_OTHER_SETUP


def test_a_short_setup_with_a_long_market_view_cannot_be_forced_long(cases):
    """Even with LONG-side prices in hand, the builder never flips the setup's direction: the
    SHORT options against a quote above the stop fail geometry instead."""
    setup, _, _ = cases["SHORT"]
    above_stop = market(SHORT_CLOSES, bid="142.0", ask="142.2")
    out = build(setup, above_stop, approve(setup))
    assert out.failure is ProposalFailure.INVALID_STOP_GEOMETRY and out.proposal is None


def test_the_schema_rejects_short_direction_with_long_geometry(cases):
    setup, mkt, _ = cases["SHORT"]
    data = build(setup, mkt, approve(setup)).proposal.model_dump()
    data["direction"] = Direction.LONG  # flip only the direction
    with pytest.raises(ValidationError):
        TradeProposal.model_validate(data)


def test_short_through_the_desk_with_the_trader(cases):
    _, mkt, (analysis, decision) = cases["SHORT"]
    with StellarJournal() as j:
        desk = TraderDesk(journal=j, setup_config=SETUP_CONFIG, trader_config=TRADER_CONFIG,
                          provider=trader_provider(), station_id=STATION, clock=lambda: AS_OF)
        out = desk.run(TraderInputs(technical=analysis, decision=decision, market=mkt,
                                    as_of=AS_OF, approval=approve_for(analysis, decision)))
        assert out.kind is OutcomeKind.TRADE_PROPOSAL
        assert out.proposal.direction is Direction.SHORT
        event = j.read(types=["trade.proposed"])[0]
        assert event.payload["direction"] == "SHORT"
        assert event.payload["approval"]["direction"] == "SHORT"
        assert event.payload["approval"]["rating"] == "Buy"


def test_short_through_the_desk_with_a_long_approval_proposes_nothing(cases):
    _, mkt, (analysis, decision) = cases["SHORT"]
    with StellarJournal() as j:
        desk = TraderDesk(journal=j, setup_config=SETUP_CONFIG, trader_config=TRADER_CONFIG,
                          provider=trader_provider(), station_id=STATION, clock=lambda: AS_OF)
        wrong = approve_for(analysis, decision, direction=Direction.LONG,
                            source=ApprovalSource.PORTFOLIO_MANAGER)
        out = desk.run(TraderInputs(technical=analysis, decision=decision, market=mkt,
                                    as_of=AS_OF, approval=wrong))
        assert out.kind is OutcomeKind.SETUP_CANDIDATE and out.proposal is None
        assert out.proposal_outcome.failure is ProposalFailure.APPROVAL_DIRECTION_MISMATCH
        assert j.read(types=["trade.proposed"]) == []


def test_zone_and_target_prices_of_a_short_are_below_its_stop(cases):
    setup, mkt, _ = cases["SHORT"]
    sel = owner_selection(setup, entry=OptionKind.LIMIT_AT_ZONE,
                          targets=(OptionKind.PRIOR_SWING_TARGET, OptionKind.ZONE_TARGET))
    p = build_proposal(setup=setup, selection=sel, approval=approve(setup), market=mkt,
                       config=SETUP_CONFIG, created_at=AS_OF).proposal
    assert p.direction is Direction.SHORT and p.entry.zone_low == Decimal("134.0")
    assert p.stop_loss.price > p.entry.zone_high
    assert [t.price for t in p.take_profits] == [Decimal("123.5"), Decimal("120.0")]
