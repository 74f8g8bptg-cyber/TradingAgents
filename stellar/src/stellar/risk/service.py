"""Risk service: runs the engine with journaled state, idempotency and events.

- **Breaker from the journal.** The context's breaker state is always replaced by
  the journal's (``BreakerLedger``); a caller cannot pass in an ARMED breaker.
- **Idempotency is scoped to the complete evaluation identity.** Every
  evaluation carries a deterministic ``fingerprint`` (engine version + policy
  hash + hash of the whole context, breaker included; see ``engine``). If the
  latest journaled evaluation of the proposal has the same fingerprint, it is
  returned unchanged: no new events, no second decision, even after a restart.
  Otherwise (any relevant input, the breaker or the policy changed) the
  proposal is evaluated again and the new evaluation is journaled as a new
  entry in its history. Earlier evaluations are never mutated or removed; they
  simply stop being current. The same ``proposal_id`` with different proposal
  content raises ``ProposalConflictError`` and records nothing.
- **Current authorisation.** ``authorize_intent`` is the only public way to an
  ``OrderIntent``. It refuses unless the journaled breaker is not TRIPPED, the
  evaluation is exactly the journaled latest evaluation of its proposal, and
  its fingerprint equals the fingerprint of the *current* context under the
  service's *current* policy (``ReevaluationRequired`` otherwise). There is no
  time-based expiry; ``as_of`` is simply one of the fingerprinted inputs.
- **Events** (canonical names): ``risk.check.started``, one ``risk.check.completed``
  per rule, then ``risk.approved`` / ``risk.rejected`` / ``risk.review.requested``
  whose payload carries the fingerprint and the complete evaluation (context,
  policy, every rule result, the decision), and ``circuit_breaker.tripped`` when
  a systemic rule trips the breaker. A rejection alone never trips it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from stellar.journal import StellarJournal
from stellar.risk.breaker import BreakerStatus
from stellar.risk.engine import RiskEngine, RiskEvaluation
from stellar.risk.intents import IntentRefused, ReevaluationRequired, _build_order_intent
from stellar.risk.ledger import BreakerLedger
from stellar.risk.state import RiskContext
from stellar.schemas.order import OrderIntent
from stellar.schemas.risk import RISK_ENGINE_ID, RiskOutcome
from stellar.serialization import content_hash
from stellar.telemetry import EventBus, new_event

FINAL_EVENTS = {
    RiskOutcome.APPROVED: "risk.approved",
    RiskOutcome.REJECTED: "risk.rejected",
    RiskOutcome.REVIEW: "risk.review.requested",
}


class ProposalConflictError(ValueError):
    """A proposal id was already evaluated with different proposal content."""


class RiskService:
    def __init__(self, engine: RiskEngine, journal: StellarJournal, *, station_id: str,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.engine = engine
        self._journal = journal
        self._bus = EventBus(journal)
        self._station_id = station_id
        self._clock = clock or (lambda: datetime.now(UTC))
        self.breaker = BreakerLedger(journal, station_id=station_id, clock=self._clock)

    # ------------------------------------------------------------------ public --

    def evaluations_for(self, proposal_id: str) -> tuple[RiskEvaluation, ...]:
        """Every journaled evaluation of a proposal, oldest first (its full history)."""
        return tuple(RiskEvaluation.model_validate(event.payload["evaluation"])
                     for event in self._journal.read(types=tuple(FINAL_EVENTS.values()))
                     if event.correlation_id == proposal_id)

    def latest_evaluation(self, proposal_id: str) -> RiskEvaluation | None:
        history = self.evaluations_for(proposal_id)
        return history[-1] if history else None

    def current_context(self, context: RiskContext) -> RiskContext:
        """The context as it will be evaluated: normalised, breaker from the journal."""
        context = self.engine.normalise(context)
        return context.model_copy(update={"breaker": self.breaker.state()})

    def evaluate(self, context: RiskContext) -> RiskEvaluation:
        context = self.current_context(context)
        proposal = context.proposal
        latest = self.latest_evaluation(proposal.proposal_id)
        if latest is not None:
            if latest.proposal_hash != content_hash(proposal.model_dump(mode="json")):
                raise ProposalConflictError(
                    f"{proposal.proposal_id} was already evaluated with different content")
            if latest.fingerprint == self.engine.fingerprint(context):
                return latest  # the same complete evaluation: nothing new to record
        evaluation = self.engine.evaluate(context)
        self._publish(evaluation)
        if evaluation.breaker_trip is not None:
            self.breaker.trip(evaluation.breaker_trip)
        return evaluation

    def authorize_intent(
        self,
        evaluation: RiskEvaluation,
        context: RiskContext,
        *,
        intent_id: str,
        broker_symbol: str,
        created_at: datetime,
        expires_at: datetime,
        take_profit: Decimal | None = None,
    ) -> OrderIntent:
        """Build an ``OrderIntent`` only if ``evaluation`` is the current APPROVED one.

        ``context`` is the caller's current risk context for the same proposal.
        """
        if self.breaker.state().status is BreakerStatus.TRIPPED:
            raise IntentRefused("the circuit breaker is TRIPPED")
        proposal_id = evaluation.decision.proposal_id
        latest = self.latest_evaluation(proposal_id)
        if latest is None or latest != evaluation:
            raise ReevaluationRequired(
                f"{evaluation.decision.decision_id} is not the latest journaled evaluation "
                f"of {proposal_id}")
        current = self.current_context(context)
        if current.proposal.proposal_id != proposal_id:
            raise ReevaluationRequired("the current context is for another proposal")
        if self.engine.fingerprint(current) != evaluation.fingerprint:
            raise ReevaluationRequired(
                f"the risk context or policy changed since {evaluation.decision.decision_id}")
        return _build_order_intent(evaluation, intent_id=intent_id, broker_symbol=broker_symbol,
                                   created_at=created_at, expires_at=expires_at,
                                   take_profit=take_profit)

    # ----------------------------------------------------------------- helpers --

    def _event(self, event_type: str, payload: dict, evaluation: RiskEvaluation):
        return new_event(event_type, station_id=self._station_id, source="stellar.risk",
                         agent_id=RISK_ENGINE_ID, instrument=evaluation.decision.instrument,
                         run_id=evaluation.decision.run_id,
                         correlation_id=evaluation.decision.proposal_id,
                         payload=payload, ts=self._clock())

    def _publish(self, evaluation: RiskEvaluation) -> None:
        decision = evaluation.decision
        self._bus.publish(self._event("risk.check.started", {
            "proposal_id": decision.proposal_id,
            "decision_id": decision.decision_id,
            "fingerprint": evaluation.fingerprint,
            "checks": [r.check for r in evaluation.results],
            "policy_version": evaluation.policy.version,
            "policy_hash": evaluation.policy_hash,
        }, evaluation))
        for r in evaluation.results:
            self._bus.publish(self._event("risk.check.completed", {
                "proposal_id": decision.proposal_id,
                "check": r.check,
                "rule": r.rule.value,
                "status": r.status.value,
                "reason": r.reason,
                "passed": r.status.value in {"PASS", "NOT_APPLICABLE"},
                "blocking": r.blocking,
                "value": None if r.value is None else str(r.value),
                "limit": None if r.limit is None else str(r.limit),
                "unit": r.unit,
            }, evaluation))
        final = {
            "proposal_id": decision.proposal_id,
            "decision_id": decision.decision_id,
            "fingerprint": evaluation.fingerprint,
            "outcome": decision.outcome.value,
            "reasons": [r.value for r in decision.reasons],
            "policy_hash": evaluation.policy_hash,
            "context_hash": evaluation.context_hash,
            "evaluation": evaluation.model_dump(mode="json"),
        }
        if decision.outcome is RiskOutcome.APPROVED:
            final["volume"] = str(decision.volume)
            final["risk_pct_equity"] = str(decision.risk_pct_equity)
        if decision.outcome is RiskOutcome.REJECTED:
            final["shadow_tracked"] = True  # layer design §4.3
        self._bus.publish(self._event(FINAL_EVENTS[decision.outcome], final, evaluation))
