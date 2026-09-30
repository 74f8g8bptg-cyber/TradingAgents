"""The deterministic Risk Engine (Foundation §8; P3 ``risk_engine``).

``RiskEngine(policy).evaluate(context)`` runs every rule in a fixed order and
aggregates the results with one precedence:

1. any blocking **FAIL** → ``REJECTED``;
2. otherwise any blocking **REVIEW** or blocking **NOT_CONFIGURED** → ``REVIEW``;
3. otherwise → ``APPROVED`` (which also requires a computed volume and risk %).

Same context + same policy → the same ``RiskEvaluation``, byte for byte: time is
``context.as_of``, and no rule reads a clock, a model or the network. The
evaluation carries the full context and policy, so it can be replayed and audited.

**Evaluation fingerprint.** ``evaluation_fingerprint`` hashes the complete
evaluation identity: the engine version, the policy hash and the hash of the
whole normalised ``RiskContext`` (proposal, ``as_of``, breaker state, account and
equity, daily P/L, drawdown, positions, pending orders, exposure, cooldowns,
event restriction, market snapshot, quote, broker metadata, execution mode).
Any change to any of them gives a different fingerprint. The decision id is
derived from it, so two evaluations share a decision id exactly when they share
every input.

A rule failure may *propose* a breaker trip (only the systemic rules named by
``TripPolicy``); applying it is the service's job, and a trip is never lifted here.
"""

from __future__ import annotations

from pydantic import ValidationError, model_validator

from stellar.risk.breaker import BreakerStatus, BreakerTrip, TripCause
from stellar.risk.policy import RiskPolicy
from stellar.risk.rules import RULES, RuleResult
from stellar.risk.sizing import size_trade
from stellar.risk.state import RiskContext
from stellar.schemas.common import Label, Provenance, Sha256Hex, StellarModel, UtcDatetime
from stellar.schemas.risk import RISK_ENGINE_ID, CheckStatus, RiskDecision, RiskOutcome
from stellar.serialization import content_hash

ENGINE_VERSION = "phase3_1"


class PolicyRejected(ValueError):
    """The policy cannot be used for this engine (for example a test-only policy)."""


class InvalidRiskInput(ValueError):
    """The context (including its proposal) is malformed. No decision is produced, so a
    malformed input can never be approved; it is refused before any rule runs."""


def evaluation_fingerprint(engine_version: str, policy_hash: str, context_hash: str) -> str:
    """The deterministic identity of one complete risk evaluation."""
    return content_hash({"engine_version": engine_version, "policy_hash": policy_hash,
                         "context_hash": context_hash})


def decision_id_for(fingerprint: str) -> str:
    return "dec_" + fingerprint[:40]


class RiskEvaluation(StellarModel):
    """One complete, replayable evaluation."""

    engine_version: Label
    fingerprint: Sha256Hex
    as_of: UtcDatetime
    policy: RiskPolicy
    policy_hash: Sha256Hex
    context: RiskContext
    context_hash: Sha256Hex
    proposal_hash: Sha256Hex
    results: tuple[RuleResult, ...]
    decision: RiskDecision
    breaker_status: BreakerStatus
    breaker_trip: BreakerTrip | None = None

    @model_validator(mode="after")
    def _consistent(self) -> RiskEvaluation:
        if self.policy.policy_hash() != self.policy_hash:
            raise ValueError("policy_hash does not match the policy")
        if content_hash(self.context.model_dump(mode="json")) != self.context_hash:
            raise ValueError("context_hash does not match the context")
        if evaluation_fingerprint(self.engine_version, self.policy_hash,
                                  self.context_hash) != self.fingerprint:
            raise ValueError("fingerprint does not match the evaluation inputs")
        if self.decision.decision_id != decision_id_for(self.fingerprint):
            raise ValueError("decision_id does not match the fingerprint")
        if self.decision.proposal_id != self.context.proposal.proposal_id:
            raise ValueError("the decision references another proposal")
        if self.decision.outcome is not decide(self.results):
            raise ValueError("the outcome does not follow the precedence of its results")
        return self


def decide(results: tuple[RuleResult, ...] | list[RuleResult]) -> RiskOutcome:
    """The precedence: blocking FAIL → REJECTED; other blocking → REVIEW; else APPROVED."""
    blocking = [r for r in results if r.blocking]
    if any(r.status is CheckStatus.FAIL for r in blocking):
        return RiskOutcome.REJECTED
    if blocking:
        return RiskOutcome.REVIEW
    return RiskOutcome.APPROVED


class RiskEngine:
    def __init__(self, policy: RiskPolicy, *, allow_test_policy: bool = False) -> None:
        policy = RiskPolicy.model_validate(policy.model_dump())  # re-validate
        if policy.test_only and not allow_test_policy:
            raise PolicyRejected("a test-only policy cannot make real risk decisions")
        self.policy = policy
        self.policy_hash = policy.policy_hash()

    @staticmethod
    def normalise(context: RiskContext) -> RiskContext:
        """Re-validate: an object built with ``model_construct`` cannot slip through."""
        try:
            return RiskContext.model_validate(context.model_dump(warnings=False))
        except ValidationError as exc:
            raise InvalidRiskInput(f"malformed risk input: {exc.error_count()} error(s)") from exc

    def fingerprint(self, context: RiskContext) -> str:
        """The fingerprint ``evaluate(context)`` would carry, without running any rule."""
        context = self.normalise(context)
        return evaluation_fingerprint(ENGINE_VERSION, self.policy_hash,
                                      content_hash(context.model_dump(mode="json")))

    def evaluate(self, context: RiskContext) -> RiskEvaluation:
        context = self.normalise(context)
        sizing = size_trade(context, self.policy)
        results = tuple(rule(context, self.policy, sizing) for rule in RULES)
        outcome = decide(results)
        context_hash = content_hash(context.model_dump(mode="json"))
        fingerprint = evaluation_fingerprint(ENGINE_VERSION, self.policy_hash, context_hash)
        decision_id = decision_id_for(fingerprint)
        reasons = tuple(dict.fromkeys(r.rule for r in results if r.blocking))
        approved = outcome is RiskOutcome.APPROVED
        decision = RiskDecision(
            decision_id=decision_id,
            proposal_id=context.proposal.proposal_id,
            run_id=context.proposal.run_id,
            instrument=context.proposal.instrument,
            outcome=outcome,
            reasons=reasons,
            checks=tuple(r.to_check() for r in results),
            volume=sizing.volume if approved else None,
            risk_pct_equity=sizing.risk_fraction if approved else None,
            decided_at=context.as_of,
            provenance=Provenance(produced_by=RISK_ENGINE_ID, config_hash=self.policy_hash,
                                  input_ids=(context.proposal.proposal_id,)),
        )
        return RiskEvaluation(
            engine_version=ENGINE_VERSION,
            fingerprint=fingerprint,
            as_of=context.as_of,
            policy=self.policy,
            policy_hash=self.policy_hash,
            context=context,
            context_hash=context_hash,
            proposal_hash=content_hash(context.proposal.model_dump(mode="json")),
            results=results,
            decision=decision,
            breaker_status=context.breaker.status,
            breaker_trip=self._trip(context, results),
        )

    @staticmethod
    def _trip(context: RiskContext, results) -> BreakerTrip | None:
        if context.breaker.status is BreakerStatus.TRIPPED:
            return None  # sticky: the first trip stays; nothing to add
        for r in results:
            if r.trips_breaker and r.status is CheckStatus.FAIL:
                return BreakerTrip(cause=TripCause.RISK_RULE, rule=r.rule, value=r.value,
                                   limit=r.limit, tripped_by=RISK_ENGINE_ID,
                                   tripped_at=context.as_of)
        return None
