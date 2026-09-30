# Stellar Phase 7: V1 PAPER end-to-end orchestration and validation

**Status:** implemented and tested; not committed.
**PAPER ONLY.** No MT5, no Vantage, no broker API, no DEMO or LIVE path, no credentials.
**No profitability claim is made.** Every threshold stays unset by default. Tests use labelled
synthetic fixtures, an in-memory market source and a scripted LLM.

---

## 1. Scope and sequencing decision

Phase 7 wires the Phase 2–6b components into one journaled PAPER run and proves they operate
safely together:

```
Market Data (P2) → Technical (P5) → Research / debate (P6) → Setup / Trader / Proposal (P6b)
  → Risk (P3) → OrderIntent (P3) → Paper Broker (P4) → position / trade / P&L (P4)
  → journal / replay / recovery (P1 journal)
```

It is orchestration, lifecycle, checkpointing, replay, recovery, reconciliation and health.
No earlier engine is rewritten. The only change to earlier code is a narrow idempotency fix in
the Phase 6 pipeline (§10).

### Canonical conflict (recorded, not silently resolved)

The Foundation plan (§11) names Phase 7 "Simulation, backtesting and attribution". This phase
follows the owner's instruction instead: **V1 PAPER end-to-end orchestration**.

The following remain future work under the owner's sequencing:
- the event-driven simulator (§4.17);
- attribution;
- profile comparison (D-7);
- threshold evidence (D-12).

### Deployment sequencing decision (owner, Phase 7)

**MT5 / Vantage DEMO integration is NOT the next automatic step.** The owner has chosen to
complete and validate Stellar in PAPER mode first:
- the Research Lab runtime;
- monitoring and performance;
- the visual station;
- broader validation.

Broker demo integration (Foundation Phase 8) waits until then. This records a sequencing
decision; the canonical roadmap is not rewritten.

---

## 2. Architecture

Everything is in a new package, `stellar/src/stellar/runtime/`. Nothing imports it, so it
creates no dependency cycle.

| Module | Role |
|---|---|
| `config.py` | `RuntimeConfig` (versioned wiring only), `OperatorRiskInputs` (explicit per-run risk inputs), `TakeProfitPolicy` |
| `models.py` | `RunRequest`, `RunStage`, `RunState`, `RuntimeFailure`, `StageCheckpoint`, `RunRecord` |
| `ledger.py` | `RunLedger`: writes run events and folds them back into a `RunRecord` |
| `orchestrator.py` | `PaperRuntime`: `run`, `status`, `advance`, `cancel`, `close`, `context`, `intent_for` |
| `reconcile.py` | deterministic PAPER reconciliation |
| `health.py` | deterministic V1 PAPER health check |
| `metrics.py` | operational metrics from the journal |

**The orchestrator decides nothing.** Each decision stays with its owner:
- the desk decides the setup and the proposal;
- the Risk Engine decides APPROVED / REVIEW / REJECTED;
- the only path to an `OrderIntent` is `RiskService.authorize_intent`;
- the Paper Broker decides acceptance, fills and closes, and re-confirms every fill through
  Phase 3.

The runtime constructs no proposal, decision, intent, order, fill, trade or approval. It
never resets or trips the breaker. It never writes SQL; it only appends events. Boundary tests
enforce all of this (§16).

### Changes to existing files

| File | Change |
|---|---|
| `telemetry/catalogue.py` | + `run.stage.completed`, required keys `run_id`, `stage`, `fingerprint`, `state` |
| `pipeline/orchestrator.py` | descriptive events are not re-emitted when the same research run is re-run (§10) |
| `tests/contract/test_upstream_boundary.py` | runtime boundary tests; runtime added to the technical-import allowance and the import-order list |

---

## 3. Configuration (nothing new is decided)

`RuntimeConfig` holds only wiring that no earlier phase owns:

| Field | Unset / default means |
|---|---|
| `timeframe` | the setup timeframe (a profile decision, D-7). Unset → `RuntimeConfigError`; nothing runs |
| `profile` | label only. It must equal `SetupConfig.profile` when both are set |
| `enabled_instruments` | none: the Risk Engine refuses every instrument |
| `broker_symbols` | none: no intent can be built (ORDER_AUTHORISATION_FAILED) |
| `take_profit` | `NONE`: no take-profit on the intent (RK-9 safe default). `NEAREST_PROPOSAL_TARGET` is an explicit owner choice |

Every other setting is referenced by hash, never duplicated:
- `TechnicalConfig`;
- `WorkflowConfig`, allowlist and validation (Phase 6 defaults: empty allowlist, LLM disabled);
- `SetupConfig` / `TraderConfig`;
- `RiskPolicy` (inside `RiskEngine`);
- `PaperBrokerConfig`.

**`OperatorRiskInputs`** carries the risk inputs that no component produces yet:
- the daily window (RK-6);
- cooldowns;
- event restriction;
- instrument metadata;
- requested volume;
- currency conversions.

They are explicit, part of the run identity, and `None` means unknown. The Risk Engine's
missing-input rule then decides (FAIL or REVIEW).

**Not chosen anywhere:**
- a lot size;
- a starting balance or account currency (D-8);
- a profile (D-7);
- a risk threshold (D-12);
- a setup threshold;
- a spread or slippage;
- a conversion rate.

---

## 4. The V1 run contract

**`RunRequest`:**
- instrument, `as_of`;
- research collections, declared labels, calendar;
- operator inputs;
- `approval` and `owner_selection`: optional, and not part of the identity.

**`RunRecord`**, rebuilt from the journal and the Phase 4 book, holds:
- `run_id`, instrument, timeframe, profile, `as_of`, workflow version;
- `config_hashes`: runtime, technical and its engine version, workflow, allowlist, validation,
  prompts, setup, trader, risk policy and engine version, paper broker;
- `state`, last `stage`, `failure`, `detail`;
- `refs`: snapshot id and series hash; technical analysis id and hash; research run id,
  snapshot id and outputs hash; setup id, fingerprint and status; proposal id and direction;
  risk decision id, fingerprint and outcome; intent id and side; order id and status; position
  id; trade id;
- every stage checkpoint, `started_at`, `finished_at`, and the resume count.

---

## 5. Lifecycle

| Stage | Component | State reached |
|---|---|---|
| MARKET_DATA | Phase 2 source → `VerifiedMarketSnapshot` (`snapshot.created`) | MARKET_DATA_READY |
| TECHNICAL | Phase 5 `analyse` (`analysis.created`) | TECHNICAL_COMPLETE |
| RESEARCH | Phase 6 `ResearchPipeline` | RESEARCH_COMPLETE |
| SETUP | Phase 6b `TraderDesk` | SETUP_COMPLETE, NO_SETUP, SETUP_CANDIDATE or AWAITING_APPROVAL |
| PROPOSAL | Phase 6b P1 (inside the desk) | PROPOSAL_CREATED |
| RISK | Phase 3 `RiskService.evaluate` | RISK_REVIEWED, REVIEW_REQUIRED or REJECTED |
| ORDER_AUTHORISATION | Phase 3 `authorize_intent` | ORDER_AUTHORISED or BLOCKED |
| PAPER_SUBMISSION | Phase 4 `submit` | PAPER_SUBMITTED, POSITION_OPEN, ORDER_REJECTED or BLOCKED |

After submission the state follows the Phase 4 book:

| Book | Run state |
|---|---|
| PENDING | PAPER_SUBMITTED |
| BLOCKED | ORDER_BLOCKED |
| FILLED, position open | POSITION_OPEN |
| trade closed | COMPLETED |
| CANCELLED | CANCELLED |
| EXPIRED | EXPIRED |
| REJECTED | ORDER_REJECTED |
| PREFLIGHT_FAILED | BLOCKED |

**State kinds:**
- **Terminal:** COMPLETED, NO_SETUP, SETUP_CANDIDATE, REVIEW_REQUIRED, REJECTED, BLOCKED,
  ORDER_REJECTED, CANCELLED, EXPIRED, FAILED.
- **Parked:** AWAITING_APPROVAL.
- **Live:** PAPER_SUBMITTED, ORDER_BLOCKED, POSITION_OPEN.

**Brief states not used:**
- **POSITION_CLOSED:** a closed trade is COMPLETED.
- **PARTIAL:** the paper broker has no partial fills.

### Approval (producer-agnostic)

The runtime consumes a typed Phase 6b `Approval` produced **outside** the runtime. It does not
care which producer made it:
- the future Portfolio Manager / supervisor agent (`source=portfolio_manager`);
- an explicitly authorised owner action (`source=owner`);
- another canonical producer defined later (a new `ApprovalSource` value in `stellar.proposals`;
  the runtime needs no change).

The runtime never produces, defaults or requires a particular source. It checks only what the
Phase 6b builder checks: the approval is bound to this `setup_id` and this direction, and its
rating approves (Buy; Overweight → D-9 no trade; anything else → no proposal).

The approval binds to a setup id that exists only after the SETUP stage. So:
1. A READY setup parks the run at **AWAITING_APPROVAL**.
2. The same request plus an `Approval` resumes **the same run** (the same `run_id`). This is
   why the approval is excluded from the run identity.
3. The approval is journaled once as `decision.final.created`, with its source, reference,
   setup id, direction, rating and hash.

An approval is an input to the proposal builder, **never execution authority**. Every order
still needs a current Phase 3 evaluation, `authorize_intent`, and the broker's confirmation at
submission and at every fill.

In the synthetic tests the approvals are test fixtures, from both `owner` and
`portfolio_manager` sources.

---

## 6. Orchestration, checkpoints and resume

### Run identity

`run_id` hashes the complete input:
- the request;
- the market data actually read (series hash and quote, or the read error);
- the workflow version;
- every configuration hash.

The same input is the same run; any change is a new run. The approval is excluded.

### Checkpoints

Each stage appends `run.stage.completed` with its input fingerprint, the state reached, typed
outputs and refs:
- snapshot and quote;
- the full `TechnicalAnalysis`;
- the full `DecisionSupport`;
- setup, outcome and selection;
- the proposal;
- risk refs, reasons and unresolved checks;
- the intent;
- the execution result.

The journal alone is enough to resume; no in-memory state is the source of truth.

### What `run` does with the same request

| Situation | Result |
|---|---|
| Run already finished (terminal or live) | the recorded run is returned; **nothing is emitted** |
| A stage has a checkpoint | it is loaded, not re-executed |
| A stage has no checkpoint | execution continues there, with one `run.resumed` |
| MARKET_DATA or TECHNICAL checkpoint has a different fingerprint | refused: FAILED / CHECKPOINT_CONFLICT |
| Parked SETUP receives an approval | SETUP is re-entered (the desk is idempotent) |
| SETUP checkpointed but PROPOSAL not | SETUP is asked again, and the desk returns its journaled proposal |

### Crash between a side effect and its checkpoint

This window is covered by the components' own idempotency:

| Component | What happens on the retry |
|---|---|
| Research | journaled LLM steps are reused (no second call), and the pipeline no longer re-emits descriptive events (§10) |
| Desk | returns the journaled Trader answer and proposal |
| Risk | returns the journaled evaluation for the same fingerprint |
| Broker | returns the journaled order for the same `intent_id` |
| Technical / snapshot reports | de-duplicated by id |

The intent id is `int_` + a hash of the proposal id and the evaluation fingerprint.

**Tested:** a crash after each of the 8 stages, and a crash before the checkpoint at 6 stages.
In every case the resumed run matches an uninterrupted run exactly, with the same refs, the
same side-effect counts and the same number of LLM requests.

---

## 7. Stale context and invalidation

The risk context is rebuilt from current state whenever it is used:
- the journaled breaker;
- the Phase 4 book;
- the run's snapshot and quote;
- the operator inputs.

| Change | Effect |
|---|---|
| Account, positions, pending orders or another evaluation of the same proposal changed after RISK | `authorize_intent` raises `ReevaluationRequired` → **BLOCKED / STALE_CONTEXT**. It is never silently re-authorised (tested with a competing run) |
| Breaker TRIPPED | BLOCKED / CIRCUIT_BREAKER_TRIPPED, or REJECTED by the breaker rule |
| Anything at submission or fill | the broker re-confirms against the current context (Phase 4); a stale approval cannot fill |
| Market data, research, technical or config changed | a different `run_id`: a new run |
| Setup invalidated or expired | the desk returns NO_SETUP (INVALIDATED / EXPIRED) |
| The paper world moved past an unfinished run | before authorising or submitting, the run is **BLOCKED / STALE_CONTEXT** if the paper book has processed a later input (`paper_book_moved_past_as_of`) or a later run for the same instrument has started (`superseded_by_<run_id>`). A crashed run's approval or intent is never carried into a newer market |
| A market view for the same setup changes (a new quote or a later moment) | a new run; the Phase 6b desk gives the setup no second proposal (`setup_already_proposed`), and the old run is superseded, so nothing trades on the old view |
| A run for a moment after the runtime clock | refused before anything is journaled (`FutureRunError`, look-ahead) |

An approval is an input to the proposal builder only. Execution authority is always a
current Phase 3 evaluation plus `authorize_intent` plus the broker's confirmation.

Phase 3 / 4 safety is unchanged.

---

## 8. Account → RiskContext bridge (RK-11)

`PaperRuntime.context()` builds the context from these parts:

| Part | Source |
|---|---|
| Account, positions, pending orders, prior idempotency keys | Phase 4 `PaperBroker.risk_inputs(as_of, excluding_order_id=)`, the canonical paper account read model |
| Breaker | the journal (`RiskService` replaces it anyway) |
| Snapshot and quote | the run's market stage |
| Daily, cooldowns, event restriction, metadata, volume | `OperatorRiskInputs` |
| Enabled instruments | `RuntimeConfig` |
| Execution mode | `ExecutionModeInput(mode="PAPER")` |

The dependency points one way: runtime → execution → risk.

**RK-11 is resolved for PAPER.** The current context comes from the paper book plus explicit
operator inputs. An unknown balance (unknown economics) yields `account=None`, and the Risk
Engine then refuses; it is never estimated.

---

## 9. NO_SETUP, REVIEW, REJECTED, BLOCKED, breaker

| Outcome | What happens |
|---|---|
| NO_SETUP (also conflicting or insufficient evidence) | A successful terminal state. There is no risk evaluation, no proposal and no order. Journaled with `run.completed` |
| REVIEW_REQUIRED | Terminal for the run, and never approved. The RISK checkpoint keeps the proposal, the reason codes and the unresolved checks. Nothing is submitted. Resolving it means a new run with changed inputs |
| REJECTED | Terminal. No intent and no order. The breaker is not touched unless Phase 3's own systemic rules trip it |
| Pending / BLOCKED | A limit order stays PAPER_SUBMITTED. When executable without a current authorisation, it becomes ORDER_BLOCKED (visible, not FAILED); a fresh quote alone never re-authorises it. `advance(..., reauthorise=True)` asks Phase 3 for a new evaluation and intent at that moment (same terms and expiry); only an APPROVED, current one is offered. The order can also be cancelled (`cancel`) or expire |
| Breaker | Phase 3 trips it (daily-loss breach in the test). A pending order then cannot fill: the broker cancels it (`circuit_breaker_tripped`) and the run is CANCELLED / CIRCUIT_BREAKER_TRIPPED. A restart keeps it TRIPPED, health is BLOCKED, and new runs are REJECTED. The runtime has no reset |

---

## 10. Journal and events

**Run events:**
- `run.started`;
- `run.stage.completed` (new);
- `run.resumed`;
- `run.completed`;
- `run.failed`.

All carry the run id as `run_id` and `correlation_id`. The existing `snapshot.created` and
`decision.final.created` (the approval) are used. Everything else is the components' own
events.

**Why `run.stage.completed` is new.** No canonical event records a run-level stage
checkpoint:
- `run.started` / `run.resumed` / `run.completed` / `run.failed` mark the run, not its stages;
- `agent.task.completed` is an agent's task, and the Phase 6 pipeline looks its LLM
  checkpoints up there by role and fingerprint. Runtime stages are not agent tasks, and
  sharing the name would mix two checkpoint systems.

**Shape.**
- It uses the standard event envelope (`schema_version`, `run_id`, `correlation_id`), with
  required keys `run_id`, `stage`, `fingerprint` and `state`.
- It also carries `failure`, `detail`, `refs` and typed `outputs`; each typed record inside
  carries its own `schema_version`.
- It is not in a critical domain.

**Not a domain event.** It never replaces or re-announces a domain event: the proposal is
announced only by `trade.proposed`, the decision by `risk.*`, the order by `order.*`. It keeps
copies of stage outputs so that a run can resume from the journal alone (the full
`TechnicalAnalysis` and `DecisionSupport` are journaled nowhere else, P5-10). Reconciliation
checks that these copies equal the domain records.


**Pipeline idempotency fix (Phase 6, additive; `_Run.emit` only).** Re-running the same research run (the same
`run_id`, after a crash) reused every LLM step, but re-emitted these events:
- `analysis.created`;
- `debate.*`;
- `decision.research_plan.created`.

An identical descriptive event already journaled for that run is now not emitted again.
Re-running the same pipeline now appends nothing.

The journal is never mutated; replay from a file journal rebuilds the same state.

---

## 11. Reconciliation (`reconcile`)

Checks, all read from the journal:
- journal verification (sequence and body hashes);
- FILLED order without a position or trade;
- duplicate entry fill;
- closed position still open;
- duplicate accepted order per proposal;
- duplicate `trade.proposed`;
- balance = starting balance + known realised P&L (only when every trade is KNOWN; otherwise
  `unsettled_trade_ids`);
- run → missing order;
- run / trade reference mismatch;
- orphan intent (a finished run with an unsubmitted authorised intent);
- stage-order violation;
- checkpoint mismatch: a run checkpoint's copy of the proposal or the intent differs from
  `trade.proposed` or the broker's order.

Problems are reported, never repaired. The tests use forged events.

---

## 12. Health (`health`)

Deterministic; the worst reason wins:

| Status | When |
|---|---|
| FAILED | the journal fails verification, or reconciliation finds an inconsistency |
| BLOCKED | the breaker is TRIPPED, no instrument is enabled, or an enabled instrument has no broker symbol |
| DEGRADED | a run FAILED, REVIEW_REQUIRED or AWAITING_APPROVAL; an order is BLOCKED; P&L is unsettled; or a configuration is test-only |
| HEALTHY | none of these |

---

## 13. Operational metrics (`runtime_metrics`)

- runs by state;
- completed / NO_SETUP / REVIEW / REJECTED / FAILED counts;
- paper submissions;
- execution failures (preflight failures and broker rejections);
- per-stage count, total and max duration (journal time);
- LLM calls, attempts, retries and failures;
- tokens and cost only when reported (cost is None otherwise).

No strategy performance, ranking or profitability metric exists here.

---

## 14. Determinism

**Logical determinism.** The same synthetic market inputs, research, configs, scripted provider
outputs, `as_of`, clock and starting journal give:
- the same `run_id`;
- the same record;
- the same event stream (sequence, type, payload, correlation).

This is tested across two journals.

**Run-instance identity.** Event ids are ULIDs and differ between instances; nothing else
does. The run id is logical, not an instance id.

---

## 15. Failure taxonomy (`RuntimeFailure`)

| Failure | Trigger |
|---|---|
| MARKET_DATA_FAILED | no bar at or before `as_of` (a missing quote is not a failure; it is recorded) |
| TECHNICAL_FAILED | `TechnicalInputError` |
| RESEARCH_FAILED | the pipeline raises, or its run status is FAILED |
| SETUP_FAILED | `SetupInputError`, or the Trader's answer was rejected (for example an invented price) |
| PROPOSAL_FAILED | a builder refusal (detail = `ProposalFailure`, for example `no_quote`, `profile_not_configured`, `approval_direction_mismatch`) |
| RISK_REVIEW_REQUIRED | Phase 3 REVIEW |
| RISK_REJECTED | Phase 3 REJECTED |
| RISK_FAILED | the Risk Engine raised |
| ORDER_AUTHORISATION_FAILED | no broker symbol, or an intent refusal |
| PAPER_BROKER_FAILED | a broker exception, such as a conflicting or out-of-order input |
| PAPER_PREFLIGHT_FAILED | a Phase 4 preflight refusal |
| CHECKPOINT_CONFLICT | a stage re-entered with a different fingerprint |
| STALE_CONTEXT | the evaluation is no longer current, the paper book moved past the run, or a later run superseded it |
| CIRCUIT_BREAKER_TRIPPED | the breaker is TRIPPED |
| CONFIGURATION_INVALID | reserved (a bad runtime configuration raises `RuntimeConfigError` at construction) |

---

## 16. Tests

All fixtures are synthetic.

| File | Covers |
|---|---|
| `tests/runtime_helpers.py` | in-memory source, labelled test configs, `Script` (research + Trader), approval helper |
| `test_rt_e2e.py` (21) | full LONG (target, stop, manual close); full SHORT (SELL at the bid, target on the ask side, direction kept, Buy approval of SHORT); a LONG approval on SHORT refused; NO_SETUP; conflicting evidence; REJECTED; REVIEW; missing operator inputs; duplicate run; changed input; cross-journal determinism; no look-ahead (future bars, quotes, news); unknown economics; missing and explicit conversion; metrics; health; one Trader call; default no take-profit |
| `test_rt_recovery.py` (24) | restart after each of the 8 stages; crash before the checkpoint at 6 stages; restart after close; file replay; checkpoint conflict; stale context; duplicate submission; pending → BLOCKED → re-authorised fill; cancel; expiry; a fresh quote alone never re-authorises; breaker trip, restart, no reset; the pipeline re-run appends nothing |
| `test_rt_failures.py` (16) | market-data failure; missing quote; technical, research (two ways), setup and Trader failures; proposal failure; authorisation failure; instrument not enabled; configuration fail-closed; production defaults trade nothing; reconciliation success and failures (duplicate fill or proposal, missing order, orphan intent) |
| `test_rt_identity.py` (17) | any approval producer resumes the same run (owner / portfolio_manager); no approval → parked; wrong setup, direction or rating → no proposal; changed market identity → a new run; a policy change after approval is evaluated afresh; a market change after authorisation never executes the old intent (same moment and later); the book moved past → BLOCKED; future `as_of` refused; stale account → BLOCKED; checkpoint event shape; checkpoint copy mismatch reported |
| `test_rs_rerun_idempotency.py` (4) | Phase 6 re-run: the first run still emits everything; the same inputs repeat no LLM call, no event and give the same result; a retried failed step describes only its new result; changed inputs do new work |
| boundary (+4 tests, +1 import-order case) | the runtime builds no privileged record, never resets or trips the breaker, and never uses private risk paths; paper only (no LIVE / DEMO strings, no network, broker, LLM vendor, process, random or SQL access); nothing imports the runtime; only catalogued events |

Mutation checks were run on the runtime guards, the pipeline fix and the boundary tests. All
non-equivalent mutants are killed. The two equivalent survivors are covered by deeper layers:
- Phase 3 itself refuses a non-APPROVED intent;
- the parked-run shortcut emits nothing either way.

---

## 17. Limitations

- **One setup timeframe per run.** Multi-timeframe input to the desk is not wired; the MTF
  roles (P5-9) are undecided.
- **Operator inputs are explicit.** Daily P&L, cooldown and event-restriction producers do not
  exist yet.
- **Market data.** The runtime reads one timeframe and one quote from a Phase 2 source per run.
  A real provider is out of scope.
- **Waiting for inputs.**
  - AWAITING_APPROVAL waits for a typed approval from any approval producer.
  - REVIEW_REQUIRED waits for a new run with changed inputs.
  - No approval producer (Portfolio Manager U10) and no scheduler exist yet.
- **Stale authorisation.** STALE_CONTEXT ends the run; the runtime does not auto-reevaluate. A
  new run is needed.
- **Metrics are operational only.** There are no strategy metrics (future simulation and
  attribution work).
- **Feature gates.** The runtime does not read `StellarConfig` feature gates. Safety comes from
  explicit configuration, fail-closed defaults and the Phase 3 / 4 checks.

---

## 18. Unresolved decisions

| # | Decision | Safe default |
|---|---|---|
| RT-1 | Setup timeframe / profile per instrument (D-7) | unset → no run |
| RT-2 | Take-profit on the order (RK-9) | NONE |
| RT-3 | Enabled instruments and paper broker symbols | none → nothing trades |
| RT-4 | Producers of daily P&L window (RK-6), cooldowns, event restrictions | explicit operator input; missing → Phase 3 missing-input outcome |
| RT-5 | Which producer supplies approvals in production (PM U10, an authorised owner action, or another canonical producer) | any typed `Approval` bound to the setup; without one the run parks |
| RT-6 | Auto re-evaluation on stale context vs a new run | a new run (STALE_CONTEXT ends the run) |
| RT-7 | Resolving REVIEW_REQUIRED (owner workflow) | a new run with changed inputs |
| RT-8 | Paper account currency and starting balance (D-8) | test-only fixtures only |
| RT-9 | Risk thresholds (D-12), setup thresholds (TS-1…) | unset; tests use labelled test policies |
| RT-10 | Simulator / attribution (canonical Phase 7 content) | future, per the owner's sequencing |
| RT-11 | Scheduling / cadence of runs (O1 Supervisor) | caller-driven |
| RT-12 | Wall-clock freshness when resuming a run long after its `as_of` (no later run or book event exists) | a resumed run replays its own point-in-time moment; a later run or any later paper-book event supersedes it (BLOCKED). A wall-clock limit is a future Supervisor (O1) decision; no threshold is invented |

---

## 19. Out of scope (not added)

- MT5, Vantage, broker credentials, DEMO, LIVE, real-money execution;
- real data providers, real LLM vendor integration;
- the Research Lab runtime;
- the full visual world;
- RL or self-modification;
- profitability optimisation;
- production strategy thresholds.
