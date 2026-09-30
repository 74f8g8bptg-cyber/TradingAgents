"""Phase 7 V1 PAPER end-to-end scenarios on synthetic, labelled fixtures.

Nothing here is a real market fact or a performance claim: bars, quotes, research, the LLM
script, policies and the paper account are test-only fixtures.
"""

from decimal import Decimal

import pytest
from research_helpers import AS_OF, CB_DECISION, CPI_OFFICIAL, FUTURE_NEWS, NEWS
from runtime_helpers import (
    RUNTIME_CONFIG,
    SHORT,
    Clock,
    M,
    Script,
    approved,
    dumps,
    m5,
    operator,
    quote,
    request,
    run_to_proposal,
    run_types,
    runtime,
    setup_of,
    source,
)
from stellar.execution import PaperBrokerConfig
from stellar.execution.models import ConversionRate, PnlStatus
from stellar.journal import StellarJournal
from stellar.marketdata import VerifiedMarketSnapshot
from stellar.reasoning import ScriptedProvider, Stance
from stellar.risk import RiskPolicy
from stellar.runtime import (
    HealthStatus,
    RunNotActive,
    RunStage,
    RunState,
    RuntimeFailure,
    health,
    reconcile,
    runtime_metrics,
)
from stellar.schemas.common import Direction, OrderSide
from stellar.setups import SetupStatus
from trader_helpers import RANGE_CLOSES, TraderScript

pytestmark = pytest.mark.unit

DOWN = {"specialist": Stance.SUPPORTS_DOWNSIDE, "research_manager": Stance.SUPPORTS_DOWNSIDE}
SHORT_MARKET = (("127.8", "128.0", AS_OF),)


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def short_runtime(journal, **kw):
    return runtime(journal, market=source(SHORT, SHORT_MARKET),
                   provider=ScriptedProvider(Script(stances=DOWN)), **kw)


def domain_counts(journal) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in journal.read():
        counts[e.type] = counts.get(e.type, 0) + 1
    return counts


# ------------------------------------------------------------------------ full LONG --


def test_long_lifecycle_to_target_close(journal):
    clock = Clock()
    rt = runtime(journal, clock=clock)
    first = rt.run(request())
    assert first.state is RunState.AWAITING_APPROVAL and not first.terminal
    record = rt.run(request(approval=approved(rt, first)))
    assert record.state is RunState.POSITION_OPEN and record.failure is None
    refs = record.refs
    assert refs["direction"] == "LONG" and refs["side"] == "BUY"
    assert refs["risk_outcome"] == "APPROVED" and refs["order_status"] == "FILLED"
    position = rt.broker.positions()[0]
    assert position.side is OrderSide.BUY and position.entry_price == Decimal("122.2")  # ask
    assert position.stop_loss == Decimal("109.0") and position.take_profit == Decimal("126.5")
    # the target is reached on the bid side 5 minutes later
    clock.now = AS_OF + 10 * M
    done = rt.advance(record.run_id, m5("124", "126.9", "123.8", "126.6", start=AS_OF,
                                        side="bid"), as_of=AS_OF + 10 * M)
    assert done.state is RunState.COMPLETED and done.terminal
    trade = rt.broker.trades()[0]
    assert trade.close_reason.value == "TAKE_PROFIT" and trade.trade_id == done.refs["trade_id"]
    assert trade.realised.status is PnlStatus.KNOWN
    assert trade.realised.amount == Decimal("0.50") * (Decimal("126.5") - Decimal("122.2")) * 100
    assert rt.broker.state().balance == Decimal("100000") + trade.realised.amount
    assert run_types(journal, record.run_id)[-1] == "run.completed"
    assert reconcile(journal, account_id="paper_test", ledger=rt.ledger).ok


def test_long_lifecycle_to_stop_close(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt)
    done = rt.advance(record.run_id, m5("121", "121.5", "108.5", "109.5", start=AS_OF,
                                        side="bid"), as_of=AS_OF + 10 * M)
    trade = rt.broker.trades()[0]
    assert done.state is RunState.COMPLETED and trade.close_reason.value == "STOP_LOSS"
    assert trade.realised.amount < 0


def test_long_manual_close(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt)
    done = rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 5 * M), as_of=AS_OF + 5 * M)
    assert done.state is RunState.COMPLETED
    assert rt.broker.trades()[0].close_reason.value == "MANUAL"
    with pytest.raises(RunNotActive):
        rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 6 * M), as_of=AS_OF + 6 * M)


# ----------------------------------------------------------------------- full SHORT --


def test_short_lifecycle_stays_short_and_sells_at_the_bid(journal):
    rt = short_runtime(journal)
    record = run_to_proposal(rt)
    assert record.state is RunState.POSITION_OPEN
    setup = setup_of(rt, record)
    assert setup.direction.value == "SHORT"
    proposal = rt.ledger.checkpoints(record.run_id)[RunStage.PROPOSAL].outputs["proposal"]
    assert proposal["direction"] == Direction.SHORT.value
    assert proposal["source_rating"] == "Buy"  # approval of the SHORT setup, not a side
    assert record.refs["side"] == OrderSide.SELL.value  # Phase 3 side from direction
    position = rt.broker.positions()[0]
    assert position.side is OrderSide.SELL and position.entry_price == Decimal("127.8")  # bid
    assert position.stop_loss == Decimal("141.0") > position.entry_price
    approval = journal.read(types=["decision.final.created"])[0].payload
    assert approval["direction"] == "SHORT" and approval["rating"] == "Buy"
    # the SHORT exits by buying at the ask: its target is reached on the ask side
    done = rt.advance(record.run_id, m5("126", "126.2", "123.2", "123.4", start=AS_OF,
                                        side="ask"), as_of=AS_OF + 10 * M)
    trade = rt.broker.trades()[0]
    assert done.state is RunState.COMPLETED and trade.close_reason.value == "TAKE_PROFIT"
    assert trade.realised.amount == Decimal("0.50") * (Decimal("127.8") - Decimal("123.5")) * 100


def test_a_long_approval_cannot_make_the_short_run_long(journal):
    rt = short_runtime(journal)
    parked = rt.run(request())
    wrong = rt.run(request(approval=approved(rt, parked, direction=Direction.LONG)))
    assert wrong.state is RunState.SETUP_CANDIDATE
    assert wrong.failure is RuntimeFailure.PROPOSAL_FAILED
    assert wrong.detail == "approval_direction_mismatch"
    assert journal.read(types=["trade.proposed"]) == []


# --------------------------------------------------------------- no setup / evidence --


def test_no_setup_is_a_successful_terminal_state(journal):
    rt = runtime(journal, market=source(RANGE_CLOSES, (("101.8", "102.0", AS_OF),)))
    record = rt.run(request())
    assert record.state is RunState.NO_SETUP and record.failure is None and record.terminal
    assert record.refs["setup_status"] == SetupStatus.NO_SETUP.value
    kinds = domain_counts(journal)
    assert "risk.check.started" not in kinds and "order.created" not in kinds
    assert "trade.proposed" not in kinds
    assert run_types(journal, record.run_id)[-1] == "run.completed"
    assert rt.run(request()) == rt.status(record.run_id)  # nothing left to do


def test_conflicting_evidence_is_no_setup(journal):
    rt = runtime(journal, provider=ScriptedProvider(Script(stances=DOWN)))
    record = rt.run(request())
    assert record.state is RunState.NO_SETUP
    assert record.detail == SetupStatus.CONFLICTING_EVIDENCE.value
    assert journal.read(types=["risk.check.started"]) == []


# -------------------------------------------------------------------- risk outcomes --


def test_risk_rejected_stops_before_any_intent_or_order(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt, request(op=operator(volume="5.00")))  # 6.6 % of equity
    assert record.state is RunState.REJECTED and record.failure is RuntimeFailure.RISK_REJECTED
    assert "max_risk_per_trade" in record.detail
    assert RunStage.ORDER_AUTHORISATION not in rt.ledger.checkpoints(record.run_id)
    assert journal.read(types=["order.created"]) == []
    assert rt.risk.breaker.state().status.value == "ARMED"  # a rejection never trips it


def test_risk_review_parks_with_reasons_and_never_executes(journal):
    policy = RiskPolicy.model_validate({**_policy_dump(), "max_spread": {"state": "UNSET"}})
    rt = runtime(journal, policy=policy)
    record = run_to_proposal(rt)
    assert record.state is RunState.REVIEW_REQUIRED
    assert record.failure is RuntimeFailure.RISK_REVIEW_REQUIRED
    cp = rt.ledger.checkpoints(record.run_id)[RunStage.RISK]
    assert "max_spread" in cp.outputs["unresolved"] and cp.refs["risk_outcome"] == "REVIEW"
    assert RunStage.PROPOSAL in rt.ledger.checkpoints(record.run_id)  # proposal preserved
    assert journal.read(types=["order.created"]) == []
    assert rt.run(request()).state is RunState.REVIEW_REQUIRED  # never silently approved


def _policy_dump():
    from risk_helpers import TEST_POLICY  # noqa: PLC0415

    return TEST_POLICY.model_dump()


def test_missing_operator_inputs_fail_closed(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt, request(op=operator(volume=None, daily=None)))
    assert record.state in (RunState.REJECTED, RunState.REVIEW_REQUIRED)
    assert journal.read(types=["order.created"]) == []


# -------------------------------------------------------------------- idempotency --


def test_duplicate_run_changes_nothing(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt)
    before = journal.last_seq()
    again = rt.run(request(approval=approved(rt, record)))
    assert again == rt.status(record.run_id) and journal.last_seq() == before
    counts = domain_counts(journal)
    for kind in ("trade.proposed", "risk.approved", "order.created", "order.filled",
                 "position.opened", "decision.final.created"):
        assert counts[kind] == 1, kind


def test_changed_input_is_a_new_run(journal):
    rt = runtime(journal)
    first = rt.run(request())
    news = rt.run(request(items=(CB_DECISION, CPI_OFFICIAL, NEWS)))
    assert news.run_id != first.run_id
    other_volume = rt.run(request(op=operator(volume="0.40")))
    assert other_volume.run_id not in (first.run_id, news.run_id)
    rt2 = runtime(journal, market=source(quotes=(("122.1", "122.3", AS_OF),)))
    assert rt2.run(request()).run_id != first.run_id  # the market data read changed


def test_the_same_inputs_give_the_same_logical_run_in_another_journal():
    """Logical determinism: same inputs, config, provider script, clock and empty journal →
    the same run id, the same records and the same event payloads. Only event ids (ULIDs,
    run-instance identity) differ."""
    streams = []
    for _ in range(2):
        with StellarJournal() as j:
            rt = runtime(j)
            record = run_to_proposal(rt)
            rt.advance(record.run_id, m5("124", "126.9", "123.8", "126.6", start=AS_OF,
                                         side="bid"), as_of=AS_OF + 10 * M)
            streams.append((rt.status(record.run_id),
                            [(e.seq, e.type, dumps(e.payload), e.correlation_id)
                             for e in j.read()]))
    assert streams[0][0] == streams[1][0]
    assert streams[0][1] == streams[1][1]


# ------------------------------------------------------------------- point in time --


def test_future_bars_quotes_and_research_are_never_seen(journal):
    from trader_helpers import LONG_CLOSES, bars_for  # noqa: PLC0415

    future = bars_for([130, 131], end=AS_OF + 2 * 60 * M)
    with_future = source(quotes=(("122.0", "122.2", AS_OF), ("140.0", "140.2", AS_OF + M)),
                         extra_bars=future)
    rt = runtime(journal, market=with_future)
    record = rt.run(request(items=(CB_DECISION, CPI_OFFICIAL, FUTURE_NEWS)))
    snap = VerifiedMarketSnapshot.model_validate(
        rt.ledger.checkpoints(record.run_id)[RunStage.MARKET_DATA].outputs["snapshot"])
    assert snap.last_bar_close_time <= AS_OF
    assert snap.latest_quote.ts == AS_OF and snap.latest_quote.bid == Decimal("122.0")
    analysis = rt.ledger.checkpoints(record.run_id)[RunStage.TECHNICAL].outputs["analysis"]
    assert analysis["as_of"].startswith("2026-09-29T14:00:00")
    decision = rt.ledger.checkpoints(record.run_id)[RunStage.RESEARCH].outputs["decision"]
    assert "ri_news_future" not in dumps(decision)
    with StellarJournal() as j2:  # the same run without any future data in the source
        plain = runtime(j2).run(request(items=(CB_DECISION, CPI_OFFICIAL, FUTURE_NEWS)))
    assert plain.run_id == record.run_id and LONG_CLOSES


# ------------------------------------------------------------- economics / currency --


def test_unknown_pnl_economics_is_never_valued(journal):
    from broker_helpers import PAPER_CONFIG  # noqa: PLC0415

    config = PaperBrokerConfig.model_validate({**PAPER_CONFIG.model_dump(), "economics": []})
    rt = runtime(journal, broker_config=config)
    record = run_to_proposal(rt)
    assert record.state is RunState.POSITION_OPEN  # the fill needs no economics
    done = rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 5 * M), as_of=AS_OF + 5 * M)
    trade = rt.broker.trades()[0]
    assert done.state is RunState.COMPLETED
    assert trade.realised.status is PnlStatus.MISSING_ECONOMICS
    assert trade.realised.amount is None
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    assert report.ok and report.unsettled_trade_ids == (trade.trade_id,)
    assert "unsettled_pnl" in health(rt, checked_at=AS_OF + 5 * M).reasons
    # the next run cannot size against an account whose balance is unknown
    assert rt.broker.risk_inputs(AS_OF + 5 * M).account is None


def test_missing_currency_conversion_is_reported_not_invented(journal):
    from broker_helpers import PAPER_CONFIG  # noqa: PLC0415

    eur = PaperBrokerConfig.model_validate({**PAPER_CONFIG.model_dump(), "economics": [
        {"instrument": "XAUUSD", "pnl_currency": "EUR", "value_per_price_unit_per_lot": "100",
         "source": "test_fixture"}]})
    rt = runtime(journal, broker_config=eur)
    record = run_to_proposal(rt)
    assert record.state is RunState.POSITION_OPEN
    rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 5 * M), as_of=AS_OF + 5 * M)
    trade = rt.broker.trades()[0]
    assert trade.realised.status is PnlStatus.MISSING_CONVERSION and trade.realised.amount is None


def test_explicit_conversion_values_the_trade(journal):
    from broker_helpers import PAPER_CONFIG  # noqa: PLC0415

    eur = PaperBrokerConfig.model_validate({**PAPER_CONFIG.model_dump(), "economics": [
        {"instrument": "XAUUSD", "pnl_currency": "EUR", "value_per_price_unit_per_lot": "100",
         "source": "test_fixture"}]})
    rt = runtime(journal, broker_config=eur)
    record = run_to_proposal(rt)
    rate = ConversionRate(base="EUR", quote="USD", rate=Decimal("1.1"), as_of=AS_OF + 5 * M,
                          source="test_fixture")
    rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 5 * M), as_of=AS_OF + 5 * M,
             operator=operator(conversions=(rate,)))
    assert rt.broker.trades()[0].realised.status is PnlStatus.KNOWN


# ---------------------------------------------------------------- ops read models --


def test_metrics_count_outcomes_and_llm_usage(journal):
    rt = runtime(journal)
    run_to_proposal(rt)
    runtime(journal, market=source(RANGE_CLOSES, (("101.8", "102.0", AS_OF),))).run(request())
    metrics = runtime_metrics(journal, rt)
    assert metrics.runs == 2 and metrics.no_setup == 1 and metrics.paper_submissions == 1
    assert metrics.by_state == {"NO_SETUP": 1, "POSITION_OPEN": 1}
    assert metrics.llm.calls >= 6 and metrics.llm.cost is None  # no cost reported: none shown
    assert metrics.stages["SETUP"].count == 3  # parked + resumed (run 1), NO_SETUP (run 2)


def test_health_is_deterministic_and_reflects_state(journal):
    rt = runtime(journal)
    run_to_proposal(rt)
    a, b = health(rt, checked_at=AS_OF), health(rt, checked_at=AS_OF)
    assert a == b and a.status is HealthStatus.DEGRADED
    assert a.reasons == ("test_only_configuration",)
    unconfigured = runtime(journal, config=RUNTIME_CONFIG.model_copy(
        update={"enabled_instruments": ()}))
    assert health(unconfigured, checked_at=AS_OF).status is HealthStatus.BLOCKED


def test_trader_script_is_only_asked_once_per_run(journal):
    provider = ScriptedProvider(Script(trader=TraderScript(targets=("PRIOR_SWING_TARGET",))))
    rt = runtime(journal, provider=provider)
    run_to_proposal(rt)
    assert sum(r.role == "trader" for r in provider.requests) == 1


def test_default_take_profit_policy_sends_no_target_on_the_order(journal):
    """RK-9 is undecided: by default the order intent carries no take-profit."""
    from stellar.runtime import TakeProfitPolicy  # noqa: PLC0415

    rt = runtime(journal, config=RUNTIME_CONFIG.model_copy(
        update={"take_profit": TakeProfitPolicy.NONE}))
    record = run_to_proposal(rt)
    assert record.state is RunState.POSITION_OPEN
    assert rt.order(record.refs["order_id"]).intent.take_profit is None
    assert rt.broker.positions()[0].take_profit is None

