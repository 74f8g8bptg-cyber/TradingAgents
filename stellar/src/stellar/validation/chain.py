"""Cross-record validation along the decision chain (Foundation §9.2).

Each contract validates itself; these functions check that linked records agree:
a decision belongs to its proposal, an order intent follows an APPROVED decision
for that proposal and carries exactly its levels and volume, and an execution
result belongs to its intent. Problems are reported as deterministic codes.
This is structural validation, not risk policy.
"""

from __future__ import annotations

from collections.abc import Iterable

from stellar.schemas.common import SIDE_FOR_DIRECTION
from stellar.schemas.execution import ExecutionResult
from stellar.schemas.order import OrderIntent
from stellar.schemas.proposal import TradeProposal
from stellar.schemas.risk import RiskDecision, RiskOutcome


class ChainValidationError(ValueError):
    def __init__(self, problems: Iterable[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(", ".join(self.problems))


def _raise_if(problems: list[str]) -> None:
    if problems:
        raise ChainValidationError(problems)


def risk_decision_problems(decision: RiskDecision, proposal: TradeProposal) -> list[str]:
    problems = []
    if decision.proposal_id != proposal.proposal_id:
        problems.append("decision_proposal_mismatch")
    if decision.instrument != proposal.instrument:
        problems.append("instrument_mismatch")
    if decision.run_id is not None and decision.run_id != proposal.run_id:
        problems.append("run_id_mismatch")
    if decision.decided_at < proposal.created_at:
        problems.append("decided_before_proposal")
    return problems


def validate_risk_decision(decision: RiskDecision, proposal: TradeProposal) -> None:
    _raise_if(risk_decision_problems(decision, proposal))


def order_intent_problems(
    intent: OrderIntent, proposal: TradeProposal, decision: RiskDecision
) -> list[str]:
    problems = risk_decision_problems(decision, proposal)
    if decision.outcome is not RiskOutcome.APPROVED:
        problems.append("decision_not_approved")
    if intent.proposal_id != proposal.proposal_id:
        problems.append("proposal_id_mismatch")
    if intent.decision_id != decision.decision_id:
        problems.append("decision_id_mismatch")
    if intent.instrument != proposal.instrument and "instrument_mismatch" not in problems:
        problems.append("instrument_mismatch")
    if intent.side is not SIDE_FOR_DIRECTION[proposal.direction]:
        problems.append("side_mismatch")
    if decision.volume is None or intent.volume != decision.volume:
        problems.append("volume_mismatch")
    if intent.stop_loss != proposal.stop_loss.price:
        problems.append("stop_loss_mismatch")
    targets = {tp.price for tp in proposal.take_profits}
    if intent.take_profit is not None and intent.take_profit not in targets:
        problems.append("take_profit_mismatch")
    if intent.order_type.value != proposal.entry.type.value:
        problems.append("order_type_mismatch")
    entry = proposal.entry
    if intent.price is not None:
        if entry.price is not None and intent.price != entry.price:
            problems.append("price_mismatch")
        if entry.zone_low is not None and entry.zone_high is not None and not (
            entry.zone_low <= intent.price <= entry.zone_high
        ):
            problems.append("price_outside_entry_zone")
    if intent.expires_at > proposal.valid_until:
        problems.append("expires_after_proposal")
    if intent.created_at < decision.decided_at:
        problems.append("created_before_decision")
    return problems


def validate_order_intent(
    intent: OrderIntent, proposal: TradeProposal, decision: RiskDecision
) -> None:
    """An intent is valid only against its proposal and an APPROVED decision for it."""
    _raise_if(order_intent_problems(intent, proposal, decision))


def execution_result_problems(result: ExecutionResult, intent: OrderIntent) -> list[str]:
    problems = []
    if result.intent_id != intent.intent_id:
        problems.append("intent_id_mismatch")
    if result.instrument != intent.instrument:
        problems.append("instrument_mismatch")
    if result.side is not intent.side:
        problems.append("side_mismatch")
    if result.account_mode is not intent.account_mode:
        problems.append("account_mode_mismatch")
    if result.requested_volume != intent.volume:
        problems.append("volume_mismatch")
    if result.ts < intent.created_at:
        problems.append("result_before_intent")
    return problems


def validate_execution_result(result: ExecutionResult, intent: OrderIntent) -> None:
    _raise_if(execution_result_problems(result, intent))
