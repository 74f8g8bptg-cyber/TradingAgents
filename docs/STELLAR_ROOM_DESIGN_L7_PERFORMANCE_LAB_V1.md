# Stellar Room Design Sheet — L7 Performance Lab (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; DP-1…DP-9 decided, DP-10 / DP-11 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change, no trading logic |
| **Room** | `L7` — Performance Lab · ACTIVE · public (Room Registry v2 §3.9) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Figures: `STELLAR_CHARACTER_REGISTRY.md` §3–§4, `STELLAR_CHARACTER_BIBLE_V1.md`. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Background: `STELLAR_LAYER_DESIGN.md`, `STELLAR_MASTER_ROADMAP.md`, `STELLAR_PHASE4_PAPER_BROKER.md`, `STELLAR_PHASE7_V1_PAPER_END_TO_END.md`. Engine facts: `stellar/src/stellar/runtime/metrics.py`, `runtime/reconcile.py`, `runtime/ledger.py`, `execution/paper.py`, `execution/state.py`, `execution/models.py`, `config/models.py`, `risk/rules.py`, `telemetry/catalogue.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | L7 answers **"what actually happened?"**, never "who is winning?". It shows engine-recorded outcomes and engine-computed counts only. The visual layer never calculates a metric, score, rate, ratio, ranking or benchmark, and nothing here authorises, sizes or changes a trade |

---

## 1. StarNet concept review (outcomes, statistics, reports, progress)

**Method.** I read the audit (S43, S46) and the local StarNet checkout at pinned revision
`fbddbf99` **read-only**:
- `frontend/app/floorstats.js`: a few read-outs folded from real outcome events; a metric with no
  real sample reports `known:false` and shows "—"; proof / sample dispatches are excluded;
- `sidecar/recommendation-ledger.js`: a lifecycle ledger (shown → outcome) whose pure `replay()` gives
  "identical history → identical metrics";
- `frontend/app/nightreport.js`: one digest of what happened **and** what was declined, "every line
  maps to one provable field";
- `frontend/app/linewatch.js`: per-station last outcome and status priority with an honest unknown;
- `frontend/app/xp.js`: XP, levels, a confidence gauge and reliability per agent.

StarNet measures harness runs, not trading. Only structural ideas are taken. **Nothing is copied:**
no art, layouts, interfaces, characters, assets, dialogue, personality systems, XP or game
mechanics, and no artificial performance score.

| StarNet concept | Structural idea | How Stellar adapts it | What Stellar rejects |
|---|---|---|---|
| **Folds of real outcome events; `known:false` until a real sample** (`floorstats.js`) | A figure exists only if real events produced it | Every L7 value is an engine value (`runtime_metrics`, account state, `trade.closed`, `order.*`); a metric the engine does not compute reads **NOT AVAILABLE**, never a placeholder number (adaptation A19) | Yield, "slag", cache, throughput and dwell gauges |
| **Test dispatches excluded from stats** (`sample:true`) | Results from different contexts are never pooled | **Environment isolation:** every value is labelled with its account id and mode (only `PAPER` exists); PAPER, future DEMO and LIVE are never merged (§8) | — |
| **Deterministic replay of a ledger** (`recommendation-ledger.js` `replay()`) | Same history → same numbers | Stellar's `runtime_metrics()` and `reconcile()` are already deterministic folds of the journal; L7 shows their results with the time they were read | Preference weights, feedback learning, recommendation verdicts |
| **"What happened and what was declined"** (`nightreport.js`) | An honest digest includes the refusals and the "nothing happened" cases | Run outcomes include `NO_SETUP`, `REVIEW_REQUIRED`, `REJECTED` and `FAILED` alongside `COMPLETED`; execution failures are shown next to submissions | The persona "morning report" story; narrative text |
| **Per-station last outcome, honest unknown** (`linewatch.js`, S46) | Status comes from confirmed events only | Per-order outcomes come from the order's own events (`order.filled` / `rejected` / `cancelled` / `expired` / `preflight.failed`) | Lamp colours as the only signal |
| **XP, levels, confidence and reliability per agent** (`xp.js`) | Growth meters per agent | — | **Rejected: cannot be adapted honestly.** Stellar has no agent scoring, and rankings, XP, levels and badges are gamification |
| Idle "sentience" engine, StarNet art / HUD | — | — | **Rejected** (S27, S33, S34, S45) |

**Stellar original design (not from StarNet):** the metrics terminal, the evidence boards, the
environment labels, the layout, materials and lighting (§3).

---

## 2. Engine truth (what exists today)

### 2.1 Internal paper trading — implemented (V1 PAPER)

The **Paper Broker** (`execution/paper.py`, Phase 4) and the **V1 PAPER runtime**
(`runtime/orchestrator.py`, Phase 7) exist and are tested:

| Capability | Exists? | How |
|---|---|---|
| Receive market prices | **Yes, pushed in** | A `Quote` or closed `Candle` is passed explicitly (`PaperRuntime.run` / `advance` / `close`); there is **no continuous feed or scheduler** |
| Create virtual orders | **Yes** | `order.created` after the Execution Checker passes (`order.preflight.failed` otherwise) |
| Fill virtual orders | **Yes** | Conservative fill rules; `order.filled` |
| Reject, cancel and expire orders | **Yes** | `order.rejected`, `order.cancelled`, `order.expired` (and `order.preflight.failed` before acceptance) |
| Maintain virtual positions | **Yes** | `position.opened`, `position.updated` |
| Close virtual positions | **Yes** | Stop, target or manual close → `trade.closed` (full `TradeRecord`) |
| Virtual P&L | **Yes, with honest unknowns** | Per trade: `price_change` always; money only when `KNOWN`. Account: balance, realised / unrealised P&L, equity, peak equity, open risk; `None` = unknown, never zero |
| Record virtual trades | **Yes** | The journal (append-only) |

### 2.2 Not implemented (future)

| Capability | Status | Source of the plan |
|---|---|---|
| Event-driven **simulator / backtesting** | **Future** | Foundation §4.17; Phase 7 doc §1 (deferred by the owner's sequencing) |
| **Attribution** (per-agent contribution) | **Future** (no producer; `memory.outcome.settled` not emitted) | Foundation §4.22; Phase 7 doc |
| **Profile comparison** (D-7), **threshold evidence** (D-12) | **Future** | Phase 7 doc |
| **Post-Trade Reviewer** (`review/`) | **Future** (deferred in Phase 4) | Phase 4 doc |
| **MT5 DEMO** | **Future**: `ExecutionMode.DEMO` is **refused** until the Phase 8 demo gate | `config/models.py`; Roadmap Phase 8 |
| **LIVE** | **Reserved, always refused** | `config/models.py` |

### 2.3 Existing aggregation (the only computed performance-related figures)

- **`runtime_metrics(journal, runtime)`** (`runtime/metrics.py`, on demand): runs; runs by state;
  completed; no setup; review required; rejected; failed; paper submissions; execution failures
  (`order.preflight.failed` + `order.rejected`, **combined**); stage timings (count, total, max ms);
  LLM calls, attempts, retries, failed, tokens, cost (cost `None` when unknown or in mixed
  currencies). Its own header: "**No** strategy performance, ranking or profitability figure is
  computed here".
- **Account state** (`account.snapshot.created`, Paper Broker): balance, realised P&L, unrealised
  P&L, equity, peak equity, open risk, unsettled trade ids, open positions, pending orders, closed
  trades.
- **`reconcile()`** (on demand): counts of events / runs / orders / trades checked, issues.
- **Risk Engine** (L10): the current drawdown fraction (from peak and current equity) is computed
  **only** inside the `max_drawdown` pre-trade rule; it is a risk check, not a performance history.

Nothing else is aggregated: no win / loss counts, rates, expectancy, profit factor, Sharpe,
maximum drawdown history, R multiple, reward:risk, attribution, rankings or comparisons.

### 2.4 Metric availability

| Metric | Exists in engine? | Producer | Source | Displayed in L7? | Status |
|---|---|---|---|---|---|
| Closed trades (records) | Yes | Paper Broker | `trade.closed`; account state `closed_trades` | `DSP-PRF-01` (list) | **Available** |
| Closed-trade count | Yes (as the engine's records) | Paper Broker; `reconcile()` (`trades_checked`) | Account state; RC | `DSP-PRF-01` | **Available** |
| Wins / losses (counts) | **No** | — | (only per-trade `price_change`) | — | **NOT AVAILABLE** (never counted by the UI) |
| Per-trade P&L | Yes | Paper Broker | `trade.closed` `realised` | `DSP-PRF-01` | **Available** (money only when `KNOWN`, else the engine's reason) |
| Realised P&L (account) | Yes | Paper Broker | `account.snapshot.created` `realised_pnl` | `DSP-PRF-01` | **Available** (`None` → **UNKNOWN**) |
| Balance, equity, peak equity, open risk | Yes | Paper Broker | `account.snapshot.created` | `DSP-PRF-01` (account strip) | **Available** (`None` → **UNKNOWN**) |
| Price change per trade | Yes | Paper Broker | `trade.closed` | `DSP-PRF-01` | **Available** |
| Execution outcome per order | Yes | Paper Broker | `order.*` events | `DSP-PRF-03` | **Available** |
| Paper submissions (count) | Yes | `runtime_metrics` | MT | `DSP-PRF-03` | **Available** |
| Execution failures (count) | Yes, **combined** | `runtime_metrics` | MT (`preflight.failed` + `rejected`) | `DSP-PRF-03` | **Available** (combined only) |
| Rejected orders (separate count) | **No** | — | — | — | **NOT AVAILABLE** as a count |
| Cancelled / expired orders (counts) | **No** (events exist) | — | — | Per-order rows only | **NOT AVAILABLE** as counts |
| Runs by state, stage timings | Yes | `runtime_metrics` | MT | `DSP-PRF-02` | **Available** |
| LLM calls, retries, tokens, cost | Yes (station-wide) | `runtime_metrics` | MT | `DSP-PRF-05` | **Available** |
| Per-agent task counts / durations | **No** | — | (`agent.task.*` events exist) | — | **NOT AVAILABLE** as metrics |
| Drawdown (max, history) | **No** | — | — | — | **NOT AVAILABLE** (current drawdown exists only as an L10 risk rule input) |
| Win rate | No | — | — | — | **NOT AVAILABLE** |
| Expectancy | No | — | — | — | **NOT AVAILABLE** |
| Profit factor | No | — | — | — | **NOT AVAILABLE** |
| Sharpe / Sortino | No | — | — | — | **NOT AVAILABLE** |
| R multiple | No | — | — | — | **NOT AVAILABLE** (L6 DM-4) |
| Reward / risk | No (`reward_risk` stays `None`; `min_reward_risk` NOT CONFIGURED) | — | — | — | **NOT AVAILABLE** |
| Attribution | No | — | `memory.outcome.settled` (no producer) | `DSP-PRF-04` | **NOT AVAILABLE** |
| Strategy / profile comparison | No | — | — | — | **NOT AVAILABLE** (future D-7) |
| Environment comparison | No (only PAPER exists) | — | — | — | **NOT AVAILABLE** (and never mixed) |
| Agent performance / ranking | No | — | — | — | **NOT AVAILABLE** (rankings rejected) |
| Review outcomes | No | — | `memory.review.created` (no producer) | `DSP-PRF-05` | **NOT AVAILABLE** |

### 2.5 The four kinds of question, kept separate

| Kind | Question | What exists today | Where |
|---|---|---|---|
| **System validation** | Did the software behave correctly? | Run states, stage timings, execution failures, LLM retries (`runtime_metrics`); journal integrity and reconciliation (L4) | `DSP-PRF-02`, `-03`, `-05`; L4 |
| **Trading outcome** | What happened to an individual paper trade? | The `TradeRecord` per closed trade | `DSP-PRF-01`; L6 `DSP-MEM-01` |
| **Performance analysis** | What can be calculated from recorded outcomes? | Only the engine's account aggregates (realised P&L, balance, equity, peak equity) | `DSP-PRF-01` |
| **Agent / strategy performance** | Which agent or strategy did better? | **Nothing.** No attribution, no comparison, no ranking | `DSP-PRF-04` NOT AVAILABLE |

---

## 3. Room identity, relationships and architecture

### 3.1 Identity

| Aspect | Definition |
|---|---|
| **Purpose** | The place where **recorded outcomes are examined**: closed paper trades, account aggregates, run and execution counts, and the system's own validation figures |
| **It is not** | A trading or command room, a decision room, a gamification room or a scoreboard. It never authorises a trade and never invents a score |
| **Atmosphere** | Objective, quiet, evidence-based; it neither celebrates nor shames results |
| **Visual identity** | A metrics terminal, a small review table, and a few clean evidence boards of numbers and tables, each labelled with its environment |
| **Importance** | **Medium-low today** (few computed figures); it grows only when real producers exist |

### 3.2 Relationships

| Room | Relationship (engine-true) |
|---|---|
| **L6 Memory Archive** | **Same source, different view.** L6 lists individual records (closed trades, run replay); L7 shows the engine's counts and aggregates over the same journal. **No physical hand-off:** both read the journal through the future read-only adapter; the Record Crystal goes to L6 only |
| **`H-CMD`** | **Separate role.** Decisions, approval and coordination happen in `H-CMD`; L7 never feeds a decision back. Account figures shown here are the same engine values `H-CMD` may show |
| **L9 Execution Bay** | **Source of execution outcomes.** Order and trade events come from the Paper Broker; no walk |
| **L10 Risk Control** | **Source of risk outcomes.** Runs `REJECTED` by risk are counted by `runtime_metrics`; the drawdown and daily-loss checks live in L10 and are not re-shown as performance |
| **L5** (reserved) | Shares L7's north wall; no door |

No new door or connection: L7 is reached only through `DR-L7` from `COR-S`.

### 3.3 Shape and entrance (approved; unchanged)

- **Shape:** a short rectangular room (size S; Floor Plan rev C §4: x 620–734, y 697–788, about
  114 × 91 px; **not frozen**). North of `COR-S`. North: **shared wall** with L5 (reserved), no door.
  West: L6, across **non-walkable hull** (Q4).
- **One door:** `DR-L7`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator, in
  the **south wall**, opening onto `COR-S`. **No other opening.** No lock, no new airlock, no hidden
  passage, no restricted marking (public room).
- **Cutaway:** the camera-facing walls are cut away (`WAL-008`); the door keeps a visible frame,
  threshold and opening (Visual Bible C4). No screens on a cut-away wall.

### 3.4 Schematic (not to scale; door at the bottom)

```
             north wall (shared with L5, no door)
   +----------------------------------------------+
   | DSP-PRF-01 outcome board   DSP-PRF-02 runtime |
   | (N wall, west)             metrics (N, east)  |
   |                                              |
   | CON-020 metrics            DSP-PRF-04         |
   | terminal (W wall)          attribution (E,    |
   | perflab.terminal           north; NOT AVAIL.) |
   |                                              |
   | DSP-PRF-03 execution       DSP-PRF-05         |
   | metrics (W wall, south)    workload (E, south)|
   |          TBL-005 review table                |
   |          perflab.table_1                     |
   +------------------[ DR-L7 ]-------------------+
                        COR-S
```

- **Analysis zone (north / west):** the outcome board and runtime metrics on the north wall, the
  metrics terminal and execution metrics on the west wall.
- **Comparison / review zone (centre):** the small review table. **No comparison exists today**; the
  table stays a neutral surface (§10, P9).
- **East wall:** attribution (NOT AVAILABLE) and workload.

### 3.5 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`) |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium trims** |
| Equipment | **Graphite** terminal body, table and screen bezels |
| Accent | **Restrained science blue** (SCI department) on the terminal edge. Static; never a data state |
| Boards | Numbers and tables in neutral type. **No** green = good / red = bad; gains and losses are shown with a sign and a word, never with a colour alone. **No** trophies, rankings, leaderboards, badges, XP or celebration effects |

### 3.6 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a soft light over the boards; not drawn in the cutaway |
| General | Calm neutral white; even and never dark |
| Work pool | `LGT-002` over the terminal: **off** in V1 (no producer works here) |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.7 Walkable areas and zones

| Zone | Anchor | Rule |
|---|---|---|
| Entry (inside the door) | — | The door approach tile stays empty |
| Analysis zone | `perflab.terminal` (Attribution) | Reserved; the figure stands there idle (no producer) |
| Comparison / review zone | `perflab.table_1` | **Unused in V1** (no comparison producer; §10, P9) |

---

## 4. Characters

| Aspect | Performance / Attribution — `CHR-034` (L2 `attribution`, SCI) |
|---|---|
| Registry | Home `L7` · `perflab.terminal`; ACTIVE with a **no producer** note (`memory.outcome.settled` not emitted; no L6 visit in V1) |
| Engine | **No producer**: the roster role has no code |
| Workstation / position | `CON-020` at `perflab.terminal` |
| Behaviour | `stand_idle` at the terminal, or seeded ambient via `COR-S` → `H-CMD` → `H-HAB`. **Never** shown calculating, comparing, attributing or reviewing |
| Visits | None in V1 |

| Other figures | L7 in V1 |
|---|---|
| Post-Trade Reviewer `CHR-033` | Registry lists an L7 visit; **no producer** → **no visit** |
| Supervisor `CHR-003` | No real L7 event → no visit |
| Medic persona `CHR-041` | Entry only, for a figure in a real `error` / `overloaded` state |

No roster-only role is turned into an active agent, and no runtime roles are merged.

---

## 5. Engine-supported workflow

| # | Step | Event | Producer | Consumer | Data source | Visual reaction | Status |
|---|---|---|---|---|---|---|---|
| 1 | Trade / run completes | `trade.closed`; `run.completed` / `run.failed`; `order.*` | Paper Broker; runtime | Journal | Events | Nothing animated; figures stay idle | Yes |
| 2 | Result recorded | the same events (journal `seq`) | Journal | — | Journal | — | Yes |
| 3 | Result available to L7 | account state (`account.snapshot.created`); the event itself | Paper Broker | `DSP-PRF-01`, `-03` | EV | The affected board updates **once**, at the real event | Yes |
| 4 | Metrics calculated | — (on-demand call) | `runtime_metrics()` | `DSP-PRF-02`, `-03`, `-05` | MT | The boards show the report with its read time and age | Yes, when called (on connection or on the owner's request; same rule as L4 DK-5) |
| 4a | Performance metrics (win rate, expectancy, drawdown, R …) | — | — | — | — | Read **NOT AVAILABLE** | **NOT AVAILABLE** |
| 5 | Historical results displayed | — (read) | Journal / account state | Owner | EV, MT | Tables of recorded values | Yes |
| 6 | Comparison performed | — | — | — | — | — | **NOT AVAILABLE** (no comparison, no profile comparison) |
| 7 | Report stored | — | — | — | — | — | **NOT AVAILABLE** (no performance report is produced or stored) |
| 8 | Attribution | `memory.outcome.settled` | — | — | — | `DSP-PRF-04` **NOT AVAILABLE · attribution** | **NOT AVAILABLE** |

No calculation, "thinking" or update animation is shown between real data changes.

---

## 6. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Metrics terminal** | `CON-020` | The Attribution role's station (idle today) | West wall | `perflab.terminal` (reserved) | High (as the room's anchor) |
| 2 | **Review table** | `TBL-005` | Neutral surface for future comparison | Centre | `perflab.table_1` (unused in V1) | Low |
| 3 | **Outcome board** | `SCR-002` (`DSP-PRF-01`) | Closed-trade outcomes and account aggregates | North wall, west | Look target | **Hero** |
| 4 | **Runtime metrics board** | `SCR-002` (`DSP-PRF-02`) | Runs by state, stage timings | North wall, east | Look target | High |
| 5 | **Execution metrics panel** | `SCR-003` (`DSP-PRF-03`) | Submissions, execution failures, per-order outcomes | West wall, south | Look target | Medium |
| 6 | **Attribution panel** | `SCR-003` (`DSP-PRF-04`) | NOT AVAILABLE today | East wall, north | none | Low |
| 7 | **Workload panel** | `SCR-003` (`DSP-PRF-05`) | LLM totals; per-agent items NOT AVAILABLE | East wall, south | Look target | Medium |
| 8 | Work pool light | `LGT-002` | Off in V1 | Above the terminal | none | Low |
| 9 | Room plate, emblem | `SGN-001`, `DEC-006` | Name and department emblem | Corridor side of `DR-L7` | none | Low |

**Not added:** no validation station, result table, comparison surface, chart wall or report
printer beyond these (§10, P10).

---

## 7. Screen design (Screen Registry v2 §5.8 is the authority)

Every board carries an **environment label**: the account id and the mode from the events
(`PAPER` today). DEMO and LIVE values will never share a board, a total or a chart with PAPER (§8).

| Display | Location | Purpose | Actual source | Producer | Consumer | States |
|---|---|---|---|---|---|---|
| `DSP-PRF-01` Outcome board | North wall, west | Recorded closed trades (instrument, side, close reason, price change, money P&L when `KNOWN`); account aggregates (realised P&L, balance, equity, peak equity, open risk). Win / loss counts, win rate, expectancy and R: **NOT AVAILABLE** | `trade.closed`; `account.snapshot.created` | Paper Broker | Owner | **AWAITING DATA** until the first trade / account event; money not known → **UNKNOWN** with the engine's reason; account `None` → **UNKNOWN**; **LINK DOWN · age** |
| `DSP-PRF-02` Runtime metrics | North wall, east | Runs; by state (`COMPLETED`, `NO_SETUP`, `REVIEW_REQUIRED`, `REJECTED`, `FAILED` …); stage timings | `runtime_metrics()` | Runtime (on demand) | Owner | **AWAITING DATA** until read; otherwise the report with its read time and age; **LINK DOWN · age** |
| `DSP-PRF-03` Execution metrics | West wall, south | Paper submissions; execution failures (combined); per-order outcome rows | MT; `order.*` events | Runtime; Paper Broker | Owner | **AWAITING DATA**; separate rejected / cancelled / expired **counts NOT AVAILABLE**; **LINK DOWN · age** |
| `DSP-PRF-04` Attribution | East wall, north | — | `memory.outcome.settled` (**no producer**) | — | — | **NOT AVAILABLE · attribution** ("no attribution is implemented") |
| `DSP-PRF-05` Workload & review | East wall, south | LLM calls, attempts, retries, failed, tokens, cost (station-wide) | MT | Runtime (on demand) | Owner | Per-agent task counts / durations → **NOT AVAILABLE** (not computed); review outcomes → **NOT AVAILABLE** (no review producer); cost `None` → **UNKNOWN**; **LINK DOWN · age** |

**Screen rules for this room:**
- **Never invent** a score, rate, ratio, ranking, benchmark, confidence or "accuracy", and never
  compute one in the UI from recorded rows.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **LIVE** does not
  apply (recorded history). **STALE** is not applied to on-demand reports (no age threshold exists;
  §10, P5). **MODE UNKNOWN** applies to the environment label if an event carries no mode.
- Numbers and tables only; no chart is added (no approved chart display exists for L7).
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- All displays are read-only.

---

## 8. Environments and the validation ladder

| Level | Environment | Status today | Rule |
|---|---|---|---|
| 1 | **INTERNAL PAPER TRADING** (Paper Broker, V1 PAPER runtime) | **Implemented**; prices pushed in explicitly | The only environment with results |
| 1b | **INTERNAL SIMULATION / BACKTESTING** (event-driven simulator) | **Future** (Foundation §4.17; deferred) | Would get its own label and boards |
| 2 | **MT5 DEMO** | **Future**: refused until the Phase 8 demo gate | Separate label, separate totals |
| 3 | **LIVE** | **Reserved, always refused** | Separate label, separate totals |

- Results of different environments are **never combined** in one number, table or chart.
- The configuration's `Environment` (`development` / `test` / `production`) is a separate
  configuration label, not an execution environment; a test-only configuration is already reported
  by `health()` (L4).

Future architecture (documentation only, not implemented beyond the paper path):
Market data → Stellar analysis → proposal → risk → virtual execution → virtual position →
virtual P&L → performance archive. Today this chain runs **only** as V1 PAPER runs driven by
explicit market inputs; the simulator, attribution and comparison steps are future.

---

## 9. Agent life and access

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Idle at the terminal | Always (no producer) | `CHR-034` | `stand_idle` |
| Seeded ambient | Idle | `CHR-034` | `walk`, `stand_idle` |

No calculation, comparison, reviewing, celebration or disappointment animation exists.

- **One explicit door** (`DR-L7`, `DOR-001`, south wall onto `COR-S`). No lock, no automatic door
  beyond the approved `DOR-001` behaviour, no new airlock, no hidden passage. No door to L5 or L6.
- Public room; `perflab.terminal` is reserved to `CHR-034`. **Red** only from real system states.

---

## 10. Contradictions and owner decisions

| # | Topic | Documents | Engine | Resolution |
|---|---|---|---|---|
| **P1** | **Outcome board content** | Screen Registry `DSP-PRF-01` (before): "Win / loss, expectancy, R distribution" (P) | None of these is computed | **Resolved (DP-1):** recorded trades, account totals and other engine values only. Screen Registry `DSP-PRF-01` re-worded |
| **P2** | **Planned global metrics** | Layer Design §6.1; Visual World Plan §10 (Performance Lab row) | Not computed; `runtime_metrics` explicitly excludes them | **Stands:** **NOT AVAILABLE**; never calculated (DP-2). Later task (§12) |
| **P3** | **Attribution** | Room Registry §3.9 purpose; Character Registry `CHR-034` | No producer | **Resolved (DP-6):** `CHR-034` idle; `DSP-PRF-04` **NOT AVAILABLE**; Room Registry L7 purpose note added |
| **P4** | **Workload per agent and review metrics** | Screen Registry `DSP-PRF-05` (before): "task counts, durations and failures per agent" (P) | The engine aggregates nothing per agent | **Resolved (DP-5):** station-wide AI-model call totals only. Screen Registry `DSP-PRF-05` re-worded |
| **P5** | **STALE placeholder for on-demand reports** | Screen Registry `DSP-PRF-02`, `-03` (before): **STALE** | `runtime_metrics()` is on demand; no age threshold exists | **Resolved (DP-3):** read time, age and the report values; no STALE threshold. Screen Registry placeholders re-worded |
| **P6** | **"INSUFFICIENT SAMPLE" overlay** | Screen Registry `DSP-PRF-01` (before); Visual World Plan §10 | No sample threshold and no metric that needs one | **Resolved (DP-4):** removed from `DSP-PRF-01`; deferred until a real metric and threshold exist. Visual World Plan wording is a later task (§12) |
| **P7** | **Roadmap Phase 7 content** | Roadmap / Foundation: Phase 7 "Simulation, backtesting, attribution" | The implemented Phase 7 is V1 PAPER orchestration; the rest is deferred (Phase 7 doc §1) | **Stands:** documented as future; later task (§12) |
| **P8** | **Post-Trade Reviewer visits L7** | Character Registry `CHR-033`: visits L7 | No producer | **Resolved (DP-6):** no L7 visit; Character Registry note added |
| **P9** | **Comparison zone** | Request: comparison / review zone | No comparison producer | **Stands:** neutral table; `perflab.table_1` unused in V1 |
| **P10** | **Useful objects that do not exist** | Request categories | No such assets | **Stands:** not invented |
| **P11** | **Environment separation display** | Request: INTERNAL / DEMO / LIVE kept distinct | Only PAPER exists; no environment-selector display | **Resolved (DP-7):** every board carries its environment label (`PAPER` today); PAPER, DEMO and LIVE never mixed |
| **P12** | **Separate order-outcome counts** | Screen Registry `DSP-PRF-03`: "order outcomes" | Only the combined execution-failure count is computed | **Stands:** per-order rows; separate counts **NOT AVAILABLE** |

No conflicts with:
- the topology (one door `DR-L7` on `COR-S`; shared wall with L5 without a door; L6 across hull);
- the access model, the door rules and the Visual Bible materials;
- the Character Registry (one `CHR-034` figure with its no-producer note; no merge);
- the Screen Registry display list (`DSP-PRF-01`…`05`) and its availability flag for `-04` (N);
- the StarNet exclusions (S27, S33, S34, S45).

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| DP-1 | Outcome board (P1) | **Closed:** recorded trades, account totals and available engine values only |
| DP-2 | Unsupported metrics | **Closed:** the UI never calculates or displays win rate, win / loss counts, expectancy, profit factor, Sharpe / Sortino, rankings or any other unsupported metric |
| DP-3 | On-demand reports (P5) | **Closed:** read time, age and actual values; no STALE threshold |
| DP-4 | "INSUFFICIENT SAMPLE" (P6) | **Closed:** removed / deferred until a real metric and threshold exist |
| DP-5 | Workload display (P4) | **Closed:** station-wide AI-model call totals only |
| DP-6 | Characters (P3, P8) | **Closed:** `CHR-034` idle; `CHR-033` never visits L7 |
| DP-7 | Environment (P11) | **Closed:** every board labelled; `PAPER` today; never mixed with DEMO / LIVE |
| DP-8 | Stale performance wording (P2, P6, P7) | **Closed as a later alignment task** (§12) |
| DP-9 | Layout (§3.4) | **Closed:** approved as drawn |
| DP-10 | Exact dimensions | **Open** (after the global tile scale, VB-3) |
| DP-11 | Exact colour values | **Open** (visual production, VB-4) |

---

## 12. Later alignment tasks (recorded, not done here)

- **Layer Design §6.1** (global metrics): win rate, profit factor, average R, expectancy, maximum
  drawdown, Sharpe / Sortino, rating distribution, REVIEW rate, setup hit rate, setup funnel,
  vendor error rate: all planned, none computed.
- **Visual World Plan §10** (Performance Lab row: "Win / loss; expectancy; drawdown; R-multiple
  distribution; per-agent contribution; … 'insufficient sample' overlays") and §10.2 (illustrative
  worked example).
- **Master Roadmap / Foundation Plan:** Phase 7 named "Simulation, backtesting, attribution",
  while the implemented Phase 7 is V1 PAPER orchestration (the Phase 7 doc records the owner's
  sequencing).
- **Screen Registry, other rooms' displays that name unsupported metrics:** `DSP-CMD-05`
  Portfolio and `DSP-RSK-08` Paper P&L list "drawdown", but `account.snapshot.created` carries no
  drawdown value (only equity and peak equity; the current drawdown fraction exists only inside the
  L10 `max_drawdown` rule); `DSP-CMD-10` lists "reward:risk", which the engine always leaves `None`.
  Neither may be calculated by the UI (DP-2).
- **Screen Registry §5.6:** the **STALE** placeholder for `DSP-DCR-04` / `-05` (already recorded in
  the L4 sheet §12); L7's own displays are aligned.
