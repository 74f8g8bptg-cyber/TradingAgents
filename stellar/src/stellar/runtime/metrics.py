"""Operational metrics of V1 PAPER runs, folded from the journal.

Safe, descriptive counts and durations only: runs by state, stage durations, LLM calls,
attempts (retries), token and cost metadata when a provider reported it, paper submissions
and execution failures. **No** strategy performance, ranking or profitability figure is
computed here (that is simulation / attribution work, not Phase 7 orchestration).

Durations are the journal time between a stage's checkpoint and the run's previous event,
in milliseconds: they measure this process, not the market.
"""

from __future__ import annotations

from decimal import Decimal

from stellar.journal import StellarJournal
from stellar.runtime.ledger import RunLedger
from stellar.runtime.models import STAGE_ORDER, RunState
from stellar.schemas.common import StellarModel


class StageTiming(StellarModel):
    count: int = 0
    total_ms: int = 0
    max_ms: int = 0


class LlmTotals(StellarModel):
    calls: int = 0
    attempts: int = 0
    retries: int = 0
    failed: int = 0
    input_tokens: int | None = 0
    output_tokens: int | None = 0
    cost: Decimal | None = Decimal(0)
    cost_currency: str | None = None


class RuntimeMetrics(StellarModel):
    runs: int
    by_state: dict[str, int]
    completed: int
    no_setup: int
    review_required: int
    rejected: int
    failed: int
    paper_submissions: int
    execution_failures: int
    stages: dict[str, StageTiming]
    llm: LlmTotals


def _sum(a, b):
    return None if a is None or b is None else a + b


def runtime_metrics(journal: StellarJournal, runtime) -> RuntimeMetrics:
    ledger: RunLedger = runtime.ledger
    records = runtime.runs()
    by_state: dict[str, int] = {}
    for r in records:
        by_state[r.state.value] = by_state.get(r.state.value, 0) + 1
    stages = {s.value: StageTiming() for s in STAGE_ORDER}
    submissions = 0
    for r in records:
        previous = r.started_at
        events = [e for e in ledger.events(r.run_id) if e.type == "run.stage.completed"]
        for e in events:
            ms = int((e.ts - previous).total_seconds() * 1000) if previous else 0
            t = stages[e.payload["stage"]]
            stages[e.payload["stage"]] = StageTiming(count=t.count + 1, total_ms=t.total_ms + ms,
                                                     max_ms=max(t.max_ms, ms))
            previous = e.ts
            if e.payload["stage"] == "PAPER_SUBMISSION":
                submissions += 1
    llm = LlmTotals()
    currencies: set[str] = set()
    for e in journal.read(types=["agent.llm_call.completed"]):
        call = e.payload.get("call") or {}
        usage = call.get("usage") or {}
        attempts = int(call.get("attempts") or 0)
        cost = usage.get("cost")
        if usage.get("cost_currency"):
            currencies.add(usage["cost_currency"])
        llm = LlmTotals(
            calls=llm.calls + 1, attempts=llm.attempts + attempts,
            retries=llm.retries + max(attempts - 1, 0),
            failed=llm.failed + (call.get("status") == "FAILED"),
            input_tokens=_sum(llm.input_tokens, usage.get("input_tokens")),
            output_tokens=_sum(llm.output_tokens, usage.get("output_tokens")),
            cost=_sum(llm.cost, None if cost is None else Decimal(str(cost))))
    if len(currencies) > 1:
        llm = llm.model_copy(update={"cost": None})
    elif currencies:
        llm = llm.model_copy(update={"cost_currency": currencies.pop()})
    elif llm.calls:
        llm = llm.model_copy(update={"cost": None})
    preflight = len(journal.read(types=["order.preflight.failed"]))
    rejected_orders = len(journal.read(types=["order.rejected"]))
    return RuntimeMetrics(
        runs=len(records), by_state=dict(sorted(by_state.items())),
        completed=by_state.get(RunState.COMPLETED.value, 0),
        no_setup=by_state.get(RunState.NO_SETUP.value, 0),
        review_required=by_state.get(RunState.REVIEW_REQUIRED.value, 0),
        rejected=by_state.get(RunState.REJECTED.value, 0),
        failed=by_state.get(RunState.FAILED.value, 0), paper_submissions=submissions,
        execution_failures=preflight + rejected_orders, stages=stages, llm=llm)
