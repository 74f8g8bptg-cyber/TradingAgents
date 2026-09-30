"""Paper Broker: configuration (D-8), account state, order intake and idempotency."""

from datetime import timedelta
from decimal import Decimal

import pytest
from broker_helpers import PAPER_CONFIG, STATION, Desk, M, bar, long_proposal, paper_config, quote
from factories import make_intent, make_proposal
from pydantic import ValidationError
from risk_helpers import AS_OF
from stellar.execution import (
    AccountConfigConflict,
    InvalidMarketInput,
    OrderConflictError,
    OutOfOrderInput,
    PaperBroker,
    PaperBrokerConfig,
    PaperOrderStatus,
)
from stellar.journal import StellarJournal
from stellar.schemas.execution import ExecutionStatus
from stellar.schemas.order import AccountMode, OrderIntent
from stellar.validation import validate_execution_result

pytestmark = pytest.mark.unit
Q0 = quote("2399.80", "2400.10", ts=AS_OF - timedelta(seconds=5))


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


@pytest.fixture
def desk(journal):
    return Desk(journal)


# --- configuration and account ---------------------------------------------------------------


@pytest.mark.parametrize("missing", ["account_currency", "starting_balance", "spread",
                                     "slippage"])
def test_account_currency_balance_and_models_have_no_default(missing):
    data = PAPER_CONFIG.model_dump()
    del data[missing]
    with pytest.raises(ValidationError):
        PaperBrokerConfig.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("spread", {"mode": "QUOTE_ONLY", "synthetic": {"XAUUSD": "0.3"}}),
    ("spread", {"mode": "SYNTHETIC_FIXED"}),
    ("slippage", {"mode": "ZERO", "fixed": {"XAUUSD": "0.1"}}),
    ("slippage", {"mode": "FIXED"}),
    ("starting_balance", "0"),
    ("account_currency", "usd"),
])
def test_inconsistent_configuration_is_refused(field, value):
    with pytest.raises(ValidationError):
        paper_config(**{field: value})


def test_initial_account_state(desk, journal):
    state = desk.broker.state()
    assert state.currency == "USD" and state.starting_balance == Decimal("100000")
    assert state.balance == state.equity == state.peak_equity == Decimal("100000")
    assert state.realised_pnl == state.unrealised_pnl == Decimal(0)  # known zero, not unknown
    assert state.open_positions == state.pending_orders == state.closed_trades == ()
    assert state.unsettled_trade_ids == state.unvalued_position_ids == ()
    opened = journal.read(types=["account.opened"])
    assert len(opened) == 1 and opened[0].payload["starting_balance"] == "100000"


def test_restart_does_not_reopen_and_a_changed_config_is_refused(journal, desk):
    PaperBroker(PAPER_CONFIG, journal, desk.risk, station_id=STATION, opened_at=AS_OF)
    assert len(journal.read(types=["account.opened"])) == 1
    with pytest.raises(AccountConfigConflict):
        PaperBroker(paper_config(starting_balance="5000"), journal, desk.risk,
                    station_id=STATION, opened_at=AS_OF)


# --- intake ------------------------------------------------------------------------------------


def test_authorised_limit_intent_is_accepted_pending(desk, journal):
    intent, ctx = desk.authorise()
    result = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert result.status is ExecutionStatus.ACKNOWLEDGED and result.filled_volume == 0
    validate_execution_result(result, intent)
    order = desk.broker.state().pending_orders[0]
    assert order.status is PaperOrderStatus.PENDING and order.intent == intent
    assert order.evaluation_fingerprint == desk.risk.latest_evaluation("prop_01").fingerprint
    created = journal.read(types=["order.created"])[0]
    assert created.payload["idempotency_key"] == intent.idempotency_key
    assert created.payload["mode"] == "PAPER" and created.correlation_id == "prop_01"


def test_only_paper_intents_are_accepted(desk):
    intent, ctx = desk.authorise()
    demo = intent.model_copy(update={"account_mode": AccountMode.DEMO})
    result = desk.broker.submit(demo, ctx, as_of=AS_OF)
    assert result.status is ExecutionStatus.PREFLIGHT_FAILED
    assert result.reason == "account_mode_not_paper"
    assert desk.broker.state().pending_orders == ()


def test_an_intent_the_risk_engine_never_authorised_is_refused(desk):
    _, ctx = desk.authorise()
    forged = make_intent(intent_id="int_99", decision_id="dec_99",
                         created_at=AS_OF, expires_at=AS_OF + 5 * M)
    result = desk.broker.submit(forged, ctx, as_of=AS_OF)
    assert result.reason == "reevaluation_required"


def test_a_tampered_intent_is_refused(desk):
    intent, ctx = desk.authorise()
    bigger = OrderIntent.model_validate({**intent.model_dump(), "intent_id": "int_02",
                                         "volume": Decimal("5.00")})
    assert desk.broker.submit(bigger, ctx, as_of=AS_OF).reason == "intent_not_authorised"


def test_malformed_intent_is_refused_before_anything_is_recorded(desk, journal):
    intent, ctx = desk.authorise()
    count = len(journal.read())
    broken = OrderIntent.model_construct(**{**dict(intent), "volume": Decimal("-1")})
    with pytest.raises(ValidationError):
        desk.broker.submit(broken, ctx, as_of=AS_OF)
    assert len(journal.read()) == count


def test_duplicate_submission_is_idempotent(desk, journal):
    intent, ctx = desk.authorise()
    first = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    count = len(journal.read())
    again = desk.broker.submit(intent, ctx, as_of=AS_OF + M, market=Q0)
    assert again == first and len(journal.read()) == count
    assert desk.broker.stats().submitted == 1


def test_same_intent_id_with_other_content_is_a_conflict(desk):
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    other = OrderIntent.model_validate({**intent.model_dump(), "take_profit": None})
    with pytest.raises(OrderConflictError):
        desk.broker.submit(other, ctx, as_of=AS_OF)


def test_second_intent_for_an_accepted_proposal_is_a_duplicate_order(desk):
    first, ctx = desk.authorise(intent_id="int_01")
    evaluation = desk.risk.latest_evaluation("prop_01")
    second = desk.risk.authorize_intent(evaluation, ctx, intent_id="int_02",
                                        broker_symbol="XAUUSD", created_at=AS_OF,
                                        expires_at=AS_OF + 20 * M)
    desk.broker.submit(first, ctx, as_of=AS_OF)
    result = desk.broker.submit(second, ctx, as_of=AS_OF)
    assert result.status is ExecutionStatus.PREFLIGHT_FAILED
    assert result.reason == "duplicate_order"
    assert desk.broker.stats().accepted == 1


def test_a_preflight_failure_does_not_use_up_the_proposal(desk):
    intent, ctx = desk.authorise()
    desk.risk.breaker.trip(_trip())
    assert desk.broker.submit(intent, ctx, as_of=AS_OF).reason == "circuit_breaker_tripped"
    assert desk.broker.risk_inputs(AS_OF).prior_idempotency_keys == ()


def test_expired_intent_is_refused(desk):
    intent, ctx = desk.authorise()
    result = desk.broker.submit(intent, ctx, as_of=intent.expires_at)
    assert result.reason == "intent_expired"


def test_time_cannot_move_backwards(desk):
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF + M)
    with pytest.raises(OutOfOrderInput):
        desk.broker.process(Q0, as_of=AS_OF)


@pytest.mark.parametrize("market", [
    quote("2399.80", "2400.10", ts=AS_OF + M),  # stamped after as_of
    quote("2399.80", "2400.10", proxy=True),
    bar("2400", "2401", "2399", "2400.5", start=AS_OF - 3 * M),  # closes after as_of
    bar("2400", "2401", "2399", "2400.5", start=AS_OF - 10 * M).model_copy(
        update={"is_closed": False}),
])
def test_unusable_market_input_is_refused(desk, journal, market):
    count = len(journal.read())
    with pytest.raises(InvalidMarketInput):
        desk.broker.process(market, as_of=AS_OF)
    assert len(journal.read()) == count


def test_market_input_for_another_instrument_is_refused_on_submit(desk):
    intent, ctx = desk.authorise()
    eur = Q0.model_copy(update={"instrument": "EURUSD"})
    with pytest.raises(InvalidMarketInput):
        desk.broker.submit(intent, ctx, as_of=AS_OF, market=eur)


def test_long_and_short_intents_share_no_position(desk):
    short, ctx = desk.authorise()
    desk.broker.submit(short, ctx, as_of=AS_OF)
    long_intent, ctx2 = desk.authorise(long_proposal(proposal_id="prop_02"), intent_id="int_02")
    assert desk.broker.submit(long_intent, ctx2, as_of=AS_OF).status is \
        ExecutionStatus.ACKNOWLEDGED
    assert len(desk.broker.state().pending_orders) == 2


def _trip():
    from stellar.risk import BreakerTrip
    return BreakerTrip(cause="risk_rule", rule="max_daily_loss", value="0.031", limit="0.03",
                       tripped_by="risk_engine", tripped_at=AS_OF)


def test_market_order_without_a_quote_is_rejected(desk):
    proposal = make_proposal(entry={"type": "market", "price": "2399.80"})
    intent, ctx = desk.authorise(proposal)
    result = desk.broker.submit(intent, ctx, as_of=AS_OF,
                                market=bar("2400", "2401", "2399", "2400.5",
                                           start=AS_OF - 5 * M, side="bid"))
    assert result.status is ExecutionStatus.REJECTED
    assert result.reason == "market_order_needs_quote"
    assert desk.broker.state().open_positions == ()


@pytest.mark.parametrize("status", ["cancelled", "expired"])
def test_cancelled_and_expired_results_carry_no_fill(status):
    from factories import make_result

    assert make_result(status=status, filled_volume="0", fill_id=None, fill_price=None,
                       slippage=None).status.value == status
    with pytest.raises(ValidationError):
        make_result(status=status)  # a fill is not allowed
