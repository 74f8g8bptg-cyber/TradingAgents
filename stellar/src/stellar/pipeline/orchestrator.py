"""The Phase 6 research / debate pipeline (Foundation §4.29; decision support only).

**Stages** (fixed order and dependencies; the workflow config decides only enablement):
```
V4 claim_classifier (LLM, only for claims without declared labels)
 → research validation V1–V3 + corroboration + snapshot (deterministic)
 → evidence pool (research claims + Phase 5 technical evidence, point in time)
 → M1 causal_macro_analyst (LLM)
 → S* specialist of the focus instrument (LLM)          needs M1
 → U1 bull_researcher / U2 bear_researcher (LLM)          need the specialist view
 → P2 contradiction_checker (deterministic)
 → U3 research_manager (LLM)                               needs both debate sides
 → evidence quality + stance guards (deterministic)
 → DecisionSupport
```

**No privileges.** No stage can create a proposal, decision, intent or order, change risk
policy, touch the breaker or the broker, or change configuration. A model's answer is used
only through its typed fields.

**Checkpoints and idempotency.**
- Every stage has a fingerprint: role, prompt template hash, model, schema, ``as_of`` and
  the exact inputs.
- A completed result is journaled (``agent.task.completed`` with the fingerprint and
  output). A later run with the same fingerprint reuses it (REUSED, no provider call). A
  failed step is never reused.
- Any change of evidence, prompt, model, config or ``as_of`` changes the fingerprint and runs
  the step again. Nothing is overwritten: the journal is append-only.

**Budget (D-11).** LLM stages run only when enabled with an explicit budget (a call count).
Attempts count against it; when it is spent, a stage fails with BUDGET_EXHAUSTED instead of
calling. Usage (tokens, cost, latency) is recorded when the provider reports it.

**Events** (existing names only):
- ``agent.task.started`` / ``completed`` / ``failed`` per stage;
- ``agent.llm_call.started`` / ``completed`` per call;
- ``research.*`` for the snapshot;
- ``analysis.created`` for the macro and market assessments;
- ``debate.started``, ``debate.turn.completed``, ``debate.completed``;
- ``decision.research_plan.created`` for the synthesis.

All carry the run id as correlation. Re-running the same run (same inputs, after a crash
for example) emits no descriptive event that is already journaled for it (Phase 7).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from stellar.journal import StellarJournal
from stellar.pipeline.challenger import challenge, check_output
from stellar.pipeline.config import LLM_ROLES, SPECIALISTS, WorkflowConfig
from stellar.pipeline.evidence import EvidenceItem, EvidenceKind, EvidencePool, build_pool
from stellar.pipeline.quality import evidence_quality, guard_stance
from stellar.pipeline.records import (
    ChallengeReport,
    DecisionSupport,
    MacroAssessment,
    MarketView,
    RunStatus,
    StepRecord,
    StepStatus,
    Synthesis,
    TechnicalRef,
)
from stellar.reasoning.contracts import (
    ClaimLabelling,
    DebateCaseOutput,
    DebateSide,
    MacroAssessmentOutput,
    MarketViewOutput,
    Stance,
    SynthesisOutput,
)
from stellar.reasoning.prompts import TEMPLATES, PromptTemplate, registry_hash
from stellar.reasoning.provider import FailureKind, ReasoningProvider, UntrustedBlock
from stellar.reasoning.structured import AgentCallRecord, CallStatus, call_structured, fingerprint
from stellar.research import (
    CalendarValue,
    CollectionResult,
    CollectionStatus,
    ResearchSnapshot,
    SourceAllowlist,
    ValidationConfig,
    assess_claims,
    build_snapshot,
    publish_snapshot,
    validate_claims,
)
from stellar.schemas.analysis import AnalysisKind, AnalysisReport, Coverage
from stellar.schemas.common import InstrumentId, Provenance
from stellar.schemas.research import ClaimLabel, ResearchItem, ResearchRole
from stellar.serialization import content_hash, sha256_hex
from stellar.technical import MultiTimeframeAnalysis, TechnicalAnalysis
from stellar.telemetry import EventBus, new_event

SOURCE = "stellar.pipeline"
DESCRIPTIVE_EVENTS = frozenset({"analysis.created", "debate.started", "debate.turn.completed",
                                "debate.completed", "decision.research_plan.created"})
"""Events that only describe a run's outputs. Re-running the same run (same run id, after a
crash for example) reuses every journaled step, and these are not emitted twice."""


@dataclass(frozen=True)
class PipelineInputs:
    instrument: InstrumentId
    as_of: datetime
    collections: Sequence[CollectionResult]
    technical: Sequence[TechnicalAnalysis] = ()
    mtf: MultiTimeframeAnalysis | None = None
    declared_labels: Mapping[str, ClaimLabel] = field(default_factory=dict)
    """Owner-declared V4 labels (for example from a structured calendar). They win over
    model labels."""
    calendar: Sequence[CalendarValue] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument", InstrumentId(self.instrument))
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if any(c.as_of != self.as_of for c in self.collections):
            raise ValueError("every collection must be for the run's as_of")


class ResearchPipeline:
    def __init__(self, *, provider: ReasoningProvider, journal: StellarJournal,
                 config: WorkflowConfig, allowlist: SourceAllowlist,
                 validation_config: ValidationConfig, station_id: str,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._provider = provider
        self._journal = journal
        self._bus = EventBus(journal)
        self.config = WorkflowConfig.model_validate(config.model_dump())
        self._allowlist = allowlist
        self._vconfig = validation_config
        self._station = station_id
        self._clock = clock or (lambda: datetime.now(UTC))

    # ----------------------------------------------------------------------- run --

    def run(self, inputs: PipelineInputs) -> DecisionSupport:
        run = _Run(self, inputs)
        return run.execute()


class _Run:
    """One execution; holds the step records and the budget counter."""

    def __init__(self, pipeline: ResearchPipeline, inputs: PipelineInputs) -> None:
        self.p = pipeline
        self.inputs = inputs
        self.as_of = inputs.as_of
        self.steps: list[StepRecord] = []
        self.calls_used = 0
        self.run_id = "run_" + content_hash({
            "instrument": inputs.instrument.value, "as_of": inputs.as_of.isoformat(),
            "collections": [c.model_dump(mode="json") for c in inputs.collections],
            "technical": [t.content_hash for t in inputs.technical],
            "mtf": inputs.mtf.content_hash if inputs.mtf else None,
            "declared": sorted((k, v.value) for k, v in inputs.declared_labels.items()),
            "calendar": [c.model_dump(mode="json") for c in inputs.calendar],
            "config": pipeline.config.config_hash(), "prompts": registry_hash(),
            "allowlist": pipeline._allowlist.allowlist_hash(),
            "validation": pipeline._vconfig.config_hash()})[:40]

    # ------------------------------------------------------------------- events --

    def emit(self, event_type: str, payload: dict[str, Any], *, agent: str | None = None) -> None:
        body = {"run_id": self.run_id, "as_of": self.as_of.isoformat(), **payload}
        if event_type in DESCRIPTIVE_EVENTS and any(
                e.source == SOURCE and e.correlation_id == self.run_id and e.payload == body
                for e in self.p._journal.read(types=[event_type])):
            return  # Phase 7: a re-run of the same run re-describes nothing already journaled
        self.p._bus.publish(new_event(
            event_type, station_id=self.p._station, source=SOURCE, agent_id=agent,
            instrument=self.inputs.instrument, correlation_id=self.run_id, ts=self.p._clock(),
            payload=body))

    def checkpoint(self, role: str, fp: str) -> dict | None:
        for event in reversed(self.p._journal.read(types=["agent.task.completed"])):
            if event.source == SOURCE and event.payload.get("role") == role and \
                    event.payload.get("fingerprint") == fp:
                return event.payload
        return None

    # -------------------------------------------------------------- LLM stage --

    def llm_step(self, role: str, template: PromptTemplate, schema, *, trusted: dict,
                 untrusted: Sequence[UntrustedBlock], allowed: set[str],
                 check: Callable[[Any], str | None] | None = None,
                 depends_on: Sequence[str] = ()):
        cfg = self.p.config
        if role in cfg.disabled_roles:
            return self._skip(role, "disabled")
        if not cfg.llm_enabled:
            return self._skip(role, "llm_disabled", FailureKind.LLM_DISABLED)
        for dep in depends_on:
            if not self._ok(dep):
                return self._skip(role, f"dependency_{dep}", FailureKind.DEPENDENCY_FAILED)
        model = cfg.models.get(role)
        if model is None:
            return self._fail(role, FailureKind.UNSUPPORTED_MODEL, "model_unset", None, None)
        fp = fingerprint(template, model, self.as_of, trusted, untrusted)
        stored = self.checkpoint(role, fp)
        if stored is not None:
            output = schema.model_validate(stored["output"])
            self.steps.append(StepRecord(role=role, status=StepStatus.REUSED, fingerprint=fp,
                                         call=AgentCallRecord.model_validate(stored["call"]),
                                         output_hash=stored["output_hash"]))
            return output
        assert cfg.budget is not None
        remaining = cfg.budget.max_calls_per_run - self.calls_used
        if remaining <= 0:
            return self._fail(role, FailureKind.BUDGET_EXHAUSTED, "budget_exhausted", fp, None)
        self.emit("agent.task.started", {"role": role, "fingerprint": fp}, agent=role)
        self.emit("agent.llm_call.started", {"role": role, "fingerprint": fp,
                                              "model": model.model_dump(mode="json"),
                                              "prompt_version": template.version},
                  agent=role)
        output, record = call_structured(
            self.p._provider, template, role=role, model=model, as_of=self.as_of,
            trusted=trusted, untrusted=untrusted, schema=schema, allowed_evidence=allowed,
            max_attempts=min(cfg.max_attempts, remaining), run_id=self.run_id,
            timeout_seconds=cfg.timeout_seconds)
        self.calls_used += record.attempts
        self.emit("agent.llm_call.completed", {"role": role, "fingerprint": fp,
                                                "call": record.model_dump(mode="json")},
                  agent=role)
        if output is not None and check is not None:
            problem = check(output)
            if problem is not None:
                record = record.model_copy(update={"status": CallStatus.FAILED,
                                                   "failure": FailureKind.MALFORMED_OUTPUT,
                                                   "failure_detail": problem,
                                                   "output_hash": None})
                output = None
        if output is None:
            return self._fail(role, record.failure or FailureKind.MALFORMED_OUTPUT,
                              record.failure_detail or record.failure.value
                              if record.failure else "malformed", fp, record)
        data = output.model_dump(mode="json")
        self.emit("agent.task.completed", {"role": role, "fingerprint": fp, "output": data,
                                           "output_hash": record.output_hash,
                                           "call": record.model_dump(mode="json")}, agent=role)
        self.steps.append(StepRecord(role=role, status=StepStatus.COMPLETED, fingerprint=fp,
                                     call=record, output_hash=record.output_hash))
        return output

    def _skip(self, role: str, reason: str, failure: FailureKind | None = None):
        self.steps.append(StepRecord(role=role, status=StepStatus.SKIPPED, reason=reason,
                                     failure=failure))
        return None

    def _fail(self, role, failure, reason, fp, record):
        self.emit("agent.task.failed", {"role": role, "fingerprint": fp,
                                        "failure": failure.value, "reason": reason,
                                        "call": record.model_dump(mode="json") if record
                                        else None}, agent=role)
        self.steps.append(StepRecord(role=role, status=StepStatus.FAILED, reason=reason,
                                     failure=failure, fingerprint=fp, call=record))
        return None

    def _ok(self, role: str) -> bool:
        return any(s.role == role and s.status in (StepStatus.COMPLETED, StepStatus.REUSED)
                   for s in self.steps)

    def _deterministic(self, role: str, payload: Any) -> None:
        digest = content_hash(payload)
        self.steps.append(StepRecord(role=role, status=StepStatus.COMPLETED,
                                     fingerprint=digest, output_hash=digest))

    # ---------------------------------------------------------------- stages --

    def visible_items(self) -> list[ResearchItem]:
        """Items that existed at as_of. Later items never reach a model."""
        return [i for c in self.inputs.collections for i in c.items
                if i.published_at <= self.as_of and i.retrieved_at <= self.as_of]

    def classify(self) -> dict[str, ClaimLabel]:
        labels = dict(self.inputs.declared_labels)
        pending = [(i, c) for i in self.visible_items() for c in i.claims
                   if c.claim_id not in labels]
        if not pending:
            return labels
        claim_ids = {c.claim_id for _, c in pending}
        trusted = {"task": "label_claims",
                   "claims": [{"claim_id": c.claim_id, "item_id": i.item_id,
                               "statement": c.statement,
                               "value": None if c.value is None else str(c.value), "unit": c.unit,
                               "period": c.period} for i, c in pending]}
        untrusted = _excerpts(i for i, _ in pending)
        output = self.llm_step("claim_classifier", TEMPLATES["claim_classifier"],
                               ClaimLabelling, trusted=trusted, untrusted=untrusted,
                               allowed=claim_ids)
        if output is not None:
            for x in output.labels:
                labels.setdefault(x.claim_id, x.label)
        return labels

    def research(self, labels: Mapping[str, ClaimLabel]) -> ResearchSnapshot:
        items = [i for c in self.inputs.collections for i in c.items]
        validations = validate_claims(items, allowlist=self.p._allowlist,
                                      config=self.p._vconfig, as_of=self.as_of, labels=labels,
                                      calendar=self.inputs.calendar)
        assessments = assess_claims(items, validations, allowlist=self.p._allowlist,
                                    as_of=self.as_of)
        snapshot = build_snapshot(self.inputs.collections, validations, assessments,
                                  as_of=self.as_of,
                                  allowlist_hash=self.p._allowlist.allowlist_hash(),
                                  validation_config_hash=self.p._vconfig.config_hash())
        known = any(e.payload.get("research_snapshot_id") == snapshot.research_snapshot_id
                    for e in self.p._journal.read(types=["research.snapshot.created"]))
        if not known:
            publish_snapshot(self.p._journal, snapshot, station_id=self.p._station,
                             ts=self.p._clock())
        self._deterministic("research_validation", snapshot.content_hash)
        return snapshot

    def execute(self) -> DecisionSupport:
        inputs, instrument = self.inputs, self.inputs.instrument
        labels = self.classify()
        snapshot = self.research(labels)
        pool = build_pool(snapshot, inputs.technical, as_of=self.as_of, mtf=inputs.mtf)
        relevant = pool.for_instrument(instrument)
        claims = [e for e in relevant if e.kind is not EvidenceKind.TECHNICAL]
        technical = [e for e in relevant if e.kind is EvidenceKind.TECHNICAL]
        claim_ids = {e.evidence_id for e in claims}
        technical_ids = {e.evidence_id for e in technical}
        cited_items = {e.item_id for e in claims}
        untrusted = _excerpts(i for i in snapshot.items if i.item_id in cited_items)
        required = [r.value for r in snapshot.missing_roles(self.p.config.required_research_roles)]
        absent = sorted(c.role.value for c in inputs.collections
                        if c.status is not CollectionStatus.OK)
        coverage = Coverage(contributed=snapshot.contributed_roles(),
                            missing=tuple(ResearchRole(r) for r in sorted(set(required) |
                                                                           set(absent))))

        # M1 ----------------------------------------------------------------------------------
        macro_out = self.llm_step(
            "causal_macro_analyst", TEMPLATES["causal_macro_analyst"], MacroAssessmentOutput,
            trusted={"instrument_focus": instrument.value, "evidence": _records(claims),
                     "coverage": coverage.model_dump(mode="json")},
            untrusted=untrusted, allowed=claim_ids)
        macro = None
        if macro_out is not None:
            ids = tuple("drv_" + sha256_hex(f"{self.run_id}|{n}|{d.driver.value}")[:16]
                        for n, d in enumerate(macro_out.drivers))
            macro = MacroAssessment(driver_ids=ids, output=macro_out, coverage=coverage)
            self._report(AnalysisKind.MACRO, "causal_macro_analyst", snapshot, coverage)
        driver_records = [] if macro is None else [
            {"driver_id": i, **d.model_dump(mode="json")}
            for i, d in zip(macro.driver_ids, macro.output.drivers, strict=True)]
        driver_ids = set(macro.driver_ids) if macro else set()

        # S* ----------------------------------------------------------------------------------
        specialist = SPECIALISTS[instrument]
        allowed_all = claim_ids | technical_ids | driver_ids
        view_out = self.llm_step(
            specialist, TEMPLATES["market_specialist"], MarketViewOutput,
            trusted={"instrument": instrument.value, "evidence": _records(claims),
                     "technical_evidence": _records(technical), "macro_drivers": driver_records,
                     "coverage": coverage.model_dump(mode="json")},
            untrusted=untrusted, allowed=allowed_all, depends_on=["causal_macro_analyst"],
            check=lambda o: None if o.instrument is instrument else "instrument_mismatch")
        view = None
        if view_out is not None:
            view = MarketView(instrument=instrument, specialist=specialist, output=view_out,
                              coverage=coverage)
            self._report(AnalysisKind.MARKET, specialist, snapshot, coverage)

        # U1 / U2 ------------------------------------------------------------------------------
        bull_cases: list[DebateCaseOutput] = []
        bear_cases: list[DebateCaseOutput] = []
        base = {"instrument": instrument.value, "evidence": _records(claims),
                "technical_evidence": _records(technical), "macro_drivers": driver_records,
                "market_view": view_out.model_dump(mode="json") if view_out else None}
        self.emit("debate.started", {"rounds": self.p.config.debate_rounds})
        for rnd in range(1, self.p.config.debate_rounds + 1):
            for role, side, mine, other in (("bull_researcher", DebateSide.BULL, bull_cases,
                                             bear_cases),
                                            ("bear_researcher", DebateSide.BEAR, bear_cases,
                                             bull_cases)):
                out = self.llm_step(
                    role, TEMPLATES[role], DebateCaseOutput,
                    trusted={**base, "round": rnd,
                             "opposing_case": other[-1].model_dump(mode="json") if other
                             else None},
                    untrusted=untrusted, allowed=allowed_all, depends_on=[specialist],
                    check=lambda o, s=side: None if o.side is s else "side_mismatch")
                if out is not None:
                    mine.append(out)
                    self.emit("debate.turn.completed", {"round": rnd, "side": side.value,
                                                        "role": role}, agent=role)

        # P2 ---------------------------------------------------------------------------------
        findings = challenge(pool=relevant, as_of=self.as_of,
                             macro=macro_out, view=view_out, bull=bull_cases, bear=bear_cases,
                             missing_roles=required, absent_collections=absent)
        report = ChallengeReport(findings=tuple(findings))
        self._deterministic("contradiction_checker", report.model_dump(mode="json"))
        self.emit("debate.completed", {"bull_turns": len(bull_cases), "bear_turns": len(bear_cases),
                                       "findings": [f.model_dump(mode="json") for f in findings]})
        quality = evidence_quality(relevant, pool, missing_roles=sorted(set(required) | set(absent)),
                                   findings=findings)

        # U3 ---------------------------------------------------------------------------------
        synth_out = self.llm_step(
            "research_manager", TEMPLATES["research_manager"], SynthesisOutput,
            trusted={**base, "bull_cases": [c.model_dump(mode="json") for c in bull_cases],
                     "bear_cases": [c.model_dump(mode="json") for c in bear_cases],
                     "contradiction_findings": [f.model_dump(mode="json") for f in findings],
                     "evidence_quality": quality.model_dump(mode="json")},
            untrusted=untrusted, allowed=allowed_all,
            depends_on=["bull_researcher", "bear_researcher"])
        synthesis = None
        if synth_out is not None:
            final, adjustments = guard_stance(synth_out, quality, findings)
            post = check_output("research_manager", synth_out, relevant, as_of=self.as_of)
            synthesis = Synthesis(output=synth_out, model_stance=synth_out.stance,
                                  final_stance=final, guard_adjustments=adjustments,
                                  post_findings=tuple(post))
            self.emit("decision.research_plan.created", {
                "role": "research_manager", "model_stance": synth_out.stance.value,
                "final_stance": final.value, "guard_adjustments": list(adjustments),
                "evidence_grade": quality.grade.value,
                "research_snapshot_id": snapshot.research_snapshot_id},
                agent="research_manager")
        return self._result(snapshot, pool, macro, view, bull_cases, bear_cases, report, quality,
                            synthesis)

    # ---------------------------------------------------------------- output --

    def _report(self, kind: AnalysisKind, role: str, snapshot: ResearchSnapshot,
                coverage: Coverage) -> None:
        report = AnalysisReport(
            analysis_id=f"an_{sha256_hex(f'{self.run_id}|{role}')[:40]}", kind=kind,
            run_id=self.run_id, instrument=self.inputs.instrument,
            research_snapshot_id=snapshot.research_snapshot_id, as_of=self.as_of,
            created_at=max(self.p._clock(), self.as_of), coverage=coverage,
            provenance=Provenance(produced_by=role, config_hash=self.p.config.config_hash(),
                                  input_ids=(snapshot.research_snapshot_id,)))
        self.emit("analysis.created", {"analysis_id": report.analysis_id, "kind": kind.value,
                                       "coverage": coverage.model_dump(mode="json"),
                                       "report": report.model_dump(mode="json")}, agent=role)

    def _result(self, snapshot, pool: EvidencePool, macro, view, bull, bear, report, quality,
                synthesis) -> DecisionSupport:
        cfg = self.p.config
        final = synthesis.final_stance if synthesis else Stance.INSUFFICIENT_EVIDENCE
        llm_steps = [s for s in self.steps if s.role in LLM_ROLES]
        if not cfg.llm_enabled:
            status = RunStatus.DETERMINISTIC_ONLY
        elif any(s.status in (StepStatus.FAILED, StepStatus.SKIPPED)
                 and s.role not in cfg.optional_roles for s in llm_steps):
            status = RunStatus.FAILED if synthesis is None else RunStatus.PARTIAL
        elif any(s.status in (StepStatus.FAILED, StepStatus.SKIPPED) for s in llm_steps):
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.COMPLETED
        limitations = sorted({*(f"missing_{r.value}" for r in (macro.coverage.missing
                                                              if macro else ())),
                              *(f"technical_{x}" for x in quality.technical_limitations),
                              *(["llm_disabled"] if not cfg.llm_enabled else [])})
        outputs = {"macro": macro, "view": view, "bull": bull, "bear": bear, "report": report,
                   "quality": quality, "synthesis": synthesis, "final": final}
        return DecisionSupport(
            run_id=self.run_id, instrument=self.inputs.instrument, as_of=self.as_of,
            research_snapshot_id=snapshot.research_snapshot_id,
            technical=tuple(TechnicalRef(analysis_id=t.analysis_id, content_hash=t.content_hash,
                                         timeframe=t.timeframe)
                            for t in self.inputs.technical),
            evidence_pool_hash=pool.pool_hash, workflow_config_hash=cfg.config_hash(),
            prompt_registry_hash=registry_hash(), steps=tuple(self.steps), macro=macro,
            market_view=view, bull_cases=tuple(bull), bear_cases=tuple(bear), challenge=report,
            quality=quality, synthesis=synthesis, final_stance=final, status=status,
            limitations=tuple(limitations),
            outputs_hash=content_hash({k: (v.model_dump(mode="json") if hasattr(v, "model_dump")
                                           else [x.model_dump(mode="json") for x in v]
                                           if isinstance(v, list) else v)
                                       for k, v in outputs.items()}))


def _records(items: Sequence[EvidenceItem]) -> list[dict]:
    return [e.model_dump(mode="json") for e in items]


def _excerpts(items) -> list[UntrustedBlock]:
    seen, out = set(), []
    for item in items:
        if item.item_id not in seen:
            seen.add(item.item_id)
            out.append(UntrustedBlock(ref=item.item_id, content=item.excerpt))
    return sorted(out, key=lambda b: b.ref)
