"""``OrderIntent`` construction: only from a currently valid APPROVED evaluation (Foundation §8.4).

No broker, no order is sent. An intent is the typed hand-off a later phase's
Execution Checker and Paper Broker will consume.

The only public way to obtain an intent is ``RiskService.authorize_intent``,
which first proves the evaluation is *current* (journaled, the latest for its
proposal, the same fingerprint as the current context under the current
policy, and the journaled circuit breaker not TRIPPED). This module holds the
structural part it then applies. An intent is built only when:
- the evaluation's decision is APPROVED;
- the execution mode was PAPER (DEMO stays gated; LIVE does not exist);
- the owner configured a slippage tolerance for the instrument;
- the result passes the Phase 1 chain validation against its proposal and decision.

The idempotency key is the Phase 1 hash of the proposal id, so one proposal can
yield at most one order (Foundation §8.1 duplicate order prevention), whichever
of its evaluations authorised it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from stellar.risk.engine import RiskEvaluation
from stellar.risk.policy import ControlState
from stellar.schemas.common import SIDE_FOR_DIRECTION, Provenance
from stellar.schemas.order import AccountMode, OrderIntent, OrderType, idempotency_key_for
from stellar.schemas.risk import RISK_ENGINE_ID, RiskOutcome
from stellar.validation import validate_order_intent


class IntentRefused(ValueError):
    """No intent can be built from this evaluation."""


class ReevaluationRequired(IntentRefused):
    """The evaluation is not the current one for its proposal: evaluate again first."""


def _build_order_intent(
    evaluation: RiskEvaluation,
    *,
    intent_id: str,
    broker_symbol: str,
    created_at: datetime,
    expires_at: datetime,
    take_profit: Decimal | None = None,
) -> OrderIntent:
    """Structural checks only; callers must have proved the evaluation is current."""
    decision, proposal = evaluation.decision, evaluation.context.proposal
    if decision.outcome is not RiskOutcome.APPROVED:
        raise IntentRefused(f"decision {decision.decision_id} is {decision.outcome.value}")
    if evaluation.context.execution.mode != "PAPER":
        raise IntentRefused("only PAPER intents exist before the demo gate")
    slippage = evaluation.policy.max_slippage
    limit = slippage.limits.get(proposal.instrument) if slippage.state is \
        ControlState.ENABLED else None
    if limit is None:
        raise IntentRefused("no slippage tolerance is configured for this instrument")
    intent = OrderIntent(
        intent_id=intent_id,
        proposal_id=proposal.proposal_id,
        decision_id=decision.decision_id,
        account_mode=AccountMode.PAPER,
        instrument=proposal.instrument,
        broker_symbol=broker_symbol,
        side=SIDE_FOR_DIRECTION[proposal.direction],
        volume=decision.volume,
        order_type=OrderType(proposal.entry.type.value),
        price=proposal.entry.price,
        stop_loss=proposal.stop_loss.price,
        take_profit=take_profit,
        max_slippage=limit,
        idempotency_key=idempotency_key_for(proposal.proposal_id),
        expires_at=expires_at,
        created_at=created_at,
        provenance=Provenance(produced_by=RISK_ENGINE_ID, config_hash=evaluation.policy_hash,
                              input_ids=(proposal.proposal_id, decision.decision_id)),
    )
    validate_order_intent(intent, proposal, decision)
    return intent
