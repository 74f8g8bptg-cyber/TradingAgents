"""The deterministic V1 PAPER health check (operational health; not a trading signal).

``HealthStatus`` is the worst of the reasons found, in this order:
- FAILED: the journal fails verification, or reconciliation found an inconsistency;
- BLOCKED: nothing can trade on paper: the circuit breaker is TRIPPED, or the runtime has no
  enabled instrument / no paper broker symbol for one;
- DEGRADED: it works but needs attention: a run FAILED, a run waits for review or approval,
  an order is BLOCKED waiting for re-authorisation, P&L is unsettled (unknown economics or
  conversion), or a configuration is labelled test-only;
- HEALTHY: none of these.

Same journal and configuration → same report (``checked_at`` is the caller's time).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from stellar.risk.breaker import BreakerStatus
from stellar.runtime.models import RunState
from stellar.runtime.reconcile import ReconciliationReport, reconcile
from stellar.schemas.common import Label, StellarModel, UtcDatetime


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


_RANK = {HealthStatus.HEALTHY: 0, HealthStatus.DEGRADED: 1, HealthStatus.BLOCKED: 2,
         HealthStatus.FAILED: 3}


class HealthReport(StellarModel):
    status: HealthStatus
    reasons: tuple[Label, ...] = ()
    breaker: BreakerStatus
    runs_by_state: dict[str, int]
    reconciliation: ReconciliationReport
    checked_at: UtcDatetime


def health(runtime, *, checked_at: datetime) -> HealthReport:
    """``runtime`` is a ``PaperRuntime``; everything is read from its journal and config."""
    found: list[tuple[HealthStatus, str]] = []
    report = reconcile(runtime._journal, account_id=runtime.broker.config.account_id,  # noqa: SLF001
                       ledger=runtime.ledger)
    if not report.ok:
        found += [(HealthStatus.FAILED, f"reconciliation_{i.code}") for i in report.issues]
    breaker = runtime.risk.breaker.state().status
    if breaker is BreakerStatus.TRIPPED:
        found.append((HealthStatus.BLOCKED, "circuit_breaker_tripped"))
    cfg = runtime.config
    if not cfg.enabled_instruments:
        found.append((HealthStatus.BLOCKED, "no_enabled_instrument"))
    missing = sorted(i.value for i in cfg.enabled_instruments if i not in cfg.broker_symbols)
    if missing:
        found.append((HealthStatus.BLOCKED, "no_paper_broker_symbol_" + "_".join(missing)))
    records = runtime.runs() if report.ok or not any(
        i.code == "journal_integrity" for i in report.issues) else []
    by_state: dict[str, int] = {}
    for r in records:
        by_state[r.state.value] = by_state.get(r.state.value, 0) + 1
    attention = {RunState.FAILED: "run_failed", RunState.REVIEW_REQUIRED: "run_review_required",
                 RunState.AWAITING_APPROVAL: "run_awaiting_approval",
                 RunState.ORDER_BLOCKED: "order_blocked"}
    for state, reason in attention.items():
        if by_state.get(state.value):
            found.append((HealthStatus.DEGRADED, reason))
    if report.unsettled_trade_ids:
        found.append((HealthStatus.DEGRADED, "unsettled_pnl"))
    if cfg.test_only or runtime.risk.engine.policy.test_only or \
            runtime.setup_config.test_only or runtime.technical_config.test_only:
        found.append((HealthStatus.DEGRADED, "test_only_configuration"))
    status = max((s for s, _ in found), key=_RANK.__getitem__, default=HealthStatus.HEALTHY)
    return HealthReport(status=status, reasons=tuple(sorted({r for _, r in found})),
                        breaker=breaker, runs_by_state=dict(sorted(by_state.items())),
                        reconciliation=report, checked_at=checked_at)
