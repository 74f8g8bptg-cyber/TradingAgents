"""The V1 PAPER orchestrator: one run from market data to a paper position, journaled.

```
Market Data (Phase 2) → Technical (Phase 5) → Research / debate (Phase 6)
 → Setup / Trader / TradeProposal (Phase 6b) → Risk (Phase 3) → OrderIntent (Phase 3)
 → Paper Broker (Phase 4) → position / trade / P&L (Phase 4) → journal / replay
```

**It coordinates; it does not decide.** Every decision is made by the component that owns it:
the desk decides setup and proposal, the Risk Engine decides APPROVED / REVIEW / REJECTED and
the only way to an ``OrderIntent`` is ``RiskService.authorize_intent``; the Paper Broker
decides acceptance, fills and closes, and re-confirms every fill through Phase 3. The
runtime builds no proposal, decision, intent, order, fill or approval itself (approvals are
typed inputs from any approval producer, never execution authority), never resets
the breaker, and has no LIVE / DEMO path (``ExecutionModeInput(mode="PAPER")`` only).

**Run identity.** ``run_id`` is a hash of the complete input: the request (instrument,
``as_of``, research collections, declared labels, calendar, operator inputs), the market data
actually read (series hash and quote), the workflow version and every configuration hash
(runtime, technical, research workflow, allowlist, validation, prompt registry, setup,
trader, risk policy and engine version, paper broker). The same input is the same run; any
change is a new run. The approval is not part of the identity: it is a later decision that
resumes a parked run.

**Checkpoints and resume.** Each stage writes ``run.stage.completed`` with its input
fingerprint, the state reached and its typed outputs. ``run`` with the same request:
- a finished run is returned as recorded (nothing is emitted);
- otherwise every checkpointed stage is loaded, not re-executed, and execution continues at
  the first stage without a checkpoint (``run.resumed``);
- a stage re-entered with a different fingerprint is refused (CHECKPOINT_CONFLICT), except
  SETUP when a parked run receives its approval.

A crash between a stage's side effect and its checkpoint is covered by the components' own
idempotency: journaled research steps and Trader answers are reused (no second LLM call), the
desk returns the journaled proposal, the Risk Engine returns the journaled evaluation for the
same fingerprint, the same ``intent_id`` returns the broker's journaled order, and published
reports are deduplicated here by id.

**Stale context.** The risk context is rebuilt from current state (journaled breaker, the
paper book, the run's market data and operator inputs) whenever it is used. Authorisation
refuses a context that no longer matches the evaluation (``ReevaluationRequired`` →
BLOCKED / STALE_CONTEXT), the breaker blocks (CIRCUIT_BREAKER_TRIPPED), and the broker
re-confirms at submission and at every fill.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from stellar.execution import CurrentAuthorisation, PaperBroker, PaperBrokerConfig
from stellar.execution.models import PaperOrder, PaperOrderStatus, trade_id_for
from stellar.execution.pricing import MarketInput
from stellar.execution.state import load_book
from stellar.journal import StellarJournal
from stellar.marketdata import (
    MarketDataError,
    MarketDataRequest,
    MarketDataResponse,
    MarketDataSource,
    QuoteResponse,
    VerifiedMarketSnapshot,
    build_verified_snapshot,
)
from stellar.pipeline import PipelineInputs, ResearchPipeline, WorkflowConfig
from stellar.pipeline.records import DecisionSupport, RunStatus
from stellar.proposals import ProposalFailure, load_proposal
from stellar.reasoning.prompts import registry_hash
from stellar.reasoning.provider import ReasoningProvider
from stellar.research import SourceAllowlist, ValidationConfig
from stellar.risk import RiskEngine, RiskService
from stellar.risk.breaker import BreakerStatus
from stellar.risk.engine import ENGINE_VERSION as RISK_ENGINE_VERSION, RiskEvaluation
from stellar.risk.intents import IntentRefused, ReevaluationRequired
from stellar.risk.state import ExecutionModeInput, RiskContext
from stellar.runtime.config import OperatorRiskInputs, RuntimeConfig, TakeProfitPolicy
from stellar.runtime.ledger import RunLedger
from stellar.runtime.models import (
    LIVE_ORDER_STATES,
    TERMINAL_STATES,
    RunRecord,
    RunRequest,
    RunStage,
    RunState,
    RuntimeFailure,
    StageCheckpoint,
)
from stellar.schemas.market import Quote
from stellar.schemas.order import OrderIntent
from stellar.schemas.proposal import TradeProposal
from stellar.schemas.risk import RiskOutcome
from stellar.serialization import content_hash
from stellar.setups import Setup, SetupConfig, SetupInputError
from stellar.technical import (
    ENGINE_VERSION as TECHNICAL_ENGINE_VERSION,
    TechnicalAnalysis,
    TechnicalConfig,
    TechnicalInputError,
    analyse,
    publish_technical_analysis,
)
from stellar.telemetry import EventBus, new_event
from stellar.trader import DeskFailure, OutcomeKind, TraderConfig, TraderDesk, TraderInputs

SOURCE = "stellar.runtime"

ORDER_STATE = {
    PaperOrderStatus.PENDING: RunState.PAPER_SUBMITTED,
    PaperOrderStatus.BLOCKED: RunState.ORDER_BLOCKED,
    PaperOrderStatus.FILLED: RunState.POSITION_OPEN,
    PaperOrderStatus.REJECTED: RunState.ORDER_REJECTED,
    PaperOrderStatus.CANCELLED: RunState.CANCELLED,
    PaperOrderStatus.EXPIRED: RunState.EXPIRED,
    PaperOrderStatus.PREFLIGHT_FAILED: RunState.BLOCKED,
}


class RuntimeConfigError(ValueError):
    """The runtime's configuration is inconsistent; nothing runs."""


class FutureRunError(ValueError):
    """A run was requested for a moment after the runtime clock (look-ahead); nothing runs."""


class RunNotActive(ValueError):
    """The run has no working order or open position to advance."""


class _Stop(Exception):
    """A stage ended the run (a stop state, not necessarily a failure)."""

    def __init__(self, checkpoint: StageCheckpoint) -> None:
        self.checkpoint = checkpoint


@dataclass
class _Market:
    response: MarketDataResponse | None
    quote: QuoteResponse | None
    snapshot: VerifiedMarketSnapshot | None
    error: str | None
    quote_error: str | None


class PaperRuntime:
    def __init__(self, *, journal: StellarJournal, market_source: MarketDataSource,
                 provider: ReasoningProvider, config: RuntimeConfig,
                 technical_config: TechnicalConfig, workflow: WorkflowConfig,
                 allowlist: SourceAllowlist, validation: ValidationConfig,
                 setup_config: SetupConfig, trader_config: TraderConfig | None = None,
                 risk_engine: RiskEngine, broker_config: PaperBrokerConfig, station_id: str,
                 account_opened_at: datetime,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.config = RuntimeConfig.model_validate(config.model_dump())
        if self.config.timeframe is None:
            raise RuntimeConfigError("the run timeframe is unset (a profile decision, D-7)")
        if self.config.profile and setup_config.profile and \
                self.config.profile != setup_config.profile:
            raise RuntimeConfigError("the runtime and setup profiles differ")
        self._journal = journal
        self._bus = EventBus(journal)
        self._source = market_source
        self._station = station_id
        self._clock = clock or (lambda: datetime.now(UTC))
        self.technical_config = technical_config
        self.setup_config = setup_config
        self.risk = RiskService(risk_engine, journal, station_id=station_id, clock=self._clock)
        self.broker = PaperBroker(broker_config, journal, self.risk, station_id=station_id,
                                  opened_at=account_opened_at)
        self.pipeline = ResearchPipeline(provider=provider, journal=journal, config=workflow,
                                         allowlist=allowlist, validation_config=validation,
                                         station_id=station_id, clock=self._clock)
        self.desk = TraderDesk(journal=journal, setup_config=setup_config,
                               trader_config=trader_config, provider=provider,
                               station_id=station_id, clock=self._clock)
        self.ledger = RunLedger(journal, station_id=station_id, clock=self._clock)
        self.config_hashes = {
            "runtime": self.config.config_hash(),
            "technical": technical_config.config_hash(),
            "technical_engine": content_hash(TECHNICAL_ENGINE_VERSION),
            "workflow": self.pipeline.config.config_hash(),
            "allowlist": allowlist.allowlist_hash(),
            "validation": validation.config_hash(),
            "prompts": registry_hash(),
            "setup": setup_config.config_hash(),
            "trader": self.desk.trader_config.config_hash(),
            "risk_policy": risk_engine.policy_hash,
            "risk_engine": content_hash(RISK_ENGINE_VERSION),
            "paper_broker": self.broker.config_hash,
        }

    # ================================================================= public ==

    def run(self, request: RunRequest) -> RunRecord:
        request = RunRequest.model_validate(request.model_dump())
        if request.as_of > self._clock():
            raise FutureRunError(f"as_of {request.as_of.isoformat()} is after the runtime "
                                 "clock: a run cannot describe a moment that has not happened")
        market = self._read_market(request.instrument, request.as_of, "run")
        run_id = self._run_id(request, market)
        existing = self.ledger.record(run_id)
        if existing is None:
            self.ledger.emit("run.started", run_id, {
                "instrument": request.instrument.value, "timeframe": self.config.timeframe.value,
                "profile": self.config.profile, "as_of": request.as_of.isoformat(),
                "workflow_version": self.config.workflow_version,
                "config_hashes": self.config_hashes,
                "operator": request.operator.model_dump(mode="json")},
                instrument=request.instrument.value)
        elif self.ledger.finished(run_id) or not self._has_work(existing, request):
            return self.status(run_id)
        _RunExecution(self, run_id, request, market, resumed=existing is not None).execute()
        return self.status(run_id)

    def status(self, run_id: str) -> RunRecord:
        """The run as the journal and the paper book describe it now (a pure read)."""
        record = self.ledger.record(run_id)
        if record is None:
            raise KeyError(f"unknown run {run_id}")
        order_id = record.refs.get("order_id")
        if order_id is None or record.state is RunState.FAILED:
            return record
        order = self.order(order_id)
        if order is None:
            return record
        closed = self.broker.state().closed_trades
        state = ORDER_STATE[order.status]
        refs = dict(record.refs)
        refs["order_status"] = order.status.value
        if order.position_id:
            refs["position_id"] = order.position_id
            trade_id = trade_id_for(order.position_id)
            if any(t.trade_id == trade_id for t in closed):
                refs["trade_id"] = trade_id
                state = RunState.COMPLETED
        detail = record.detail
        failure = record.failure
        if order.status in (PaperOrderStatus.BLOCKED, PaperOrderStatus.CANCELLED,
                            PaperOrderStatus.EXPIRED, PaperOrderStatus.REJECTED,
                            PaperOrderStatus.PREFLIGHT_FAILED) and order.reason:
            detail = order.reason
            if "breaker" in order.reason:
                failure = RuntimeFailure.CIRCUIT_BREAKER_TRIPPED
        return record.model_copy(update={"state": state, "refs": refs, "detail": detail,
                                         "failure": failure})

    def order(self, order_id: str) -> PaperOrder | None:
        """The paper order as the Phase 4 journal read model holds it."""
        return load_book(self._journal, self.broker.config.account_id).orders.get(order_id)

    def _stage_done(self, stage: RunStage) -> None:
        """Called after each stage checkpoint is journaled (a test hook for crash simulation;
        it does nothing in operation)."""

    def runs(self) -> list[RunRecord]:
        return [self.status(r) for r in self.ledger.run_ids()]

    def advance(self, run_id: str, trigger: MarketInput, *, as_of: datetime,
                reauthorise: bool = False,
                operator: OperatorRiskInputs | None = None) -> RunRecord:
        """Advance a submitted run's order / position with one market input (Phase 4
        ``process``). A working order fills only if ``reauthorise`` asks the Risk Engine for a
        current authorisation at ``as_of`` and it is APPROVED; otherwise it becomes BLOCKED
        when executable. The breaker, stops and targets are the broker's."""
        record = self.status(run_id)
        if record.state not in LIVE_ORDER_STATES:
            raise RunNotActive(f"{run_id} is {record.state.value}")
        operator = operator or self._operator(run_id)
        offered: list[CurrentAuthorisation] = []
        if reauthorise and record.state in (RunState.PAPER_SUBMITTED, RunState.ORDER_BLOCKED):
            auth = self._reauthorise(record, as_of, operator)
            if auth is not None:
                offered.append(auth)
        self.broker.process(trigger, as_of=as_of, conversions=operator.conversions,
                            authorisations=offered)
        return self._settle(run_id)

    def cancel(self, run_id: str, *, as_of: datetime) -> RunRecord:
        """Cancel the run's working (PENDING or BLOCKED) paper order (Phase 4 ``cancel``)."""
        record = self.status(run_id)
        if record.state not in (RunState.PAPER_SUBMITTED, RunState.ORDER_BLOCKED):
            raise RunNotActive(f"{run_id} has no working order")
        self.broker.cancel(record.refs["order_id"], as_of=as_of)
        return self._settle(run_id)

    def close(self, run_id: str, quote: Quote, *, as_of: datetime,
              operator: OperatorRiskInputs | None = None) -> RunRecord:
        """Manually close the run's open position at ``quote`` (Phase 4 ``close``)."""
        record = self.status(run_id)
        position_id = record.refs.get("position_id")
        if record.state is not RunState.POSITION_OPEN or position_id is None:
            raise RunNotActive(f"{run_id} has no open position")
        operator = operator or self._operator(run_id)
        self.broker.close(position_id, quote, as_of=as_of, conversions=operator.conversions)
        return self._settle(run_id)

    # ================================================================ helpers ==

    def _settle(self, run_id: str) -> RunRecord:
        record = self.status(run_id)
        if record.state in TERMINAL_STATES and not self.ledger.finished(run_id):
            self._finish(run_id, record.state, record.failure, record.detail,
                         instrument=record.instrument.value, refs=record.refs)
        return self.status(run_id)

    def _finish(self, run_id: str, state: RunState, failure: RuntimeFailure | None,
                detail: str | None, *, instrument: str, refs: dict) -> None:
        event = "run.failed" if state is RunState.FAILED else "run.completed"
        self.ledger.emit(event, run_id, {
            "state": state.value, "failure": failure.value if failure else None,
            "detail": detail, "refs": refs}, instrument=instrument)

    def _operator(self, run_id: str) -> OperatorRiskInputs:
        started = self.ledger.started(run_id)
        assert started is not None
        return OperatorRiskInputs.model_validate(started.payload["operator"])

    def _has_work(self, record: RunRecord, request: RunRequest) -> bool:
        if record.state in TERMINAL_STATES or record.state in LIVE_ORDER_STATES:
            return False
        if record.state is RunState.AWAITING_APPROVAL:
            return request.approval is not None or request.owner_selection is not None
        return True

    def _read_market(self, instrument, as_of: datetime, purpose: str) -> _Market:
        try:
            response = self._source.candles(MarketDataRequest(
                instrument=instrument, timeframe=self.config.timeframe, as_of=as_of))
        except MarketDataError as exc:
            return _Market(None, None, None, f"{exc.code.value.lower()}", None)
        quote, quote_error = None, None
        try:
            quote = self._source.quote(instrument, as_of)
        except MarketDataError as exc:
            quote_error = exc.code.value.lower()
        try:
            snapshot_id = "snap_" + content_hash({
                "series": response.series.content_hash if response.series else None,
                "quote": quote.model_dump(mode="json") if quote else None,
                "as_of": as_of.isoformat()})[:40]
            snapshot = build_verified_snapshot(response, snapshot_id=snapshot_id,
                                               created_at=as_of,
                                               config_hash=self.config.config_hash(),
                                               quote=quote)
        except MarketDataError as exc:
            return _Market(response, quote, None, exc.code.value.lower(), quote_error)
        return _Market(response, quote, snapshot, None, quote_error)

    def _run_id(self, request: RunRequest, market: _Market) -> str:
        identity = {
            "workflow": self.config.workflow_version, "request": request.identity(),
            "timeframe": self.config.timeframe.value, "configs": self.config_hashes,
            "market": {"error": market.error,
                       "series": market.snapshot.series_hash if market.snapshot else None,
                       "quote": market.quote.model_dump(mode="json") if market.quote else None,
                       "quote_error": market.quote_error}}
        return "run_" + content_hash(identity)[:40]

    def context(self, proposal: TradeProposal, *, as_of: datetime,
                snapshot: VerifiedMarketSnapshot | None, quote: QuoteResponse | None,
                operator: OperatorRiskInputs,
                excluding_order_id: str | None = None) -> RiskContext:
        """The current risk context: the paper book (Phase 4 read model, RK-11), the journaled
        breaker, the run's market data and the explicit operator inputs. Nothing estimated."""
        view = self.broker.risk_inputs(as_of, excluding_order_id=excluding_order_id)
        return RiskContext(
            as_of=as_of, proposal=proposal, execution=ExecutionModeInput(mode="PAPER"),
            breaker=self.risk.breaker.state(), account=view.account, daily=operator.daily,
            positions=view.positions, pending_orders=view.pending_orders, snapshot=snapshot,
            quote=quote, metadata=operator.metadata,
            requested_volume=operator.requested_volume, cooldowns=operator.cooldowns,
            event_restriction=operator.event_restriction,
            enabled_instruments=self.config.enabled_instruments,
            prior_idempotency_keys=view.prior_idempotency_keys)

    def intent_for(self, evaluation: RiskEvaluation, context: RiskContext, *,
                   created_at: datetime, suffix: str = "",
                   expires_at: datetime | None = None) -> OrderIntent:
        """Through ``RiskService.authorize_intent`` only. Raises ``IntentRefused`` /
        ``ReevaluationRequired`` (Phase 3) or ``RuntimeConfigError`` (no broker symbol)."""
        proposal = context.proposal
        symbol = self.config.broker_symbols.get(proposal.instrument)
        if symbol is None:
            raise RuntimeConfigError(f"no paper broker symbol for {proposal.instrument.value}")
        take_profit = proposal.take_profits[0].price \
            if self.config.take_profit is TakeProfitPolicy.NEAREST_PROPOSAL_TARGET else None
        intent_id = "int_" + content_hash({"proposal": proposal.proposal_id,
                                           "evaluation": evaluation.fingerprint,
                                           "suffix": suffix})[:40]
        return self.risk.authorize_intent(
            evaluation, context, intent_id=intent_id, broker_symbol=symbol,
            created_at=created_at, expires_at=expires_at or proposal.valid_until,
            take_profit=take_profit)

    def _reauthorise(self, record: RunRecord, as_of: datetime,
                     operator: OperatorRiskInputs) -> CurrentAuthorisation | None:
        """A fill-time authorisation for the run's working order, through Phase 3 only."""
        cps = self.ledger.checkpoints(record.run_id)
        proposal = load_proposal(cps[RunStage.PROPOSAL].outputs["proposal"])
        order_id = record.refs["order_id"]
        market = self._read_market(proposal.instrument, as_of, "reauthorise")
        context = self.context(proposal, as_of=as_of, snapshot=market.snapshot,
                               quote=market.quote, operator=operator,
                               excluding_order_id=order_id)
        evaluation = self.risk.evaluate(context)
        if evaluation.decision.outcome is not RiskOutcome.APPROVED:
            return None
        original = self.order(order_id).intent
        try:  # the same terms and expiry as the working order; only Phase 3 builds it
            intent = self.intent_for(evaluation, context, created_at=as_of,
                                     suffix=f"reauth:{order_id}",
                                     expires_at=original.expires_at)
        except (IntentRefused, ReevaluationRequired):
            return None
        return CurrentAuthorisation(order_id=order_id, intent=intent, context=context)


class _RunExecution:
    """One pass over the stages of one run."""

    def __init__(self, rt: PaperRuntime, run_id: str, request: RunRequest, market: _Market, *,
                 resumed: bool) -> None:
        self.rt, self.run_id, self.req, self.market = rt, run_id, request, market
        self.instrument = request.instrument.value
        self.resumed = resumed
        self.resume_emitted = False
        self.cps = rt.ledger.checkpoints(run_id)

    # --------------------------------------------------------------- plumbing --

    def cp(self, stage: RunStage, fingerprint: str, state: RunState, *,
           failure: RuntimeFailure | None = None, detail: str | None = None,
           refs: dict | None = None, outputs: dict | None = None) -> StageCheckpoint:
        return StageCheckpoint(run_id=self.run_id, stage=stage, fingerprint=fingerprint,
                               state=state, failure=failure,
                               detail=None if detail is None else str(detail)[:500],
                               refs=refs or {}, outputs=outputs or {})

    def stage(self, stage: RunStage, fingerprint: str,
              execute: Callable[[], StageCheckpoint], *, reenter: bool = False,
              force: bool = False) -> StageCheckpoint:
        existing = self.cps.get(stage)
        if existing is not None and not force and (existing.fingerprint == fingerprint
                                                   or not reenter):
            if existing.fingerprint != fingerprint and stage in (RunStage.MARKET_DATA,
                                                                 RunStage.TECHNICAL):
                raise _Stop(self.cp(stage, fingerprint, RunState.FAILED,
                                    failure=RuntimeFailure.CHECKPOINT_CONFLICT,
                                    detail=f"{stage.value}_fingerprint_changed"))
            if existing.state in TERMINAL_STATES | {RunState.AWAITING_APPROVAL}:
                raise _Stop(existing)
            return existing
        if self.resumed and not self.resume_emitted:
            self.rt.ledger.emit("run.resumed", self.run_id, {"from_stage": stage.value},
                                instrument=self.instrument)
            self.resume_emitted = True
        result = execute()
        stored = self.rt.ledger.checkpoint(result, instrument=self.instrument)
        self.cps[stored.stage] = stored
        self.rt._stage_done(stored.stage)  # noqa: SLF001 - test hook for crash simulation
        if stored.state in TERMINAL_STATES | {RunState.AWAITING_APPROVAL}:
            raise _Stop(stored)
        return stored

    def execute(self) -> None:
        try:
            self._execute()
        except _Stop as stop:
            cp = stop.checkpoint
            if cp.seq is None:  # a stop decided before writing (conflict): record it
                self.rt.ledger.checkpoint(cp, instrument=self.instrument)
            if cp.state in TERMINAL_STATES and not self.rt.ledger.finished(self.run_id):
                self.rt._finish(self.run_id, cp.state, cp.failure, cp.detail,  # noqa: SLF001
                                instrument=self.instrument,
                                refs=self.rt.ledger.record(self.run_id).refs)

    # ----------------------------------------------------------------- stages --

    def _execute(self) -> None:
        rt, req, m = self.rt, self.req, self.market
        # MARKET_DATA ---------------------------------------------------------------------
        fp_market = content_hash({"error": m.error,
                                  "snapshot": m.snapshot.snapshot_id if m.snapshot else None,
                                  "series": m.snapshot.series_hash if m.snapshot else None})
        market_cp = self.stage(RunStage.MARKET_DATA, fp_market, self._market_stage)
        snapshot = VerifiedMarketSnapshot.model_validate(market_cp.outputs["snapshot"])
        quote = QuoteResponse.model_validate(market_cp.outputs["quote"]) \
            if market_cp.outputs.get("quote") else None

        # TECHNICAL -----------------------------------------------------------------------
        fp_tech = content_hash({"series": snapshot.series_hash,
                                "config": rt.technical_config.config_hash(),
                                "engine": TECHNICAL_ENGINE_VERSION})
        tech_cp = self.stage(RunStage.TECHNICAL, fp_tech, lambda: self._technical(snapshot))
        technical = TechnicalAnalysis.model_validate(tech_cp.outputs["analysis"])

        # RESEARCH ------------------------------------------------------------------------
        fp_research = content_hash({"technical": technical.content_hash,
                                    "request": req.identity(), "configs": {
                                        k: rt.config_hashes[k] for k in
                                        ("workflow", "allowlist", "validation", "prompts")}})
        research_cp = self.stage(RunStage.RESEARCH, fp_research,
                                 lambda: self._research(technical))
        decision = DecisionSupport.model_validate(research_cp.outputs["decision"])

        # SETUP + PROPOSAL ----------------------------------------------------------------
        fp_setup = content_hash({
            "technical": technical.content_hash, "decision": decision.outputs_hash,
            "snapshot": snapshot.snapshot_id, "setup": rt.config_hashes["setup"],
            "trader": rt.config_hashes["trader"],
            "approval": req.approval.model_dump(mode="json") if req.approval else None,
            "selection": req.owner_selection.model_dump(mode="json")
            if req.owner_selection else None})
        parked = self.cps.get(RunStage.SETUP)
        reenter = parked is not None and parked.state is RunState.AWAITING_APPROVAL
        # A crash between the SETUP and PROPOSAL checkpoints: the desk is asked again and
        # returns the proposal it already journaled (Phase 6b idempotency).
        force = parked is not None and parked.state is RunState.SETUP_COMPLETE and \
            RunStage.PROPOSAL not in self.cps
        self.stage(RunStage.SETUP, fp_setup,
                   lambda: self._setup(fp_setup, technical, decision, snapshot),
                   reenter=reenter, force=force)
        proposal_cp = self.cps[RunStage.PROPOSAL]
        proposal = load_proposal(proposal_cp.outputs["proposal"])

        # RISK ----------------------------------------------------------------------------
        context = rt.context(proposal, as_of=req.as_of, snapshot=snapshot, quote=quote,
                             operator=req.operator)
        fp_risk = rt.risk.engine.fingerprint(rt.risk.current_context(context))
        risk_cp = self.stage(RunStage.RISK, fp_risk, lambda: self._risk(context))
        evaluation = next((e for e in rt.risk.evaluations_for(proposal.proposal_id)
                           if e.fingerprint == risk_cp.fingerprint), None)
        if evaluation is None:
            raise _Stop(self.cp(RunStage.RISK, risk_cp.fingerprint, RunState.FAILED,
                                failure=RuntimeFailure.CHECKPOINT_CONFLICT,
                                detail="risk_evaluation_not_in_journal"))

        # ORDER_AUTHORISATION -------------------------------------------------------------
        fp_auth = content_hash({"evaluation": evaluation.fingerprint,
                                "runtime": rt.config_hashes["runtime"]})
        auth_cp = self.stage(RunStage.ORDER_AUTHORISATION, fp_auth,
                             lambda: self._superseded(RunStage.ORDER_AUTHORISATION, fp_auth)
                             or self._authorise(fp_auth, evaluation, proposal, snapshot, quote))
        intent = OrderIntent.model_validate(auth_cp.outputs["intent"])

        # PAPER_SUBMISSION ----------------------------------------------------------------
        fp_submit = content_hash({"intent": intent.intent_id,
                                  "broker": rt.config_hashes["paper_broker"]})
        self.stage(RunStage.PAPER_SUBMISSION, fp_submit,
                   lambda: self._superseded(RunStage.PAPER_SUBMISSION, fp_submit)
                   or self._submit(fp_submit, intent, proposal, snapshot, quote))

    # ------------------------------------------------------------ stage bodies --

    def _superseded(self, stage: RunStage, fp: str) -> StageCheckpoint | None:
        """An unfinished run never authorises or submits once the paper world has moved past
        its moment: the paper book has processed a later input, or a later run for the same
        instrument (a newer market view) has started. BLOCKED / STALE_CONTEXT; a new run with
        current inputs is the only way forward. An approval or intent is never carried over."""
        rt, req = self.rt, self.req
        book_as_of = rt.broker.state().as_of
        if book_as_of is not None and book_as_of > req.as_of:
            return self.cp(stage, fp, RunState.BLOCKED, failure=RuntimeFailure.STALE_CONTEXT,
                           detail="paper_book_moved_past_as_of")
        started = rt.ledger.started(self.run_id)
        assert started is not None
        for event in rt._journal.read(since_seq=started.seq,  # noqa: SLF001
                                      types=["run.started"]):
            if event.payload.get("instrument") == self.instrument and \
                    event.payload["run_id"] != self.run_id and \
                    event.payload["as_of"] >= req.as_of.isoformat():
                return self.cp(stage, fp, RunState.BLOCKED,
                               failure=RuntimeFailure.STALE_CONTEXT,
                               detail=f"superseded_by_{event.payload['run_id']}")
        return None

    def _market_stage(self) -> StageCheckpoint:
        m = self.market
        fp = content_hash({"error": m.error,
                           "snapshot": m.snapshot.snapshot_id if m.snapshot else None,
                           "series": m.snapshot.series_hash if m.snapshot else None})
        if m.snapshot is None:
            return self.cp(RunStage.MARKET_DATA, fp, RunState.FAILED,
                           failure=RuntimeFailure.MARKET_DATA_FAILED, detail=m.error)
        self._publish_snapshot(m.snapshot)
        return self.cp(RunStage.MARKET_DATA, fp, RunState.MARKET_DATA_READY,
                       detail=m.quote_error and f"quote_unavailable_{m.quote_error}",
                       refs={"snapshot_id": m.snapshot.snapshot_id,
                             "series_hash": m.snapshot.series_hash},
                       outputs={"snapshot": m.snapshot.model_dump(mode="json"),
                                "quote": m.quote.model_dump(mode="json") if m.quote else None})

    def _publish_snapshot(self, snapshot: VerifiedMarketSnapshot) -> None:
        known = any(e.payload.get("snapshot_id") == snapshot.snapshot_id
                    for e in self.rt._journal.read(types=["snapshot.created"]))  # noqa: SLF001
        if not known:
            self.rt._bus.publish(new_event(  # noqa: SLF001
                "snapshot.created", station_id=self.rt._station, source=SOURCE,  # noqa: SLF001
                agent_id="market_data", instrument=snapshot.instrument,
                correlation_id=snapshot.snapshot_id, ts=self.rt._clock(),  # noqa: SLF001
                payload={"snapshot_id": snapshot.snapshot_id,
                         "timeframe": snapshot.timeframe.value,
                         "as_of": snapshot.as_of.isoformat(),
                         "series_hash": snapshot.series_hash,
                         "last_bar_close_time": snapshot.last_bar_close_time.isoformat(),
                         "freshness": snapshot.freshness.status.value,
                         "has_quote": snapshot.latest_quote is not None}))

    def _technical(self, snapshot: VerifiedMarketSnapshot) -> StageCheckpoint:
        rt = self.rt
        fp = content_hash({"series": snapshot.series_hash,
                           "config": rt.technical_config.config_hash(),
                           "engine": TECHNICAL_ENGINE_VERSION})
        assert self.market.response is not None
        try:
            analysis = analyse(self.market.response, as_of=self.req.as_of,
                               config=rt.technical_config, snapshot_id=snapshot.snapshot_id)
        except (TechnicalInputError, ValueError) as exc:
            return self.cp(RunStage.TECHNICAL, fp, RunState.FAILED,
                           failure=RuntimeFailure.TECHNICAL_FAILED, detail=str(exc))
        known = rt._journal.read(types=["analysis.created"])  # noqa: SLF001
        if not any(e.correlation_id == analysis.analysis_id for e in known):
            publish_technical_analysis(rt._journal, analysis, snapshot,  # noqa: SLF001
                                       station_id=rt._station,  # noqa: SLF001
                                       created_at=rt._clock())  # noqa: SLF001
        return self.cp(RunStage.TECHNICAL, fp, RunState.TECHNICAL_COMPLETE,
                       refs={"technical_analysis_id": analysis.analysis_id,
                             "technical_content_hash": analysis.content_hash},
                       outputs={"analysis": analysis.model_dump(mode="json")})

    def _research(self, technical: TechnicalAnalysis) -> StageCheckpoint:
        rt, req = self.rt, self.req
        fp = content_hash({"technical": technical.content_hash, "request": req.identity(),
                           "configs": {k: rt.config_hashes[k] for k in
                                       ("workflow", "allowlist", "validation", "prompts")}})
        try:
            decision = rt.pipeline.run(PipelineInputs(
                instrument=req.instrument, as_of=req.as_of, collections=req.collections,
                technical=(technical,), declared_labels=dict(req.declared_labels),
                calendar=req.calendar))
        except ValueError as exc:
            return self.cp(RunStage.RESEARCH, fp, RunState.FAILED,
                           failure=RuntimeFailure.RESEARCH_FAILED, detail=str(exc))
        refs = {"research_run_id": decision.run_id,
                "research_snapshot_id": decision.research_snapshot_id,
                "research_outputs_hash": decision.outputs_hash}
        outputs = {"decision": decision.model_dump(mode="json")}
        if decision.status is RunStatus.FAILED:
            failed = [s.role for s in decision.steps if s.status.value == "FAILED"]
            return self.cp(RunStage.RESEARCH, fp, RunState.FAILED,
                           failure=RuntimeFailure.RESEARCH_FAILED,
                           detail="research_run_failed:" + ",".join(failed),
                           refs=refs, outputs=outputs)
        return self.cp(RunStage.RESEARCH, fp, RunState.RESEARCH_COMPLETE, refs=refs,
                       outputs=outputs)

    def _setup(self, fp: str, technical: TechnicalAnalysis, decision: DecisionSupport,
               snapshot: VerifiedMarketSnapshot) -> StageCheckpoint:
        rt, req = self.rt, self.req
        if req.approval is not None:
            self._journal_approval(req)
        try:
            out = rt.desk.run(TraderInputs(technical=technical, decision=decision,
                                           market=snapshot, as_of=req.as_of,
                                           approval=req.approval,
                                           owner_selection=req.owner_selection))
        except (SetupInputError, ValueError) as exc:
            return self.cp(RunStage.SETUP, fp, RunState.FAILED,
                           failure=RuntimeFailure.SETUP_FAILED, detail=str(exc))
        setup: Setup = out.setup
        refs = {"setup_id": setup.setup_id, "setup_fingerprint": setup.fingerprint,
                "setup_status": setup.status.value}
        outputs: dict[str, Any] = {
            "setup": setup.model_dump(mode="json"), "outcome": out.kind.value,
            "desk_failure": out.failure.value if out.failure else None,
            "selection": out.selection.model_dump(mode="json") if out.selection else None}
        if out.kind is OutcomeKind.NO_SETUP:
            return self.cp(RunStage.SETUP, fp, RunState.NO_SETUP, detail=setup.status.value,
                           refs=refs, outputs=outputs)
        if out.kind is OutcomeKind.SETUP_CANDIDATE:
            built = out.proposal_outcome
            if out.failure is DeskFailure.PROPOSAL_REFUSED and built is not None:
                if built.failure is ProposalFailure.APPROVAL_REQUIRED:
                    return self.cp(RunStage.SETUP, fp, RunState.AWAITING_APPROVAL,
                                   detail="approval_required", refs=refs, outputs=outputs)
                return self.cp(RunStage.SETUP, fp, RunState.SETUP_CANDIDATE,
                               failure=RuntimeFailure.PROPOSAL_FAILED,
                               detail=built.failure.value if built.failure else None,
                               refs=refs, outputs=outputs)
            failure = RuntimeFailure.SETUP_FAILED if out.failure is DeskFailure.TRADER_FAILED \
                else None
            detail = out.failure.value if out.failure else setup.status.value
            if out.detail:
                detail = f"{detail}:{out.detail}"
            return self.cp(RunStage.SETUP, fp, RunState.SETUP_CANDIDATE, failure=failure,
                           detail=detail, refs=refs, outputs=outputs)
        proposal = out.proposal
        assert proposal is not None
        done = self.cp(RunStage.SETUP, fp, RunState.SETUP_COMPLETE, refs=refs, outputs=outputs)
        stored = rt.ledger.checkpoint(done, instrument=self.instrument)
        self.cps[RunStage.SETUP] = stored
        rt._stage_done(RunStage.SETUP)  # noqa: SLF001 - test hook for crash simulation
        proposal_cp = self.cp(RunStage.PROPOSAL, content_hash(proposal.model_dump(mode="json")),
                              RunState.PROPOSAL_CREATED,
                              refs={"proposal_id": proposal.proposal_id,
                                    "direction": proposal.direction.value},
                              outputs={"proposal": proposal.model_dump(mode="json")})
        return proposal_cp

    def _journal_approval(self, req: RunRequest) -> None:
        approval = req.approval
        assert approval is not None
        digest = content_hash(approval.model_dump(mode="json"))
        known = any(e.payload.get("approval_hash") == digest and e.run_id == self.run_id
                    for e in self.rt._journal.read(types=["decision.final.created"]))  # noqa: SLF001
        if not known:
            self.rt.ledger.emit("decision.final.created", self.run_id, {
                "approval_hash": digest, "setup_id": approval.setup_id,
                "direction": approval.direction.value, "rating": approval.rating.value,
                "source": approval.source.value, "approval": approval.model_dump(mode="json")},
                instrument=self.instrument)

    def _risk(self, context: RiskContext) -> StageCheckpoint:
        rt = self.rt
        fp = rt.risk.engine.fingerprint(rt.risk.current_context(context))
        try:
            evaluation = rt.risk.evaluate(context)
        except ValueError as exc:
            return self.cp(RunStage.RISK, fp, RunState.FAILED,
                           failure=RuntimeFailure.RISK_FAILED, detail=str(exc))
        decision = evaluation.decision
        refs = {"decision_id": decision.decision_id,
                "risk_fingerprint": evaluation.fingerprint, "risk_outcome": decision.outcome.value}
        outputs = {"reasons": [r.value for r in decision.reasons],
                   "unresolved": [r.check for r in evaluation.results
                                  if r.status.value in ("REVIEW", "NOT_CONFIGURED", "FAIL")],
                   "volume": None if decision.volume is None else str(decision.volume)}
        detail = ",".join(outputs["reasons"]) or None
        if decision.outcome is RiskOutcome.REVIEW:
            return self.cp(RunStage.RISK, evaluation.fingerprint, RunState.REVIEW_REQUIRED,
                           failure=RuntimeFailure.RISK_REVIEW_REQUIRED, detail=detail,
                           refs=refs, outputs=outputs)
        if decision.outcome is RiskOutcome.REJECTED:
            tripped = rt.risk.breaker.state().status is BreakerStatus.TRIPPED
            return self.cp(RunStage.RISK, evaluation.fingerprint, RunState.REJECTED,
                           failure=RuntimeFailure.CIRCUIT_BREAKER_TRIPPED if tripped
                           else RuntimeFailure.RISK_REJECTED, detail=detail, refs=refs,
                           outputs=outputs)
        return self.cp(RunStage.RISK, evaluation.fingerprint, RunState.RISK_REVIEWED, refs=refs,
                       outputs=outputs)

    def _authorise(self, fp: str, evaluation: RiskEvaluation, proposal: TradeProposal,
                   snapshot, quote) -> StageCheckpoint:
        rt, req = self.rt, self.req
        context = rt.context(proposal, as_of=req.as_of, snapshot=snapshot, quote=quote,
                             operator=req.operator)
        try:
            intent = rt.intent_for(evaluation, context, created_at=req.as_of)
        except RuntimeConfigError as exc:
            return self.cp(RunStage.ORDER_AUTHORISATION, fp, RunState.FAILED,
                           failure=RuntimeFailure.ORDER_AUTHORISATION_FAILED, detail=str(exc))
        except ReevaluationRequired as exc:
            return self.cp(RunStage.ORDER_AUTHORISATION, fp, RunState.BLOCKED,
                           failure=RuntimeFailure.STALE_CONTEXT, detail=str(exc))
        except IntentRefused as exc:
            tripped = rt.risk.breaker.state().status is BreakerStatus.TRIPPED
            return self.cp(RunStage.ORDER_AUTHORISATION, fp, RunState.BLOCKED,
                           failure=RuntimeFailure.CIRCUIT_BREAKER_TRIPPED if tripped
                           else RuntimeFailure.ORDER_AUTHORISATION_FAILED, detail=str(exc))
        return self.cp(RunStage.ORDER_AUTHORISATION, fp, RunState.ORDER_AUTHORISED,
                       refs={"intent_id": intent.intent_id, "side": intent.side.value},
                       outputs={"intent": intent.model_dump(mode="json")})

    def _submit(self, fp: str, intent: OrderIntent, proposal: TradeProposal, snapshot,
                quote) -> StageCheckpoint:
        rt, req = self.rt, self.req
        context = rt.context(proposal, as_of=req.as_of, snapshot=snapshot, quote=quote,
                             operator=req.operator)
        try:
            result = rt.broker.submit(intent, context, as_of=req.as_of,
                                      market=quote.quote if quote else None,
                                      conversions=req.operator.conversions)
        except ValueError as exc:
            return self.cp(RunStage.PAPER_SUBMISSION, fp, RunState.FAILED,
                           failure=RuntimeFailure.PAPER_BROKER_FAILED,
                           detail=f"{type(exc).__name__}:{exc}")
        order = rt.order(result.order_id)
        state = ORDER_STATE[order.status]
        refs = {"order_id": order.order_id, "order_status": order.status.value,
                "position_id": order.position_id}
        failure = None
        if order.status is PaperOrderStatus.PREFLIGHT_FAILED:
            failure = RuntimeFailure.CIRCUIT_BREAKER_TRIPPED if order.reason and \
                "breaker" in order.reason else RuntimeFailure.PAPER_PREFLIGHT_FAILED
        return self.cp(RunStage.PAPER_SUBMISSION, fp, state, failure=failure,
                       detail=order.reason, refs=refs,
                       outputs={"execution": result.model_dump(mode="json")})


def runs_by_state(records: Sequence[RunRecord]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in records:
        out[r.state.value] = out.get(r.state.value, 0) + 1
    return out
