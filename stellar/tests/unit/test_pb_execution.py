"""Paper Broker: execution prices, spread, slippage, pending orders, expiry, cancellation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from broker_helpers import Desk, M, bar, long_proposal, paper_config, quote
from factories import make_proposal
from risk_helpers import AS_OF
from stellar.execution import (
    InvalidMarketInput,
    OrderNotCancellable,
    PaperFill,
    PaperOrderStatus,
    SlippageSource,
    SpreadSource,
)
from stellar.journal import StellarJournal
from stellar.risk import BreakerTrip
from stellar.schemas.execution import ExecutionStatus

pytestmark = pytest.mark.unit
S5 = timedelta(seconds=5)
Q0 = quote("2399.80", "2400.10", ts=AS_OF - S5)


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def market_long(desk, **kw):
    proposal = long_proposal(entry={"type": "market", "price": "2400.10"})
    return desk.authorise(proposal, **kw)


def market_short(desk, **kw):
    return desk.authorise(make_proposal(entry={"type": "market", "price": "2399.80"}), **kw)


# --- market orders: bid / ask ------------------------------------------------------------------


def test_buy_executes_at_the_ask(journal):
    desk = Desk(journal)
    intent, ctx = market_long(desk)
    result = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert result.status is ExecutionStatus.FILLED and result.fill_price == Decimal("2400.10")
    position = desk.broker.state().open_positions[0]
    assert position.entry_price == Decimal("2400.10") and position.side.value == "BUY"
    entry = PaperFill.model_validate(journal.read(types=["order.filled"])[0].payload["fill"])
    assert entry.spread == Decimal("0.30") and entry.spread_source is SpreadSource.QUOTE
    assert entry.source_price == Q0.ask and entry.source_ts == Q0.ts and entry.as_of == AS_OF


def test_sell_executes_at_the_bid(journal):
    desk = Desk(journal)
    intent, ctx = market_short(desk)
    result = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert result.status is ExecutionStatus.FILLED and result.fill_price == Decimal("2399.80")


def test_never_a_mid_price(journal):
    desk = Desk(journal)
    intent, ctx = market_long(desk)
    fill = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert fill.fill_price != (Q0.bid + Q0.ask) / 2


# --- slippage ----------------------------------------------------------------------------------


def test_slippage_within_the_maximum_is_applied_adversely(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.20"}}))
    intent, ctx = market_long(desk)
    assert intent.max_slippage == Decimal("0.30")
    result = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert result.fill_price == Decimal("2400.30") and result.slippage == Decimal("0.20")
    short_desk = Desk(StellarJournal(),
                      paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.20"}}))
    s_intent, s_ctx = market_short(short_desk)
    assert short_desk.broker.submit(s_intent, s_ctx, as_of=AS_OF, market=Q0).fill_price == \
        Decimal("2399.60")


def test_slippage_above_the_maximum_rejects_the_fill(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.40"}}))
    intent, ctx = market_long(desk)
    result = desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
    assert result.status is ExecutionStatus.REJECTED and result.reason == "slippage_exceeds_max"
    assert desk.broker.state().open_positions == ()
    assert journal.read(types=["order.rejected"])[0].payload["reason"] == "slippage_exceeds_max"


def test_fixed_slippage_without_a_value_for_the_instrument_is_refused(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"EURUSD": "0.0001"}}))
    intent, ctx = market_long(desk)
    assert desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0).reason == \
        "slippage_unavailable"


def test_slippage_is_deterministic_not_random():
    fills = []
    for _ in range(3):
        with StellarJournal() as j:
            desk = Desk(j, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.10"}}))
            intent, ctx = market_long(desk)
            desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)
            fills.append(desk.broker.state().open_positions[0])
    assert fills[0] == fills[1] == fills[2]


# --- limit orders ------------------------------------------------------------------------------


def test_limit_order_waits_then_fills_at_its_price_never_better(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()  # SELL limit 2400.00
    assert desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0).status is \
        ExecutionStatus.ACKNOWLEDGED
    assert desk.broker.process(quote("2399.90", "2400.20", ts=AS_OF + M),
                               as_of=AS_OF + M).executions == ()
    result = desk.fill_with(quote("2401.00", "2401.30", ts=AS_OF + 2 * M), at=AS_OF + 2 * M)
    filled = result.executions[0]
    assert filled.status is ExecutionStatus.FILLED and filled.fill_price == Decimal("2400.00")
    assert filled.slippage == 0


def test_buy_limit_fills_when_the_ask_reaches_it(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise(long_proposal())  # BUY limit 2400.00
    desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)  # ask 2400.10: not yet
    assert desk.broker.state().pending_orders
    result = desk.fill_with(quote("2399.70", "2400.00", ts=AS_OF + M), at=AS_OF + M)
    assert result.executions[0].fill_price == Decimal("2400.00")


def test_marketable_limit_fills_on_the_submission_quote(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise(long_proposal())
    result = desk.broker.submit(intent, ctx, as_of=AS_OF,
                                market=quote("2399.60", "2399.90", ts=AS_OF - S5))
    assert result.status is ExecutionStatus.FILLED and result.fill_price == Decimal("2400.00")


def test_a_quote_older_than_the_order_cannot_fill_it(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF + M)
    stale = quote("2401.00", "2401.30", ts=AS_OF)  # before the order was accepted
    assert desk.broker.process(stale, as_of=AS_OF + 2 * M).executions == ()
    assert desk.broker.state().pending_orders


def test_a_bar_fills_a_limit_only_if_it_opened_after_acceptance(journal):
    desk = Desk(journal, paper_config(spread={"mode": "SYNTHETIC_FIXED",
                                              "synthetic": {"XAUUSD": "0.30"}}))
    intent, ctx = desk.authorise()  # SELL limit 2400: needs bid >= 2400
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    straddle = bar("2399.5", "2401", "2399", "2400", start=AS_OF - 2 * M, side="bid")
    assert desk.broker.process(straddle, as_of=AS_OF + 3 * M).executions == ()
    later = bar("2399.5", "2401", "2399", "2400", start=AS_OF + 3 * M, side="bid")
    assert desk.fill_with(later, at=AS_OF + 8 * M).executions[0].fill_price == \
        Decimal("2400.00")


# --- spread ------------------------------------------------------------------------------------


def test_no_spread_is_invented_for_the_other_side_of_a_bar(journal):
    desk = Desk(journal)  # QUOTE_ONLY
    intent, ctx = desk.authorise()  # SELL limit 2400 on bid; bars below are ask-side
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    ask_bar = bar("2400", "2403", "2399", "2402", start=AS_OF, side="ask")
    assert desk.broker.process(ask_bar, as_of=AS_OF + 5 * M).executions == ()
    assert desk.broker.state().pending_orders  # not evaluated: no bid without a spread


def test_synthetic_spread_is_explicit_and_labelled(journal):
    desk = Desk(journal, paper_config(spread={"mode": "SYNTHETIC_FIXED",
                                              "synthetic": {"XAUUSD": "0.40"}}))
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    ask_bar = bar("2400", "2400.50", "2399", "2400.2", start=AS_OF, side="ask")
    assert desk.fill_with(ask_bar, at=AS_OF + 5 * M).executions[0].fill_price == \
        Decimal("2400.00")  # bid high = 2400.50 - 0.40 = 2400.10 >= 2400
    fill = journal.read(types=["order.filled"])[0].payload["fill"]
    assert fill["spread_source"] == SpreadSource.SYNTHETIC and fill["spread"] == "0.40"
    assert fill["slippage_source"] == SlippageSource.NOT_APPLIED


def test_a_mid_bar_needs_a_synthetic_spread(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    mid = bar("2400", "2405", "2399", "2402", start=AS_OF, side="mid")
    assert desk.broker.process(mid, as_of=AS_OF + 5 * M).executions == ()


# --- expiry, cancellation, breaker -------------------------------------------------------------


def test_pending_order_expires(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    (expired,) = desk.broker.expire_due(as_of=intent.expires_at)
    assert expired.status is ExecutionStatus.EXPIRED
    assert journal.read(types=["order.expired"])[0].payload["order_id"] == expired.order_id


def test_a_bar_that_ends_after_expiry_cannot_fill(journal):
    desk = Desk(journal, paper_config(spread={"mode": "SYNTHETIC_FIXED",
                                              "synthetic": {"XAUUSD": "0.30"}}))
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    late = bar("2401", "2402", "2400.5", "2401", start=intent.expires_at - 2 * M, side="bid")
    result = desk.broker.process(late, as_of=intent.expires_at + 3 * M)
    assert [r.status for r in result.executions] == [ExecutionStatus.EXPIRED]


def test_cancel_is_idempotent_and_never_touches_a_filled_order(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    order = desk.broker.submit(intent, ctx, as_of=AS_OF)
    cancelled = desk.broker.cancel(order.order_id, as_of=AS_OF + M)
    assert cancelled.status is ExecutionStatus.CANCELLED
    count = len(journal.read())
    assert desk.broker.cancel(order.order_id, as_of=AS_OF + 2 * M) == cancelled
    assert len(journal.read()) == count
    filled_desk = Desk(StellarJournal())
    f_intent, f_ctx = market_long(filled_desk)
    filled = filled_desk.broker.submit(f_intent, f_ctx, as_of=AS_OF, market=Q0)
    with pytest.raises(OrderNotCancellable):
        filled_desk.broker.cancel(filled.order_id, as_of=AS_OF + M)
    with pytest.raises(KeyError):
        desk.broker.cancel("ord_unknown", as_of=AS_OF + M)


def test_a_tripped_breaker_cancels_a_pending_order_instead_of_filling(journal):
    desk = Desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    desk.risk.breaker.trip(BreakerTrip(cause="risk_rule", rule="max_daily_loss", value="0.031",
                                       limit="0.03", tripped_by="risk_engine",
                                       tripped_at=AS_OF))
    result = desk.broker.process(quote("2401.00", "2401.30", ts=AS_OF + M), as_of=AS_OF + M)
    assert result.executions[0].status is ExecutionStatus.CANCELLED
    order = desk.broker.state()
    assert order.open_positions == ()
    stored = journal.read(types=["order.cancelled"])[0].payload
    assert stored["reason"] == "circuit_breaker_tripped"
    assert stored["order"]["status"] == PaperOrderStatus.CANCELLED


def test_quotes_older_than_the_configured_age_are_refused(journal):
    desk = Desk(journal, paper_config(max_quote_age_seconds=2))
    intent, ctx = market_long(desk)
    with pytest.raises(InvalidMarketInput):
        desk.broker.submit(intent, ctx, as_of=AS_OF, market=Q0)  # 5 s old
