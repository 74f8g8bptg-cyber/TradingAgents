# Stellar Screen Registry — v2 (flat vessel)

> **Status:** v2.0, rebuilt on Floor Plan revision C. Documentation only: no renderer, no art.
>
> **Scope:** every in-world display (`DSP-…`): its room, purpose, screen hardware, data source,
> availability today, and what it shows when data is missing or stale.
>
> **ID policy:** the v1 display IDs belonged to the void stacked-deck layout and were never
> released. v2 issues a fresh `DSP-<room code>-NN` space. Carried-over *concepts* are mapped in §7.
>
> **Builds on:** Visual World Plan §1.4, §10, §10.1, §11, §17; `STELLAR_ROOM_REGISTRY.md` v2;
> `STELLAR_STARNET_VISUAL_ADAPTATION.md` rows A18, A19, A23.

---

## 1. Principles (unchanged)

1. **Never fabricate.** A display shows only values from real telemetry: canonical events, the
   read-only snapshot, or the Phase 7 runtime reads (run ledger, `health()`, `runtime_metrics()`,
   `reconcile()`). Otherwise it shows a typed placeholder (§3). There are no mock prices, no sample
   P&L, no invented orders and no default "OK".
2. **Screen hardware carries no numbers** (Asset Registry rule 2.10).
3. **Every value has an age.** A value older than its freshness window is dimmed, hatched and
   labelled with its age.
4. **Read-only.** A display is `RO` (display only) or `NAV` (a click opens a room, a stage screen,
   a replay or the proposal timeline). No display can approve, reject, reset, send, cancel or
   change anything; the UI has no write endpoint (Visual plan §17, §20; A27).
5. **Mode text comes from telemetry.** `PAPER` appears only after a Paper Broker `account.opened`.
   Otherwise the plaque shows **MODE UNKNOWN** in amber. There is no DEMO, LIVE, MT5 or Vantage
   path, and no display offers one.
6. **Planned means not rendered.** `PLANNED` IDs are reserved: no art, no in-world placeholder.
7. **Colour is never the only signal.** Every state has a word and an icon; stale uses hatching.
8. **Freeze and grey, never guess** (A18). On link loss, values freeze and grey out with their
   age. After a gap reset they return to `AWAITING DATA` until the snapshot is reloaded.

## 2. Data sources and producer audit

| Code | Source |
|---|---|
| **EV** | Canonical events (`stellar.telemetry.catalogue`), folded into WorldState by the Visual State Adapter |
| **SN** | Read-only `/snapshot` (on connect and after a gap reset) |
| **RL** | Phase 7 run ledger / `RunRecord` |
| **HL** | Phase 7 `health()` → `HealthReport` |
| **MT** | Phase 7 `runtime_metrics()` → `RuntimeMetrics` |
| **RC** | Phase 7 `reconcile()` → `ReconciliationReport` |
| **CF** | Engine configuration (for example the enabled instruments). Used only to show `NOT CONFIGURED`, never as a market value |
| **LK** | The UI's own link state (connected / reconnecting / gap reset); concerns only the UI link |

### 2.1 Producer audit (as of Phase 7, commit `2085f25`; re-run at every visual phase gate)

| Has a producer | No producer yet (display shows `NOT AVAILABLE`) |
|---|---|
| `run.started` / `resumed` / `completed` / `failed` / `stage.completed`; `research.item.collected` / `accepted` / `rejected`; `research.snapshot.created`; `snapshot.created`; `analysis.created`; `setup.state.changed`; `debate.started` / `turn.completed` / `completed`; `decision.research_plan.created` / `trader_plan.created` / `final.created`; `trade.proposed`; `risk.check.started` / `completed`; `risk.approved` / `rejected` / `review.requested`; `circuit_breaker.tripped` / `reset` / `reset_refused`; `order.created` / `filled` / `rejected` / `cancelled` / `expired` / `preflight.failed`; `position.opened` / `updated`; `trade.closed`; `account.opened` / `snapshot.created`; `agent.task.*`; `agent.llm_call.started` / `completed` | `station.alert_level.changed`; `station.heartbeat.emitted`; `market.quote.received`; `market.session.changed`; `market.focus.changed`; `market.data.stale_detected`; `snapshot.rejected`; `order.sent`; `order.acknowledged`; `order.partially_filled`; `risk.limit.approached`; `memory.*`; `wellbeing.load.updated`; `budget.warning`; `agent.state.changed` / `moved` / `resting` / `rest.ended` / `degraded` / `overloaded` / `wrap_up.forced`; `agent.tool_call.*`; `system.paused` / `resumed` |

**Configured instruments today (CF):** XAU/USD, EUR/USD, USD/JPY, NAS100. The specialist family
displays list only these. Other family members (XAG, FX minors, other indices) show
`NOT CONFIGURED` when a slot is shown at all.

### 2.2 Station alert level (derived until a producer exists)

| Level | Derived from |
|---|---|
| **RED** | Breaker `TRIPPED`, or `HealthReport.status = FAILED` |
| **AMBER** | `risk.review.requested`, `HealthReport.status = DEGRADED` / `BLOCKED`, or a reconciliation issue |
| **BLUE** | A run in progress (`run.started` with no terminal `run.*` yet) |
| **GREEN** | None of the above, and fresh telemetry |
| *(none; shows **NO TELEMETRY**)* | No snapshot yet, or link down past its window |

## 3. Display states and placeholders

| State | Placeholder / treatment |
|---|---|
| `LIVE` | Values with timestamps |
| `STALE` | Dimmed, hatched, **"STALE · <age>"** |
| `AWAITING` | **"AWAITING DATA"**: the producer exists, but nothing has arrived this session. No value, no zero |
| `NOT_AVAILABLE` | **"NOT AVAILABLE"** plus the feed name: no producer exists (§2.1) |
| `NOT_CONFIGURED` | **"NOT CONFIGURED"**: the feature or instrument is switched off in configuration |
| `UNKNOWN` | The field shows **"UNKNOWN"** in amber: the event arrived but the field is missing. For the mode plaque this is **"MODE UNKNOWN"** |
| `LINK_DOWN` | Frozen and greyed, **"LINK DOWN · <age>"** |
| `PLANNED` | Not rendered |

`LINK_DOWN` and `STALE` never change a value; they change only how it is drawn. A display fault
(renderer exception) shows **"DISPLAY FAULT"**, never a frozen number without a label (A23).

---

## 4. Summary

| Room | Code | Displays | Planned |
|---|---|---|---|
| `H-CMD` Main Command | CMD | 12 | 0 |
| `H-LAB` Lab / Research Hub | LAB | 13 | 5 (Research Lab) |
| `H-HAB` Habitat | HAB | 4 | 0 |
| `L1` Market Specialists | SPC | 4 | 0 |
| `L2` Technical Deck | TEC | 7 | 0 |
| `L3` Debate Chamber | DEB | 6 | 0 |
| `L4` Data Core | DCR | 6 | 0 |
| `L6` Memory Archive | MEM | 4 | 0 |
| `L7` Performance Lab | PRF | 5 | 0 |
| `L9` Execution Bay | EXB | 5 | 0 |
| `L10` Risk Control Room | RSK | 9 | 0 |
| `R1` Coaching Room (designated) | CCH | 4 | 4 |
| Corridors | CRN, CRS | 2 | 0 |
| Reserved rooms L5, L8, R2–R6 | — | 0 | — |
| **Total** | | **81** | **9** |

**Availability as of Phase 7** (against §2.1): **50 available** (`A`), **11 partial** (`P`), **11 not available** (`N`), **9 planned** (`X`).

Column key:
- **HW** = hardware type;
- **Src** = source (§2);
- **Av** = availability: `A` available, `P` partial, `N` not available, `X` planned;
- **I/O** = `RO` / `NAV`.

---

## 5. Display tables

### 5.1 `H-CMD` — Main Command

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-CMD-01` | Market Overview (main viewscreen, north rim) | `SCR-001` | The configured instruments grouped by family: latest snapshot price context with its time, session, active setup and latest specialist view | EV · `snapshot.created`, `setup.state.changed`, `analysis.created`; SN; CF | P | NAV | Live quotes → **NOT AVAILABLE · live quotes** (snapshot values never pose as live) |
| `DSP-CMD-02` | Technical Analysis summary | `SCR-002` | Setup states per instrument; latest technical assessment | EV · `setup.state.changed`, `analysis.created` | A | NAV | **AWAITING DATA** |
| `DSP-CMD-03` | Research / News | `SCR-002` | Latest research snapshot (counts, labels) and macro assessment | EV · `research.snapshot.created`, `analysis.created` (macro) | A | NAV | **AWAITING DATA**; news feed → dormant (R3 deferred) |
| `DSP-CMD-04` | Agent Pipeline | `SCR-005` | The decision chain in the engine's run order (technical → research → specialists → debate → setup → trader → approval → risk → execution → review): each stage lit **only** by its event, with a timestamp; the working agents per stage | EV · the chain events, `agent.task.*`; RL checkpoints | A | NAV | Unreached stages stay unlit |
| `DSP-CMD-05` | Portfolio | `SCR-002` | Paper balance / equity, open positions, P&L, drawdown | EV · `account.snapshot.created`, `position.*`, `trade.closed`; SN | A | NAV | Missing economics → **UNKNOWN** |
| `DSP-CMD-06` | Global System Status | `SCR-002` | Health status and reasons, runs by state, breaker state, alert level, link state | HL; RL; LK; derived alert | A | NAV | Never "HEALTHY" by default; old read → **STALE** |
| `DSP-CMD-07` | Alert band | `SCR-005` | Alert level word + icon | derived (§2.2) | P | RO | **NO TELEMETRY** |
| `DSP-CMD-08` | Execution-mode plaque | `SCR-009` | **PAPER** from telemetry | EV · `account.opened`; SN | P | RO | **MODE UNKNOWN** (amber) |
| `DSP-CMD-09` | Central Trader console | `SCR-004` | **All concurrent opportunities**: each trader plan / setup with its instrument, family, stage and age; a count | EV · `decision.trader_plan.created`, `setup.state.changed`, `run.*` | A | NAV | **AWAITING DATA** |
| `DSP-CMD-10` | Proposal console | `SCR-004` | Latest proposal: direction, entry, stop, target, reward:risk, rating, contradictions | EV · `trade.proposed`, `decision.final.created` | A | NAV | **AWAITING DATA** |
| `DSP-CMD-11` | Operations console (Supervisor) | `SCR-004` | Run lifecycle, stage timings, LLM calls / retries / failures, cost with currency | RL; MT; EV · `run.stage.completed`, `agent.llm_call.*` | A | NAV | Null totals → **UNKNOWN** |
| `DSP-CMD-12` | Budget console (Quartermaster) | `SCR-004` | Budgets and warnings | EV · `budget.warning` (no producer) | N | RO | **NOT AVAILABLE · budgets** |

### 5.2 `H-LAB` — Lab / Research Hub

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-LAB-01` | Source feeds | `SCR-002` | New items per collector role, source and age; deferred roles show dormant | EV · `research.item.collected` | A | NAV | **AWAITING DATA** per role |
| `DSP-LAB-02` | Source validation board | `SCR-002` | Accepted / rejected items with reasons (source, freshness, duplicates) | EV · `research.item.accepted` / `rejected` | A | NAV | **AWAITING DATA** |
| `DSP-LAB-03` | Evidence board | `SCR-002` | Accepted claims labelled FACT / REACTION / INTERPRETATION, with citations | EV · `research.item.accepted`, `research.snapshot.created` | A | NAV | **AWAITING DATA** |
| `DSP-LAB-04` | Freshness clocks | `SCR-010` | Age of the newest item per role | EV · `research.item.collected` | A | RO | **STALE** |
| `DSP-LAB-05` | Research snapshot pulse | `SCR-006` | Latest snapshot id, counts, duplicates merged | EV · `research.snapshot.created` | A | NAV | **AWAITING DATA** |
| `DSP-LAB-06` | Macro context | `SCR-002` | Drivers with direction and strength, cited claim ids, coverage | EV · `analysis.created` (macro) | A | NAV | **AWAITING DATA**; shown with age between cycles |
| `DSP-LAB-07` | Specialist market views (repeater) | `SCR-003` | Latest view per family (Metals / FX / Indices) | EV · `analysis.created` (market), mapped by family (Character Registry §5) | A | NAV | **AWAITING DATA** |
| `DSP-LAB-08` | Hypotheses | `SCR-003` | Research hypotheses | No producer | N | RO | **NOT AVAILABLE · hypotheses** |
| `DSP-LAB-10` | Experiment state | `SCR-002` | Research Lab | — | X | — | not rendered |
| `DSP-LAB-11` | Validation result | `SCR-003` | Research Lab | — | X | — | not rendered |
| `DSP-LAB-12` | Out-of-sample results | `SCR-003` | Research Lab | — | X | — | not rendered |
| `DSP-LAB-13` | Regime comparison | `SCR-003` | Research Lab | — | X | — | not rendered |
| `DSP-LAB-14` | Experiment history | `SCR-002` | Research Lab | — | X | — | not rendered |

`DSP-LAB-09` is deliberately left unused, to separate the research-team block from the lab block.

### 5.3 `L1` — Market Specialists Room

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-SPC-01` | Metals desk | `SCR-004` | **One row per underlying runtime agent** (today: S1 / XAU/USD): its own state, task, pressure, drivers, counter-evidence, event risk, coverage, age | EV · `analysis.created` (market; `specialist_xauusd` today); CF | P | NAV | XAG → **NOT CONFIGURED**; no view → **AWAITING DATA** |
| `DSP-SPC-02` | FX desk (multi-pair scan) | `SCR-004` | **One row per underlying runtime agent** (today: S2 / EUR/USD **and** S3 / USD/JPY, shown **side by side**), each with its **own** state chip, task, latest view and age; the count of active rows. The desk never shows one merged state (Character Registry §5.2) | EV · `analysis.created` (`specialist_eurusd`, `specialist_usdjpy` today); CF | A | NAV | Unconfigured pairs are not listed; **AWAITING DATA** per pair |
| `DSP-SPC-03` | Indices desk | `SCR-004` | **One row per underlying runtime agent** (today: S4 / NAS100): its own state, task, view and age; extensible | EV · `analysis.created` (`specialist_nas100` today); CF | A | NAV | **AWAITING DATA** |
| `DSP-SPC-04` | Macro context repeater | `SCR-003` | Same content as `DSP-LAB-06` | EV · `analysis.created` (macro) | A | RO | **AWAITING DATA** |

Footer on every specialist desk: **"Family desk · interim view of N runtime agents"** (interim adapter; removed after the engine migrates to family specialists).

### 5.4 `L2` — Technical Deck

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-TEC-01` | Chart table | `SCR-012` | Candles (and structure overlays) of the run's technical analysis, one timeframe | RL · the `TECHNICAL` checkpoint (`run.stage.completed`: `outputs.analysis` candles); EV · `snapshot.created` for freshness only (it carries no bars) | A | RO | **AWAITING DATA** / **STALE** |
| `DSP-TEC-02` | Indicator panels | `SCR-002` | SMA / EMA / RSI / MACD / Bollinger / ATR values, as configured and computed by the engine; volatility | RL · the `TECHNICAL` checkpoint (`indicators`, `volatility`); EV · `analysis.created` (`momentum`) as trigger and ids (it carries no values) | A | RO | Disabled indicator → **NOT CONFIGURED**; unevaluated → **NOT AVAILABLE** with the engine's reason |
| `DSP-TEC-03` | Structure & zones | `SCR-002` | Structure state; swings, structure events, levels and zones | EV · `analysis.created` (`structure`: state and ids); RL · the `TECHNICAL` checkpoint (levels, zones) | A | RO | **AWAITING DATA** |
| `DSP-TEC-04` | Setup lifecycle | `SCR-005` | Setup states per instrument | EV · `setup.state.changed` | A | NAV | **NO ACTIVE SETUP** |
| `DSP-TEC-05` | Pullback state | `SCR-003` | Pullback on the active setup's reference leg | EV · `setup.state.changed` (setup, reference leg); RL · the `TECHNICAL` checkpoint (`pullback`) | A | RO | **NO ACTIVE SETUP** |
| `DSP-TEC-06` | Entry timing | `SCR-003` | Entry-timing countdown | No producer | N | RO | **NOT AVAILABLE · entry timing** |
| `DSP-TEC-07` | Session clock | `SCR-010` | Market sessions | EV · `market.session.changed` (no producer) | N | RO | **NOT AVAILABLE · session feed**; the ring shows UTC (UI clock, not market state) |

### 5.5 `L3` — Debate Chamber

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-DEB-01` | Bull wall | `SCR-002` | Bull arguments | EV · `agent.task.completed` (`bull_researcher`: the case) paired with `debate.turn.completed` (round, side; carries no arguments) | A | RO | **NO DEBATE IN PROGRESS** |
| `DSP-DEB-02` | Bear wall | `SCR-002` | Bear arguments | EV · `agent.task.completed` (`bear_researcher`: the case) paired with `debate.turn.completed` (round, side; carries no arguments) | A | RO | as above |
| `DSP-DEB-03` | Evidence projector | `SCR-012` | Evidence cited in the current turn | EV · the speaking role's `agent.task.completed` (cited evidence ids) paired with `debate.turn.completed` | A | NAV | **NO EVIDENCE CITED** |
| `DSP-DEB-04` | Round counter | `SCR-003` | Round n of N; debate type | EV · `debate.started`, `debate.turn.completed` | A | RO | as above |
| `DSP-DEB-05` | Contradiction feed | `SCR-003` | P2 contradiction findings of the debate (remote data feed) | EV · `debate.completed` (findings) | A | RO | **AWAITING DATA** |
| `DSP-DEB-06` | Verdict | `SCR-005` | Research plan / debate outcome | EV · `debate.completed`, `decision.research_plan.created` | A | NAV | **PENDING** |

### 5.6 `L4` — Data Core (system)

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-DCR-01` | Snapshot pulse | `SCR-006` | Market snapshots: time, instruments | EV · `snapshot.created` | A | RO | **AWAITING DATA** |
| `DSP-DCR-02` | Feed health | `SCR-002` | Per-source feed health, stale alerts | EV · `market.data.stale_detected`, `snapshot.rejected` (no producers) | N | RO | **NOT AVAILABLE · feed health** |
| `DSP-DCR-03` | Journal & event-stream health | `SCR-003` | Journal sequence, last event time, link state | EV sequence; LK | A | RO | **LINK DOWN · <age>** |
| `DSP-DCR-04` | Runtime health | `SCR-003` | `HealthReport`: status, reasons | HL | A | RO | **STALE** |
| `DSP-DCR-05` | Reconciliation | `SCR-004` (on `CON-027`) | Reconciliation status and issues | RC; HL | A | RO | **STALE** |
| `DSP-DCR-06` | Heartbeat | `SCR-011` | Engine heartbeat | EV · `station.heartbeat.emitted` (no producer) | N | RO | **NOT AVAILABLE · heartbeat** |

### 5.7 `L6` — Memory Archive

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-MEM-01` | Trade history | `SCR-002` | Closed paper trades: instrument, direction, close reason, price change, money P&L only when `KNOWN` (else the engine's reason); R multiple **NOT AVAILABLE** (not computed; L6 sheet DM-4) | EV · `trade.closed` | A | NAV | **NO CLOSED TRADES** |
| `DSP-MEM-02` | Run replay index | `SCR-003` | Recorded runs with state and stages; a click opens a **read-only** replay | RL | A | NAV | **AWAITING DATA** |
| `DSP-MEM-03` | Reviews & lessons | `SCR-003` | Post-trade reviews and reflections | EV · `memory.review.created`, `memory.reflection.written` (no producers) | N | RO | **NOT AVAILABLE · reviews** |
| `DSP-MEM-04` | Comparable setups | `SCR-012` | Stored comparable decisions | EV · `memory.decision.stored` (no producer) | N | RO | **NOT AVAILABLE · memory store** |

### 5.8 `L7` — Performance Lab

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-PRF-01` | Outcome board | `SCR-002` | Win / loss, expectancy, R distribution, from closed trades only | EV · `trade.closed` | P | RO | Below the sample threshold → **INSUFFICIENT SAMPLE** (hatched) |
| `DSP-PRF-02` | Runtime metrics | `SCR-002` | Runs by outcome, stage timings | MT | A | RO | **STALE** |
| `DSP-PRF-03` | Execution metrics | `SCR-003` | Paper submissions, execution failures, order outcomes | MT; EV · `order.*` | A | RO | **STALE** |
| `DSP-PRF-04` | Attribution | `SCR-003` | Per-agent contribution | Needs `memory.outcome.settled` (no producer) | N | RO | **NOT AVAILABLE · attribution** |
| `DSP-PRF-05` | Workload & review metrics | `SCR-003` | Task counts, durations and failures per agent; LLM retries; review outcomes where they exist | EV · `agent.task.*`, `agent.llm_call.*`; MT | P | RO | Failed-review counts → **NOT AVAILABLE** until review events exist |

### 5.9 `L9` — Execution Bay

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-EXB-01` | Order lifecycle | `SCR-002` | created → filled / rejected / cancelled / expired → closed | EV · `order.*`, `trade.closed` | P | NAV | `sent` / `acknowledged` / `partially filled` steps drawn as **NOT AVAILABLE**, never skipped as if they happened |
| `DSP-EXB-02` | Working orders | `SCR-003` | Orders not yet final: PENDING / BLOCKED | EV · `order.created`, `order.preflight.failed` | A | RO | **NO WORKING ORDERS** |
| `DSP-EXB-03` | Positions | `SCR-003` | Open paper positions and unrealised P&L | EV · `position.*`; SN | A | RO | **UNKNOWN** |
| `DSP-EXB-04` | Pre-flight results | `SCR-004` | Pre-flight checks for the latest order | EV · `order.created`, `order.preflight.failed` | A | RO | **AWAITING DATA** |
| `DSP-EXB-05` | Hull mode marking | `SCR-009` | Large **PAPER** from telemetry | as `DSP-CMD-08` | P | RO | **MODE UNKNOWN** |

### 5.10 `L10` — Risk Control Room

| ID | Name | HW | Content | Src · events | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-RSK-01` | Proposal intake | `SCR-004` (on `CON-012`) | The proposal under review: direction, entry, stop, size, % of equity at stop | EV · `trade.proposed`, `risk.check.started` | A | RO | **AWAITING DATA**; missing economics → **UNKNOWN** |
| `DSP-RSK-02` | Contradictions | `SCR-004` | Contradictions checked at intake | EV · `trade.proposed` | A | RO | Missing field → **UNKNOWN**; "NONE REPORTED" only when present and empty |
| `DSP-RSK-03` | Risk Rules | `SCR-002` | Every rule: value vs limit, pass / fail | EV · `risk.check.completed` | A | RO | Rows show **PENDING**; never pre-ticked |
| `DSP-RSK-04` | Exposure | `SCR-003` | Exposure bars by instrument / currency | EV · `position.*`, `account.snapshot.created`; SN | A | RO | **UNKNOWN** |
| `DSP-RSK-05` | Circuit Breaker | `SCR-005` | `ARMED` / `TRIPPED`, trip reason, reset and refused-reset history (**display only**) | EV · `circuit_breaker.*`; HL | A | RO | **UNKNOWN**, never "ARMED" by default |
| `DSP-RSK-06` | Approval Queue | `SCR-003` | Proposals awaiting a risk decision, and `REVIEW_REQUIRED` items | EV · `trade.proposed`, `risk.check.*`, `risk.review.requested` | A | RO | **QUEUE EMPTY** only when the data is fresh |
| `DSP-RSK-07` | Pending / Blocked Orders | `SCR-003` | Pending orders, pre-flight blocks, risk rejections with reasons | EV · `order.created`, `order.preflight.failed`, `risk.rejected` | A | RO | **NONE** only when the data is fresh |
| `DSP-RSK-08` | Paper P&L | `SCR-003` | Realised and unrealised paper P&L, drawdown | EV · `account.snapshot.created`, `trade.closed`, `position.updated`; SN | A | RO | **UNKNOWN** |
| `DSP-RSK-09` | Door status panel (corridor side of `DR-L10`) | `SCR-011` | Breaker word + icon (**BREAKER TRIPPED** / ARMED) | as `DSP-RSK-05` | A | RO | **UNKNOWN** |

### 5.11 `H-HAB` — Habitat

| ID | Name | HW | Content | Src | Av | I/O | Missing / stale |
|---|---|---|---|---|---|---|---|
| `DSP-HAB-01` | Alert repeater (café) | `SCR-011` | Alert word + icon | derived | P | RO | **NO TELEMETRY** |
| `DSP-HAB-02` | Agent load (recovery zone) | `SCR-002` | Per-agent load / overload | EV · `wellbeing.load.updated`, `agent.overloaded` (no producers) | N | RO | **NOT AVAILABLE · load** |
| `DSP-HAB-03` | Retries & latency (recovery zone) | `SCR-003` | LLM retries, failures and timings | MT; EV · `agent.llm_call.*` | A | RO | **UNKNOWN** for null totals |
| `DSP-HAB-04` | Rest schedule (recovery zone) | `SCR-003` | Real cooldowns | EV · `agent.resting`, `agent.rest.ended` (no producers) | N | RO | **NOT AVAILABLE · rest schedule** |

### 5.12 `R1` — Performance & Wellbeing / Coaching Room (PLANNED)

| ID | Name | Intended content (measurable signals only) | Av |
|---|---|---|---|
| `DSP-CCH-01` | Team debrief board | Run outcomes and failed stages after difficult runs | X |
| `DSP-CCH-02` | Repeated-error review | Recurring `agent.task.failed` patterns per agent | X |
| `DSP-CCH-03` | Workload balance | Task counts, durations, retries, long-running tasks | X |
| `DSP-CCH-04` | Conflict & recovery | Conflict frequency (contradiction flags, debate reversals); real-cooldown recommendations | X |

No emotion, mood or diagnosis wording on any coaching display.

### 5.13 Corridors

| ID | Name | HW | Content | Av | I/O | Missing |
|---|---|---|---|---|---|---|
| `DSP-CRN-01` | `COR-N` alert repeater | `SCR-011` | Alert word + icon | P | RO | **NO TELEMETRY** |
| `DSP-CRS-01` | `COR-S` alert repeater | `SCR-011` | Alert word + icon | P | RO | **NO TELEMETRY** |

---

## 6. Owner screen themes → displays

| Owner theme | Displays |
|---|---|
| **Main Command:** Market Overview, Technical Analysis, Research / News, Agent Pipeline, Portfolio, Global System Status | `DSP-CMD-01`, `-02`, `-03`, `-04`, `-05`, `-06` |
| **Risk:** Exposure, Circuit Breaker, Risk Rules, Approval Queue, Pending / Blocked Orders, Paper P&L | `DSP-RSK-04`, `-05`, `-03`, `-06`, `-07`, `-08` |
| **Research:** hypotheses, evidence, source validation, macro context, specialist market views | `DSP-LAB-08` (NOT AVAILABLE), `-03`, `-02`, `-06`, `-07` (+ `DSP-SPC-01`…`-03`) |
| **Research Lab:** experiment state, validation result, OOS results, regime comparison, experiment history | `DSP-LAB-10`…`-14` (PLANNED) |
| **System / Memory:** journal, replay, reconciliation, health | `DSP-DCR-03`, `DSP-MEM-02`, `DSP-DCR-05`, `DSP-DCR-04` |
| **Performance:** runtime metrics, execution metrics, attribution, workload / review metrics | `DSP-PRF-02`, `-03`, `-04` (NOT AVAILABLE), `-05` |

## 7. Changes from v1 (concept carry-over)

| v1 concept | v2 display |
|---|---|
| Main viewscreen (decision chain) + decision-chain strip | `DSP-CMD-04` Agent Pipeline; `DSP-CMD-01` becomes Market Overview |
| Portfolio & risk wall, operations wall | `DSP-CMD-05`, `DSP-CMD-06`, `DSP-CMD-11` |
| Market strip (NOT AVAILABLE) | folded into `DSP-CMD-01` (live quotes NOT AVAILABLE) |
| Research Observatory (6) + Macro & News (5) | `DSP-LAB-01`…`08`. Central-bank board, calendar and rates boards dropped: no producers, and no invented boards |
| Market Analysis Wing: 4 instrument desks + session clock | `DSP-SPC-01`…`03` (3 families) + `DSP-TEC-07` |
| Technical Deck, Debate Chamber | `DSP-TEC-01`…`06`, `DSP-DEB-01`…`06` (unchanged content) |
| Risk Vault (7) | `DSP-RSK-01`…`09`: adds Approval Queue, Pending / Blocked Orders and Paper P&L; lift indicator removed |
| Execution Bay (6) | `DSP-EXB-01`…`05`; reconciliation moved to `DSP-DCR-05` |
| Data Core, Memory, Performance, Wellbeing | `DSP-DCR-*`, `DSP-MEM-*` (+ replay index), `DSP-PRF-*` (+ workload / review), `DSP-HAB-02`…`04`, `DSP-CMD-12` |
| Café / Lounge / Observation / lobby repeaters (9) | `DSP-HAB-01`, `DSP-CRN-01`, `DSP-CRS-01` |
| Lift indicators, `SEALED` state | **removed** (no lifts) |
| Placeholder "AWAITING TELEMETRY" | now **"AWAITING DATA"** (owner wording) |

## 8. Verification rules

- Every `DSP-…` in the Room Registry exists here, and every display here belongs to a room or
  corridor of Topology v2.
- Every `HW` value is an active `SCR-…` type in the Asset Registry (`SCR-008` is retired).
- Golden tests (A26):
  - recorded runs replay to identical values;
  - producer-removed fixtures show the exact `NOT AVAILABLE` placeholder;
  - stale fixtures show `STALE · <age>`;
  - a gap reset returns every display to `AWAITING DATA`.
- A static check that no display module imports sample or mock data outside test fixtures.
- Availability counts (§4) are recomputed from §5 at each visual phase gate.

## 9. Open decisions

| # | Decision | Default |
|---|---|---|
| SR-1 | Engine producer for `station.alert_level.changed` vs the adapter derivation | Adapter derivation |
| SR-2 | Freshness windows per display family | Short, fixed, configurable |
| SR-3 | Focus rule for `DSP-CMD-01` when several runs are active | Show all configured instruments; highlight active runs |
| SR-4 | Snapshot prices on `DSP-CMD-01` with a snapshot-time label | Shown with the snapshot time; live quotes NOT AVAILABLE |
| SR-5 | Sample-size threshold for "insufficient sample" | From engine performance settings; otherwise always hatched |
| SR-6 | An explicit execution-mode field in `run.started` / `account.opened` (an engine change) | Inferred from the Paper Broker `account.opened` |
