"""Paper Broker: a working order fills only under a current Phase 3 authorisation.

All prices are synthetic test fixtures. Scenario: a BUY limit at 2400.00 (stop 2388.00,
target 2424.00, 0.50 lots), authorised at AS_OF against a marketable synthetic quote
(ask 2399.90), submitted without market input, then made executable later.
"""

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from broker_helpers import Desk, M, bar, long_proposal, paper_config, quote
from factories import make_proposal
from risk_helpers import AS_OF, market, policy
from stellar.execution import (
    CurrentAuthorisation,
    FillAuthorisation,
    PaperBrokerError,
    PaperOrderStatus,
)
from stellar.journal import StellarJournal
from stellar.risk import BreakerTrip
from stellar.schemas.execution import ExecutionStatus

pytestmark = pytest.mark.unit
EXECUTION_SRC = Path(__file__).resolve().parents[2] / "src" / "stellar" / "execution"
Q1 = quote("2399.60", "2399.90", ts=AS_OF)  # makes the BUY limit 2400.00 executable


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def submitted(desk, proposal=None, *, intent_id="int_01", **overrides):
    """Authorise at AS_OF with Q1 in the context; submit without market input."""
    snap, q = market(bid="2399.60", ask="2399.90", quote_ts=AS_OF)
    intent, ctx = desk.authorise(proposal or long_proposal(), intent_id=intent_id,
                                 snapshot=snap, quote=q, **overrides)
    result = desk.broker.submit(intent, ctx, as_of=AS_OF)
    assert result.status is ExecutionStatus.ACKNOWLEDGED
    order = next(o for o in desk.broker.state().pending_orders if o.intent == intent)
    return order, CurrentAuthorisation(order_id=order.order_id, intent=intent, context=ctx)


def trigger(desk, auth=None, market_input=Q1, at=AS_OF):
    return desk.broker.process(market_input, as_of=at,
                               authorisations=[] if auth is None else [auth])


def status(desk, order):
    return next(o for o in desk.broker._book().orders.values()
                 if o.order_id == order.order_id)


def trip():
    return BreakerTrip(cause="risk_rule", rule="max_daily_loss", value="0.031", limit="0.03",
                       tripped_by="risk_engine", tripped_at=AS_OF)


# 1 --------------------------------------------------------------------------------------------


def test_unchanged_context_fills_under_the_original_approval(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    (filled,) = trigger(desk, auth).executions
    assert filled.status is ExecutionStatus.FILLED and filled.fill_price == Decimal("2400.00")
    record = status(desk, order)
    assert record.fill_authorisation.stage.value == "FILL"
    assert record.fill_authorisation.decision_id == order.intent.decision_id  # still current


# 2 --------------------------------------------------------------------------------------------


def test_a_tripped_breaker_never_lets_a_working_order_fill(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    desk.risk.breaker.trip(trip())
    (result,) = trigger(desk, auth).executions
    assert result.status is ExecutionStatus.CANCELLED
    assert status(desk, order).reason == "circuit_breaker_tripped"
    assert desk.broker.state().open_positions == ()


def test_no_authorisation_blocks_instead_of_filling(journal):
    desk = Desk(journal)
    order, _ = submitted(desk)
    (result,) = trigger(desk).executions
    assert result.status is ExecutionStatus.PREFLIGHT_FAILED
    assert result.reason == "authorisation_required" and result.filled_volume == 0
    blocked = status(desk, order)
    assert blocked.status is PaperOrderStatus.BLOCKED and blocked.fill is None
    assert desk.broker.state().pending_orders == (blocked,)  # still working, explicitly
    event = journal.read(types=["order.preflight.failed"])[-1].payload
    assert event["stage"] == "fill" and event["reason"] == "authorisation_required"
    count = len(journal.read())
    assert trigger(desk).executions == ()  # still blocked; the same reason is not re-journaled
    assert len(journal.read()) == count and desk.broker.stats().blocked == 1


# 3 --------------------------------------------------------------------------------------------


def test_changed_equity_does_not_use_the_old_approval(journal):
    desk = Desk(journal)
    short, ctx = desk.authorise(make_proposal(proposal_id="prop_02", entry={
        "type": "market", "price": "2399.80"}), intent_id="int_02")
    desk.broker.submit(short, ctx, as_of=AS_OF,
                       market=quote("2399.80", "2400.10", ts=AS_OF - timedelta(seconds=5)))
    order, auth = submitted(desk)  # authorised with the short marked at 2400.10
    equity = desk.broker.state().equity
    trigger(desk, market_input=quote("2400.10", "2400.40", ts=AS_OF))  # re-marks, no trigger
    assert desk.broker.state().equity != equity
    (result,) = trigger(desk, auth).executions
    assert result.reason == "broker_state_changed"
    assert status(desk, order).status is PaperOrderStatus.BLOCKED


# 4 --------------------------------------------------------------------------------------------


def test_changed_daily_pnl_does_not_use_the_old_approval(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    lower = {**auth.context.daily.model_dump(), "realised_pnl": "-500"}
    desk.risk.evaluate(auth.context.model_copy(update={"daily": auth.context.daily.model_copy(
        update={"realised_pnl": Decimal("-500")})}))  # the risk context has moved on
    assert trigger(desk, auth).executions[0].reason == "reevaluation_required"
    fresh = desk.reauthorise(status(desk, order), Q1, at=AS_OF, daily=lower)
    (filled,) = trigger(desk, fresh).executions
    assert filled.status is ExecutionStatus.FILLED
    assert status(desk, order).fill_authorisation.intent_id == "int_01_r1"


# 5 --------------------------------------------------------------------------------------------


def test_changed_positions_do_not_use_the_old_approval(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    other, ctx = desk.authorise(make_proposal(proposal_id="prop_02", entry={
        "type": "market", "price": "2399.80"}), intent_id="int_02")
    assert desk.broker.submit(other, ctx, as_of=AS_OF, market=quote(
        "2399.80", "2400.10", ts=AS_OF - timedelta(seconds=5))).status is ExecutionStatus.FILLED
    (result,) = trigger(desk, auth).executions
    assert result.reason == "broker_state_changed"
    assert len(desk.broker.state().open_positions) == 1  # only the other position


# 6 --------------------------------------------------------------------------------------------


def test_a_changed_quote_requires_reconfirmation(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    later = quote("2399.20", "2399.70", ts=AS_OF + M)  # wider spread, a later quote
    assert trigger(desk, auth, later, AS_OF + M).executions[0].reason == \
        "authorisation_not_current"
    stale_intent = CurrentAuthorisation(
        order_id=order.order_id, intent=auth.intent,
        context=desk.reauthorise(status(desk, order), later, at=AS_OF + M).context)
    assert trigger(desk, stale_intent, later, AS_OF + M).executions[0].reason == \
        "reevaluation_required"
    fresh = desk.reauthorise(status(desk, order), later, at=AS_OF + M, n=2)
    (filled,) = trigger(desk, fresh, later, AS_OF + M).executions
    assert filled.status is ExecutionStatus.FILLED
    record = status(desk, order)
    assert record.fill.spread == Decimal("0.50") and record.fill.source_price == later.ask
    assert record.fill_authorisation.context_as_of == AS_OF + M


# 7 --------------------------------------------------------------------------------------------


def test_a_changed_policy_blocks_the_old_approval(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    stricter = Desk(journal, policy=policy(version="test_policy_2"))  # same account, new policy
    (result,) = trigger(stricter, auth).executions
    assert result.reason == "reevaluation_required"
    fresh = stricter.reauthorise(status(stricter, order), Q1, at=AS_OF)
    assert trigger(stricter, fresh).executions[0].status is ExecutionStatus.FILLED
    assert status(stricter, order).fill_authorisation.evaluation_fingerprint == \
        stricter.risk.latest_evaluation("prop_01").fingerprint


# 8 --------------------------------------------------------------------------------------------


def test_a_blocked_order_stays_blocked_after_restart(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        desk = Desk(j)
        order, _ = submitted(desk)
        trigger(desk)
        before = desk.broker.state()
    with StellarJournal(path) as j:
        restarted = Desk(j)
        assert restarted.broker.state() == before
        assert status(restarted, order).status is PaperOrderStatus.BLOCKED
        count = len(j.read())
        assert trigger(restarted).executions == () and len(j.read()) == count
        fresh = restarted.reauthorise(status(restarted, order), Q1, at=AS_OF)
        assert trigger(restarted, fresh).executions[0].status is ExecutionStatus.FILLED


def test_blocked_orders_still_expire_and_can_be_cancelled(journal):
    desk = Desk(journal)
    order, _ = submitted(desk)
    trigger(desk)
    assert desk.broker.cancel(order.order_id, as_of=AS_OF + M).status is \
        ExecutionStatus.CANCELLED
    with StellarJournal() as j:
        other_desk = Desk(j)
        other, _ = submitted(other_desk)
        trigger(other_desk)
        (expired,) = other_desk.broker.expire_due(as_of=other.intent.expires_at)
        assert expired.status is ExecutionStatus.EXPIRED


# 9 --------------------------------------------------------------------------------------------


def test_an_authorisation_with_other_terms_is_refused(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    evaluation = desk.risk.latest_evaluation("prop_01")
    no_target = desk.risk.authorize_intent(evaluation, auth.context, intent_id="int_09",
                                           broker_symbol="XAUUSD", created_at=AS_OF,
                                           expires_at=order.intent.expires_at)
    offered = CurrentAuthorisation(order_id=order.order_id, intent=no_target,
                                   context=auth.context)
    assert trigger(desk, offered).executions[0].reason == "authorisation_terms_changed"


def test_authorisations_for_unknown_or_finished_orders_are_refused(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    trigger(desk, auth)  # filled
    with pytest.raises(ValueError, match="not a working order"):
        trigger(desk, auth)


def test_only_the_checker_builds_fill_authorisations():
    builders = sorted(
        p.name for p in EXECUTION_SRC.glob("*.py")
        if any(isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", ""))
               == "FillAuthorisation" for n in ast.walk(ast.parse(p.read_text())))
    )
    assert builders == ["checker.py"]


def test_a_position_cannot_be_opened_without_a_confirmed_authorisation(journal):
    desk = Desk(journal)
    order, auth = submitted(desk)
    stale = FillAuthorisation(stage="FILL", intent_id="int_01",
                              decision_id=order.intent.decision_id,
                              evaluation_fingerprint="0" * 64,
                              context_as_of=AS_OF - 2 * M, confirmed_at=AS_OF - M)
    with pytest.raises(PaperBrokerError):
        desk.broker._open(desk.broker._book(), order, None, (AS_OF, AS_OF), AS_OF, stale)


def test_every_fill_records_the_authorisation_it_ran_under(journal):
    desk = Desk(journal)
    submitted(desk)
    trigger(desk)  # blocked: no fill
    fresh = desk.reauthorise(desk.broker.state().pending_orders[0], Q1, at=AS_OF)
    trigger(desk, fresh)
    filled = journal.read(types=["order.filled"])
    assert len(filled) == 1 and filled[0].payload["authorised_intent_id"] == "int_01_r1"
    assert filled[0].payload["authorisation_stage"] == "FILL"


# max_slippage on protective exits ---------------------------------------------------------------


def test_a_stop_exit_beyond_max_slippage_executes_and_records_the_breach(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.40"}}))
    order, auth = submitted(desk)  # a limit entry: no slippage, admitted
    trigger(desk, auth)
    position = desk.broker.state().open_positions[0]
    assert position.max_slippage == Decimal("0.30")
    (trade,) = desk.broker.process(quote("2388.00", "2388.30", ts=AS_OF + M),
                                   as_of=AS_OF + M).trades
    assert trade.exit_fill.execution_price == Decimal("2387.60")  # protective: executed
    assert trade.exit_fill.slippage_breach is True
    assert journal.read(types=["trade.closed"])[0].payload["slippage_breach"] is True


def test_a_stop_exit_within_max_slippage_is_not_a_breach(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.10"}}))
    order, auth = submitted(desk)
    trigger(desk, auth)
    (trade,) = desk.broker.process(quote("2388.00", "2388.30", ts=AS_OF + M),
                                   as_of=AS_OF + M).trades
    assert trade.exit_fill.slippage == Decimal("0.10") and not trade.exit_fill.slippage_breach


def test_an_approval_older_than_the_triggering_bar_cannot_fill(journal):
    desk = Desk(journal, paper_config(spread={"mode": "SYNTHETIC_FIXED",
                                              "synthetic": {"XAUUSD": "0.30"}}))
    order, auth = submitted(desk)  # context as_of AS_OF
    bar_input = bar("2400.50", "2401.00", "2399.00", "2400.00", start=AS_OF, side="ask")
    (result,) = trigger(desk, auth, bar_input, AS_OF + 5 * M).executions
    assert result.reason == "authorisation_not_current"


def test_an_approval_that_never_saw_the_triggering_quote_cannot_fill(journal):
    desk = Desk(journal)
    order, _ = submitted(desk)
    recent_but_old_quote = desk.reauthorise(order, Q1, at=AS_OF + M)  # carries Q1 (AS_OF)
    later = quote("2399.50", "2399.80", ts=AS_OF + M)
    (result,) = trigger(desk, recent_but_old_quote, later, AS_OF + M).executions
    assert result.reason == "authorisation_not_current"


def test_an_authorisation_only_covers_its_own_order(journal):
    desk = Desk(journal)
    first, _ = submitted(desk)
    second, auth2 = submitted(desk, long_proposal(proposal_id="prop_02"), intent_id="int_02")
    fresh2 = desk.reauthorise(status(desk, second), Q1, at=AS_OF)
    results = {r.order_id: r for r in trigger(desk, fresh2).executions}
    assert results[first.order_id].reason == "authorisation_required"
    assert results[second.order_id].status is ExecutionStatus.FILLED
