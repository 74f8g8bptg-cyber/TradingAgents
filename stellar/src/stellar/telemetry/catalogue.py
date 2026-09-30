"""The canonical event catalogue (layer design §4.3; Foundation §10.1; naming R-3).

Only names listed here may be emitted. Names follow
``<domain>.<entity>.<past-tense verb>`` or ``<domain>.<past-tense verb>``.
Adding a name is an additive change; renaming or removing one is not.
"""

from __future__ import annotations

import re

EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z_]*(?:\.[a-z][a-z_]*){1,2}$")

MINIMUM_V1_EVENT_TYPES: frozenset[str] = frozenset({
    "agent.task.started",
    "agent.task.completed",
    "agent.state.changed",
    "market.focus.changed",
    "snapshot.created",
    "snapshot.rejected",
    "research.item.collected",
    "research.item.accepted",
    "research.item.rejected",
    "research.snapshot.created",
    "analysis.created",
    "setup.state.changed",
    "debate.started",
    "debate.completed",
    "trade.proposed",
    "risk.approved",
    "risk.rejected",
    "order.created",
    "order.sent",
    "order.filled",
    "order.rejected",
    "trade.closed",
    "agent.resting",
    "agent.overloaded",
    "system.paused",
    "system.resumed",
    "budget.warning",
    "circuit_breaker.tripped",
    "circuit_breaker.reset",
})
"""Foundation §10.1: the minimum V1 event set."""

EVENT_TYPES: frozenset[str] = MINIMUM_V1_EVENT_TYPES | frozenset({
    # Station, system and run
    "station.heartbeat.emitted",
    "station.alert_level.changed",
    "run.started",
    "run.resumed",
    "run.completed",
    "run.failed",
    # Agent state and activity
    "agent.task.failed",
    "agent.moved",
    "agent.llm_call.started",
    "agent.llm_call.completed",
    "agent.tool_call.started",
    "agent.tool_call.completed",
    "agent.wrap_up.forced",
    # Market data
    "market.session.changed",
    "market.quote.received",
    "market.data.stale_detected",
    # Debate and decision
    "debate.turn.completed",
    "decision.research_plan.created",
    "decision.trader_plan.created",
    "decision.final.created",
    # Risk and circuit breaker
    "risk.check.started",
    "risk.check.completed",
    "risk.limit.approached",
    "circuit_breaker.reset_refused",
    "risk.review.requested",  # Phase 3 addition: the REVIEW outcome had no event
    # Orders, trades and account
    "order.preflight.failed",
    "order.acknowledged",
    "order.partially_filled",
    "position.opened",
    "position.updated",
    "account.snapshot.created",
    # Review and memory
    "memory.review.created",
    "memory.outcome.settled",
    "memory.decision.stored",
    "memory.reflection.written",
    # Wellbeing and workload
    "wellbeing.load.updated",
    "agent.rest.ended",
    "agent.degraded",
})
"""The full canonical catalogue of layer design §4.3."""

CRITICAL_DOMAINS: frozenset[str] = frozenset({"trade", "risk", "order", "circuit_breaker"})
"""Decision and order events: if one cannot be journaled, execution must halt (§4.5)."""

REQUIRED_PAYLOAD_KEYS: dict[str, frozenset[str]] = {
    "trade.proposed": frozenset({"proposal_id", "setup_id", "instrument", "direction"}),
    "risk.approved": frozenset({"proposal_id", "decision_id"}),
    "risk.rejected": frozenset({"proposal_id", "decision_id", "reasons"}),
    "risk.review.requested": frozenset({"proposal_id", "decision_id", "reasons"}),
    "order.created": frozenset({"order_id", "intent_id", "idempotency_key", "mode"}),
    "order.preflight.failed": frozenset({"order_id", "reason"}),
    "order.sent": frozenset({"order_id"}),
    "order.filled": frozenset({"order_id", "fill_price", "filled_volume"}),
    "order.rejected": frozenset({"order_id", "reason"}),
    "trade.closed": frozenset({"trade_id"}),
    "circuit_breaker.tripped": frozenset({"rule"}),
    "circuit_breaker.reset": frozenset({"by", "reason"}),
    "circuit_breaker.reset_refused": frozenset({"source", "reason"}),
}
"""Payload keys named explicitly by layer design §4.3 for decision-critical events."""


def is_critical(event_type: str) -> bool:
    return event_type.split(".", 1)[0] in CRITICAL_DOMAINS


def _check_catalogue() -> None:
    bad = sorted(n for n in EVENT_TYPES if not EVENT_NAME_PATTERN.match(n))
    if bad:  # pragma: no cover - guarded by tests
        raise RuntimeError(f"non-canonical event names in the catalogue: {bad}")
    unknown = sorted(set(REQUIRED_PAYLOAD_KEYS) - EVENT_TYPES)
    if unknown:  # pragma: no cover - guarded by tests
        raise RuntimeError(f"payload rules for unknown events: {unknown}")


_check_catalogue()
