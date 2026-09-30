"""Paper Broker: positions, stop-loss and take-profit, bar ambiguity, P&L and currencies."""

from datetime import timedelta
from decimal import Decimal

import pytest
from broker_helpers import Desk, M, bar, long_proposal, paper_config, quote
from risk_helpers import AS_OF, context
from stellar.execution import (
    CloseReason,
    ConversionRate,
    InvalidMarketInput,
    PaperOrder,
    PnlStatus,
    PositionStatus,
)
from stellar.journal import StellarJournal
from stellar.risk import InstrumentRiskMetadata

pytestmark = pytest.mark.unit
T1 = AS_OF + M  # entry time in these scenarios


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def open_short(desk):
    """SELL limit 2400.00, stop 2412.00, target 2376.00, 0.50 lots, filled at T1."""
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1)
    return desk.broker.state().open_positions[0]


def open_long(desk):
    """BUY limit 2400.00, stop 2388.00, target 2424.00, 0.50 lots, filled at T1."""
    intent, ctx = desk.authorise(long_proposal())
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    desk.fill_with(quote("2399.70", "2400.00", ts=T1), at=T1)
    return desk.broker.state().open_positions[0]


def closed(desk, market, as_of):
    (trade,) = desk.broker.process(market, as_of=as_of).trades
    return trade


# --- positions ---------------------------------------------------------------------------------


def test_position_opens_with_the_approved_stop_and_linked_ids(journal):
    desk = Desk(journal)
    position = open_short(desk)
    filled = journal.read(types=["order.filled"])[0].payload
    order = PaperOrder.model_validate(filled["order"])
    assert position.stop_loss == Decimal("2412.00") == order.intent.stop_loss
    assert position.take_profit == Decimal("2376.00") and position.volume == Decimal("0.50")
    assert position.entry_price == Decimal("2400.00") and position.status is PositionStatus.OPEN
    assert (position.order_id, position.intent_id, position.proposal_id) == (
        order.order_id, "int_01", "prop_01")
    # The fill was confirmed current at T1 by a fresh Phase 3 evaluation and intent.
    auth = order.fill_authorisation
    assert auth.stage.value == "FILL" and auth.confirmed_at == T1
    assert (position.authorised_intent_id, position.decision_id) == ("int_01_r1",
                                                                     auth.decision_id)
    assert auth.evaluation_fingerprint == desk.risk.latest_evaluation("prop_01").fingerprint
    assert auth.decision_id != order.intent.decision_id  # the submission approval was not reused
    assert position.entry_fill_id == order.fill.fill_id == filled["fill_id"]
    assert position.position_id == order.position_id == filled["position_id"]
    opened = journal.read(types=["position.opened"])[0]
    assert opened.payload["position_id"] == position.position_id


def test_open_position_is_marked_on_its_exit_side(journal):
    desk = Desk(journal)
    open_short(desk)
    position = desk.broker.state().open_positions[0]
    assert position.mark_price == Decimal("2400.50")  # a short closes at the ask
    assert position.unrealised.amount == Decimal("-25.0000")  # 0.50 * 0.50 * 100
    assert desk.broker.state().equity == Decimal("99975.0000")


# --- stop-loss / take-profit on quotes -----------------------------------------------------------


def test_sell_position_stop(journal):
    desk = Desk(journal)
    open_short(desk)
    trade = closed(desk, quote("2411.70", "2412.00", ts=T1 + M), T1 + M)
    assert trade.close_reason is CloseReason.STOP_LOSS and trade.exit_fill.side.value == "BUY"
    assert trade.exit_fill.execution_price == Decimal("2412.00") and not trade.exit_fill.gap
    assert trade.realised.amount == Decimal("-600.0000")


def test_buy_position_stop(journal):
    desk = Desk(journal)
    open_long(desk)
    trade = closed(desk, quote("2388.00", "2388.30", ts=T1 + M), T1 + M)
    assert trade.close_reason is CloseReason.STOP_LOSS and trade.exit_fill.side.value == "SELL"
    assert trade.exit_fill.execution_price == Decimal("2388.00")
    assert trade.realised.amount == Decimal("-600.0000")


def test_sell_position_target_fills_at_the_target_never_better(journal):
    desk = Desk(journal)
    open_short(desk)
    trade = closed(desk, quote("2375.60", "2375.90", ts=T1 + M), T1 + M)
    assert trade.close_reason is CloseReason.TAKE_PROFIT
    assert trade.exit_fill.execution_price == Decimal("2376.00")
    assert trade.realised.amount == Decimal("1200.0000")


def test_buy_position_target(journal):
    desk = Desk(journal)
    open_long(desk)
    trade = closed(desk, quote("2424.50", "2424.80", ts=T1 + M), T1 + M)
    assert trade.close_reason is CloseReason.TAKE_PROFIT
    assert trade.exit_fill.execution_price == Decimal("2424.00")
    assert trade.realised.amount == Decimal("1200.0000")


def test_a_stop_gapped_through_fills_at_the_worse_price_plus_slippage(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.10"}}))
    open_short(desk)
    trade = closed(desk, bar("2415.00", "2416.00", "2410.00", "2414.00", start=T1 + M), T1 + 6 * M)
    assert trade.exit_fill.gap and trade.exit_fill.execution_price == Decimal("2415.10")
    assert trade.exit_fill.slippage == Decimal("0.10")


# --- bar ambiguity -----------------------------------------------------------------------------


def test_a_bar_touching_stop_and_target_takes_the_stop(journal):
    desk = Desk(journal)
    open_short(desk)
    trade = closed(desk, bar("2400.00", "2413.00", "2370.00", "2380.00", start=T1 + M),
                   T1 + 6 * M)
    assert trade.close_reason is CloseReason.STOP_LOSS
    assert trade.exit_fill.execution_price == Decimal("2412.00")
    assert trade.exit_fill.intrabar_ambiguous and trade.exit_fill.intrabar_resolution == \
        "stop_first"
    assert trade.realised.amount < 0  # never the profitable outcome


def test_a_bar_reaching_only_the_target_takes_it(journal):
    desk = Desk(journal)
    open_short(desk)
    trade = closed(desk, bar("2390.00", "2395.00", "2370.00", "2380.00", start=T1 + M),
                   T1 + 6 * M)
    assert trade.close_reason is CloseReason.TAKE_PROFIT and not trade.exit_fill.intrabar_ambiguous


def _synthetic_desk(journal):
    return Desk(journal, paper_config(spread={"mode": "SYNTHETIC_FIXED",
                                              "synthetic": {"XAUUSD": "0.30"}}))


def test_stop_in_the_entry_bar_counts_pessimistically(journal):
    desk = _synthetic_desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    entry_bar = bar("2399.00", "2412.00", "2398.00", "2405.00", start=T1, side="bid")
    result = desk.fill_with(entry_bar, at=T1 + 5 * M)  # bid 2412 -> ask 2412.30
    (trade,) = result.trades
    assert trade.close_reason is CloseReason.STOP_LOSS
    assert trade.exit_fill.intrabar_resolution == "stop_counted_in_entry_window"


def test_target_in_the_entry_bar_is_never_taken(journal):
    desk = _synthetic_desk(journal)
    intent, ctx = desk.authorise()
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    entry_bar = bar("2399.00", "2400.50", "2370.00", "2380.00", start=T1, side="bid")
    result = desk.fill_with(entry_bar, at=T1 + 5 * M)
    assert result.trades == () and len(desk.broker.state().open_positions) == 1


def test_a_bar_open_before_the_entry_can_stop_but_not_take_profit(journal):
    desk = Desk(journal)
    open_short(desk)  # entered at T1 from a quote
    straddle = bar("2390.00", "2395.00", "2370.00", "2380.00", start=T1 - 2 * M)
    assert desk.broker.process(straddle, as_of=T1 + 3 * M).trades == ()
    stop_straddle = bar("2400.00", "2413.00", "2399.00", "2405.00", start=T1 - M)
    (trade,) = desk.broker.process(stop_straddle, as_of=T1 + 4 * M).trades
    assert trade.close_reason is CloseReason.STOP_LOSS


def test_bars_that_predate_the_position_are_ignored(journal):
    desk = Desk(journal)
    open_short(desk)
    old = bar("2400.00", "2450.00", "2350.00", "2400.00", start=AS_OF - 10 * M)
    assert desk.broker.process(old, as_of=T1 + M).trades == ()


def test_manual_close_at_the_quote_with_slippage(journal):
    desk = Desk(journal, paper_config(slippage={"mode": "FIXED", "fixed": {"XAUUSD": "0.10"}}))
    intent, ctx = desk.authorise(long_proposal())
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    desk.fill_with(quote("2399.70", "2400.00", ts=T1), at=T1)
    position = desk.broker.state().open_positions[0]
    trade = desk.broker.close(position.position_id, quote("2405.00", "2405.30", ts=T1 + M),
                              as_of=T1 + M)
    assert trade.close_reason is CloseReason.MANUAL
    assert trade.exit_fill.execution_price == Decimal("2404.90")
    assert desk.broker.close(position.position_id, quote("2405.00", "2405.30", ts=T1 + M),
                             as_of=T1 + M) == trade


# --- P&L, balance and equity -------------------------------------------------------------------


def test_realised_pnl_moves_balance_and_trade_record_is_complete(journal):
    desk = Desk(journal)
    open_short(desk)
    trade = closed(desk, quote("2375.60", "2375.90", ts=T1 + M), T1 + M)
    state = desk.broker.state()
    assert state.balance == state.equity == Decimal("101200.0000")
    assert state.realised_pnl == Decimal("1200.0000") and state.unrealised_pnl == 0
    assert state.peak_equity == Decimal("101200.0000") and state.closed_trades == (trade,)
    evaluation = desk.risk.latest_evaluation("prop_01")
    assert (trade.proposal_id, trade.decision_id, trade.evaluation_fingerprint) == (
        "prop_01", evaluation.decision.decision_id, evaluation.fingerprint)
    assert trade.entry_fill.execution_price == Decimal("2400.00")
    assert (trade.stop_loss, trade.take_profit) == (Decimal("2412.00"), Decimal("2376.00"))
    assert trade.opened_at == T1 and trade.closed_at == T1 + M
    assert trade.provenance.produced_by == "paper_execution"
    assert desk.broker.stats().closed_trades == 1


def test_missing_economics_never_invents_money(journal):
    desk = Desk(journal, paper_config(economics=[]))
    open_short(desk)
    state = desk.broker.state()
    position = state.open_positions[0]
    assert position.unrealised.status is PnlStatus.MISSING_ECONOMICS
    assert position.unrealised.amount is None
    assert position.unrealised.price_change == Decimal("-0.50")
    assert state.unrealised_pnl is None and state.equity is None
    assert state.unvalued_position_ids == (position.position_id,)
    assert desk.broker.risk_inputs(T1).account is None  # risk sees "unknown", not zero
    trade = closed(desk, quote("2375.60", "2375.90", ts=T1 + M), T1 + M)
    state = desk.broker.state()
    assert trade.realised.status is PnlStatus.MISSING_ECONOMICS
    assert state.balance is None and state.realised_pnl is None and state.equity is None
    assert state.unsettled_trade_ids == (trade.trade_id,)


CHF_METADATA = InstrumentRiskMetadata(instrument="XAUUSD", account_currency="CHF",
                                      value_per_price_unit_per_lot="80", lot_step="0.01",
                                      min_volume="0.01", max_volume="50", source="test_fixture")


def _chf_desk(journal):
    config = paper_config(account_currency="CHF")  # economics stay in USD
    desk = Desk(journal, config)
    intent, ctx = desk.authorise(metadata=CHF_METADATA)
    assert ctx.metadata.account_currency == "CHF"
    desk.broker.submit(intent, ctx, as_of=AS_OF)
    return desk


def _rate(base, quote_ccy, rate="0.80", at=AS_OF):
    return ConversionRate(base=base, quote=quote_ccy, rate=rate, as_of=at, source="test_fixture")


def test_no_hidden_currency_conversion(journal):
    desk = _chf_desk(journal)
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1, metadata=CHF_METADATA)
    position = desk.broker.state().open_positions[0]
    assert position.unrealised.status is PnlStatus.MISSING_CONVERSION
    assert position.unrealised.instrument_amount == Decimal("-25.0000")
    assert position.unrealised.instrument_currency == "USD" and position.unrealised.amount is None
    trade = closed(desk, quote("2375.60", "2375.90", ts=T1 + M), T1 + M)
    assert trade.realised.status is PnlStatus.MISSING_CONVERSION
    assert desk.broker.state().balance is None


def test_an_inverse_rate_is_not_inverted(journal):
    desk = _chf_desk(journal)
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1, metadata=CHF_METADATA)
    trade = desk.broker.process(quote("2375.60", "2375.90", ts=T1 + M), as_of=T1 + M,
                                conversions=[_rate("CHF", "USD", "1.25")]).trades[0]
    assert trade.realised.status is PnlStatus.MISSING_CONVERSION


def test_an_explicit_rate_converts_with_provenance(journal):
    desk = _chf_desk(journal)
    desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1, metadata=CHF_METADATA)
    rate = _rate("USD", "CHF")
    trade = desk.broker.process(quote("2375.60", "2375.90", ts=T1 + M), as_of=T1 + M,
                                conversions=[rate]).trades[0]
    assert trade.realised.status is PnlStatus.KNOWN
    assert trade.realised.amount == Decimal("960.000000") and trade.realised.conversion == rate
    assert trade.realised.currency == "CHF"


def test_a_future_rate_is_look_ahead(journal):
    desk = _chf_desk(journal)
    with pytest.raises(InvalidMarketInput):
        desk.fill_with(quote("2400.20", "2400.50", ts=T1), at=T1, metadata=CHF_METADATA,
                       conversions=[_rate("USD", "CHF", at=T1 + timedelta(seconds=1))])


def test_sizing_economics_must_match_the_broker_economics(journal):
    desk = Desk(journal)  # broker: 100 USD per 1.0 move per lot
    metadata = context().metadata.model_copy(update={"value_per_price_unit_per_lot":
                                                     Decimal("90")})
    intent, ctx = desk.authorise(metadata=metadata)  # the risk engine sized with 90
    assert desk.broker.submit(intent, ctx, as_of=AS_OF).reason == "economics_mismatch"


def test_risk_metadata_in_another_account_currency_is_refused():
    from stellar.execution import ExecutionChecker, PreflightFailed

    with pytest.raises(PreflightFailed, match="account_currency_mismatch"):
        ExecutionChecker._check_metadata(paper_config(account_currency="CHF"), context())


def test_exits_are_not_evaluated_from_a_side_that_needs_an_invented_spread(journal):
    desk = Desk(journal)  # QUOTE_ONLY
    position = open_short(desk)  # a short exits on the ask
    bid_bar = bar("2420.00", "2425.00", "2419.00", "2421.00", start=T1 + M, side="bid")
    assert desk.broker.process(bid_bar, as_of=T1 + 6 * M).trades == ()
    assert desk.broker.state().open_positions[0].mark_price == position.mark_price
