# Stellar Room Design Sheet — H-CMD Main Command Hub (V1)

| | |
|---|---|
| **Status** | V1, design direction **approved by the owner**; HC-1, HC-2 and HC-5 decided (§9). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `H-CMD` — Main Command / Central Operations (Room Registry v2 §3.2) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C and `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones and anchors: `STELLAR_ROOM_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2 |
| **Not changed here** | Room position, shape, doors, topology, anchors, the screen list, and data rules. Every placement below is **provisional** (tile scale is open) and is described by **clock sector** (12 o'clock = top of the floor plan) |

---

## 1. Room identity

| Aspect | Definition |
|---|---|
| **Purpose** | The central operational space: coordination, decision making, the Central Trader across all concurrent opportunities, Portfolio Manager approval, the Research Manager, and the Supervisor's run lifecycle. **"The place where everything connects."** |
| **Atmosphere** | Calm, focused, confident. A bright, premium command space, never a dark military bunker |
| **Visual identity** | The largest circular hub. A raised central dais with the **circular** command table. A curved overview wall on the north rim is the brightest surface in the vessel. Subtle command-red accents on warm off-white architecture |
| **Importance level** | **Highest** (hero room). It is the first room the camera frames at vessel overview after the whole-vessel view, and its hero objects must read at overview zoom |
| **Relationship with other rooms** | **Physical** (Topology v2 §5–§6):<ul><li>`COR-N` via `DR-N-CMD` (the analysis chain from `H-LAB`, L1–L4);</li><li>`COR-S` via `DR-S-CMD` (to the Risk Control Room L10, Execution Bay L9, Memory L6, Performance L7);</li><li>`H-HAB` via `DR-CMD-HAB`.</li></ul>It is the **only route** between the working side of the vessel and the Habitat, so it carries through-traffic.<br>**Functional:** the end of the analysis chain (in the engine's order: technical → research → specialists → debate → setup → **Central Trader → Portfolio Manager approval**) and the start of the decision chain (proposal → Risk → Execution) |

---

## 2. Architecture

### 2.1 Shape and entrances (approved; unchanged)

- **Shape:** circle, the largest hub (sketch diameter ≈ 448 px; about 28 tiles at the working scale, which is **not frozen**).
- **Doors (3; all ordinary 2-tile curved-rim doors `DOR-009`, normal indicator):**
  - `DR-N-CMD` at about **10 o'clock**, to `COR-N` (upper corridor);
  - `DR-S-CMD` at about **8 o'clock**, to `COR-S` (lower corridor);
  - `DR-CMD-HAB` at **3 o'clock**, to `H-HAB` (the two hub rims touch here).
- **Closed contact:** L10's north-east corner touches the rim at about 7–8 o'clock. The wall there is solid (Topology v2 §7): no door, no opening, no furniture that suggests one.
- **Cutaway rule** (Visual Bible C4): the camera-facing rim (south / south-east arc) is cut away. Any door there keeps a visible frame, threshold and structural opening.

### 2.2 Schematic (not to scale; clock sectors)

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

### 2.3 Materials (Visual Bible C1)

| Surface | Material |
|---|---|
| Floor | **Deep navy** matte deck (`FLR-001`). The dais (`FLR-002`) is a lighter navy with a titanium edge band. A thin titanium inlay ring marks the **walkway** edge (walk-over, not a barrier) |
| Walls | **Warm off-white structural panels** (`WAL-002` curved rim) with soft seams. **Titanium / light metallic** trim at the base and cove. **No exterior windows** (HC-5): the rim is reserved for screens, information surfaces and a clean command atmosphere |
| Accents | **Graphite** on console bodies, the command table base and screen bezels. **Command red** as thin accent lines (dais edge, chair piping, console trim), never large red surfaces |
| Screens | Dark smoked glass (`SCR-*`) in titanium frames |

### 2.4 Ceiling

- A shallow **domed ceiling** with a continuous **cove light ring** (`LGT-001`) following the rim.
- A **central light oculus** above the dais.
- In the cutaway 2.5D view the ceiling is not drawn over the floor. It is suggested by the cove ring and the upper rim edge only, so agents and the table are never hidden.

### 2.5 Lighting

| Layer | Treatment |
|---|---|
| General | Clean **white / cyan** cove light (the GREEN baseline), soft shadows, high readability |
| Command accent | **Subtle red** accent strips at the dais edge and console trims (not an alert colour; always static) |
| Work pools | `LGT-002` pools over active consoles, on only while the console's agent works (from telemetry) |
| Hero | The main viewscreen is the brightest surface |
| Alert | The station alert tint on `LGT-001` (GREEN / BLUE / AMBER / RED), **always paired** with the alert band word and icon (`DSP-CMD-07`). Lighting alone never communicates a data state (Visual Bible C7) |

### 2.6 Walkable areas

| Area | Rule |
|---|---|
| **`command.walkway`** | A clear ring between the dais and the rim consoles, linking `DR-N-CMD` (10), `DR-S-CMD` (8) and `DR-CMD-HAB` (3) by **both** the north and the south arc. **No furniture** in the ring. At least corridor width (the corridor width is equal for both corridors and not yet frozen) |
| Door approaches | The 1-tile approach in front of each door stays empty (Room Registry §6) |
| Dais | Walkable (a raised step), reached by two short ramps or steps at about 9 and 3 o'clock (facing the doors), so the table is reachable from both sides |
| Behind consoles | Not walkable: consoles sit against the rim |
| **Through-traffic** | West ↔ Habitat traffic uses the ring, never the dais. Operational agents have right of way over ambient ones (Character Registry §3) |

---

## 3. Main objects (hero objects first)

| # | Object | Asset | Purpose | Approximate placement | Interaction role | Visual importance |
|---|---|---|---|---|---|---|
| 1 | **Central command table** (**circular**, HC-1) | `TBL-001` | Collaborative decision and meeting surface; the gathering point on `run.started`. The round form matches the round hub and a collaborative command style | Centre, on the dais | 4 seat anchors (`table_n1`, `n2`, `s1`, `s2`) + `table_head` (Research Manager) | **Hero** (overview) |
| 2 | **Command chair** | `SEA-001` on `FLR-002` | Portfolio Manager's approval seat (the rating stamp) | On the dais, just east of the circular table, facing the main viewscreen at 12 | `command.chair` (**restricted: PM**) | **Hero** |
| 3 | **Main overview wall** | `SCR-001` (`DSP-CMD-01`) + `SCR-005` band (`DSP-CMD-04`) | Market Overview + Agent Pipeline | North rim, about 11–1 o'clock | Look target for everyone in the room | **Hero** (brightest surface) |
| 4 | **Holo globe** (decorative, **kept**, HC-2) | `DEC-007` | Atmosphere: "everything connects". **Decorative only: no real data, no fake system status, no charts or metrics** | Projected above the table's centre, low, never blocking the viewscreen line of sight | none | High (ambient); must never read as a data display |
| 5 | **Central Trader console** (triple display) | `CON-004` + `DSP-CMD-09` | All concurrent opportunities | North-east arc, about 1–2 o'clock, facing inward to the viewscreen | `command.console_trader` (**restricted: trader**) | High |
| 6 | **Operations console** | `CON-003` + `DSP-CMD-11` | Supervisor: run lifecycle, stage timings | North-west arc, about 11 o'clock (clear of the `DR-N-CMD` approach) | `command.console_ops` | High |
| 7 | **Proposal console** | `CON-005` + `DSP-CMD-10` | Trade Proposal Builder; the courier's start point toward L10 | South-west, about 7 o'clock, beside `DR-S-CMD` (clear of its approach tile) | `command.console_proposal` (**restricted: P1**) | Medium |
| 8 | **Budget console** | `CON-022` + `DSP-CMD-12` | Quartermaster persona (budgets: NOT AVAILABLE today) | South arc, about 6 o'clock | `command.console_budget` | Low–medium |
| 9 | **Coordination status walls** | `SCR-002` | Technical Analysis, Research / News, Portfolio, Global System Status | Rim, between the doors (§5) | Look targets | Medium |
| 10 | **Waiting bench** | `SEA-005` | Visitors waiting (for example a hand-off in progress) | South-east arc, about 4–5 o'clock, facing the Portfolio wall | `command.bench_1`, `bench_2` | Low |
| 11 | **Mode plaque** | `SCR-009` (`DSP-CMD-08`) | **PAPER** from telemetry, otherwise MODE UNKNOWN | North rim, at the right edge of the viewscreen (about 1 o'clock) | none | Medium (always readable) |
| 12 | **Alert band** | `SCR-005` (`DSP-CMD-07`) | Alert word + icon | Continuous band under the cove ring, around the rim | none | High while not GREEN |
| 13 | Console chairs, planters | `SEA-002`, `PLT-001` | Seating; softening | At consoles; planters only at the rim between screens, never in the ring | seats | Low |

The **meeting area is the command table** itself (object 1). No separate meeting furniture is
added, which keeps the room uncluttered (Visual Bible §12).

---

## 4. Character placement

| Agent | Workstation (anchor) | Usual position | Movement pattern | Interaction with other agents |
|---|---|---|---|---|
| **Supervisor** `CHR-003` | `CON-003` · `command.console_ops` | Standing at the ops console, north-west arc | The most mobile command figure:<ul><li>to the command table on `run.started`;</li><li>event-driven visits to other rooms through `DR-N-CMD` (analysis rooms) or `DR-S-CMD` (L6, L7, and **only the entry zones** of L9 / L10);</li><li>returns to the console.</li></ul> | Gathers the command group on `run.started`; visits rooms as events require. Never touches restricted anchors |
| **Central Trader** `CHR-004` | `CON-004` · `command.console_trader` | Seated at the triple display, north-east arc | Mostly stationary. To the table on `run.started`; ambient to the Habitat via `DR-CMD-HAB` (close by) **only when idle** | Receives specialist hand-offs (`PRP-001`, arriving through `DR-N-CMD`, only on a real consumed `analysis.created`). Works **every concurrent opportunity** at one console; the figure is never duplicated |
| **Portfolio Manager** `CHR-001` | `SEA-001` · `command.chair` | Seated in the command chair on the dais, facing the viewscreen | Stands for the **rating stamp** (only on `decision.final.created`). Walks via `DR-N-CMD` → `COR-N` → L3 `debate.judge_seat` to close the risk debate, then returns | Final approval: the rating appears on `DSP-CMD-10` (and the Agent Pipeline) only when the event exists. After it, P1 builds the proposal |
| **Research Manager** `CHR-002` | `TBL-001` · `command.table_head` | Seated at the **head seat** of the circular table (its west side, facing the viewscreen; the seat is marked by a slightly raised chair back, since a round table has no natural head) | Walks via `DR-N-CMD` → `COR-N` → L3 `debate.judge_seat` to judge the investment debate; returns to the table | Verdict and investment plan (`decision.research_plan.created`); meets with the group at the table |

**Secondary occupants** (from the Room Registry):
- **Trade Proposal Builder** `CHR-005` at `command.console_proposal`. It carries the proposal card
  (`PRP-003`) out through `DR-S-CMD` to the L10 intake, **only** after `trade.proposed`.
- **Quartermaster persona** `CHR-042` at `command.console_budget`.

**Visitors:**
- `command.visitor_1`, `visitor_2` for agents arriving on a hand-off;
- `command.bench_1`, `bench_2` for waiting.

**Readability check:** the four main figures differ in silhouette (Character Bible §4.1–§4.4):
- the Supervisor is tall with a high bun, standing;
- the Trader is broad, with an open coat and a beard, seated at a console;
- the PM is slim and tall, with the ankle-length coat, in the chair;
- the RM is average, curly-haired, with glasses, at the table.

---

## 5. Screen design (Screen Registry v2 §5.1 is the authority)

| Display | Content (from the registry) | Placement | Hardware | Main placeholders |
|---|---|---|---|---|
| `DSP-CMD-01` **Market Overview** | Configured instruments grouped by family (Metals / FX / Indices). Snapshot price context **with its time**; session; active setup; latest specialist view. FX lists EUR/USD and USD/JPY as **separate rows** (interim adapter) | North rim, the main curved viewscreen (about 11–1 o'clock) | `SCR-001` | live quotes → **NOT AVAILABLE**; old snapshot → **STALE** |
| `DSP-CMD-04` **Agent Pipeline** | The decision chain; each stage lit **only** by its event, with a timestamp | Band directly under the main viewscreen | `SCR-005` | unreached stages unlit; **AWAITING DATA** |
| `DSP-CMD-02` **Technical Analysis** | Setup states per instrument; latest technical assessment | North-east rim, about 1:30–2 o'clock (above / beside the trader arc) | `SCR-002` | **AWAITING DATA** |
| `DSP-CMD-03` **Research status** (Research / News) | Latest research snapshot and macro assessment; the news feed is dormant (R3 deferred) | North-west rim, about 10:30–11 o'clock (beside `DR-N-CMD`, the research corridor side) | `SCR-002` | **AWAITING DATA** |
| `DSP-CMD-05` **Portfolio** | Paper balance / equity, positions, P&L, drawdown | South-east rim, about 4–5 o'clock | `SCR-002` | missing economics → **UNKNOWN** |
| `DSP-CMD-06` **Global System Status** | Health status and reasons, runs by state, breaker, alert level, link state | South rim, about 5–7 o'clock (facing the dais) | `SCR-002` | never "HEALTHY" by default; **STALE**; **LINK DOWN** |
| `DSP-CMD-07` Alert band | Alert word + icon | Continuous band under the cove ring | `SCR-005` | **NO TELEMETRY** |
| `DSP-CMD-08` Mode plaque | **PAPER** from telemetry | North rim, about 1 o'clock | `SCR-009` | **MODE UNKNOWN** (amber + icon) |
| `DSP-CMD-09` Central Trader console | All concurrent opportunities with instrument, stage and age, plus a count | On `CON-004` | `SCR-004` | **AWAITING DATA** |
| `DSP-CMD-10` Proposal console | Latest proposal and rating | On `CON-005` | `SCR-004` | **AWAITING DATA** |
| `DSP-CMD-11` Operations console | Run lifecycle, stage timings, LLM totals | On `CON-003` | `SCR-004` | null totals → **UNKNOWN** |
| `DSP-CMD-12` Budget console | Budgets | On `CON-022` | `SCR-004` | **NOT AVAILABLE · budgets** |

**Screen rules for this room:**
- **Never invent data.** Every value comes from the registry's sources, with its age.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). On link loss, every
  wall freezes and greys with **LINK DOWN · age**.
- **No screen sits over a door or its approach**, including the 8, 10 and 3 o'clock arcs.
- **Hierarchy** (Visual World Plan §14.8): the alert band and breaker state (in `DSP-CMD-06`)
  come first; then decisions (the rating, the proposal); then the working consoles; then the
  status walls.
- Only **one animated screen** is active at overview zoom (the main viewscreen). The others render
  as static frames until the room is focused (Visual World Plan §2.4).
- All displays are read-only or navigation-only. No screen can approve, reject, reset or send
  anything.

---

## 6. Animation and life

All activity comes from **real system events**, **real tasks** or **normal idle behaviour**.
There is **no emotional simulation** (Character Bible K6).

| Activity | Trigger | Who / where | Clips |
|---|---|---|---|
| Agents working | `agent.task.started` … `completed` for that role | At their consoles | `sit_work` / `stand_work` |
| Reviewing screens | The screen the agent's task concerns updates | Supervisor at ops; Trader at the triple display; PM toward the viewscreen | `look_screen` |
| **Command meeting** | `run.started` | Supervisor, PM, RM and Trader gather at the command table | `meeting`, `talk` / `listen` |
| Rating | `decision.final.created` | PM at the command chair | `stamp` |
| Coordination hand-off in | A specialist's `analysis.created` consumed downstream | A specialist walks in via `DR-N-CMD` to the trader console, then leaves | `walk`, `carry` (`PRP-001`) |
| Proposal out | `trade.proposed` | P1 from the proposal console out through `DR-S-CMD` | `walk`, `carry` (`PRP-003`) |
| Debate judging | debate close (real events) | RM / PM leave via `DR-N-CMD` to L3, then return | `walk` |
| Through-traffic | Any agent routed between the west side and the Habitat | The ring walkway only | `walk` |
| Idle | No task | At the home anchor; after the idle delay, optional ambient to the Habitat via `DR-CMD-HAB` | `stand_idle`, seeded ambient |
| Pause / error | `system.paused` (no producer yet) / real `error` | Figures freeze or show the beacon in place | overlays |

The room never shows a decision, rating, proposal or alert that did not happen. The ring traffic and
idle ambient life are the only non-event motion, and both are seeded and deterministic.

---

## 7. Style guardrails

- **Keep:** a bright premium command space; warm off-white architecture; titanium trims; deep
  navy floor; graphite consoles; subtle static command-red accents; clean white / cyan light.
- **Avoid:** a fully dark military look; large red surfaces; red used as decoration (red is
  reserved for real states); clutter (Visual Bible §12).
- **Originality:** no Star Trek bridge layout, captain's-chair silhouette, LCARS panels, insignia
  or props. No StarNet art or look. The command chair and table are original Stellar designs.

---

## 8. Contradictions and owner decisions

| # | Topic | Resolution |
|---|---|---|
| **X1 / HC-1** | Command table shape (Asset Registry "oval" vs Visual World Plan "circular") | **Owner: circular.** Asset Registry `TBL-001` is renamed "Circular command table". The Visual World Plan §14.5 already says circular |
| **X2** | Proposal Builder and Quartermaster persona in H-CMD | Not a conflict; both included as secondary occupants (§4) |
| **X3 / HC-2** | Holo globe at the centre vs the screen truth rule | **Owner: keep.** Decorative only: no real data, no fake system status, no charts or metrics. Asset Registry `DEC-007` wording aligned |
| **HC-5** | Windows on the H-CMD rim | **Owner: no exterior windows.** The rim carries screens and information surfaces. Asset Registry `WAL-003` and `DEC-001` now exclude H-CMD |

No remaining conflicts with:
- the topology (doors, positions, the closed L10 contact, the through-route);
- the Visual Bible, the Character Bible and the Screen Registry.

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| HC-1 | Command table shape | **Closed:** circular |
| HC-2 | Decorative holo globe | **Closed:** kept, decorative only |
| HC-3 | Exact dimensions: dais size, ring width, viewscreen arc width | **Open** (after the tile scale, VB-3) |
| HC-4 | Ceiling in the cutaway: cove ring only, or a partial translucent dome edge | **Open** (default: cove ring and upper rim edge only) |
| HC-5 | Windows on the rim | **Closed:** no exterior windows |
| HC-6 | Central platform (dais) ramps: about 9 and 3 o'clock proposed | **Open** |
| HC-7 | Exact colour values | **Open** (visual production, VB-4) |
