"""Helpers for the Phase 4 Paper Broker tests.

Every price, balance, spread, slippage and economics value here is a TEST-ONLY,
SYNTHETIC fixture. None is historical market data, a default or a recommendation.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from factories import make_proposal
from risk_helpers import AS_OF, context, engine, market
from stellar.execution import CurrentAuthorisation, PaperBroker, PaperBrokerConfig
from stellar.risk import RiskService
from stellar.schemas.market import Candle, Quote

STATION = "stellar-test"
M = timedelta(minutes=1)

# TEST-ONLY synthetic paper account (D-8 is the owner's decision; these are fixtures).
PAPER_CONFIG = PaperBrokerConfig.model_validate({
    "account_id": "paper_test",
    "account_currency": "USD",
    "starting_balance": "100000",
    "spread": {"mode": "QUOTE_ONLY"},
    "slippage": {"mode": "ZERO"},
    "economics": [{"instrument": "XAUUSD", "pnl_currency": "USD",
                   "value_per_price_unit_per_lot": "100", "source": "test_fixture"}],
})


def paper_config(**overrides: Any) -> PaperBrokerConfig:
    return PaperBrokerConfig.model_validate({**PAPER_CONFIG.model_dump(), **overrides})


def long_proposal(**overrides: Any):
    data = {"direction": "LONG", "stop_loss": {"price": "2388.00", "basis": "structure_low"},
            "take_profits": [{"price": "2424.00", "basis": "structure_high"}]}
    data.update(overrides)
    return make_proposal(**data)


def quote(bid: str, ask: str, ts=AS_OF, **kw: Any) -> Quote:
    """A synthetic XAUUSD quote."""
    return Quote(instrument="XAUUSD", bid=bid, ask=ask, ts=ts, source="synthetic_fixture",
                 provider_symbol="XAUUSD", **kw)


def bar(o: str, h: str, low: str, c: str, *, start, side: str = "ask",
        minutes: int = 5, **kw: Any) -> Candle:
    """A synthetic closed XAUUSD M5 bar on one price side."""
    return Candle(instrument="XAUUSD", timeframe="M5", open_time=start,
                  close_time=start + timedelta(minutes=minutes), open=o, high=h, low=low,
                  close=c, volume_kind="none", price_side=side, source="synthetic_fixture",
                  provider_symbol="XAUUSD", is_closed=True, **kw)


class Desk:
    """A risk service and a paper broker on one journal, as the execution service holds them."""

    def __init__(self, journal, config: PaperBrokerConfig | None = None, policy=None,
                 opened_at=AS_OF - timedelta(hours=1)) -> None:
        self.journal = journal
        self.risk = RiskService(engine(policy), journal, station_id=STATION,
                                clock=lambda: AS_OF)
        self.broker = PaperBroker(config or PAPER_CONFIG, journal, self.risk,
                                  station_id=STATION, opened_at=opened_at)

    def context(self, *, as_of=AS_OF, excluding_order_id=None, **overrides: Any):
        """A risk context whose account and book come from the paper broker."""
        view = self.broker.risk_inputs(as_of, excluding_order_id=excluding_order_id)
        data = {"as_of": as_of, "account": view.account, "positions": view.positions,
                "pending_orders": view.pending_orders,
                "prior_idempotency_keys": view.prior_idempotency_keys}
        data.update(overrides)
        return context(**data)

    def authorise(self, proposal=None, *, intent_id: str = "int_01", as_of=AS_OF,
                  take_profit: str | None = "from_proposal", **overrides: Any):
        """Evaluate and authorise through the Phase 3 path; returns (intent, context)."""
        ctx = self.context(as_of=as_of, **({"proposal": proposal} if proposal else {}),
                           **overrides)
        evaluation = self.risk.evaluate(ctx)
        tp = ctx.proposal.take_profits[0].price if take_profit == "from_proposal" else (
            None if take_profit is None else Decimal(take_profit))
        intent = self.risk.authorize_intent(evaluation, ctx, intent_id=intent_id,
                                            broker_symbol="XAUUSD", created_at=as_of,
                                            expires_at=as_of + 20 * M, take_profit=tp)
        return intent, ctx

    def reauthorise(self, order, trigger, *, at, n: int = 1, **overrides: Any):
        """A fill-time ``CurrentAuthorisation`` for one working order, through Phase 3.

        The context is evaluated at ``at`` against the book the order fills into (the
        current book without the order). For a quote trigger it carries that quote.
        The proposal is read back from the journaled evaluation (works after a restart).
        """
        intent = order.intent
        if isinstance(trigger, Quote):
            _, q = market(bid=str(trigger.bid), ask=str(trigger.ask), quote_ts=trigger.ts, at=at)
        else:
            _, q = market(at=at)
        snap, _ = market(at=at)
        data = {
            "proposal": self.risk.evaluations_for(intent.proposal_id)[0].context.proposal,
            "snapshot": snap, "quote": q,
            "daily": {**context().daily.model_dump(), "as_of": at},
            "event_restriction": {"instrument": "XAUUSD", "restricted": False,
                                  "evaluated_at": at, "source": "test_fixture"},
        }
        data.update(overrides)
        ctx = self.context(as_of=at, excluding_order_id=order.order_id, **data)
        evaluation = self.risk.evaluate(ctx)
        new = self.risk.authorize_intent(
            evaluation, ctx, intent_id=f"{intent.intent_id}_r{n}", broker_symbol="XAUUSD",
            created_at=at, expires_at=intent.expires_at, take_profit=intent.take_profit)
        return CurrentAuthorisation(order_id=order.order_id, intent=new, context=ctx)

    def fill_with(self, trigger, *, at, n: int = 1, conversions=(), **overrides: Any):
        """Process ``trigger`` with a fresh Phase 3 authorisation for every working order."""
        offered = [self.reauthorise(o, trigger, at=at, n=n, **overrides)
                   for o in self.broker.state().pending_orders]
        return self.broker.process(trigger, as_of=at, authorisations=offered,
                                   conversions=conversions)
