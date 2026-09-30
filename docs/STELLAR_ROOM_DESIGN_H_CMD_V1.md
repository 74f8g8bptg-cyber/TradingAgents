# Stellar Room Design Sheet — H-CMD Main Command Hub (V1)

| | |
|---|---|
| **Status** | V1, design direction **approved by the owner**; HC-1, HC-2, HC-5 and HC-8…HC-20 decided; HC-3, HC-4, HC-6, HC-7 open (§12). **Revision 2 (engine audit), approved:** adds the StarNet command review, the engine audit, user interaction, authority boundaries and the workflow table; HC-8…HC-20 decided (§11). Visual design specification only: no code, no images, no assets, no runtime change, no trading logic |
| **Room** | `H-CMD` — Main Command / Central Operations (Room Registry v2 §3.2) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C and `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones and anchors: `STELLAR_ROOM_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_REGISTRY.md`, `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Engine facts: `stellar/src/stellar/runtime/orchestrator.py`, `runtime/ledger.py`, `runtime/health.py`, `trader/desk.py`, `proposals/`, `owner/`, `execution/paper.py`, `config/models.py`, `agents/roster.py`, `telemetry/catalogue.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, doors, topology, anchors, the screen list, and data rules. Every placement below is **provisional** (tile scale is open) and is described by **clock sector** (12 o'clock = top of the floor plan) |
| **Hard boundary** | H-CMD **shows** the mission state and the real coordination steps. It never approves, sizes, sends, cancels or resets anything from the visual layer, never bypasses L10, and never executes |

---

## 1. StarNet concept review (command, orchestration, human interaction)

**Method.** I read the audit (S10–S12, S26, S46–S48) and the local StarNet checkout at pinned
revision `fbddbf99` **read-only**:
- `frontend/app/world.js`: the hero "Commander" agent; lead → worker **delegation** shown as
  hand-off boxes only inside a real `team.dispatch` window; the **approval walk-and-wait** (a run
  blocked on `permission.prompt` walks to a wait anchor with an "AWAITING APPROVAL" tag until
  `permission.response`);
- `frontend/app/chat.js`: the COMMS panel: talking to the agent is a real streaming model call;
- `sidecar/autonomy-ledger.js`: an append-only ledger of every autonomous decision, **including the
  ones not taken** (fire / skip / defer);
- `frontend/app/stationcommands.js` (audit S47): agent tools drive UI verbs.

**Nothing is copied:** no UI, art, characters, dialogue, personality simulation, emotions, XP or game
mechanics.

| StarNet concept | What StarNet does | Structural idea | How Stellar adapts it | What Stellar rejects |
|---|---|---|---|---|
| **Delegation made visible** | Boxes fly lead → worker only during a real `team.dispatch` | Coordination is shown only when a real hand-off happens | Hand-off walks (`PRP-001` in, `PRP-003` out) only on the consuming or producing event (§6) | Flying boxes; hand-offs without events |
| **Approval walk-and-wait** | A blocked run walks to a wait spot with "AWAITING APPROVAL" until a response | A waiting state is a real state with its own place | A run in `AWAITING_APPROVAL` is shown as text on the pipeline and proposal console; no figure invents an approval | Permission prompts driven from the UI |
| **Decision ledger with "not taken" entries** | Every autonomous decision is logged, including skips and defers | A command view shows refusals and waits, not only successes | The pipeline and ops console show `NO_SETUP`, `SELECTION_REQUIRED`, `AWAITING_APPROVAL`, `REVIEW_REQUIRED`, `REJECTED` and `FAILED` as honestly as `COMPLETED` | — |
| **COMMS chat with the hero agent** | The user talks to the agent through a real model call | A human conversation channel | **Future only** (§3.3): Stellar has no chat, intent parser or user-request event | Presenting chat as implemented; persona voice |
| **Commander hero** | One central agent the user identifies with | A single focal point | The **main overview wall** is the focal point, not a character | A captain / hero persona |
| **Agent tools drive UI verbs** (S47) | Agents command the interface | — | — | **Rejected:** Stellar's UI is read-only; the engine never commands the UI |
| XP, levels, idle sentience, StarNet art / HUD | — | — | — | **Rejected** (S27, S33, S34, S45) |

---

## 2. Engine audit (what H-CMD actually does today)

### 2.1 Command roles

| Role | Figure | Does code call it? | Emits | Receives | Status |
|---|---|---|---|---|---|
| **Supervisor** O1 `supervisor` | `CHR-003` | **Yes, as the run lifecycle**: the run ledger journals every `run.*` event with `agent_id = supervisor` | `run.started`, `run.stage.completed`, `run.resumed`, `run.completed`, `run.failed`; also `decision.final.created` (journaled from the run request) | The runtime's own stage results | **Active** (run lifecycle only; no scheduling, market focus or pauses: `market.focus.changed`, `system.paused` have no producer) |
| **Central Trader** U4 `trader` | `CHR-004` | **Only when needed**: the trader desk calls the LLM when a setup has several level options, no owner selection, and the LLM is enabled with a budget | `agent.task.*`, `agent.llm_call.*`, `decision.trader_plan.created` | The setup, the decision support (research plan, specialist view), the snapshot | **Active, conditional**; otherwise a single option or an owner selection is used, or the run stops at `SELECTION_REQUIRED` |
| **Trade Proposal Builder** P1 `trade_proposal_builder` | `CHR-005` | **Yes** (deterministic builder in the trader desk) | `trade.proposed` (proposal, selection, approval) | Setup, selection, approval | **Active** |
| **Portfolio Manager** U8 `portfolio_manager` | `CHR-001` | **No.** No PM model runs. The approval is **supplied in the run request** (`Approval.source` = `portfolio_manager` or `owner`) and journaled as `decision.final.created` by the runtime | — (the record names its source) | — | **No producer** for PM reasoning; the approval record is real |
| **Research Manager** U3 `research_manager` | `CHR-002` | Yes (research pipeline) | `agent.task.*`, `decision.research_plan.created` | Debate cases, findings | **Active**; works at the L3 judge seat (L3 sheet DC-8) |
| **Quartermaster persona** (O2 `wellbeing_monitor`) | `CHR-042` | **No** (no O2 code) | `budget.warning`: no producer | — | **No producer** |

### 2.2 What enters and leaves H-CMD (as data)

- **Enters:** the research plan (`decision.research_plan.created`), specialist and technical views
  (`analysis.created`), setups (`setup.state.changed`), the snapshot, the run request's approval and
  level selection.
- **Leaves:** the trader plan (`decision.trader_plan.created`) and the proposal (`trade.proposed`) to
  L10. Risk evaluation, order authorisation and paper submission are **runtime stages that follow**;
  H-CMD does not trigger them.

### 2.3 Commands and user interaction

| Capability | Exists? | Facts |
|---|---|---|
| Start a run | **Yes, programmatic** | `PaperRuntime.run(RunRequest)` (Python API). The request may carry an **owner approval**, an **owner level selection** and operator risk inputs |
| Approval flow | **Partial** | Without an approval a run parks in `AWAITING_APPROVAL`; the same run re-enters when an approval is supplied later. No approval UI |
| Confirmation flow | **Only for the breaker** | `python -m stellar.owner reset-breaker`: interactive terminal only, exact phrase, a reason, breaker actually `TRIPPED`; journaled as `circuit_breaker.reset` / `reset_refused` |
| Advance / cancel / close a run | **Programmatic** | `advance`, `cancel`, `close` on `PaperRuntime` |
| **User chat, command input, natural-language parser, user-request events** | **No** | No HTTP server, no chat, no intent parser; the catalogue has no user-request or chat event |

### 2.4 Future architecture (not implemented)

User → chat interface → intent understanding → Stellar planning → agent coordination →
confirmation → execution. **All FUTURE.** When built it must keep: owner confirmation before any
order, L10 as the only approval authority, no UI-driven order, and a journaled record of each request.

### 2.5 Authority boundaries

| H-CMD does | H-CMD does **not** |
|---|---|
| Show the complete mission state (runs, stages, setups, proposals, portfolio, system status) | Approve risk: only the deterministic Risk Engine in **L10** approves or rejects |
| Host the trader's selection and the proposal build (engine stages) | Execute: orders exist only after `risk.approved`, through the runtime and the Paper Broker (L9) |
| Show the approval record from the run request | Override specialists, technical evidence or the debate verdict |
| Show the owner's breaker reset result | Reset the breaker (terminal-only owner command), pause the system or start runs from the UI |

---

## 3. Room identity and relationships

### 3.1 Identity

| Aspect | Definition |
|---|---|
| **Purpose** | **"The place where Stellar sees the complete mission state and coordinates real work."** The Central Trader across all concurrent opportunities, the proposal build, the approval record, the Supervisor's run lifecycle, and the global status wall |
| **It is not** | The execution room (L9), the risk room (L10), the research rooms (`H-LAB`, L1–L3), the memory room (L6) or the performance room (L7) |
| **Atmosphere** | Calm, focused, confident. A bright, premium command space; never a dark military bunker, a spaceship-bridge cliché or a room of flashing alarms |
| **Visual identity** | The largest circular hub. A central dais with the **circular** command table. A curved overview wall on the north rim is the brightest surface in the vessel. Subtle command-red accents on warm off-white architecture |
| **Importance level** | **Highest** (hero room). It is the first room the camera frames at vessel overview after the whole-vessel view |

### 3.2 Relationships (physical, information, hand-off)

| Room | Physical | Information | Hand-off? |
|---|---|---|---|
| **L1 Specialists** | `DR-N-CMD` → `COR-N` → `DR-L1` | Specialist views reach the trader desk inside the decision support | **Yes, conditional:** a specialist walks in with `PRP-001` only when the trader's `agent.task.started` follows in the same run |
| **L2 Technical Deck** | `COR-N` | Setups (`setup.state.changed`) and technical evidence | **No** (data only; L2 sheet) |
| **L3 Debate Chamber** | `COR-N` | The research plan (`decision.research_plan.created`) | **Yes:** the Research Manager walks to L3 on `debate.started` and returns after the verdict (L3 DC-8) |
| **L4 Data Core** | `COR-N` | The snapshot; health (L4 shows it) | **No** |
| **L6 Memory Archive** | `DR-S-CMD` → `COR-S` | Closed trades, run history | **No** |
| **L7 Performance Lab** | `COR-S` | Runtime and execution metrics | **No** |
| **L9 Execution Bay** | `COR-S` (via L10's side) | Orders, fills, positions (shown on the pipeline and portfolio) | **No** from H-CMD (E1's route is L10 → L9) |
| **L10 Risk Control** | `DR-S-CMD` → `COR-S` → `DR-L10`; the L10 corner touches the rim with a **solid** wall | Risk decisions back to the pipeline | **Yes:** P1 carries the proposal card (`PRP-003`) to `risk.intake_drop` on `trade.proposed` |
| **`H-HAB`** | `DR-CMD-HAB` | — | Ambient only (idle) |

---

## 4. Architecture

### 4.1 Shape and entrances (approved; unchanged)

- **Shape:** circle, the largest hub (sketch diameter ≈ 448 px; about 28 tiles at the working scale, which is **not frozen**).
- **Doors (3; all ordinary 2-tile curved-rim doors `DOR-009`, normal indicator):**
  - `DR-N-CMD` at about **10 o'clock**, to `COR-N` (upper corridor);
  - `DR-S-CMD` at about **8 o'clock**, to `COR-S` (lower corridor);
  - `DR-CMD-HAB` at **3 o'clock**, to `H-HAB` (the two hub rims touch here).
- **Closed contact:** L10's north-east corner touches the rim at about 7–8 o'clock. The wall there is solid (Topology v2 §7): no door, no opening, no furniture that suggests one.
- **Cutaway rule** (Visual Bible C4): the camera-facing rim (south / south-east arc) is cut away. Any door there keeps a visible frame, threshold and structural opening.

### 4.2 Schematic (not to scale; clock sectors)

```
                         12
                 .-~~ DSP-CMD-01 MAIN VIEWSCREEN ~~-.
            11 .'   [DSP-CMD-04 pipeline band below]  '. 1
   DSP-CMD-03 /  OPS ARC              TRADER ARC        \  DSP-CMD-02
   (research)/   CON-003 (Supervisor)   CON-004 (Trader) \ (technical)
  10  DR-N-CMD|                                           |
     =========|        .-----------------------.          |  2
              |       /     DAIS  (FLR-002)     \         |
   9          |      |  TBL-001 circular table   |        |
              |      |   SEA-001 command chair   |        DR-CMD-HAB  3
   8 DR-S-CMD |       \   (DEC-007 globe above) /         |=========
     =========|        '-----------------------'          |
   CON-005 ->  \  PROPOSAL (SW)          waiting bench    / DSP-CMD-05
   (P1)      7  \                        SEA-005 (SE)    /  (portfolio) 4
   [L10 corner   '.   CON-022 budget (S)               .'
    contact:       '-~~ DSP-CMD-06 SYSTEM STATUS ~~-'   5
    solid]                        6
   ( ring walkway `command.walkway` runs between the dais and the rim, linking 8, 10 and 3 o'clock )
```

### 4.3 Materials (Visual Bible C1)

| Surface | Material |
|---|---|
| Floor | **Deep navy** matte deck (`FLR-001`). The dais (`FLR-002`) is a lighter navy with a titanium edge band. A thin titanium inlay ring marks the **walkway** edge (walk-over, not a barrier) |
| Walls | **Warm off-white structural panels** (`WAL-002` curved rim) with soft seams. **Titanium / light metallic** trim at the base and cove. **No exterior windows** (HC-5) |
| Accents | **Graphite** on console bodies, the command table base and screen bezels. **Command red** as thin static accent lines (dais edge, console trim), never large red surfaces (Visual Bible §6.2 department lighting; see §11 HC-9 on the request's science-blue wording) |
| Screens | Dark smoked glass (`SCR-*`) in titanium frames |

### 4.4 Ceiling and lighting

- A shallow **domed ceiling** with a continuous **cove light ring** (`LGT-001`) and a **central
  light oculus** above the dais; in the cutaway only the cove ring and upper rim edge are drawn.

| Layer | Treatment |
|---|---|
| General | Clean **white / cyan** cove light, soft shadows, high readability |
| Command accent | **Subtle red** accent strips at the dais edge and console trims (static; not an alert colour) |
| Work pools | `LGT-002` over a console only while its agent's **real task** runs (§6) |
| Hero | The main viewscreen is the brightest surface |
| Alert | The derived alert tint on `LGT-001`, **always paired** with the band word and icon (`DSP-CMD-07`). **Steady, never flashing** (HC-15). Lighting alone never communicates a data state (Visual Bible C7) |

### 4.5 Walkable areas (approved; unchanged)

| Area | Rule |
|---|---|
| **`command.walkway`** | A clear ring between the dais and the rim consoles, linking `DR-N-CMD` (10), `DR-S-CMD` (8) and `DR-CMD-HAB` (3) by **both** arcs. **No furniture** in the ring |
| Door approaches | The 1-tile approach in front of each door stays empty (Room Registry §6) |
| Dais | Walkable (a raised step), reached at about 9 and 3 o'clock (HC-6 open) |
| Behind consoles | Not walkable |
| **Through-traffic** | West ↔ Habitat traffic uses the ring, never the dais. Operational agents have right of way |

---

## 5. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Data source | Importance |
|---|---|---|---|---|---|---|
| 1 | **Central command table** (**circular**, HC-1) | `TBL-001` | Coordination surface; Research Manager's home seat | Centre, on the dais | none (furniture) | **Hero** |
| 2 | **Command chair** | `SEA-001` on `FLR-002` | Portfolio Manager's seat (restricted) | On the dais, east of the table | none | High (HC-8: simple table-height seat, no captain / hero look; PM idle) |
| 3 | **Main overview wall** | `SCR-001` (`DSP-CMD-01`) + `SCR-005` band (`DSP-CMD-04`) | Market overview + Agent Pipeline | North rim, 11–1 o'clock | §7 | **Hero** |
| 4 | **Holo globe** (decorative, HC-2) | `DEC-007` | Atmosphere only: **no data, no status, no charts** | Low above the table centre | none | High (ambient) |
| 5 | **Central Trader console** | `CON-004` + `DSP-CMD-09` | Concurrent opportunities | North-east, 1–2 o'clock | §7 | High |
| 6 | **Operations console** | `CON-003` + `DSP-CMD-11` | Run lifecycle | North-west, 11 o'clock | §7 | High |
| 7 | **Proposal console** | `CON-005` + `DSP-CMD-10` | Proposal build; P1's start point to L10 | South-west, 7 o'clock, beside `DR-S-CMD` | §7 | Medium |
| 8 | **Budget console** | `CON-022` + `DSP-CMD-12` | Budgets: NOT AVAILABLE | South, 6 o'clock | none (no producer) | Low |
| 9 | **Coordination status walls** | `SCR-002` | Technical, research, portfolio, global status | Rim, between doors | §7 | Medium |
| 10 | **Waiting bench** | `SEA-005` | Visitors waiting | South-east, 4–5 o'clock | none | Low |
| 11 | **Mode plaque** | `SCR-009` (`DSP-CMD-08`) | Execution mode | North rim, 1 o'clock | §7 (HC-13) | Medium |
| 12 | **Alert band** | `SCR-005` (`DSP-CMD-07`) | Alert word + icon | Under the cove ring | Derived (§7) | High while not GREEN |
| 13 | Console chairs, planters | `SEA-002`, `PLT-001` | Seating; softening | At consoles; planters at the rim only | none | Low |
| 14 | Proposal card | `PRP-003` | Carried to L10 on `trade.proposed` | P1's hands | `trade.proposed` | Medium |

**Not added:** no chat terminal, command input station, agent-status wall or communication object
exists in the Asset Registry (§11, HC-18).

---

## 6. Character placement (engine-true)

| Figure | Anchor | Engine status | What is shown |
|---|---|---|---|
| **Supervisor** `CHR-003` | `CON-003` · `command.console_ops` | Real producer of `run.*` | `stand_work` briefly on each real `run.started` / `run.stage.completed` / `run.completed` / `run.failed`; otherwise `stand_idle`. Leaves H-CMD **only** for visits the room sheets define: L2 / L3 / L4 on their named `run.failed`; L1, L9 (entry), L10 (entry) on the `run.failed` codes of their stage (HC-16) |
| **Central Trader** `CHR-004` | `CON-004` · `command.console_trader` | Real **only when called** | `sit_work` between its real `agent.task.started` and `completed` / `failed`; `decision.trader_plan.created` updates `DSP-CMD-09`. Otherwise idle at the console; ambient to `H-HAB` only when idle |
| **Trade Proposal Builder** `CHR-005` | `CON-005` · `command.console_proposal` | Real | On `trade.proposed`: picks up `PRP-003` and walks `DR-S-CMD` → `COR-S` → L10 `risk.intake_drop`, then returns |
| **Research Manager** `CHR-002` | `TBL-001` · `command.table_head` | Real (at L3) | At the table when idle; walks to L3 on `debate.started`, returns after the verdict or the run's end |
| **Portfolio Manager** `CHR-001` | `SEA-001` · `command.chair` | **No producer** | Idle in the chair. `stamp` only on a real `decision.final.created` whose source is `portfolio_manager`; an `owner` approval is shown as text ("OWNER APPROVAL"), no figure stamps (HC-8). **No L3 visit** (L3 DC-5) |
| **Quartermaster persona** `CHR-042` | `CON-022` · `command.console_budget` | **No producer** | Idle; never shown working |

Visitors: specialists (L1) with `PRP-001` on a real consumed hand-off (`command.visitor_1`, `_2`);
the waiting bench for waiting visitors; the Medic persona at the entry for a real `error`.

**Readability** (Character Bible §4.1–§4.4, unchanged): Supervisor tall, standing; Trader broad,
seated; PM slim and tall with the long coat; RM curly-haired with glasses.

---

## 7. Screen design (Screen Registry v2 §5.1 is the authority)

| Display | Placement | Source | Producer | Consumer | States / findings |
|---|---|---|---|---|---|
| `DSP-CMD-01` Market Overview | North rim viewscreen | `snapshot.created`, `setup.state.changed`, `analysis.created`; price context from the `MARKET_DATA` checkpoint (RL); CF | Runtime, T6, T3–T5 / S1–S4 | Owner | Live quotes → **NOT AVAILABLE** (no `market.quote.received` producer); session → **NOT AVAILABLE** (no `market.session.changed` producer); snapshot freshness word from the engine (**STALE** when it says so); uncfg. instruments → **NOT CONFIGURED**. `snapshot.created` carries no prices (HC-17) |
| `DSP-CMD-04` Agent Pipeline | Band under the viewscreen | Chain events, `run.stage.completed`, `agent.task.*` | Runtime and stage producers | Owner | Each stage lit only by its event; waits and refusals shown as words (`SELECTION_REQUIRED`, `AWAITING_APPROVAL`, `REVIEW_REQUIRED`, `REJECTED`); **AWAITING DATA** |
| `DSP-CMD-02` Technical Analysis | North-east rim | `setup.state.changed`, `analysis.created` | T6, T3–T5 | Owner | **AWAITING DATA** |
| `DSP-CMD-03` Research / News | North-west rim | `research.snapshot.created`, `analysis.created` (macro) | Pipeline | Owner | **AWAITING DATA**; news dormant (R3 deferred) |
| `DSP-CMD-05` Portfolio | South-east rim | `account.snapshot.created`, `position.*`, `trade.closed` | Paper Broker | Owner | Balance, equity, peak equity, open positions, realised / unrealised P&L, open risk; `None` → **UNKNOWN**. **Drawdown: not in the snapshot → NOT AVAILABLE; never computed by the UI** (HC-11). Environment label `PAPER` |
| `DSP-CMD-06` Global System Status | South rim | HL (on demand), RL, breaker events, derived alert, LK | Runtime; owner reset command | Owner | Never "HEALTHY" by default; health shown with its read time and age (**no STALE threshold**, HC-14); breaker state from `circuit_breaker.*`; **LINK DOWN · age** |
| `DSP-CMD-07` Alert band | Under the cove ring | Derived (Screen Registry §2.2) | Derived from real states | Owner | **NO TELEMETRY**; steady (HC-15) |
| `DSP-CMD-08` Mode plaque | North rim, 1 o'clock | Order events' `mode` and the Paper-Broker account state (HC-13) | Paper Broker | Owner | **PAPER** / **MODE UNKNOWN** until an order event or the Paper-Broker account exists |
| `DSP-CMD-09` Central Trader console | On `CON-004` | `decision.trader_plan.created`, `setup.state.changed`, `run.*` | Trader desk, T6, runtime | Owner | One row per concurrent run / setup with stage and age; **AWAITING DATA** |
| `DSP-CMD-10` Proposal console | On `CON-005` | `trade.proposed`, `decision.final.created` | P1; runtime (approval record) | Owner; L10 | Direction, entry, stop, targets, contradictions, rating and approval source. **Reward:risk: always `None` in the engine → NOT AVAILABLE** (HC-12); **AWAITING DATA** |
| `DSP-CMD-11` Operations console | On `CON-003` | RL, MT, `run.stage.completed`, `agent.llm_call.*` | Runtime | Owner | Report read time and age; null totals → **UNKNOWN** |
| `DSP-CMD-12` Budget console | On `CON-022` | `budget.warning` (**no producer**) | — | — | **NOT AVAILABLE · budgets** |

**Agent status:** no dedicated agent-status display exists; the pipeline shows the working agents
per stage from `agent.task.*` (`agent.state.changed` has no producer).
**Environment:** only `PAPER` exists (DEMO refused until the Phase 8 gate; LIVE refused); every
money value is labelled `PAPER`.

**Screen rules:** never invent data; the registry's eight states apply; on link loss every wall
freezes and greys with **LINK DOWN · age**; no screen over a door or its approach; only the main
viewscreen animates at overview zoom; all displays are read-only or navigation-only.

---

## 8. Workflow (engine order)

| Step | Event | Producer | Consumer | Visible? |
|---|---|---|---|---|
| User request (chat / command) | — | — | — | **NOT AVAILABLE** (future) |
| Run starts | `run.started` | Runtime (`supervisor`) from a programmatic `RunRequest` | All stages | Yes: pipeline; Supervisor at the ops console |
| Market data, technical, research | `run.stage.completed`, `snapshot.created`, `analysis.created` | Runtime, L4, L2, `H-LAB`, L1 | Next stages | Yes: pipeline stages light |
| Analysis arrival (specialist view) | `analysis.created` → the trader's `agent.task.started` | S1–S4 → U4 | Trader desk | Yes, only when the trader's task starts (`PRP-001` walk) |
| Debate result | `decision.research_plan.created` | U3 (at L3) | Setup evaluation (T6) | Yes: RM returns; pipeline |
| Setup | `setup.state.changed` | T6 (L2) | Trader desk | Yes: `DSP-CMD-02`, `-09` |
| Trader selection | `agent.task.*`, `decision.trader_plan.created` | U4 (conditional) | Proposal builder | Yes, when called; otherwise the selection source (owner / single option) as text, or `SELECTION_REQUIRED` |
| Approval | `decision.final.created` (from the request's `Approval`) | Runtime, recording the approval's source | Proposal builder | Yes as a record; `AWAITING_APPROVAL` while missing. PM reasoning: **NOT AVAILABLE** |
| Proposal creation | `trade.proposed` | P1 | L10 | Yes: `DSP-CMD-10`; P1 courier walk |
| Risk approval | `risk.check.*`, `risk.approved` / `rejected` / `review.requested` | Risk Engine (L10) | Order authorisation | Yes: pipeline (decided in L10, not here) |
| Execution request | `order.created` (or `order.preflight.failed`) after the runtime's order-authorisation and paper-submission stages | Runtime, Paper Broker | L9 | Yes: pipeline only; **H-CMD sends nothing** |
| Execution result | `order.filled` / `rejected` / `cancelled` / `expired`, `position.*`, `trade.closed`, `account.snapshot.created` | Paper Broker | Owner | Yes: pipeline, `DSP-CMD-05` |
| Archive update | `trade.closed` | Paper Broker | L6 (record crystal via E1) | Not in H-CMD (L6) |
| Pause / resume | `system.paused` / `resumed` | — | — | **NOT AVAILABLE** (no producer) |
| Breaker reset | `circuit_breaker.reset` / `reset_refused` | Owner terminal command | Risk Engine | Yes: `DSP-CMD-06` breaker state (never from the UI) |

---

## 9. Animation and life (revised)

| Activity | Trigger | Who / where | Clips |
|---|---|---|---|
| Run lifecycle | `run.*` | Supervisor at the ops console (display time) | `stand_work` |
| Trader working | Trader `agent.task.started` … `completed` / `failed` | Trader at `CON-004` | `sit_work` |
| Specialist hand-off in | `analysis.created` consumed by the trader's task | Specialist via `DR-N-CMD` to `command.visitor_1` / `visitor_2` | `walk`, `carry` (`PRP-001`) |
| Proposal out | `trade.proposed` | P1 via `DR-S-CMD` to L10 | `walk`, `carry` (`PRP-003`) |
| Debate judging | `debate.started` → verdict | RM to L3 and back | `walk` |
| Approval record | `decision.final.created` with source `portfolio_manager` | PM at the chair | `stamp` (display time) |
| Through-traffic | Routing between the west side and `H-HAB` | Ring walkway | `walk` |
| Idle | No task | Home anchors; seeded ambient to `H-HAB` | `stand_idle` |

**Removed from the approved Revision 1** (engine audit): the `run.started` **command meeting** of
Supervisor, PM, RM and Trader (PM and a non-called Trader have no work; HC-10); the PM's walk to L3
(no risk-debate producer; L3 DC-5); generic "Supervisor event-driven visits" (limited to
the room's `run.failed` codes; HC-16); the pause / error freeze on `system.paused` (no producer).

---

## 10. Style guardrails

- **Keep:** a bright premium command space; warm off-white architecture; titanium trims; deep navy
  floor; graphite consoles; subtle static command-red accents; clean white / cyan light.
- **Avoid:** a dark military look; spaceship-bridge clichés; a captain's-chair silhouette; large
  red surfaces; flashing alarms; clutter (Visual Bible §12).
- **Originality:** no Star Trek bridge layout, LCARS panels, insignia or props; no StarNet art or look.

---

## 11. Contradictions and owner decisions

**Approved (Revision 1):**

| # | Topic | Resolution |
|---|---|---|
| **X1 / HC-1** | Command table shape | **Owner: circular** (Asset Registry `TBL-001` renamed) |
| **X2** | Proposal Builder and Quartermaster persona in H-CMD | Not a conflict; both included |
| **X3 / HC-2** | Holo globe vs the screen truth rule | **Owner: keep**, decorative only |
| **HC-5** | Windows on the rim | **Owner: no exterior windows** |

**Revision 2 (engine audit), decided by the owner:**

| # | Topic | Engine fact | Decision |
|---|---|---|---|
| **HC-8** | Command chair and the PM | No PM model; the approval comes from the run request (`portfolio_manager` or `owner`) | **Yes:** `SEA-001` kept, drawn as a **simple table-height seat**, no captain / hero aesthetic. The PM stays **idle** in V1; a `portfolio_manager` approval record may show its `stamp`, an `owner` approval is text only. Character Registry note added |
| **HC-9** | Accent colour | — | **Yes:** Command keeps the Visual Bible's **subtle red** accents; science blue stays with the SCI rooms |
| **HC-10** | `run.started` command meeting | PM has no producer; the Trader works only when called | **Yes:** removed. No gathering on `run.started`; only the Supervisor's run-lifecycle reaction remains. The Visual World Plan §8 wording is a later task (§13) |
| **HC-11** | Portfolio drawdown | `account.snapshot.created` has no drawdown field | **Yes:** **NOT AVAILABLE**; never computed by the UI. Screen Registry `DSP-CMD-05` re-worded |
| **HC-12** | Proposal reward:risk | `reward_risk` is always `None` | **Yes:** **NOT AVAILABLE**. Screen Registry `DSP-CMD-10` re-worded |
| **HC-13** | Mode source | `account.opened` has no mode field; order events carry `mode`; the account comes from the Paper Broker | **Yes:** **PAPER** from the order events' `mode` and the Paper-Broker account state (source `stellar.paper_broker`); **MODE UNKNOWN** until one exists. Screen Registry `DSP-CMD-08` / `DSP-EXB-05` and the L9 sheet aligned |
| **HC-14** | Health STALE | `health()` is on demand; no threshold | **Yes:** read time and age; no STALE threshold. The Screen Registry `DSP-CMD-06` placeholder wording is a later task (§13) |
| **HC-15** | Alert pulses | — | **Yes:** no flashing; a **steady** tint with icon and text, only for real states |
| **HC-16** | Supervisor visits | Only the run lifecycle has a producer | **Yes:** a visit only on a real `run.failed` (run state `FAILED`) whose failure belongs to the room's stage (L1 `RESEARCH_FAILED`; L2 `TECHNICAL_FAILED` / `SETUP_FAILED`; L3 the debating run; L4 `MARKET_DATA_FAILED`; L9 `PAPER_BROKER_FAILED` / `PAPER_PREFLIGHT_FAILED`; L10 `RISK_FAILED` / `ORDER_AUTHORISATION_FAILED`). No generic visits. L1, L9, L10 sheets and the Character Registry aligned |
| **HC-17** | Market Overview prices | `snapshot.created` carries no prices | **Yes:** prices from the `MARKET_DATA` checkpoint (RL) with their time; never presented as live or continuous. The Screen Registry `DSP-CMD-01` source note is a later task (§13) |
| **HC-18** | Chat, command input, agent-status wall | None exists | **Yes:** **FUTURE**; no asset invented; no chat, intent parser, user-request event or HTTP interface is claimed |
| **HC-19** | Quartermaster | O2 has no code; `budget.warning` no producer | **Yes:** idle; Character Registry "no producer" note added |
| **HC-20** | Supervisor scope | No scheduler; `market.focus.changed`, `system.paused` / `resumed` no producers | **Yes:** run lifecycle only |

No remaining conflicts with the topology (doors, positions, the closed L10 contact, the
through-route), the access model or the asset list.

---

## 12. Decisions

| # | Decision | Status |
|---|---|---|
| HC-1 | Command table shape | **Closed:** circular |
| HC-2 | Decorative holo globe | **Closed:** kept, decorative only |
| HC-3 | Exact dimensions: dais size, ring width, viewscreen arc width | **Open** (after the tile scale, VB-3) |
| HC-4 | Ceiling in the cutaway | **Open** (default: cove ring and upper rim edge only) |
| HC-5 | Windows on the rim | **Closed:** no exterior windows |
| HC-6 | Dais ramps at about 9 and 3 o'clock | **Open** |
| HC-7 | Exact colour values | **Open** (visual production, VB-4) |
| HC-8 … HC-20 | Revision 2 findings (§11) | **Closed** (owner decisions in §11) |

---

## 13. Later alignment tasks (recorded, not done here)

- **Screen Registry:** `DSP-CMD-06` placeholder "old read → **STALE**" (HC-14); `DSP-CMD-01` source note for
  checkpoint prices (HC-17).
- **Visual World Plan:** §8 "Small group around the command table: `run.started` … U3, U8, O1, U4
  gather" (HC-10); §14.3 "RED deep red pulses" (HC-15); §5.3 / §7 PM walk to close the risk debate.
- **Character Bible:** PM "visits `L3` `debate.judge_seat`" (no risk-debate producer).
