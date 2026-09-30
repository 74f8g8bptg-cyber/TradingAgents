"""Execution Checker (P4): no simulated fill happens without a *current* Phase 3 authorisation.

It never builds, widens or refreshes an approval; it only confirms one, through
``RiskService.confirm_intent`` (the Phase 3 current-authorisation check). It is
the only builder of ``FillAuthorisation``, and the broker cannot open a position
without one.

**At submission** (``check``) it refuses (``PreflightFailed``, a typed reason) unless:
1. the intent is for a PAPER account (DEMO waits for the Phase 8 gate);
2. the intent has not expired and the risk context is not from the future;
3. the journaled circuit breaker is not TRIPPED;
4. ``confirm_intent``: the intent is exactly what the safe Phase 3 path builds from
   the *latest* journaled evaluation of its proposal, and the fingerprint of the
   given context under the current policy still matches;
5. the context's account, positions, pending orders and order keys are exactly this
   broker's current state (``broker_state_changed`` otherwise);
6. the context's instrument metadata agrees with the broker's economics.

**At fill time** (``check_fill``), for an accepted order that has become executable,
a ``CurrentAuthorisation`` (an intent and the caller's current ``RiskContext``) must
be supplied and must pass all of the above again, now against the book the order
fills into (the current book without the order itself), plus:
- the intent repeats the order's economic terms exactly (``INTENT_TERMS``);
- the context is at least as recent as the market input that makes the order
  executable (and, for a quote, carries that quote or a newer one), and not after
  ``as_of`` (``authorisation_not_current``).

The submission approval is therefore reused only while *every* fingerprinted input
is unchanged. Anything else (equity, daily P&L, positions, pending orders, quote,
spread, ``as_of``, metadata, the policy) needs a new evaluation and a new intent.
"""

from __future__ import annotations

from datetime import datetime

from stellar.execution.config import PaperBrokerConfig
from stellar.execution.models import (
    INTENT_TERMS,
    AuthorisationStage,
    FillAuthorisation,
    PaperOrder,
)
from stellar.execution.pricing import MarketInput, input_window
from stellar.execution.state import Book
from stellar.execution.views import risk_inputs
from stellar.risk.breaker import BreakerStatus
from stellar.risk.engine import InvalidRiskInput, RiskEvaluation
from stellar.risk.intents import IntentRefused, ReevaluationRequired
from stellar.risk.service import RiskService
from stellar.risk.state import RiskContext
from stellar.schemas.common import OrderId, StellarModel
from stellar.schemas.market import Quote
from stellar.schemas.order import AccountMode, OrderIntent


class PreflightFailed(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class CurrentAuthorisation(StellarModel):
    """What the caller offers to let one working order fill now."""

    order_id: OrderId
    intent: OrderIntent
    context: RiskContext


class ExecutionChecker:
    def __init__(self, risk: RiskService) -> None:
        self._risk = risk

    def check(self, intent: OrderIntent, context: RiskContext, *, book: Book,
              as_of: datetime) -> FillAuthorisation:
        """Submission: returns the confirmed authorisation, or raises PreflightFailed."""
        evaluation = self._confirm(intent, context, book=book, as_of=as_of, excluding=None)
        return self._authorisation(AuthorisationStage.SUBMISSION, intent, context, evaluation,
                                   as_of)

    def check_fill(self, order: PaperOrder, offered: CurrentAuthorisation | None, *,
                   book: Book, market: MarketInput, as_of: datetime) -> FillAuthorisation:
        """Fill time: the order may fill only under a current authorisation."""
        if offered is None:
            raise PreflightFailed("authorisation_required")
        intent, context = offered.intent, offered.context
        if any(getattr(intent, f) != getattr(order.intent, f) for f in INTENT_TERMS):
            raise PreflightFailed("authorisation_terms_changed")
        _, end = input_window(market)
        if context.as_of < end:
            raise PreflightFailed("authorisation_not_current")
        if isinstance(market, Quote) and (context.quote is None
                                          or context.quote.quote.ts < market.ts):
            raise PreflightFailed("authorisation_not_current")
        evaluation = self._confirm(intent, context, book=book, as_of=as_of,
                                   excluding=order.order_id)
        return self._authorisation(AuthorisationStage.FILL, intent, context, evaluation, as_of)

    # ------------------------------------------------------------------ shared --

    def _confirm(self, intent: OrderIntent, context: RiskContext, *, book: Book,
                 as_of: datetime, excluding: str | None) -> RiskEvaluation:
        config = book.config
        assert config is not None
        if intent.account_mode is not AccountMode.PAPER:
            raise PreflightFailed("account_mode_not_paper")
        if as_of >= intent.expires_at:
            raise PreflightFailed("intent_expired")
        if intent.created_at > as_of:
            raise PreflightFailed("intent_after_execution_time")
        if context.as_of > as_of:
            raise PreflightFailed("context_after_submission")
        if context.proposal.proposal_id != intent.proposal_id:
            raise PreflightFailed("context_for_another_proposal")
        if self._risk.breaker.state().status is BreakerStatus.TRIPPED:
            raise PreflightFailed("circuit_breaker_tripped")
        try:
            evaluation = self._risk.confirm_intent(intent, context)
        except ReevaluationRequired as exc:
            raise PreflightFailed("reevaluation_required") from exc
        except IntentRefused as exc:
            raise PreflightFailed("intent_not_authorised") from exc
        except InvalidRiskInput as exc:
            raise PreflightFailed("invalid_risk_context") from exc
        view = risk_inputs(book, context.as_of, excluding_order_id=excluding)
        if (context.account != view.account or context.positions != view.positions
                or context.pending_orders != view.pending_orders
                or set(context.prior_idempotency_keys) != set(view.prior_idempotency_keys)):
            raise PreflightFailed("broker_state_changed")
        self._check_metadata(config, context)
        return evaluation

    @staticmethod
    def _authorisation(stage: AuthorisationStage, intent: OrderIntent, context: RiskContext,
                       evaluation: RiskEvaluation, as_of: datetime) -> FillAuthorisation:
        return FillAuthorisation(stage=stage, intent_id=intent.intent_id,
                                 decision_id=evaluation.decision.decision_id,
                                 evaluation_fingerprint=evaluation.fingerprint,
                                 context_as_of=context.as_of, confirmed_at=as_of)

    @staticmethod
    def _check_metadata(config: PaperBrokerConfig, context: RiskContext) -> None:
        metadata = context.metadata
        if metadata is None:
            return
        if metadata.account_currency != config.account_currency:
            raise PreflightFailed("account_currency_mismatch")
        economics = config.economics_for(metadata.instrument)
        if economics is not None and economics.pnl_currency == config.account_currency and \
                economics.value_per_price_unit_per_lot != metadata.value_per_price_unit_per_lot:
            raise PreflightFailed("economics_mismatch")
