"""Paper Broker: journal reconstruction, replay idempotency and the Risk Engine boundary."""

from datetime import timedelta

import pytest
from broker_helpers import PAPER_CONFIG, STATION, Desk, M, long_proposal, quote
from risk_helpers import AS_OF
from stellar.execution import OutOfOrderInput, PaperAccountState, PaperBroker, load_book
from stellar.journal import StellarJournal
from stellar.risk import BreakerTrip, RiskService
from stellar.schemas.execution import ExecutionStatus
from stellar.validation import validate_execution_result

pytestmark = pytest.mark.unit
T1 = AS_OF + M
T3 = T1 + 2 * M
LONG_2370 = long_proposal(proposal_id="prop_02", entry={"type": "limit", "price": "2370.00"},
                          stop_loss={"price": "2358.00", "basis": "structure_low"},
                          take_profits=[{"price": "2394.00", "basis": "structure_high"}])
LAST = quote("2369.70", "2370.00", ts=T3)


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def run_scenario(desk):
    """A short that fills and hits its target, and a long that stays open (synthetic)."""
    short, ctx = desk.authorise()
    desk.broker.submit(short, ctx, as_of=AS_OF)
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1)
    # Authorised against the current book (quotes in the fixture context are stamped
    # AS_OF - 5 s, so the evaluation stays at AS_OF; the submission is at T1).
    long_intent, ctx2 = desk.authorise(LONG_2370, intent_id="int_02")
    desk.broker.submit(long_intent, ctx2, as_of=T1)
    desk.broker.process(quote("2375.60", "2375.90", ts=T1 + M), as_of=T1 + M)  # short target
    desk.fill_with(LAST, at=T3)  # the long fills at 2370 and stays open
    return short, ctx, long_intent, ctx2


# --- reconstruction ------------------------------------------------------------------------------


def test_restart_reconstructs_identical_state(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        desk = Desk(j)
        run_scenario(desk)
        before, stats = desk.broker.state(), desk.broker.stats()
    with StellarJournal(path) as j:  # restart: a new process, only the journal survives
        risk = RiskService(desk.risk.engine, j, station_id=STATION, clock=lambda: AS_OF)
        broker = PaperBroker(PAPER_CONFIG, j, risk, station_id=STATION, opened_at=AS_OF)
        assert broker.state() == before and broker.stats() == stats
        assert len(before.closed_trades) == 1 and len(before.open_positions) == 1


def test_same_journal_gives_the_same_state(journal):
    desk = Desk(journal)
    run_scenario(desk)
    assert load_book(journal, "paper_test").state() == load_book(journal, "paper_test").state()


def test_resubmission_after_restart_does_not_duplicate(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        desk = Desk(j)
        short, ctx, *_ = run_scenario(desk)
        first = desk.broker.execution_result(desk.broker.state().closed_trades[0].order_id)
        count, stats = len(j.read()), desk.broker.stats()
    with StellarJournal(path) as j:
        restarted = Desk(j)
        again = restarted.broker.submit(short, ctx, as_of=T3)
        assert again == first and again.status is ExecutionStatus.FILLED
        assert len(j.read()) == count
        assert restarted.broker.stats() == stats and stats.filled == 2


def test_reprocessing_the_same_input_changes_nothing(journal):
    desk = Desk(journal)
    run_scenario(desk)
    count = len(journal.read())
    replayed = desk.broker.process(LAST, as_of=T3)
    assert replayed.executions == replayed.trades == ()
    assert len(journal.read()) == count


def test_journal_history_is_append_only(journal):
    desk = Desk(journal)
    short, ctx = desk.authorise()
    desk.broker.submit(short, ctx, as_of=AS_OF)
    before = [(e.seq, e.event_id, e.payload) for e in journal.read()]
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1)
    desk.broker.process(quote("2375.60", "2375.90", ts=T1 + M), as_of=T1 + M)
    after = [(e.seq, e.event_id, e.payload) for e in journal.read()]
    assert after[:len(before)] == before
    assert journal.verify() == len(after)


def test_snapshots_match_the_reconstructed_state(journal):
    desk = Desk(journal)
    run_scenario(desk)
    last = journal.read(types=["account.snapshot.created"])[-1]
    assert PaperAccountState.model_validate(last.payload["state"]) == desk.broker.state()


def test_events_carry_typed_references_and_no_secrets(journal):
    desk = Desk(journal)
    run_scenario(desk)
    types = [e.type for e in desk.broker.events()]
    assert types[0] == "account.opened"
    assert {"order.created", "order.filled", "position.opened", "position.updated",
            "trade.closed"} <= set(types)
    for event in desk.broker.events():
        assert event.source == "stellar.paper_broker" and event.agent_id == "paper_execution"
        if event.type != "account.opened":
            assert event.correlation_id in {"prop_01", "prop_02"}
            assert event.instrument == "XAUUSD"
    closed = journal.read(types=["trade.closed"])[0].payload
    assert {"trade_id", "position_id", "proposal_id", "order_id", "fill_id", "exit_price",
            "volume", "close_reason"} <= set(closed)


def test_execution_results_follow_the_phase1_chain(journal):
    desk = Desk(journal)
    short, *_ = run_scenario(desk)
    result = desk.broker.execution_result(desk.broker.state().closed_trades[0].order_id)
    validate_execution_result(result, short)
    assert result.filled_volume == short.volume and result.fill_id is not None


# --- Risk Engine boundary ------------------------------------------------------------------------


def test_a_superseded_approval_cannot_execute(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    newer = desk.context(daily={**ctx.daily.model_dump(), "realised_pnl": "-500"})
    desk.risk.evaluate(newer)  # the context changed: a new evaluation supersedes the old
    for context in (ctx, newer):
        result = desk.broker.submit(intent.model_copy(), context, as_of=AS_OF)
        assert result.reason == "reevaluation_required"
    assert desk.broker.state().pending_orders == ()


def test_a_tripped_breaker_cannot_be_bypassed(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    desk.risk.breaker.trip(BreakerTrip(cause="risk_rule", rule="max_drawdown", value="0.11",
                                       limit="0.10", tripped_by="risk_engine",
                                       tripped_at=AS_OF))
    result = desk.broker.submit(intent, ctx, as_of=AS_OF)
    assert result.status is ExecutionStatus.PREFLIGHT_FAILED
    assert result.reason == "circuit_breaker_tripped"


def test_an_approval_against_an_older_book_cannot_execute(journal):
    desk = Desk(journal)
    first, ctx1 = desk.authorise()
    second, ctx2 = desk.authorise(long_proposal(proposal_id="prop_02"), intent_id="int_02")
    desk.broker.submit(first, ctx1, as_of=AS_OF)  # the book now has a pending order
    result = desk.broker.submit(second, ctx2, as_of=AS_OF)
    assert result.reason == "broker_state_changed"
    fresh, ctx3 = desk.authorise(long_proposal(proposal_id="prop_03"), intent_id="int_03")
    assert desk.broker.submit(fresh, ctx3, as_of=AS_OF).status is ExecutionStatus.ACKNOWLEDGED


def test_an_intent_or_context_from_the_future_is_refused(journal):
    desk = Desk(journal)
    later = AS_OF + timedelta(seconds=30)
    intent, ctx = desk.authorise(as_of=later)
    with pytest.raises(OutOfOrderInput):  # the intent was created after as_of
        desk.broker.submit(intent, ctx, as_of=AS_OF)
    early = intent.model_copy(update={"created_at": AS_OF})
    assert desk.broker.submit(early, ctx, as_of=AS_OF).reason == "context_after_submission"


def test_broker_state_feeds_the_next_risk_evaluation(journal):
    desk = Desk(journal)
    run_scenario(desk)
    view = desk.broker.risk_inputs(T3)
    assert view.account.source == "paper_broker" and view.account.equity == \
        desk.broker.state().equity
    assert [p.idempotency_key for p in view.positions] == [
        desk.broker.state().open_positions[0].idempotency_key]
    assert len(view.prior_idempotency_keys) == 2
    # The same proposal cannot be approved twice: the risk engine sees its key.
    ctx = desk.context()  # the same proposal, evaluated against the current book
    assert desk.risk.evaluate(ctx).decision.outcome.value == "REJECTED"
