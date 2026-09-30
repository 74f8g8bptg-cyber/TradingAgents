"""``PaperBroker``: a deterministic, journal-backed simulated broker (Foundation §4.15, §4.16).

It never connects to a broker, never creates a price and never builds an approval.

**Intake.** ``submit(intent, context, as_of=..., market=...)``:
- the same intent again returns the journaled result (no new events); the same
  ``intent_id`` with different content raises ``OrderConflictError``;
- a second intent for a proposal that already has an accepted order is refused
  (``duplicate_order``): one proposal, at most one accepted order;
- the Execution Checker must pass (PAPER, not expired, breaker not TRIPPED, the
  intent currently authorised by Phase 3, the context matches this book);
  otherwise ``order.preflight.failed``. A preflight failure does not use up the
  proposal, so a fresh authorisation can be submitted;
- accepted orders are journaled (``order.created``). A MARKET order fills from
  the submission quote or is rejected; a LIMIT order stays PENDING until a later
  input reaches its price, it expires, or it is cancelled.

**Prices** come only from the ``Quote`` or closed ``Candle`` passed in (see
``pricing``). Fill rules, all conservative:
- market entry: ask (BUY) / bid (SELL) plus adverse slippage; slippage above the
  intent's ``max_slippage`` rejects the order;
- limit entry: at the limit price, never better, no slippage;
- stop: at the stop, or at the (worse) open when the market gapped through it,
  plus adverse slippage; always executed (protective);
- take-profit: at the target, never better, no slippage;
- a bar that reaches both the stop and the target: STOP_FIRST, flagged
  ``intrabar_ambiguous``;
- an input that overlaps the entry window (the bar the entry filled in, or a bar
  still open when the entry happened) can trigger the stop (pessimistic) but
  never the target; inputs that predate the entry are ignored.

**Working orders** (PENDING or BLOCKED) fill only from inputs that start at or after
the order was accepted (the submission quote is the one exception, for the order
just submitted) and end before it expires. When one becomes executable:
- if the breaker is TRIPPED, it is cancelled (``circuit_breaker_tripped``);
- otherwise it fills only under a **current authorisation**: the caller passes a
  ``CurrentAuthorisation`` (intent + current ``RiskContext``) to ``process`` and the
  Execution Checker confirms it through Phase 3 (``check_fill``). Without one, or
  if it is not current, the order does not fill: it becomes BLOCKED with the reason
  (``order.preflight.failed``, stage ``fill``) and stays blocked until a current
  authorisation is supplied at a later executable moment, it expires, or it is
  cancelled. The broker never refreshes or creates an approval itself.

**State** is reconstructed from the journal at every call (``state.load_book``);
``as_of`` may never move backwards.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from stellar.execution.checker import CurrentAuthorisation, ExecutionChecker, PreflightFailed
from stellar.execution.config import PaperBrokerConfig
from stellar.execution.models import (
    PAPER_EXECUTION_ID,
    WORKING_ORDER_STATUSES,
    CloseReason,
    ConversionRate,
    FillAuthorisation,
    FillKind,
    PaperAccountState,
    PaperFill,
    PaperOrder,
    PaperOrderStatus,
    PaperStats,
    Position,
    PositionStatus,
    SlippageSource,
    TradeRecord,
    entry_fill_id_for,
    exit_fill_id_for,
    order_id_for,
    position_id_for,
    trade_id_for,
)
from stellar.execution.pnl import compute_pnl
from stellar.execution.pricing import (
    InvalidMarketInput,
    MarketInput,
    PriceUnavailable,
    SidePrices,
    adverse,
    check_input,
    input_window,
    opposite,
    side_prices,
    slippage_for,
)
from stellar.execution.state import (
    BROKER_SOURCE,
    Book,
    BrokerJournalError,
    broker_events,
    load_book,
)
from stellar.execution.views import PaperRiskInputs, risk_inputs
from stellar.journal import StellarJournal
from stellar.risk.breaker import BreakerStatus
from stellar.risk.service import RiskService
from stellar.risk.state import RiskContext
from stellar.schemas.common import OrderSide, Provenance
from stellar.schemas.execution import ExecutionResult, ExecutionStatus
from stellar.schemas.market import Quote
from stellar.schemas.order import OrderIntent, OrderType
from stellar.telemetry import EventBus, StellarEvent, new_event


class PaperBrokerError(Exception):
    """Base class for refusals that record nothing."""


class OrderConflictError(PaperBrokerError):
    """The same intent id was already submitted with different content."""


class OutOfOrderInput(PaperBrokerError):
    """``as_of`` moves backwards, or precedes the intent."""


class AccountConfigConflict(PaperBrokerError):
    """The journal already holds this account with another configuration."""


class OrderNotCancellable(PaperBrokerError):
    """Only a PENDING order can be cancelled."""


_STATUS = {
    PaperOrderStatus.PREFLIGHT_FAILED: ExecutionStatus.PREFLIGHT_FAILED,
    PaperOrderStatus.PENDING: ExecutionStatus.ACKNOWLEDGED,
    PaperOrderStatus.BLOCKED: ExecutionStatus.PREFLIGHT_FAILED,  # a fill-time preflight failed
    PaperOrderStatus.FILLED: ExecutionStatus.FILLED,
    PaperOrderStatus.REJECTED: ExecutionStatus.REJECTED,
    PaperOrderStatus.CANCELLED: ExecutionStatus.CANCELLED,
    PaperOrderStatus.EXPIRED: ExecutionStatus.EXPIRED,
}
_ORDER_EVENT = {
    PaperOrderStatus.PREFLIGHT_FAILED: "order.preflight.failed",
    PaperOrderStatus.PENDING: "order.created",
    PaperOrderStatus.BLOCKED: "order.preflight.failed",
    PaperOrderStatus.FILLED: "order.filled",
    PaperOrderStatus.REJECTED: "order.rejected",
    PaperOrderStatus.CANCELLED: "order.cancelled",
    PaperOrderStatus.EXPIRED: "order.expired",
}


@dataclass(frozen=True)
class ProcessResult:
    executions: tuple[ExecutionResult, ...] = ()
    trades: tuple[TradeRecord, ...] = ()


class PaperBroker:
    def __init__(self, config: PaperBrokerConfig, journal: StellarJournal, risk: RiskService,
                 *, station_id: str, opened_at: datetime) -> None:
        self.config = PaperBrokerConfig.model_validate(config.model_dump())
        self.config_hash = self.config.config_hash()
        self._journal = journal
        self._bus = EventBus(journal)
        self._risk = risk
        self._checker = ExecutionChecker(risk)
        self._station_id = station_id
        book = self._book()
        if book.opened:
            assert book.config is not None
            if book.config.config_hash() != self.config_hash:
                raise AccountConfigConflict(
                    f"account {self.config.account_id} exists with another configuration")
        else:
            self._emit(book, "account.opened", {
                "currency": self.config.account_currency,
                "starting_balance": str(self.config.starting_balance),
                "config": self.config.model_dump(mode="json"),
                "config_hash": self.config_hash,
            }, opened_at)

    # ------------------------------------------------------------ read models --

    def state(self) -> PaperAccountState:
        return self._book().state()

    def account(self) -> PaperAccountState:
        return self.state()

    def positions(self) -> tuple[Position, ...]:
        return self.state().open_positions

    def trades(self) -> tuple[TradeRecord, ...]:
        return self.state().closed_trades

    def stats(self) -> PaperStats:
        return self._book().stats()

    def risk_inputs(self, as_of: datetime, *,
                    excluding_order_id: str | None = None) -> PaperRiskInputs:
        """Read models for ``RiskContext``. To re-authorise a working order, pass its id: the
        order is then left out of the book it would fill into."""
        return risk_inputs(self._book(), as_of, excluding_order_id=excluding_order_id)

    def events(self) -> list[StellarEvent]:
        return broker_events(self._journal, self.config.account_id)

    def execution_result(self, order_id: str) -> ExecutionResult:
        return self._result(self._book().orders[order_id])

    # ------------------------------------------------------------- operations --

    def submit(self, intent: OrderIntent, context: RiskContext, *, as_of: datetime,
               market: MarketInput | None = None,
               conversions: Sequence[ConversionRate] = ()) -> ExecutionResult:
        book = self._book()
        self._check_clock(book, as_of)
        intent = OrderIntent.model_validate(intent.model_dump())  # re-validate
        if as_of < intent.created_at:
            raise OutOfOrderInput("an intent cannot be submitted before it was created")
        order_id = order_id_for(intent.intent_id)
        existing = book.orders.get(order_id)
        if existing is not None:
            if existing.intent != intent:
                raise OrderConflictError(f"{intent.intent_id} was submitted with other content")
            return self._result(existing)  # idempotent: nothing new is recorded
        if market is not None:
            self._check_market(market, as_of, instrument=intent.instrument)
        version = book.version
        try:
            if book.accepted_order_for_key(intent.idempotency_key) is not None:
                raise PreflightFailed("duplicate_order")
            authorisation = self._checker.check(intent, context, book=book, as_of=as_of)
            try:
                slippage_for(self.config.slippage, intent.instrument)
            except PriceUnavailable as exc:
                raise PreflightFailed(exc.reason) from exc
        except PreflightFailed as refusal:
            order = PaperOrder(order_id=order_id, account_id=self.config.account_id,
                               intent=intent, status=PaperOrderStatus.PREFLIGHT_FAILED,
                               reason=refusal.reason, created_at=as_of, updated_at=as_of)
            self._emit_order(book, order, as_of)
            self._snapshot(book, version, as_of)
            return self._result(order)
        order = PaperOrder(order_id=order_id, account_id=self.config.account_id, intent=intent,
                           status=PaperOrderStatus.PENDING,
                           evaluation_fingerprint=authorisation.evaluation_fingerprint,
                           created_at=as_of, updated_at=as_of)
        self._emit_order(book, order, as_of)
        if intent.order_type is OrderType.MARKET:
            self._fill_market(book, order, market, as_of, conversions, authorisation)
        if market is not None:
            # The submission authorisation was confirmed in this call against this book
            # and covers only this order, only for the submission input.
            self._step(book, market, as_of, conversions, fresh=(order_id, authorisation))
        self._expire(book, as_of)
        self._snapshot(book, version, as_of)
        return self._result(book.orders[order_id])

    def process(self, market: MarketInput, *, as_of: datetime,
                conversions: Sequence[ConversionRate] = (),
                authorisations: Sequence[CurrentAuthorisation] = ()) -> ProcessResult:
        """Advance the book with one market input: working-order fills (each only under a
        current authorisation), expiries, stops, targets, marks."""
        book = self._book()
        self._check_clock(book, as_of)
        self._check_market(market, as_of)
        offered = {a.order_id: a for a in authorisations}
        if len(offered) != len(authorisations):
            raise ValueError("at most one authorisation per order")
        for order_id in offered:
            order = book.orders.get(order_id)
            if order is None or order.status not in WORKING_ORDER_STATUSES:
                raise ValueError(f"{order_id} is not a working order")
        version = book.version
        executions, trades = self._step(book, market, as_of, conversions, offered=offered)
        executions += self._expire(book, as_of)
        self._snapshot(book, version, as_of)
        return ProcessResult(tuple(executions), tuple(trades))

    def expire_due(self, *, as_of: datetime) -> tuple[ExecutionResult, ...]:
        book = self._book()
        self._check_clock(book, as_of)
        version = book.version
        results = self._expire(book, as_of)
        self._snapshot(book, version, as_of)
        return tuple(results)

    def cancel(self, order_id: str, *, as_of: datetime) -> ExecutionResult:
        book = self._book()
        order = book.orders.get(order_id)
        if order is None:
            raise KeyError(f"unknown order {order_id}")
        if order.status is PaperOrderStatus.CANCELLED:
            return self._result(order)  # idempotent
        if order.status not in WORKING_ORDER_STATUSES:
            raise OrderNotCancellable(f"{order_id} is {order.status.value}")
        self._check_clock(book, as_of)
        version = book.version
        cancelled = self._finish(book, order, PaperOrderStatus.CANCELLED,
                                 "cancelled_by_request", as_of)
        self._snapshot(book, version, as_of)
        return cancelled

    def close(self, position_id: str, quote: Quote, *, as_of: datetime,
              conversions: Sequence[ConversionRate] = ()) -> TradeRecord:
        """Close an open position at the current quote (MANUAL)."""
        book = self._book()
        done = book.trades.get(trade_id_for(position_id))
        if done is not None:
            return done  # idempotent
        position = book.positions.get(position_id)
        if position is None:
            raise KeyError(f"unknown position {position_id}")
        self._check_clock(book, as_of)
        self._check_market(quote, as_of, instrument=position.instrument)
        if not isinstance(quote, Quote):
            raise InvalidMarketInput("a manual close needs a quote")
        if quote.ts < position.entry_window_end:
            raise InvalidMarketInput("the quote predates the position")
        version = book.version
        exit_side = opposite(position.side)
        prices = side_prices(quote, exit_side, self.config.spread)
        slippage, source = slippage_for(self.config.slippage, position.instrument)
        fill = self._fill_record(
            fill_id=exit_fill_id_for(position_id), kind=FillKind.EXIT, side=exit_side,
            instrument=position.instrument, volume=position.volume, prices=prices,
            source_price=prices.close, level=None,
            execution_price=adverse(prices.close, slippage, exit_side),
            slippage=slippage, slippage_source=source, as_of=as_of,
            input_ids=(position.order_id,),
            slippage_breach=slippage > position.max_slippage)
        trade = self._close_position(book, position, fill, CloseReason.MANUAL, as_of,
                                     conversions)
        self._snapshot(book, version, as_of)
        return trade

    # ------------------------------------------------------------------ steps --

    def _step(self, book: Book, market: MarketInput, as_of: datetime,
              conversions: Sequence[ConversionRate], *,
              fresh: tuple[str, FillAuthorisation] | None = None,
              offered: dict[str, CurrentAuthorisation] | None = None,
              ) -> tuple[list[ExecutionResult], list[TradeRecord]]:
        executions: list[ExecutionResult] = []
        trades: list[TradeRecord] = []
        start, end = input_window(market)
        is_quote = isinstance(market, Quote)
        for order in book.working():
            intent = order.intent
            if intent.instrument is not market.instrument or \
                    intent.order_type is not OrderType.LIMIT or intent.price is None:
                continue  # market orders never wait: filled or rejected at submission
            is_fresh = fresh is not None and order.order_id == fresh[0] and is_quote
            ends_in_time = end < intent.expires_at if is_quote else end <= intent.expires_at
            if not ((start >= order.created_at or is_fresh) and ends_in_time):
                continue
            try:
                prices = side_prices(market, intent.side, self.config.spread)
            except PriceUnavailable:
                continue  # cannot be evaluated without inventing a price; stays pending
            buy = intent.side is OrderSide.BUY
            if not (prices.low <= intent.price if buy else prices.high >= intent.price):
                continue
            if self._risk.breaker.state().status is BreakerStatus.TRIPPED:
                executions.append(self._finish(book, order, PaperOrderStatus.CANCELLED,
                                               "circuit_breaker_tripped", as_of))
                continue
            if is_fresh:
                assert fresh is not None
                authorisation = fresh[1]
            else:
                try:
                    authorisation = self._checker.check_fill(
                        order, (offered or {}).get(order.order_id), book=book, market=market,
                        as_of=as_of)
                except PreflightFailed as refusal:
                    if (order.status, order.reason) != (PaperOrderStatus.BLOCKED,
                                                        refusal.reason):
                        executions.append(self._finish(book, order, PaperOrderStatus.BLOCKED,
                                                       refusal.reason, as_of))
                    continue
            fill = self._fill_record(
                fill_id=entry_fill_id_for(order.order_id), kind=FillKind.ENTRY,
                side=intent.side, instrument=intent.instrument, volume=intent.volume,
                prices=prices, source_price=prices.low if buy else prices.high,
                level=intent.price, execution_price=intent.price, slippage=Decimal(0),
                slippage_source=SlippageSource.NOT_APPLIED, as_of=as_of,
                input_ids=(intent.intent_id, order.order_id))
            executions.append(self._open(book, order, fill, (start, end), as_of,
                                         authorisation))
        for position in book.open_positions():
            if position.instrument is market.instrument:
                trade = self._exits(book, position, market, as_of, conversions)
                if trade is not None:
                    trades.append(trade)
        for position in book.open_positions():
            if position.instrument is market.instrument:
                self._mark(book, position, market, as_of, conversions)
        return executions, trades

    def _fill_market(self, book: Book, order: PaperOrder, market: MarketInput | None,
                     as_of: datetime, conversions: Sequence[ConversionRate],
                     authorisation: FillAuthorisation) -> None:
        intent = order.intent
        if not isinstance(market, Quote):
            self._finish(book, order, PaperOrderStatus.REJECTED, "market_order_needs_quote",
                         as_of)
            return
        prices = side_prices(market, intent.side, self.config.spread)
        slippage, source = slippage_for(self.config.slippage, intent.instrument)
        if slippage > intent.max_slippage:
            self._finish(book, order, PaperOrderStatus.REJECTED, "slippage_exceeds_max", as_of)
            return
        try:
            price = adverse(prices.close, slippage, intent.side)
        except PriceUnavailable as exc:
            self._finish(book, order, PaperOrderStatus.REJECTED, exc.reason, as_of)
            return
        buy = intent.side is OrderSide.BUY
        if not (intent.stop_loss < price if buy else intent.stop_loss > price):
            self._finish(book, order, PaperOrderStatus.REJECTED, "stop_through_fill", as_of)
            return
        if intent.take_profit is not None and not (
                intent.take_profit > price if buy else intent.take_profit < price):
            self._finish(book, order, PaperOrderStatus.REJECTED, "target_through_fill", as_of)
            return
        fill = self._fill_record(
            fill_id=entry_fill_id_for(order.order_id), kind=FillKind.ENTRY, side=intent.side,
            instrument=intent.instrument, volume=intent.volume, prices=prices,
            source_price=prices.close, level=None, execution_price=price, slippage=slippage,
            slippage_source=source, as_of=as_of, input_ids=(intent.intent_id, order.order_id))
        self._open(book, order, fill, input_window(market), as_of, authorisation)

    def _exits(self, book: Book, position: Position, market: MarketInput, as_of: datetime,
               conversions: Sequence[ConversionRate]) -> TradeRecord | None:
        start, end = input_window(market)
        is_quote = isinstance(market, Quote)
        predates = end < position.entry_window_start if is_quote else \
            end <= position.entry_window_start
        if predates:
            return None
        full = start >= position.entry_window_end
        exit_side = opposite(position.side)
        try:
            prices = side_prices(market, exit_side, self.config.spread)
        except PriceUnavailable:
            return None  # not evaluable without inventing a price (documented limitation)
        long = position.side is OrderSide.BUY
        stop = position.stop_loss
        stop_hit = prices.low <= stop if long else prices.high >= stop
        target = position.take_profit
        target_hit = full and target is not None and (
            prices.high >= target if long else prices.low <= target)
        if stop_hit:
            gap = prices.open < stop if long else prices.open > stop
            base = prices.open if gap else stop
            slippage, source = slippage_for(self.config.slippage, position.instrument)
            resolution = None
            if target_hit:
                resolution = "stop_first"
            elif not full:
                resolution = "stop_counted_in_entry_window"
            fill = self._fill_record(
                fill_id=exit_fill_id_for(position.position_id), kind=FillKind.EXIT,
                side=exit_side, instrument=position.instrument, volume=position.volume,
                prices=prices, source_price=prices.low if long else prices.high, level=stop,
                execution_price=adverse(base, slippage, exit_side), slippage=slippage,
                slippage_source=source, as_of=as_of, input_ids=(position.order_id,), gap=gap,
                resolution=resolution, slippage_breach=slippage > position.max_slippage)
            return self._close_position(book, position, fill, CloseReason.STOP_LOSS, as_of,
                                        conversions)
        if target_hit:
            assert target is not None
            fill = self._fill_record(
                fill_id=exit_fill_id_for(position.position_id), kind=FillKind.EXIT,
                side=exit_side, instrument=position.instrument, volume=position.volume,
                prices=prices, source_price=prices.high if long else prices.low, level=target,
                execution_price=target, slippage=Decimal(0),
                slippage_source=SlippageSource.NOT_APPLIED, as_of=as_of,
                input_ids=(position.order_id,))
            return self._close_position(book, position, fill, CloseReason.TAKE_PROFIT, as_of,
                                        conversions)
        return None

    def _mark(self, book: Book, position: Position, market: MarketInput, as_of: datetime,
              conversions: Sequence[ConversionRate]) -> None:
        _, end = input_window(market)
        if end < position.entry_window_end:
            return
        if position.mark_ts is not None and end < position.mark_ts:
            return
        try:
            prices = side_prices(market, opposite(position.side), self.config.spread)
        except PriceUnavailable:
            return
        unrealised = compute_pnl(side=position.side, entry=position.entry_price,
                                 price=prices.close, volume=position.volume,
                                 economics=self.config.economics_for(position.instrument),
                                 account_currency=self.config.account_currency,
                                 conversions=conversions, as_of=as_of)
        if (position.mark_price, position.mark_ts, position.unrealised) == (
                prices.close, end, unrealised):
            return
        updated = position.model_copy(update={"mark_price": prices.close, "mark_ts": end,
                                              "unrealised": unrealised, "updated_at": as_of})
        self._emit(book, "position.updated", self._position_payload(updated), as_of,
                   correlation_id=updated.proposal_id, instrument=updated.instrument)

    def _expire(self, book: Book, as_of: datetime) -> list[ExecutionResult]:
        return [self._finish(book, order, PaperOrderStatus.EXPIRED, "intent_expired", as_of)
                for order in book.working() if order.intent.expires_at <= as_of]

    # ------------------------------------------------------------ transitions --

    def _open(self, book: Book, order: PaperOrder, fill: PaperFill,
              window: tuple[datetime, datetime], as_of: datetime,
              authorisation: FillAuthorisation) -> ExecutionResult:
        """The only way to open a position: it needs the checker's current authorisation."""
        if not isinstance(authorisation, FillAuthorisation) or \
                authorisation.confirmed_at != as_of:
            raise PaperBrokerError("a fill needs an authorisation confirmed at this moment")
        intent = order.intent
        position = Position(
            position_id=position_id_for(order.order_id), account_id=self.config.account_id,
            order_id=order.order_id, intent_id=intent.intent_id,
            authorised_intent_id=authorisation.intent_id, proposal_id=intent.proposal_id,
            decision_id=authorisation.decision_id, idempotency_key=intent.idempotency_key,
            instrument=intent.instrument, side=intent.side, volume=intent.volume,
            entry_price=fill.execution_price, stop_loss=intent.stop_loss,
            take_profit=intent.take_profit, max_slippage=intent.max_slippage,
            entry_fill_id=fill.fill_id,
            entry_window_start=window[0], entry_window_end=window[1], opened_at=as_of,
            updated_at=as_of)
        filled = order.model_copy(update={"status": PaperOrderStatus.FILLED, "fill": fill,
                                          "position_id": position.position_id,
                                          "fill_authorisation": authorisation,
                                          "reason": None, "updated_at": as_of})
        filled = PaperOrder.model_validate(filled.model_dump())
        self._emit_order(book, filled, as_of, extra={
            "fill_price": str(fill.execution_price), "filled_volume": str(fill.volume),
            "fill_id": fill.fill_id, "fill": fill.model_dump(mode="json"),
            "authorised_intent_id": authorisation.intent_id,
            "authorisation_stage": authorisation.stage.value,
            "position_id": position.position_id,
            "position": position.model_dump(mode="json")})
        self._emit(book, "position.opened", self._position_payload(position), as_of,
                   correlation_id=position.proposal_id, instrument=position.instrument)
        return self._result(filled)

    def _close_position(self, book: Book, position: Position, fill: PaperFill,
                        reason: CloseReason, as_of: datetime,
                        conversions: Sequence[ConversionRate]) -> TradeRecord:
        order = book.orders[position.order_id]
        assert order.fill is not None and order.fill_authorisation is not None
        realised = compute_pnl(side=position.side, entry=position.entry_price,
                               price=fill.execution_price, volume=position.volume,
                               economics=self.config.economics_for(position.instrument),
                               account_currency=self.config.account_currency,
                               conversions=conversions, as_of=as_of)
        trade = TradeRecord(
            trade_id=trade_id_for(position.position_id), account_id=self.config.account_id,
            position_id=position.position_id, proposal_id=position.proposal_id,
            decision_id=position.decision_id,
            evaluation_fingerprint=order.fill_authorisation.evaluation_fingerprint,
            intent_id=position.intent_id, authorised_intent_id=position.authorised_intent_id,
            order_id=position.order_id, instrument=position.instrument, side=position.side,
            volume=position.volume, stop_loss=position.stop_loss,
            take_profit=position.take_profit, entry_fill=order.fill, exit_fill=fill,
            close_reason=reason, realised=realised, opened_at=position.opened_at,
            closed_at=as_of, provenance=self._provenance(position.order_id,
                                                         position.intent_id))
        closed = position.model_copy(update={"status": PositionStatus.CLOSED,
                                             "updated_at": as_of})
        self._emit(book, "trade.closed", {
            "trade_id": trade.trade_id, "position_id": position.position_id,
            "proposal_id": position.proposal_id, "order_id": position.order_id,
            "fill_id": fill.fill_id, "close_reason": reason.value,
            "slippage_breach": fill.slippage_breach,
            "exit_price": str(fill.execution_price), "volume": str(position.volume),
            "trade": trade.model_dump(mode="json"), "position": closed.model_dump(mode="json"),
        }, as_of, correlation_id=position.proposal_id, instrument=position.instrument)
        return trade

    def _finish(self, book: Book, order: PaperOrder, status: PaperOrderStatus, reason: str,
                as_of: datetime) -> ExecutionResult:
        done = order.model_copy(update={"status": status, "reason": reason,
                                        "updated_at": as_of})
        done = PaperOrder.model_validate(done.model_dump())
        extra = {"reason": reason}
        self._emit_order(book, done, as_of, extra=extra)
        return self._result(done)

    # ---------------------------------------------------------------- helpers --

    def _fill_record(self, *, fill_id: str, kind: FillKind, side: OrderSide, instrument: Any,
                     volume: Decimal, prices: SidePrices, source_price: Decimal,
                     level: Decimal | None, execution_price: Decimal, slippage: Decimal,
                     slippage_source: SlippageSource, as_of: datetime,
                     input_ids: Iterable[str], gap: bool = False,
                     resolution: str | None = None, slippage_breach: bool = False) -> PaperFill:
        return PaperFill(
            fill_id=fill_id, kind=kind, instrument=instrument, side=side, volume=volume,
            price_source=prices.price_source, source_price=source_price, level=level,
            execution_price=execution_price, spread=prices.spread,
            spread_source=prices.spread_source, slippage=slippage,
            slippage_source=slippage_source, gap=gap, slippage_breach=slippage_breach,
            intrabar_ambiguous=resolution is not None, intrabar_resolution=resolution,
            source_ts=prices.start, source=prices.source, provider_symbol=prices.provider_symbol,
            as_of=as_of, provenance=self._provenance(*input_ids))

    def _provenance(self, *input_ids: str) -> Provenance:
        return Provenance(produced_by=PAPER_EXECUTION_ID, config_hash=self.config_hash,
                          input_ids=tuple(dict.fromkeys(input_ids)))

    def _result(self, order: PaperOrder) -> ExecutionResult:
        intent, fill = order.intent, order.fill
        status = _STATUS[order.status]
        return ExecutionResult(
            order_id=order.order_id, intent_id=intent.intent_id, instrument=intent.instrument,
            account_mode=intent.account_mode, side=intent.side, status=status,
            requested_volume=intent.volume,
            filled_volume=intent.volume if fill is not None else Decimal(0),
            fill_id=fill.fill_id if fill is not None else None,
            fill_price=fill.execution_price if fill is not None else None,
            slippage=fill.slippage if fill is not None else None,
            reason=order.reason if status in {ExecutionStatus.PREFLIGHT_FAILED,
                                              ExecutionStatus.REJECTED} else None,
            ts=order.updated_at, provenance=self._provenance(intent.intent_id, order.order_id))

    def _book(self) -> Book:
        return load_book(self._journal, self.config.account_id)

    def _check_clock(self, book: Book, as_of: datetime) -> None:
        if as_of.tzinfo is None:
            raise OutOfOrderInput("as_of must be timezone-aware")
        if book.as_of is not None and as_of < book.as_of:
            raise OutOfOrderInput(f"as_of {as_of} is before the book's {book.as_of}")

    def _check_market(self, market: MarketInput, as_of: datetime, *,
                      instrument: Any = None) -> None:
        check_input(market, as_of, max_quote_age_seconds=self.config.max_quote_age_seconds)
        if instrument is not None and market.instrument is not instrument:
            raise InvalidMarketInput("the market input is for another instrument")

    def _position_payload(self, position: Position) -> dict[str, Any]:
        return {"position_id": position.position_id, "proposal_id": position.proposal_id,
                "order_id": position.order_id, "status": position.status.value,
                "position": position.model_dump(mode="json")}

    def _emit_order(self, book: Book, order: PaperOrder, as_of: datetime, *,
                    extra: dict[str, Any] | None = None) -> None:
        intent = order.intent
        payload = {"order_id": order.order_id, "intent_id": intent.intent_id,
                   "proposal_id": intent.proposal_id, "decision_id": intent.decision_id,
                   "idempotency_key": intent.idempotency_key, "mode": intent.account_mode.value,
                   "status": order.status.value, "order": order.model_dump(mode="json")}
        if order.reason is not None:
            payload["reason"] = order.reason
        if order.status is PaperOrderStatus.BLOCKED:
            payload["stage"] = "fill"  # the order stays working; it cannot fill as is
        payload.update(extra or {})
        self._emit(book, _ORDER_EVENT[order.status], payload, as_of,
                   correlation_id=intent.proposal_id, instrument=intent.instrument)

    def _emit(self, book: Book, event_type: str, payload: dict[str, Any], as_of: datetime,
              **fields: Any) -> None:
        event = new_event(event_type, station_id=self._station_id, source=BROKER_SOURCE,
                          agent_id=PAPER_EXECUTION_ID, ts=as_of,
                          payload={"account_id": self.config.account_id, **payload,
                                   "as_of": as_of.isoformat()}, **fields)
        stored = self._bus.publish(event)  # critical domains raise on a journal failure
        if stored is None:
            raise BrokerJournalError(f"{event_type} could not be journaled")
        book.apply(stored)

    def _snapshot(self, book: Book, version: int, as_of: datetime) -> None:
        if book.version == version:
            return
        state = book.state()
        event = new_event("account.snapshot.created", station_id=self._station_id,
                          source=BROKER_SOURCE, agent_id=PAPER_EXECUTION_ID, ts=as_of,
                          payload={"account_id": self.config.account_id,
                                   "state": state.model_dump(mode="json")})
        self._bus.publish(event)
