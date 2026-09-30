"""The Phase 6b trader desk: setup → level selection → Trade Proposal (Foundation §4.13).

```
SetupEvaluator (T6, deterministic)       evaluate_setup → Setup; lifecycle journaled
 → selection                              owner ids | single option per role | U4 Trader (LLM)
 → ProposalBuilder (P1, deterministic)    build_proposal → TradeProposal or a typed refusal
 → journal                                trade.proposed; setup ARMED → PROPOSED
```
The next step, outside this layer, is the Phase 3 Risk Engine. The desk never calls it, never
builds a risk decision, an order intent or an order, and never touches the Paper Broker, the
breaker, account state or configuration.

**Outcomes** (``OutcomeKind``):
- NO_SETUP: the setup is NO_SETUP, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE, INVALIDATED or
  EXPIRED (the ``setup`` record says which, and why);
- SETUP_CANDIDATE: a CANDIDATE setup, or a READY one without a proposal (``failure`` says why:
  no selection, the Trader declined or failed, no approval, a builder refusal …);
- TRADE_PROPOSAL: a proposal was built (or the same one was already built).

**Selection.** Levels are chosen by id only:
1. an owner ``LevelSelection``, if given;
2. otherwise, when every role has exactly one option, that option (nothing to choose);
3. otherwise the U4 Trader, when its LLM is enabled with a budget; its typed answer is
   checked (same setup and direction, offered ids only, right roles);
4. otherwise SELECTION_REQUIRED. Several targets are never reduced to one silently (RK-9).

**Idempotency.** The Trader call is checkpointed by fingerprint (``agent.task.completed``);
the same question is never paid for twice. A proposal is journaled once per proposal id. A
setup that already has a proposal gets no second one; the same evidence returns the
journaled proposal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from stellar.journal import StellarJournal
from stellar.marketdata.snapshot import VerifiedMarketSnapshot
from stellar.pipeline.records import DecisionSupport, StepRecord, StepStatus
from stellar.proposals import (
    Approval,
    LevelSelection,
    ProposalOutcome,
    ProposalStatus,
    SelectionSource,
    build_proposal,
    load_proposal,
)
from stellar.reasoning.provider import FailureKind, ReasoningProvider
from stellar.reasoning.structured import AgentCallRecord, CallStatus, call_structured, fingerprint
from stellar.schemas.common import Label, StellarModel
from stellar.schemas.proposal import TradeProposal
from stellar.setups import (
    LevelRole,
    LifecycleResult,
    Setup,
    SetupBook,
    SetupConfig,
    SetupState,
    SetupStatus,
    evaluate_setup,
)
from stellar.technical import MultiTimeframeAnalysis, TechnicalAnalysis
from stellar.telemetry import EventBus, new_event
from stellar.trader.contracts import (
    TRADER_ROLE,
    TRADER_TEMPLATE,
    TraderConfig,
    TraderDecision,
    TraderSelectionOutput,
)

SOURCE = "stellar.trader"


class OutcomeKind(StrEnum):
    NO_SETUP = "NO_SETUP"
    SETUP_CANDIDATE = "SETUP_CANDIDATE"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"


class DeskFailure(StrEnum):
    SETUP_NOT_READY = "setup_not_ready"
    LIFECYCLE_REFUSED = "lifecycle_refused"
    SETUP_ALREADY_PROPOSED = "setup_already_proposed"
    SELECTION_REQUIRED = "selection_required"
    TRADER_FAILED = "trader_failed"
    TRADER_DECLINED = "trader_declined"
    PROPOSAL_REFUSED = "proposal_refused"


class TraderOutcome(StellarModel):
    kind: OutcomeKind
    setup: Setup
    lifecycle: LifecycleResult
    selection: LevelSelection | None = None
    trader_step: StepRecord | None = None
    trader_output: TraderSelectionOutput | None = None
    proposal_outcome: ProposalOutcome | None = None
    proposal: TradeProposal | None = None
    failure: DeskFailure | None = None
    detail: Label | None = None


@dataclass(frozen=True)
class TraderInputs:
    technical: TechnicalAnalysis
    decision: DecisionSupport
    market: VerifiedMarketSnapshot
    as_of: datetime
    mtf: MultiTimeframeAnalysis | None = None
    approval: Approval | None = None
    owner_selection: LevelSelection | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if self.owner_selection is not None and \
                self.owner_selection.source is not SelectionSource.OWNER:
            raise ValueError("an owner selection must say it comes from the owner")


def single_option_selection(setup: Setup) -> LevelSelection | None:
    """The selection when each role has exactly one option; otherwise None."""
    entries, stops, targets = (setup.options_for(r) for r in LevelRole)
    if len(entries) == len(stops) == len(targets) == 1:
        return LevelSelection(setup_id=setup.setup_id, setup_fingerprint=setup.fingerprint,
                              entry_option_id=entries[0].option_id,
                              stop_option_id=stops[0].option_id,
                              target_option_ids=(targets[0].option_id,),
                              source=SelectionSource.SINGLE_OPTION)
    return None


def trader_task(setup: Setup) -> tuple[dict[str, Any], set[str]]:
    """The Trader's trusted, typed task and the ids it may cite."""
    options = [{"option_id": o.option_id, "role": o.role.value, "kind": o.kind.value,
                "price": None if o.price is None else str(o.price),
                "zone_low": None if o.zone_low is None else str(o.zone_low),
                "zone_high": None if o.zone_high is None else str(o.zone_high),
                "atr_distance": None if o.atr_distance is None else str(o.atr_distance),
                "basis": o.basis, "evidence_ids": list(o.evidence_ids)} for o in setup.options]
    ev = setup.evidence
    task = {"task": "select_levels",
            "setup": {"setup_id": setup.setup_id, "instrument": setup.instrument.value,
                      "timeframe": setup.timeframe.value, "setup_type": setup.setup_type.value,
                      "direction": setup.direction.value, "status": setup.status.value,
                      "invalidation_level": str(setup.invalidation_level),
                      "invalidation_evidence_id": setup.invalidation_evidence_id,
                      "valid_until": setup.valid_until.isoformat() if setup.valid_until else None,
                      "limitations": list(setup.limitations)},
            "options": options,
            "research": {"run_id": ev.run_id, "final_stance": ev.final_stance.value,
                         "evidence_grade": ev.evidence_grade.value,
                         "challenge_kinds": [k.value for k in ev.challenge_kinds]}}
    allowed = {o.option_id for o in setup.options} | \
        {e for o in setup.options for e in o.evidence_ids}
    allowed |= {x for x in (setup.reference_leg_id, setup.invalidation_evidence_id) if x}
    return task, allowed


def check_selection(setup: Setup, output: TraderSelectionOutput) -> str | None:
    """Why a schema-valid Trader answer is still unusable (None when usable)."""
    if output.setup_id != setup.setup_id:
        return "wrong_setup"
    if output.direction is not setup.direction:
        return "direction_mismatch"
    if output.decision is TraderDecision.DECLINE:
        return None
    wanted = [(output.entry_option_id, LevelRole.ENTRY), (output.stop_option_id, LevelRole.STOP),
              *((t, LevelRole.TARGET) for t in output.target_option_ids)]
    for option_id, role in wanted:
        option = setup.option(option_id or "")
        if option is None:
            return "not_an_option"
        if option.role is not role:
            return "option_role_mismatch"
    return None


class TraderDesk:
    def __init__(self, *, journal: StellarJournal, setup_config: SetupConfig,
                 trader_config: TraderConfig | None = None,
                 provider: ReasoningProvider | None = None, station_id: str,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._journal = journal
        self._bus = EventBus(journal)
        self.setup_config = SetupConfig.model_validate(setup_config.model_dump())
        self.trader_config = TraderConfig.model_validate(
            (trader_config or TraderConfig()).model_dump())
        if self.trader_config.llm_enabled and provider is None:
            raise ValueError("an enabled Trader LLM needs a provider")
        self._provider = provider
        self._station = station_id
        self._clock = clock or (lambda: datetime.now(UTC))
        self.book = SetupBook(journal, station_id=station_id, clock=self._clock)

    # ------------------------------------------------------------------ events --

    def _emit(self, event_type: str, setup: Setup, payload: dict[str, Any]) -> None:
        self._bus.publish(new_event(
            event_type, station_id=self._station, source=SOURCE, agent_id=TRADER_ROLE
            if not event_type.startswith("trade.") else "trade_proposal_builder",
            instrument=setup.instrument, correlation_id=setup.evidence.run_id, ts=self._clock(),
            payload={"setup_id": setup.setup_id, "setup_fingerprint": setup.fingerprint,
                     **payload}))

    def journaled_proposal(self, setup_id: str) -> dict[str, Any] | None:
        for event in reversed(self._journal.read(types=["trade.proposed"])):
            if event.payload.get("setup_id") == setup_id:
                return event.payload
        return None

    # --------------------------------------------------------------------- run --

    def run(self, inputs: TraderInputs) -> TraderOutcome:
        setup = evaluate_setup(technical=inputs.technical, decision=inputs.decision,
                               as_of=inputs.as_of, config=self.setup_config, mtf=inputs.mtf)
        life = self.book.record(setup)
        base = {"setup": setup, "lifecycle": life}
        if life.state is SetupState.PROPOSED:
            stored = self.journaled_proposal(setup.setup_id)
            if stored is not None and stored.get("setup_fingerprint") == setup.fingerprint:
                proposal = load_proposal(stored["proposal"])
                return TraderOutcome(kind=OutcomeKind.TRADE_PROPOSAL, proposal=proposal, **base)
            return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE,
                                 failure=DeskFailure.SETUP_ALREADY_PROPOSED, **base)
        if life.refused:
            kind = OutcomeKind.SETUP_CANDIDATE if setup.status in (
                SetupStatus.CANDIDATE, SetupStatus.READY_FOR_PROPOSAL) else OutcomeKind.NO_SETUP
            return TraderOutcome(kind=kind, failure=DeskFailure.LIFECYCLE_REFUSED,
                                 detail=life.rule, **base)
        if setup.status is SetupStatus.CANDIDATE:
            return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE,
                                 failure=DeskFailure.SETUP_NOT_READY, **base)
        if setup.status is not SetupStatus.READY_FOR_PROPOSAL:
            return TraderOutcome(kind=OutcomeKind.NO_SETUP, **base)

        step = output = None
        selection = inputs.owner_selection or single_option_selection(setup)
        if selection is None:
            if not self.trader_config.llm_enabled:
                return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE,
                                     failure=DeskFailure.SELECTION_REQUIRED, **base)
            output, step = self._trader(setup, inputs.as_of)
            if output is None:
                return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE, trader_step=step,
                                     failure=DeskFailure.TRADER_FAILED, detail=step.reason,
                                     **base)
            if output.decision is TraderDecision.DECLINE:
                return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE, trader_step=step,
                                     trader_output=output, failure=DeskFailure.TRADER_DECLINED,
                                     **base)
            assert output.entry_option_id and output.stop_option_id
            selection = LevelSelection(
                setup_id=setup.setup_id, setup_fingerprint=setup.fingerprint,
                entry_option_id=output.entry_option_id, stop_option_id=output.stop_option_id,
                target_option_ids=output.target_option_ids, source=SelectionSource.TRADER)
        extra = {"selection": selection, "trader_step": step, "trader_output": output}
        built = build_proposal(setup=setup, selection=selection, approval=inputs.approval,
                               market=inputs.market, config=self.setup_config,
                               created_at=inputs.as_of)
        if built.status is not ProposalStatus.BUILT:
            return TraderOutcome(kind=OutcomeKind.SETUP_CANDIDATE, proposal_outcome=built,
                                 failure=DeskFailure.PROPOSAL_REFUSED,
                                 detail=built.failure.value if built.failure else None,
                                 **extra, **base)
        proposal = built.proposal
        assert proposal is not None
        known = any(e.payload.get("proposal_id") == proposal.proposal_id
                    for e in self._journal.read(types=["trade.proposed"]))
        if not known:
            self._emit("trade.proposed", setup, {
                "proposal_id": proposal.proposal_id, "instrument": proposal.instrument.value,
                "direction": proposal.direction.value, "proposal_hash": built.proposal_hash,
                "selection": selection.model_dump(mode="json"),
                "approval": inputs.approval.model_dump(mode="json") if inputs.approval else None,
                "proposal": proposal.model_dump(mode="json")})
        life = self.book.mark_proposed(setup, proposal.proposal_id)
        return TraderOutcome(kind=OutcomeKind.TRADE_PROPOSAL, proposal_outcome=built,
                             proposal=proposal, **extra, setup=setup, lifecycle=life)

    # ------------------------------------------------------------------ U4 call --

    def _checkpoint(self, fp: str) -> dict[str, Any] | None:
        for event in reversed(self._journal.read(types=["agent.task.completed"])):
            if event.source == SOURCE and event.payload.get("role") == TRADER_ROLE and \
                    event.payload.get("fingerprint") == fp:
                return event.payload
        return None

    def _trader(self, setup: Setup, as_of: datetime
                ) -> tuple[TraderSelectionOutput | None, StepRecord]:
        cfg = self.trader_config
        assert cfg.model is not None and cfg.budget is not None and self._provider is not None
        trusted, allowed = trader_task(setup)
        fp = fingerprint(TRADER_TEMPLATE, cfg.model, as_of, trusted, ())
        stored = self._checkpoint(fp)
        if stored is not None:
            output = TraderSelectionOutput.model_validate(stored["output"])
            return output, StepRecord(role=TRADER_ROLE, status=StepStatus.REUSED, fingerprint=fp,
                                      call=AgentCallRecord.model_validate(stored["call"]),
                                      output_hash=stored["output_hash"])
        run_id = setup.evidence.run_id
        self._emit("agent.task.started", setup, {"role": TRADER_ROLE, "fingerprint": fp})
        self._emit("agent.llm_call.started", setup, {
            "role": TRADER_ROLE, "fingerprint": fp, "model": cfg.model.model_dump(mode="json"),
            "prompt_version": TRADER_TEMPLATE.version})
        output, record = call_structured(
            self._provider, TRADER_TEMPLATE, role=TRADER_ROLE, model=cfg.model, as_of=as_of,
            trusted=trusted, untrusted=(), schema=TraderSelectionOutput, allowed_evidence=allowed,
            max_attempts=min(cfg.max_attempts, cfg.budget.max_calls_per_run), run_id=run_id,
            timeout_seconds=cfg.timeout_seconds)
        self._emit("agent.llm_call.completed", setup, {"role": TRADER_ROLE, "fingerprint": fp,
                                                       "call": record.model_dump(mode="json")})
        if output is not None:
            problem = check_selection(setup, output)
            if problem is not None:
                record = record.model_copy(update={
                    "status": CallStatus.FAILED, "failure": FailureKind.MALFORMED_OUTPUT,
                    "failure_detail": problem, "output_hash": None})
                output = None
        if output is None:
            reason = record.failure_detail or (record.failure.value if record.failure
                                               else "malformed")
            self._emit("agent.task.failed", setup, {
                "role": TRADER_ROLE, "fingerprint": fp,
                "failure": (record.failure or FailureKind.MALFORMED_OUTPUT).value,
                "reason": reason, "call": record.model_dump(mode="json")})
            return None, StepRecord(role=TRADER_ROLE, status=StepStatus.FAILED, reason=reason,
                                    failure=record.failure, fingerprint=fp, call=record)
        data = output.model_dump(mode="json")
        self._emit("agent.task.completed", setup, {
            "role": TRADER_ROLE, "fingerprint": fp, "output": data,
            "output_hash": record.output_hash, "call": record.model_dump(mode="json")})
        self._emit("decision.trader_plan.created", setup, {
            "decision": output.decision.value, "direction": output.direction.value,
            "entry_option_id": output.entry_option_id, "stop_option_id": output.stop_option_id,
            "target_option_ids": list(output.target_option_ids), "fingerprint": fp})
        return output, StepRecord(role=TRADER_ROLE, status=StepStatus.COMPLETED, fingerprint=fp,
                                  call=record, output_hash=record.output_hash)
