# Stellar Agents — Visual World Plan

| | |
|---|---|
| **Status** | v0.2 — Visual Phase V0 (design only), revised with the StarNet reuse audit. No code, assets or dependencies. |
| **Date** | 2026-09-30 |
| **Reuse sources** | `docs/STARNET_REUSE_AUDIT.md` (StarNet revision `fbddbf99`). Only StarNet **code** (MIT) is considered, for the engine layer (§1.7). **No StarNet artwork, sprites, branding, visual assets, station-drawing code or look is used, and StarNet's renderer is not adopted.** Matrix item ids (S1–S57) refer to the audit |
| **Builds on** | `docs/STELLAR_FOUNDATION_PLAN.md` (v0.3, approved; canonical), `docs/STELLAR_LAYER_DESIGN.md` (v0.4; station and event detail), `docs/STELLAR_MASTER_ROADMAP.md` |
| **Scope** | The visual world of Stellar Agents: architecture of the presentation layer, camera, ship layout, agent visuals, personas, states, movement, interactions, screens, event mapping, ambient life, art direction, rendering options, navigation, interaction model, accessibility, visual phases, local frontend security, testing, and licensing / provenance of reused code |
| **Topology source of truth** | `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C** (owner-approved flat vessel), with `STELLAR_STATION_TOPOLOGY.md`, `STELLAR_ROOM_REGISTRY.md`, `STELLAR_ASSET_REGISTRY.md`, `STELLAR_CHARACTER_REGISTRY.md` and `STELLAR_SCREEN_REGISTRY.md` (all v2). Where this plan's older text mentions decks, lifts, the vault or the airlock, those documents win |
| **Hard rule** | The visual world is a **presentation layer only**. It consumes events and snapshots. It never controls, delays or overrides research, risk, execution or the circuit breaker. |

---

## Relationship to the approved documents

This plan **refines** the station design in the layer design (§2, §5) and implements Foundation
Phases 9–10 (Station V1 and V2). Canonical sources are not changed here:

- **Event names** are the canonical ones (Foundation §10.1, layer design §4.3). None are invented.
- **Runtime agent states** remain the layer design §3.2 state machine. The *visual* states in §6 are
  derived from them for presentation only.
- **Agent codes and technical ids** are the Foundation roster codes (§5.1) and the layer design's
  technical ids (§3).

**Proposed extensions that need a later documentation-only reconciliation of the layer design**
(listed, not applied, until the owner approves this plan):

| # | Extension | Layer design today |
|---|---|---|
| VX-1 | Room set becomes the owner-approved flat vessel: **19 room slots** (3 hubs, L1–L10, R1–R6; 11 active, 8 reserved), Room Registry v2 | 10 rooms (§2.2, §2.3) |
| VX-2 | Home rooms move: research roles R1–R6, validators V1–V4 and M1 → `H-LAB`; market specialists → L1 family desks; technical agents T2–T8 → Technical Deck (L2); Performance / Attribution (L2) → Performance Lab (L7) | R* in Lab / Research Hub (`H-LAB`); V* in Data Core; T* in Market Specialists Room (L1); L2 in Memory Archive (§5.1) |
| VX-3 | A **persona registry** (display names) separate from technical ids | Technical ids only |
| VX-4 | **Visual states** (§6) as a documented derivation of the §3.2 runtime states | Runtime states and a status → visual table (§5.2) |
| VX-5 | **Flat-vessel navigation**: one tile grid for the whole vessel, explicit doors only (§16; Topology v2) | Single-plane room graph with pathfinding on corridors (§5.3) |
| VX-6 | **Local frontend security** for the read-only UI (§20), and reconciliation semantics for the existing `GET /snapshot` endpoint (§1.8; Foundation §4.28) | "localhost, read-only" (LD-5); snapshot listed without reconciliation semantics |

The layer design's one-way airlock (§2.1) is **superseded** by the approved flat vessel. The
guarantee it expressed is kept as a **workflow and access rule**: no order is shown or moved
without `risk.approved` and `order.created`, and only permitted roles enter the Risk Control Room
(L10) and the Execution Bay (L9) (Character Registry v2 §3).

---

## Contents

1. [Visual architecture principles](#1-visual-architecture-principles)
2. [Camera and world view](#2-camera-and-world-view)
3. [Ship layout](#3-ship-layout)
4. [Agent visual model](#4-agent-visual-model)
5. [Persona / display-name system](#5-persona--display-name-system)
6. [Visual agent states](#6-visual-agent-states)
7. [State → room movement](#7-state--room-movement)
8. [Agent interactions](#8-agent-interactions)
9. [Status HUD above each agent](#9-status-hud-above-each-agent)
10. [Room screens](#10-room-screens)
11. [Telemetry → visual event mapping](#11-telemetry--visual-event-mapping)
12. [Ambient life](#12-ambient-life)
13. [Wellbeing visualization](#13-wellbeing-visualization)
14. [Art direction](#14-art-direction)
15. [Technical rendering options](#15-technical-rendering-options)
16. [Pathfinding and navigation](#16-pathfinding-and-navigation)
17. [Owner interaction model](#17-owner-interaction-model)
18. [Accessibility and performance](#18-accessibility-and-performance)
19. [Visual development phases](#19-visual-development-phases)
20. [Local frontend security](#20-local-frontend-security)
21. [Testing and quality gates](#21-testing-and-quality-gates)
22. [Licensing and provenance](#22-licensing-and-provenance)
23. [Unresolved visual decisions](#23-unresolved-visual-decisions)

---

## 1. Visual architecture principles

### 1.1 Pipeline

```
Stellar Engine (research, analysis, debate, risk, execution)      ← the only place decisions happen
      │ emits canonical events (Foundation §10.1, layer design §4.3)
      v
Telemetry / Event Bus + Event Store + Journal                     ← ordered, append-only, replayable
      │ protected event stream (live, cursor resume; transport VW-14, §1.8, §20)
      │ GET /snapshot (authoritative)  ·  GET /runs/{id}/events (replay)
      v
Visual State Adapter (browser)                                    ← pure reducer: events → WorldState
      │ WorldState: agents, rooms, screens, station
      v
Engine layer (browser, renderer-independent, StarNet-derived §1.7) ← vessel grid, paths, anchors,
      │ logical tile coordinates + positions                          movement, traffic, zones
      v
World Renderer (PixiJS candidate, §15)                            ← projects to isometric; draws
      │
      v
Agent animations · room lighting · screens · HUDs · camera
```

The adapter is **read-only** with respect to the engine: the API is local, read-only, protected
(§20) and has no write endpoints (layer design §7 LD-5, R-5).

### 1.2 Why the world is driven by real backend events

- **Truthfulness.** The owner must be able to trust that what an agent appears to do is what it is
  doing. Every operational animation is caused by an event; ambient animation (§12) is labelled as
  cosmetic.
- **Replay.** Because the world is a function of the event stream, any past run can be replayed and
  looks the same (layer design §5.3, deterministic life).
- **Decoupling.** The engine never waits for, or depends on, the UI. Disabling the UI changes
  nothing in trading (layer design LD-6 gate).

### 1.3 Separation of visual state from trading logic

| Concern | Lives in | Never lives in |
|---|---|---|
| Decisions, risk rules, sizing, orders, breaker | Stellar engine | UI |
| Runtime agent state (`THINKING`, `CHECKING`, …) | Engine telemetry | UI |
| Visual state (`researching`, `debating`, …), rooms, positions, animations | Visual State Adapter + renderer | Engine |
| Persona names, colours, sprites | Persona registry and art assets (UI) | Technical schemas or protocol contracts |
| Navigation grids, paths, anchors, walking, traffic | Engine layer (UI, §1.7) | Stellar engine, risk or execution |

The adapter is a **pure reducer**: `WorldState' = reduce(WorldState, event)`. It is idempotent by
`event_id` and ordered by `seq`. Positions and animations are computed from WorldState by the
engine layer and renderer, never fed back. **Visual state never feeds trading decisions:** nothing
in the UI (positions, visual states, ambient choices, persona names) is sent to the engine, and the
engine has no API through which it could be (§20).

### 1.4 Stale and missing events

| Situation | Detection | Visual handling |
|---|---|---|
| Connection lost | Stream not open, **or** no data frame for more than 1.5× the keepalive interval (keepalives are sent as **data frames**, because browsers hide event-stream comments from scripts — StarNet lesson, audit S10) | A station-wide "TELEMETRY LOST — showing last known state" banner; all agents frozen in place, desaturated, with a clock icon; no working animations |
| Recovering | Stream reopened but the authoritative snapshot has not yet been applied | Banner reads "RECONNECTING — verifying state"; world stays frozen until the snapshot is applied (bytes alone do not prove recovered state) |
| Sequence gap or cursor reset | `seq` jump, or the server's `ready` frame says the cursor has expired (`reset: true`) | Refetch `GET /snapshot`, replace WorldState, then resume from the snapshot's `seq` (layer design §4.5) |
| Agent silent too long | No event for an agent in a working state beyond its role's expected duration | Badge gains a "no update for Ns" marker; the working animation slows to a still pose. The agent is **not** shown as finishing or moving on |
| Unknown event type | Not in the adapter's table | Ignored for visuals, logged in the UI's event log |
| Replay | Events from the store | Same reducer; replay clock drives time; a "REPLAY" watermark is always visible |

### 1.5 The UI never invents operational actions

- An agent is shown **working** only while the telemetry says so (between `agent.task.started` and
  `agent.task.completed` / `agent.task.failed`, or in a runtime working state).
- **Transient outcomes** (`approved`, `rejected`) are shown for a short fixed display time after the
  real event and then revert to the state the telemetry reports.
- Ambient behaviour (§12) is only for agents whose runtime state is `IDLE` or `OFF_DUTY`, and it is
  visually distinguishable (no task label in the HUD, a small "ambient" glyph in the expanded HUD).
- Hand-offs, meetings and walks to other rooms are shown only when an event implies them (§8).

### 1.6 Movement follows state, never leads it

1. The **status badge updates immediately** when the event arrives. The badge is the truth; the
   avatar's position is decoration.
2. The avatar then walks to the new work position. Walks have a maximum visual duration; beyond it
   the avatar fades out and fades in at the destination.
3. **Teleport when late:** if another state change arrives before the walk ends, the avatar snaps
   to the newest destination (layer design §5.3 rule 3).
4. Movement never delays an event, a screen update or a badge.

Why badges must be immediate: a walk takes seconds; a risk rejection or a tripped breaker must be
visible at once. If the visual world ever lags the truth, the badge and the station alert level
carry the truth.

### 1.7 Engine layer (StarNet-derived, renderer-independent)

Between the adapter and the renderer sits an **engine layer**: pure, renderer-independent modules
that own logical coordinates, navigation and movement. They take injected time and randomness, have
no DOM or drawing code, and are testable headlessly. The renderer only projects and draws their
output. Where StarNet already solves a problem well (audit §5), Stellar derives from it rather than
building from scratch; where StarNet's solution is art-bound or non-deterministic, Stellar does not
use it.

| Capability | StarNet source (audit id) | Stellar adaptation | Class |
|---|---|---|---|
| Room / tile grid | `worldmodel.js` zone grid, rect-union rooms, corridors, `walkable`, indexed `roomAt` (S13) | **One grid for the flat vessel** (§16; Topology v2); rooms and corridors from the authored layout; no building, belts, pipelines, capabilities or materials | Copy + adapt |
| Door / room connectivity | `worldmodel.js` auto-doors on adjacency + `canStep` (S13) | **Explicit doors only**: the 21 approved doors of Topology v2 §3 are the only crossings; StarNet's automatic doors on adjacency are **switched off**; restricted rooms (L9, L10) are a per-role navigation permission, not a door property | Copy + adapt |
| Pathfinding | `path` BFS + `smoothPath` string-pulling + conservative `segmentClear` line of sight (S14) | Grid search on the single vessel grid, then string-pulling that never crosses a seam without a door; StarNet's art-tuned foot / doorway clearance (S15) is **not** used | Copy + adapt |
| Walking movement | `stepGait`, `gaitMove`, `finishGait`, `bucketDir` (S21) | Eased speed, facing slew with hysteresis, corner arcs, distance-phased stride; injected clock; **8-way** facings for isometric sprites | Copy + adapt |
| Collision / traffic | `stepTraffic` right-of-way, `separateBodies`, `containBody` (S22–S24) | Same pattern, rewritten with explicit arguments; **operational agents always have right of way over ambient ones**; jam give-up then teleport fallback | Reimplement (same pattern) |
| Zones | `zones.js` (S18) | Idle containment: home room, Habitat zones, room leash | Copy + adapt |
| Prop / workstation anchors | `propanchor.js` approach tile + facing (S19); seat reservation (S25) | Named interaction points with capacity; role-owned operational anchors; claimable ambient anchors with timeouts | Copy + adapt / reimplement |
| Waiting anchors | `waitanchor.js` anchor ladder with zone clamping (S20) | Ladder: room waiting bench → own workstation → room anchor; used for `waiting` and `paused` | Copy + adapt |
| Deterministic randomness | `shared/clock-rng.js` (mulberry32, fnv, injected clock) (S5) | The **only** randomness source in the UI; keyed by seed, agent id and time bucket | Keep as-is |
| Event validation / bus | `schema.js`, `emitter.js`, `U.bus` (S1, S2, S57) | Validate every incoming event against the Stellar catalogue before the reducer; malformed events dropped and logged | Wrap / copy + adapt |
| Reconnect, link health, stale state | Browser event-stream client, `linkDown`, TTL sweep, snapshot reconcile (S9–S11) | The Visual State Adapter contract (§1.8) | Copy + adapt / reimplement |
| Visual testing | `shoot.mjs`, `golden.mjs`, `png.mjs` (S49–S51) | Golden screenshots of recorded, deterministic replays (§21) | Reimplement / copy + adapt |

**Not adopted from StarNet:** its renderer and drawing stack (bake painters, props, surfaces,
lighting, CRT post-process), all artwork and branding, its idle "sentience" engine, its station
builder, its frontend-owned roster, and its UI command channel (audit S15, S16, S27, S33–S40,
S45, S47, S48). Provenance and attribution rules are in §22.

### 1.8 Visual State Adapter contract

1. **Authoritative engine state first.** On start, and after every reconnect, the adapter loads
   `GET /snapshot` (Foundation §4.28) and **replaces** WorldState with it. Only then does it apply
   stream events whose `seq` is greater than the snapshot's.
2. **Reconnect recovery.** The client keeps exactly one stream open, resumes from its last cursor,
   and retries with exponential backoff (capped). While the stream is reopened but the snapshot has
   not been applied, the UI shows "RECONNECTING — verifying state" (§1.4).
3. **Stale telemetry.** Link down when the stream is not open or no data frame has arrived for more
   than 1.5× the keepalive interval. Per agent, a working state with no reinforcing event beyond its
   role's expected duration gets a "no update for N s" marker; it is never animated as finishing.
4. **Periodic authoritative refresh.** While connected, the adapter re-reads the snapshot on a slow
   cadence (StarNet uses 30 s; Stellar value VW-9) so drift is corrected in both directions: a
   finished task is cleared, a still-running one is re-confirmed.
5. **Duplicate-event protection.** Events are applied at most once: by `event_id`, and by comparing
   the event's cursor with the last applied cursor (replayed events at or below it are dropped). A
   snapshot taken moments before a locally observed completion does not resurrect that task for a
   short guard window (audit S11).
6. **Visual state never feeds trading decisions.** The adapter has no write path; the engine never
   reads UI state; the API offers no endpoint that accepts UI state (§20).
7. **Snapshot contents the engine must provide** (reconciliation semantics, VX-6): station alert
   level, execution mode, breaker state; per agent: technical id, runtime state, current task,
   market focus; open setups, proposals and orders in summary; the snapshot's `seq` and timestamp.

---

## 2. Camera and world view

### 2.1 View model

A **cutaway vessel interior** in a fixed **isometric / 2.5D** projection: the roof is cut away so
the whole flat vessel (three hubs, two corridors, 16 small rooms) is visible at once, like a lit
architectural model.

| Mode | Shows | Detail level | Entered by |
|---|---|---|---|
| **Overview** | The whole vessel: all 19 room slots (reserved slots dark) | Rooms as lit volumes; agents as small figures with coloured state pips; each room shows at most one glanceable KPI; station alert lighting | App start; `Home` key; minimap "whole ship" |
| **Hub view** | One hub with its corridor or radial rooms | Agents readable with name tags; room screens show headline values | Zoom in on a hub; click a hub label |
| **Room focus** | One room, with its neighbours dimmed at the edges | Full room screens (§10), all agent HUDs in minimal form, interaction points visible | Click a room |
| **Agent focus** | One agent, camera follows it | Expanded HUD (§9), a side panel with its task, recent events and metrics | Click an agent; select from the roster panel |

### 2.2 Transitions and zoom

- Transitions are short eased camera moves (pan + zoom together). In reduced-motion mode they
  become instant cuts (§18).
- Zoom is continuous (mouse wheel / pinch) between the overview and room-focus levels, with **three
  snap levels** (overview, hub, room) so text is always rendered at a readable size.
- Level of detail changes with zoom: screens, name tags and HUDs appear only when they would be
  legible.
- Pan with drag or arrow keys. `Esc` steps out one level.

### 2.3 Minimap / ship map

A small top-right ship schematic, always visible:
- every room as a coloured tile (its alert state), the viewport rectangle, and a dot per agent;
- the Risk Control Room (L10) and Execution Bay (L9) are always drawn with their restricted markings;
- clicking a tile focuses that room.

### 2.4 Clutter rules

- Overview shows all rooms, but **agent labels are hidden** at that level; only state pips and room
  KPIs appear.
- Hub view shows a hub and its adjacent rooms with names; room focus shows one room fully plus dimmed
  neighbours.
- At most **one** animated screen per room is active in overview; other screens render as static
  frames until focused.
- Ambient agents are drawn at lower contrast than working agents at every zoom level.

---

## 3. Ship layout

> **Topology source of truth:** `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C**
> (owner-approved), detailed in `docs/STELLAR_STATION_TOPOLOGY.md` v2. Room functions are in
> `docs/STELLAR_ROOM_REGISTRY.md` v2. The stacked five-deck layout, the central and decision lifts,
> the vault antechamber and the one-way airlock of v0.1–v0.2 are **superseded** and must not be
> built.

### 3.1 The vessel (flat, one level)

- **Hubs:** three circular hubs, left to right:
  - `H-LAB` Lab / Research Hub;
  - `H-CMD` Main Command / Central Operations;
  - `H-HAB` Habitat.
- **Corridors:** between `H-LAB` and `H-CMD`, two parallel corridors (`COR-N`, `COR-S`) serve ten
  small rooms, L1–L10. Each small room has exactly one door onto its corridor.
- **Radial rooms:** six rooms R1–R6 stand around `H-HAB`, each with one door into it.
- **Doors:** 21 explicit doors, all ordinary 2-tile sliding doors. There are **no lifts, no decks,
  no airlocks, no automatic doors and no hidden passages**.

Layout principles:
- **The floor plan follows the control flow.**
  - Research leaves `H-LAB` along `COR-N` → Market Specialists (L1) → Technical Deck (L2) → Debate
    Chamber (L3) → `H-CMD`.
  - Decisions leave `H-CMD` along `COR-S` to the Risk Control Room (L10), then the Execution Bay (L9).
- **Risk isolation is logical, not geometric.** L10 and L9 have ordinary doors. Access is a
  per-role navigation permission, with restricted anchors and static markings (Character Registry
  §3). An order is only ever shown after `risk.approved` and `order.created`.
- **`H-CMD` is the through-hub** between the working side and the Habitat, so it keeps a clear
  walkway.
- **The Habitat keeps ambient walking out of working rooms:** café, lounge, billiards, plants, rest
  and the recovery pods for real cooldowns are zones of `H-HAB`.
- **Reserved slots:** L5, L8 and R1–R6 are empty. R1 is designated for the future
  Performance & Wellbeing / Coaching Room.

### 3.2 Rooms

Agent codes are Foundation §5.1 codes. "Visits" are agents that come for a task but live
elsewhere. Every room's connections are its approved doors (Topology v2 §3).

#### Main Command (`H-CMD`)
- **Purpose:** central command; the Central Trader across all concurrent opportunities; the final
  decision; global portfolio and system status.
- **Agents:** Portfolio Manager (U8), Research Manager (U3), Central Trader (U4), Trade Proposal
  Builder (P1), Supervisor (O1); the Quartermaster persona of O2.
- **Visual style:** the vessel's largest hub: a raised command chair and a circular command table on a
  dais, a curved main viewscreen on the north rim, and a clear walkway linking its three doors.
- **Screens / objects:** Market Overview, Technical Analysis, Research / News, Agent Pipeline,
  Portfolio, Global System Status; alert band; mode plaque `PAPER` from telemetry (Screen Registry
  v2 §5.1).
- **Alert states:** AMBER edge lighting on a `REVIEW` rating or a degraded source; RED on a breaker
  trip (whole vessel).
- **Connections:** `COR-N`, `COR-S`, `H-HAB`.

#### Lab / Research Hub (`H-LAB`)
- **Purpose:** the **shared** research team for all market families: source intake, validation,
  fact / reaction / interpretation separation, and macro / context synthesis.
- **Agents:** research roles R1–R6 (R3–R6 dormant while deferred), validators V1–V4, and the
  Causal / Macro Analyst (M1). The future Research Lab bench is not rendered.
- **Visual style:** a domed hub with feed consoles around the rim, a validation bench and a
  macro driver board.
- **Alert states:** amber when a source is failing; grey consoles for deferred roles.
- **Connections:** `COR-N`, `COR-S`.

#### Market Specialists Room (L1)
- **Purpose:** three **family desks** (Metals, FX, Indices) reporting to the Central Trader. These
  are **not** one desk per instrument.
- **Engine note (interim adapter):** the engine still has four per-instrument specialists
  (S1–S4). The desks show every underlying runtime agent's own state and task (Character
  Registry v2 §5).
- **Connections:** `COR-N`.

#### Technical Deck (L2)
- **Purpose:** charts, candles, indicators, market structure, pullback / setup detection, entry
  timing, market sessions.
- **Agents:** T2–T8.
- **Visual style:** a long holo chart table with timeframe layers (context, setup, pullback, entry).
- **Alert states:** setup `ARMED` glow; `EXPIRED` / `INVALIDATED` fade.
- **Connections:** `COR-N`.

#### Debate Chamber (L3)
- **Purpose:** the investment debate and the risk debate, with visible evidence exchange.
- **Agents:** Bull (U1), Bear (U2), and the Aggressive / Conservative / Neutral Risk Debaters
  (U5–U7). Visits: the Research Manager (U3) and Portfolio Manager (U8) at the judge seat.
- **Contradictions:** the Contradiction Checker (P2) works in the Risk Control Room (L10). Its
  findings appear here as a remote feed.
- **Connections:** `COR-N`.

#### Data Core (L4)
- **Purpose:** market-data snapshots and validation (T1), plus journal, event-stream and runtime
  health, and reconciliation.
- **Visual style:** a reactor column that pulses only per `snapshot.created`.
- **Connections:** `COR-N`.

#### Memory Archive (L6) and Performance Lab (L7)
- **Memory Archive:** closed trades, a read-only run replay index, reviews. Post-Trade Reviewer (L1).
- **Performance Lab:** runtime and execution metrics, attribution, workload / review metrics with
  sample-size honesty. Performance / Attribution (L2).
- **Connections:** `COR-S`.

#### Execution Bay (L9) — restricted
- **Purpose:** paper order routing. **Paper Broker only**; the MT5 / Vantage demo path is deferred
  and is not rendered.
- **Agents:** Execution Checker (P4), Paper Execution Agent (E1).
- **Visual style:** launch tubes, a docking board, and a large `PAPER` hull marking from telemetry.
- **Connections:** `COR-S` (ordinary door with a restricted marking).

#### Risk Control Room (L10) — restricted
- **Purpose:** the deterministic risk layer. Zones:
  - **intake:** the courier drops the proposal here;
  - **core:** the contradiction check (P2), rule checks, sizing, exposure and the breaker (P3);
  - **outbox:** E1 collects an order here, only after `risk.approved` + `order.created`.
- **Visual style:** cooler light and a darker palette; the breaker lever is display only.
- **Alert states:** RED when the breaker is tripped (door panel shows **BREAKER TRIPPED**, outbox
  dark); amber on `REVIEW_REQUIRED`.
- **Connections:** `COR-S` (ordinary door with a restricted marking).

#### Habitat (`H-HAB`)
- **Purpose:** ambient life (§12): café, lounge, billiards, plants, cosmetic rest. It also holds
  the **recovery zone** with real-cooldown pods and the Medic persona's vitals board (§13).
  Cosmetic rest pods and real-cooldown pods are visibly different.
- **Agents:** the Habitat Host (cosmetic), the Medic persona (O2), idle agents, and agents in a real
  cooldown.
- **Alert states:** lighting follows the station alert level.
- **Connections:** `H-CMD`, and R1–R6 (reserved in V1).

#### Reserved rooms (L5, L8, R1–R6)
- Empty, unlit shells with a "RESERVED" plate; no agents enter in V1.
- R1 is designated for the future Performance & Wellbeing / Coaching Room.

---

## 4. Agent visual model

Every visible agent is described by one record in WorldState. Technical fields come from
telemetry and the agent registry; display fields come from the persona registry (§5).

| Field | Source | Example |
|---|---|---|
| `technical_id` | Agent registry (Foundation §4.20) | `risk_engine` |
| `code` | Foundation roster | `P3` |
| `display_name` | Persona registry (UI only) | "Lt. Cmdr. Sera Quill" |
| `role` | Registry | Risk Auditor |
| `department` | Registry group | Validation and risk |
| `current_room` / `target_room` | Adapter (§7) | `L10` / `L10` |
| `anchor` | Adapter (interaction point in the room) | `risk.sizing_console` |
| `current_task` | `agent.task.started` payload | "risk checks: proposal prop_7f3a" |
| `market_focus` | `market.focus.changed`, task payload | `EURUSD` |
| `runtime_state` | Telemetry (layer design §3.2) | `CHECKING` |
| `visual_state` | Derived (§6) | `risk_review` |
| `workload` | `wellbeing.load.updated` | 0.42 |
| `confidence` | Only where a typed output has one (e.g. a classifier label confidence); **never** an LLM's self-assessment presented as fact | — |
| `metrics` | Metrics API (layer design §6.2–§6.3), role-appropriate, with sample sizes | "rules checked today: 58" |
| `status` | Derived badge: icon + colour + text | ⌕ violet "risk review" |
| `stale_since` | Adapter (§1.4) | null |

**Identity rule:** `technical_id` is the only key used in events, schemas and storage. The
`display_name`, portrait and colours can change at any time without touching any contract.

---

## 5. Persona / display-name system

### 5.1 Design

- A **persona registry** (UI configuration) maps `technical_id` → `display_name`, rank/title,
  portrait/sprite set, accent colour, voice line style (future).
- A **local override file** (not committed, owner-only) may replace any persona. Overrides are
  merged at UI start.
- **Localisation:** display names and titles are UI strings and can be translated.
- **Technical schemas, event payloads, logs and the journal never contain persona names.**

### 5.2 Franchise names

The owner likes Star Trek-style crew naming (the example `display_name: Spock`). Recommended
approach:

- The **committed default registry uses original, crew-style names** (below), so the repository and
  any shared screenshots carry no franchise character names, ranks insignia or logos.
- The owner may put **franchise names in the local override file** for personal use. They stay out
  of the repository and out of every technical contract, and can be removed at any time.

### 5.3 Proposed default personas (UI-level, replaceable)

| Code | Technical role (`technical_id`) | Suggested display persona | Room | Visual behaviour |
|---|---|---|---|---|
| U8 | Portfolio Manager (`portfolio_manager`) | Captain Aurelia Voss | Main Command | Command chair; stands to stamp the rating; walks to the judge seat to close the risk debate |
| U3 | Research Manager (`research_manager`) | Commander Idris Kael | Main Command | Strategy table; judge seat to close the investment debate |
| O1 | Supervisor (`supervisor`) | First Officer Mara Solen | Main Command | Ops console; occasional room visits when a run starts (event-driven) |
| U4 | Trader (`trader`) | Lt. Cmdr. Rook Halden | Main Command | Trading console; draws advisory levels as dashed lines |
| P1 | Trade Proposal Builder (`trade_proposal_builder`) | Ensign Tavi Marr | Main Command | Assembles the proposal card; carries it along `COR-S` to the Risk Control Room intake |
| U1 | Bull Researcher (`bull_researcher`) | Lt. Leo Brask | Debate Chamber | Left inner podium, neutral spotlight, bull icon + label |
| U2 | Bear Researcher (`bear_researcher`) | Lt. Ursa Venn | Debate Chamber | Right inner podium, neutral spotlight, bear icon + label |
| U5 | Aggressive Risk Debater (`risk_aggressive`) | Ensign Rhea Vantor | Debate Chamber | Outer arc, neutral light (unlit while the risk debate has no producer) |
| U6 | Conservative Risk Debater (`risk_conservative`) | Ensign Hollis Crane | Debate Chamber | Outer arc, neutral light (unlit while the risk debate has no producer) |
| U7 | Neutral Risk Debater (`risk_neutral`) | Ensign Tamsin Ly | Debate Chamber | Outer arc, neutral light (unlit while the risk debate has no producer) |
| M1 | Causal / Macro Analyst (`causal_macro_analyst`) | Dr. Elara Maren | Lab / Research Hub (`H-LAB`) | Driver board; draws arrows between drivers and assets |
| R1 | Central Bank Research (`research_central_bank`) | Lt. Cassian Rho | Lab / Research Hub (`H-LAB`) | Feed console; hands items to the Macro room |
| R2 | Economic Data Research (`research_economic_data`) | Ensign Mira Dal | Lab / Research Hub (`H-LAB`) | Calendar console; active after releases |
| R3 | Market News Research (`research_market_news`) | Ensign Poe Varga | Lab / Research Hub (`H-LAB`) | Feed console (deferred: greyed) |
| R4 | Geopolitical Research (`research_geopolitical`) | Lt. Imre Castell | Lab / Research Hub (`H-LAB`) | Feed console (deferred: greyed) |
| R5 | Rates/Bonds Research (`research_rates_bonds`) | Lt. Selah Ward | Lab / Research Hub (`H-LAB`) | Yield-curve console (deferred: greyed) |
| R6 | Corporate/Earnings Research (`research_corporate_earnings`) | Ensign Theo Brandt | Lab / Research Hub (`H-LAB`) | Earnings console (deferred: greyed) |
| V1 | Source Validator (`source_validator`) | Specialist Ada Kerr | Lab / Research Hub (`H-LAB`) | Scanner gate at the bench |
| V2 | Freshness Checker (`freshness_checker`) | Specialist Noor Hale | Lab / Research Hub (`H-LAB`) | Timestamp ring tool |
| V3 | Duplicate Detector (`duplicate_detector`) | Specialist Jem Oris | Lab / Research Hub (`H-LAB`) | Merges duplicate item cards |
| V4 | Fact / Reaction / Interpretation Classifier (`claim_classifier`) | Specialist Lyra Fenn | Lab / Research Hub (`H-LAB`) | Tags claim cards F / R / I |
| S1 | XAU/USD Specialist (`specialist_xauusd`) | Lt. Auric Reyes (**Metals family desk**, interim adapter) | Market Specialists Room (L1) | Own task row on the Metals desk |
| S2 | EUR/USD Specialist (`specialist_eurusd`) | Lt. Elise Marchetti (**FX family desk**, interim adapter) | Market Specialists Room (L1) | Own task row and own state on the FX desk |
| S3 | USD/JPY Specialist (`specialist_usdjpy`) | shown on the **FX family desk** (interim adapter; separate task row and state, never merged with S2) | Market Specialists Room (L1) | Own task row and own state on the FX desk |
| S4 | NAS100 Specialist (`specialist_nas100`) | Lt. Nash Coleman (**Indices family desk**, interim adapter) | Market Specialists Room (L1) | Own task row on the Indices desk |
| T2 | Market Session (`market_session`) | Ensign Sol Meridian | Technical Deck (L2) | Session clock ring |
| T3 | Market Structure (`market_structure`) | Lt. Vega Stone | Technical Deck | Draws structure levels |
| T4 | Technical Indicator (`technical_indicator`) | Lt. Iris Calder | Technical Deck | Indicator panels |
| T5 | Candle / Price Action (`price_action`) | Ensign Wick Arlo | Technical Deck | Highlights candles at levels |
| T6 | Pullback / Setup (`pullback_setup`) | Lt. Tess Harrow | Technical Deck | Setup lifecycle board |
| T7 | Entry Timing (`entry_timing`) | Ensign Kit Sparrow | Technical Deck | Countdown on an armed setup |
| T8 | Technical Analyst (`technical_analyst`) | Lt. Cmdr. Rune Halloway | Technical Deck | Assembles the report crystal |
| T1 | Data Validator (`data_validator`) | Chief Engineer Oren Kade | Data Core | Reactor console |
| P2 | Contradiction Checker (`contradiction_checker`) | Lt. Nyx Aldren | Risk Control Room (L10) | Intake checklist |
| P3 | Risk Engine / Risk Auditor (`risk_engine`) | Lt. Cmdr. Sera Quill | Risk Control Room (L10) | Rule checklist; breaker lever |
| P4 | Execution Checker (`execution_checker`) | Chief Dane Corso | Execution Bay | Pre-flight checklist |
| E1 | Paper Execution Agent (`paper_execution`) | Lt. Kiri Sato | Execution Bay | Launch console (paper) |
| E2 | MT5 Execution Agent (`mt5_execution`) | Lt. Bram Oduya | Execution Bay | Appears only after the demo gate |
| L1 | Post-Trade Reviewer (`post_trade_reviewer`) | Archivist Quinn Morrow | Memory Archive | Shelves review crystals |
| L2 | Performance / Attribution (`attribution`) | Dr. Pax Lindqvist | Performance Lab | Updates metric walls |
| O2 | Operational Wellbeing Monitor (`wellbeing_monitor`) | Dr. Noa Ferris (Medic persona); QM Bex Talon (Quartermaster persona) | Habitat recovery zone (Medic); Main Command (Quartermaster) | Medic visits overloaded agents; Quartermaster tends budget gauges |
| — | Habitat Host (`habitat_host`, cosmetic, UI-only id) | Bix, service drone | Habitat café zone | Serves drinks; no operational meaning |

Technical ids not yet fixed in the layer design (M1, V*, S*, T*, R*) are **proposals** to be
confirmed in Foundation Phase 1 when the registry is written.

---

## 6. Visual agent states

### 6.1 Derivation

`visual_state = f(runtime_state, agent role, current task kind, recent outcome event)`. The runtime
state (layer design §3.2) is the source; the visual state adds role context. Priority when several
apply: `offline` > `error` > `paused` > `overloaded` > `resting` > transient outcome (`approved` /
`rejected`, display time only) > working states > `waiting` > `walking` > `idle`.

| Runtime state (layer design §3.2) | Role / task context | Visual state |
|---|---|---|
| `OFFLINE` | any | `offline` |
| `OFF_DUTY`, `IDLE` | any | `idle` (ambient-eligible, §12) |
| `ASSIGNED` | moving to a work position | `walking` |
| `FETCHING` | research roles R* | `researching` |
| `FETCHING` | other roles (data fetch) | `analysing` |
| `CHECKING` | V1–V4, T1 | `validating` |
| `CHECKING` | P2, P3 | `risk_review` |
| `CHECKING` / `PREFLIGHT` / `LAUNCHING` / `AWAITING_FILL` | P4, E1, E2 | `executing` |
| `THINKING` / `CHECKING` | M1, S*, T2–T8, P1, U4 | `analysing` |
| `THINKING` | U3, U8 closing a debate or rating | `reviewing` |
| `SPEAKING`, `LISTENING` | U1, U2, U5–U7 | `debating` |
| working, with a continuous duty | O1, O2, T7 armed, T1 between snapshots | `monitoring` |
| `WAITING` | any | `waiting` |
| `THINKING` / `CHECKING` | L1, L2 | `post_trade_review` |
| (event) `risk.approved` / `risk.rejected` | P3 (display time only) | `approved` / `rejected` |
| `RESTING` | any | `resting` |
| `OVERLOADED` | any | `overloaded` |
| (event) `system.paused` | all agents | `paused` |
| `ERROR` | any | `error` |
| `DEGRADED` | any | working state kept, plus a flicker modifier and ⚠ badge |

### 6.2 State catalogue

| Visual state | Animation | Room behaviour | Screen behaviour | Badge (icon + colour) | Movement | Possible next states |
|---|---|---|---|---|---|---|
| `idle` | Relaxed stance at desk; may start ambient after a delay | Home workstation, or habitat when ambient | Own screens show last result | ● neutral | Yes (ambient only) | walking, any working state, offline, paused |
| `walking` | Walk cycle along the path | Corridor / hub walkway | — | ➜ white | Yes | the target state; idle |
| `researching` | Reading streams at a feed console | Lab / Research Hub (`H-LAB`) | Item stream animates | ⇣ teal | No | validating (hand-off), idle, error, overloaded |
| `validating` | Scanning item or snapshot cards | Lab / Research Hub (`H-LAB`) bench / Data Core | Pass/fail marks per item | ⌕ violet | No | idle, error |
| `analysing` | Working the room's main display | Owning analysis room | Room screen updates as outputs arrive | ✦ cyan, pulsing | No | reviewing, waiting, idle, error |
| `monitoring` | Watchful pose, periodic glance at a gauge | Assigned console | Live gauges | ◉ blue | No | analysing, executing, idle, paused |
| `debating` | Speaking: gestures, spotlight; listening: facing speaker | Debate Chamber podium | Argument columns and evidence cards | 🗨 side icon + label | No (during debate) | reviewing (judges), idle |
| `reviewing` | Judge seat or command chair; stamp gesture at the end | Debate Chamber judge seat / Main Command | Recommendation / rating appears | ⚖ gold | No | idle, walking |
| `waiting` | Seated, hourglass | Work position or waiting bench | — | ⌛ grey | No | any working state |
| `risk_review` | Checks lighting one by one | Risk Control Room (L10) | Rule checklist | ⌕ violet + shield | No | approved, rejected, idle |
| `approved` | Stamp and outbox light turns green (display time only) | Risk Control Room | Checklist all ✓; outbox light green | ✔ green | No | risk_review, idle |
| `rejected` | Stamp; outbox stays dark (display time only) | Risk Control Room | Blocked reason highlighted | ✖ red-orange + reason icon | No | risk_review, idle |
| `executing` | Pre-flight checks, launch, docking | Execution Bay | Order lifecycle board | 🚀 white on dark | No | monitoring, idle, error |
| `post_trade_review` | Shelving crystals / updating walls | Memory Archive / Performance Lab | Review and metric panels update | ◆ gold | No | idle |
| `resting` | In a pod with a recharge bar and countdown | Habitat recovery zone | Vitals board shows cooldown | ☾ soft blue | Only to the pod | idle |
| `overloaded` | Steam / sparks at the console | Stays at its console | Vitals board flags it | ♨ orange | No | resting, working state, error |
| `paused` | Standing still at station; lights dimmed | Where it is | Screens frozen with "PAUSED" | ⏸ grey-blue | No | previous state on `system.resumed` |
| `error` | Red beacon; still pose | Where it is | Error summary on its console | ✖ red | No | idle, working state (on next task) |
| `offline` | Not drawn in rooms; greyed in the roster panel | — | — | ⏻ grey | No | idle |

All badges combine **icon + text + colour**; colour is never the only signal (§18).

---

## 7. State → room movement

Movement is **cosmetic** and happens **after** the engine's state change (§1.6).

| Visual state / trigger | Destination |
|---|---|
| `researching` | Lab / Research Hub (`H-LAB`), the role's feed console |
| `validating` (research) | Lab / Research Hub (`H-LAB`) validation bench |
| `validating` (market data, T1) | Data Core reactor console |
| `analysing` — macro (M1) | Lab / Research Hub (`H-LAB`) driver board |
| `analysing` — market-specific (S*) | Market Specialists Room (L1), the family desk; each underlying agent keeps its own task row (interim adapter) |
| `analysing` — technical (T3–T8) | Technical Deck chart table |
| `analysing` — proposal (P1), Trader (U4) | Main Command consoles |
| `debating` | Debate Chamber podium (assigned seat) |
| `reviewing` | Debate Chamber judge seat (debate close) or Main Command chair (final rating) |
| `risk_review`, `approved`, `rejected` | Risk Control Room (L10) |
| `executing` | Execution Bay |
| `post_trade_review` | Memory Archive (L1) / Performance Lab (L2) |
| `monitoring` | The agent's duty console |
| `waiting` | Stay at the work position, or the room's waiting bench |
| `overloaded` | **Stays at its console**; moves to the Habitat recovery zone only when `agent.resting` arrives (a real cooldown) |
| `resting` | Habitat recovery zone pod |
| `idle` | Home workstation; after an idle delay, optionally a Habitat zone: café, lounge, window bench, billiards or rest (§12) |
| `paused` | No movement; stays where it is |
| `error` | No movement; the Medic persona walks to it |
| `offline` | Removed from rooms |

Hand-off movement (a research role carrying an item to the macro driver board, P1 carrying a
proposal along `COR-S` to the Risk Control Room intake) happens only when an event implies the hand-off, e.g. `research.item.accepted` or
`trade.proposed`.

---

## 8. Agent interactions

| Interaction | Type | Triggered by |
|---|---|---|
| Two agents at the same console | **A. Operational** | Both have tasks on the same artefact (e.g. T3 and T4 on the same snapshot id) |
| Small group around the command table | **A. Operational** | `run.started` for a decision cycle: U3, U8, O1, U4 gather |
| Debate participants facing each other | **A. Operational** | `debate.started` … `debate.completed` |
| Evidence card placed on the central evidence stage | **A. Operational** | `debate.turn.completed` whose paired `agent.task.completed` case cites research or analysis ids |
| Hand-off of a data crystal / item card | **A. Operational** | `analysis.created` → next consumer's `agent.task.started`; `research.item.accepted` |
| Proposal card carried along `COR-S` to the Risk Control Room intake | **A. Operational** | `trade.proposed` |
| Supervisor visiting a room | **A. Operational** | `market.focus.changed`, `run.started`, `system.paused` (O1 walks to the room concerned) |
| Medic persona visiting an overloaded agent | **A. Operational** | `agent.overloaded`; escort to the Habitat recovery zone on `agent.resting` |
| Idle agents chatting | **B. Ambient** | Both agents `idle` beyond the ambient delay; seeded selection |
| Billiards, café, lounge, window bench (Habitat) | **B. Ambient** | `idle` / `OFF_DUTY`; seeded selection |
| Habitat Host serving | **B. Ambient** | Agents present in the café zone |

Rules:
- Operational interactions show only relationships present in the event data (shared artefact ids,
  debate membership, hand-offs).
- Ambient interactions never depict decisions, disagreements or outcomes, and never involve an agent
  with a task.
- The expanded HUD of an agent in an ambient interaction shows the "ambient" glyph.

---

## 9. Status HUD above each agent

### 9.1 Default (minimal) HUD

```
  Lt. Cmdr. Sera Quill  ⛨      ← display name + role icon
  ⌕ risk review · EURUSD        ← state (icon + word) · market focus if any
```

Shown from hub view inward. In overview, only the state pip is drawn.

### 9.2 Expanded HUD (hover / click)

| Field | Shown for |
|---|---|
| Current task (from `agent.task.started`) | all |
| Current room, last action (last event, with age) | all |
| Workload (load score, §13) | all |
| Errors / retries (window) | all |
| Confidence | only where a typed, calibrated value exists; LLM self-reported confidence is either hidden or labelled "self-reported, uncalibrated" |
| Recent contribution | analysis and debate agents: agreement / calibration measures (layer design §6.3) **with sample size**; hidden below the minimum sample |
| Role metrics | research: items collected, acceptance rate; validators: accepted / rejected by reason; technical: setups by state; risk: checks, rejections by rule; execution: orders, fills, slippage; review: trades reviewed |

**No profit figures for agents that do not trade.** P&L appears only on the Main Command, in the
Execution Bay (positions) and in the Performance Lab (strategy level). Agent-level "profit" is never
shown, because no single agent owns a trade's outcome.

---

## 10. Room screens

> The authoritative display list, placements and data sources are `docs/STELLAR_SCREEN_REGISTRY.md` v2. The table below is the original concept summary, with room names updated to the approved vessel.

Screens render only from WorldState (events + snapshots). Each value carries its source timestamp;
values older than their freshness window are drawn dimmed with an age label.

| Room | Screens |
|---|---|
| **Main Command** | Global P/L; paper balance / equity; open positions; drawdown; system mode `PAPER` from telemetry (no DEMO / LIVE path); risk and breaker state; station alert level; market activity for the four instruments; current setup and rating |
| **Lab / Research Hub (`H-LAB`)** | Source feeds per role; new findings (accepted / rejected); source reliability (trust tier, acceptance rate); freshness clocks; duplicates merged; F / R / I label mix |
| **Lab / Research Hub (`H-LAB`), macro zone** | Central-bank events (Fed, ECB, BoJ); rates and yields; spreads; economic-calendar events with countdowns; geopolitical board; causal-analysis summary with driver arrows and coverage |
| **Market Specialists Room (L1), per family desk (one row per underlying agent / instrument)** | Price and candles; relevant macro context from the specialist; active setup; event-risk windows; session clock |
| **Technical Deck** | EMA, RSI, MACD, ATR panels; market structure levels; candle / price-action highlights; pullback state; setup lifecycle; entry-timing countdown |
| **Debate Chamber** | Bull arguments; Bear arguments; contradictions (remote feed from P2); evidence cards; round counter; verdict |
| **Risk Control Room (L10)** | Proposed risk (% of equity at stop); rule checks with value vs limit; blocked reason; exposure bars; breaker state |
| **Execution Bay** | Order lifecycle: created → sent → acknowledged → filled / rejected → closed; pending orders; pre-flight results; reconciliation status |
| **Data Core** | Feed health per source; snapshot pulses; stale-feed alerts; event-bus and journal health |
| **Memory Archive** | Previous comparable setups; trade history; post-trade reviews and lessons |
| **Performance Lab** | Win / loss; expectancy; drawdown; R-multiple distribution; per-agent contribution; sample sizes and "insufficient sample" overlays |
| **Habitat recovery zone** | Per-agent load; retries; latency; rate limits; request queue; budget gauges; rest schedule |

### 10.1 The decision chain on screen

Stellar's screens must let the owner follow **every** decision end to end. Each stage below maps
to a real artefact and event in the Foundation Plan (§9), so the chain on screen is exactly the
chain in the engine:

```
RESEARCH FINDINGS → VALIDATED FACTS → CAUSAL / MACRO INTERPRETATION → MARKET BIAS
  → TECHNICAL CONFIRMATION → TRADE PROPOSAL → RISK DECISION → EXECUTION → POST-TRADE REVIEW
```

| Stage | Source (Foundation) | Event(s) | Shown in | Screen content |
|---|---|---|---|---|
| Research findings | `ResearchItem` (R1–R6) | `research.item.collected` | Lab / Research Hub (`H-LAB`) | New items per role, source, age |
| Validated facts | Validation V1–V4, claim labels | `research.item.accepted` / `rejected`, `research.snapshot.created` | Lab / Research Hub (`H-LAB`) bench | Accepted claims tagged **FACT / REACTION / INTERPRETATION**; rejections with reasons |
| Causal / macro interpretation | `MacroAssessment` (M1) | `analysis.created` (macro) | Lab / Research Hub (`H-LAB`) | Drivers with direction and strength, each linked to cited claim ids; coverage |
| Market bias | `MarketAssessment` (S1–S4) | `analysis.created` (market) | Market Specialists family desk (L1; interim adapter); Main Command Agent Pipeline | Pressure on the instrument, primary drivers, **counter-evidence**, event-risk windows, coverage, age |
| Technical confirmation | Structure / momentum / price action / setup (T3–T7) | `analysis.created`, `setup.state.changed` | Technical Deck; family desk | Higher-timeframe bias, pullback state, candle / price-action confirmation, setup lifecycle |
| Trade proposal | `TradeProposal` (P1) from the PM's rating on the setup | `decision.final.created`, `trade.proposed` | Main Command | Direction, entry, stop, target, reward:risk, rating, contradictions |
| Risk decision | `RiskDecision` (P3) | `risk.check.*`, `risk.approved` / `risk.rejected` | Risk Control Room (L10) | Every rule with value vs limit; approved size or blocked reason |
| Execution | Order intent → Paper Broker (E1) | `order.*` | Execution Bay | `PAPER` order: entry, stop, target, size, lifecycle |
| Post-trade review | `TradeReview` (L1), settlement (L2) | `trade.closed`, `memory.review.created`, `memory.outcome.settled` | Memory Archive, Performance Lab | Outcome, R multiple, what the chain said at each stage |

The **Main Command Agent Pipeline display** (`DSP-CMD-04`) carries the **decision-chain strip** for the focus
instrument: the nine stages as a row of tiles with the current stage lit, each showing its
timestamp. Clicking a tile opens that stage's room screen, and clicking the chain opens the proposal
timeline (§17).

**How the chain is timed (Foundation setup-first rule, R-1):** research and validation run on
their own schedules. The macro and market assessments are produced when the decision chain runs for
a candidate setup (Foundation §5.1), so between cycles the "Market bias" panel shows the **latest**
assessment with its age. The "stance" line is a presentation summary: it states which setups the
deterministic technical layer is currently watching for (from the higher-timeframe bias, T3),
alongside whether the latest research pressure agrees or disagrees. It is information, not an
instruction to any agent.

**Research bias alone never executes a trade.** A trade can only follow the full chain: a
deterministic setup, the PM's typed rating on that setup, a `TradeProposal`, an approved risk
decision, then an order intent. The screens make this visible by never showing an order without
the preceding stages lit.

### 10.2 Worked example: XAU/USD (illustrative values)

```
┌ XAU/USD · RESEARCH SYNTHESIS ─────────────────────── updated 14:05 · coverage 2/4 ┐
│ Bearish pressure                                                                │
│ Primary drivers:      USD strength · rising US yields · Fed expectations          │
│ Counter-evidence:     nearby support · safe-haven demand                          │
│ Current stance:       LOOK FOR SELL SETUPS  (higher-timeframe bias: bearish)       │
│ Status:               Waiting for technical confirmation  (setup: WATCHING)       │
└──────────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌ TECHNICAL CONFIRMATION ─────────────────────────────────────────────────────────┐
│ Bearish structure confirmed · Pullback rejected at resistance · Momentum turned   │
│ Setup: ARMED → PROPOSED              SELL PROPOSED  (rating: Buy on SHORT setup)   │
└──────────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌ RISK REVIEW ──────────────────────────────────────────────────────────────────────┐
│ 12 / 12 checks passed · risk 0.x % of equity · spread OK · no event window        │
│ APPROVED                                  (or: REJECTED — reason: news window)   │
└──────────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌ EXECUTION · PAPER ─────────────────────────────────────────────────────────────────┐
│ PAPER SELL · entry · stop · target · size (lots)                                   │
│ lifecycle: created → sent → filled → open → closed                                 │
└──────────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌ POST-TRADE REVIEW ─────────────────────────────────────────────────────────────────┐
│ outcome · R multiple · exit reason · which stages agreed / disagreed · coverage     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Values in the example are placeholders. No risk threshold, price level or rating mapping is chosen
here; all come from the engine (Foundation §8 and §13).

---

## 11. Telemetry → visual event mapping

All event names are canonical (Foundation §10.1, layer design §4.3). The adapter reduces them into
WorldState; the renderer then animates.

| Event | Visual response (world) | Room response | Agent animation | Screen update |
|---|---|---|---|---|
| `station.heartbeat.emitted` | Clears "telemetry lost" if shown | — | — | Uptime indicator |
| `station.alert_level.changed` | Ship lighting changes (GREEN / BLUE / AMBER / RED) | All rooms relit | — | Main Command alert panel |
| `run.started` | Decision cycle begins | Main Command brightens | Supervisor, PM, RM, Trader gather at the command table | Run queue |
| `market.focus.changed` | Focus instrument highlighted on the minimap | The instrument's row on its family desk lights up | The family specialist is at its desk; Supervisor visits | Main viewscreen switches instrument |
| `agent.task.started` | Badge → derived working state | Target room marks the work position | Walk to work position, then working animation | Task label in HUD |
| `agent.task.completed` | Badge → next state (usually idle) | — | Working animation ends; hand-off if a consumer starts | Output appears on the relevant screen |
| `agent.task.failed` | Badge → `error` | Room outline amber | Red beacon; Medic persona walks over | Error summary on the agent's console |
| `agent.state.changed` | Badge → derived visual state (§6.1) | — | Per state catalogue | — |
| `snapshot.created` / `snapshot.rejected` | Reactor pulse / red flash | Data Core | T1 validating | Feed health; stale alerts |
| `market.data.stale_detected` | Conduit flicker | Data Core, affected family-desk row outlined | — | Stale-feed alert with age |
| `research.item.collected` | New star in the item stream | Lab / Research Hub (`H-LAB`) | Collector at feed console | Findings stream |
| `research.item.accepted` / `research.item.rejected` | Item passes the gate / dims | Lab / Research Hub (`H-LAB`) bench | Validator scan; hand-off to the macro driver board on accept | Reliability and acceptance counters |
| `research.snapshot.created` | Coverage bar refresh | Lab / Research Hub (`H-LAB`) | — | Coverage line |
| `analysis.created` | Report / assessment crystal appears | Producing room | Producer lifts the crystal; carries it to the consumer if one starts | Assessment summary on the producing room's screen |
| `setup.state.changed` | Setup card changes state | Technical Deck | T6 moves the card on the lifecycle board | Setup lifecycle; `ARMED` glow |
| `debate.started` | Chamber spotlights on | Debate Chamber | Participants walk to podiums and face each other | Round counter starts |
| `debate.turn.completed` | Round counter advances (no score, bar or winner) | Debate Chamber | Speaker gestures; evidence card placed on the central stage | New argument in the speaker's column (content from the paired `agent.task.completed`) |
| `debate.completed` | Spotlights off; verdict shown | Debate Chamber | Judge stamps; participants return to seats / idle | Verdict |
| `decision.final.created` | Rating stamped on the main viewscreen | Main Command | PM stamp gesture | Rating; `REVIEW` flashes amber with icon |
| `trade.proposed` | Proposal card leaves Main Command | Main Command → `COR-S` → Risk Control Room intake | P1 carries the card to `risk.intake_drop` | Risk intake shows the proposal |
| `risk.check.started` / `risk.check.completed` | Checklist lines light one by one | Risk Control Room (L10) | P2 / P3 `risk_review` | Rule checks with value vs limit |
| `risk.approved` | Outbox light turns green | Risk Control Room | P3 `approved` (display time); an order capsule appears in the outbox **only after** `order.created`, and E1 carries it to the Execution Bay | "Approved" with size and risk % |
| `risk.rejected` | Outbox stays dark | Risk Control Room | P3 `rejected` (display time) | Blocked reason(s) highlighted |
| `order.created` | Shuttle loaded in a launch tube | Execution Bay | E1 at the launch console | Order row "created" |
| `order.preflight.failed` | Launch aborted | Execution Bay amber | P4 shakes head; checklist item ✖ | Pre-flight failure reason |
| `order.sent` | Shuttle launches | Execution Bay | E1 launch gesture | Row "sent" |
| `order.filled` | Shuttle docks | Execution Bay | — | Row "filled", fill price, slippage |
| `order.rejected` | Shuttle returns | Execution Bay | — | Row "rejected", reason |
| `trade.closed` | Crystal travels to the Memory Archive | Execution Bay → Memory Archive | L1 receives and shelves it | Trade history; P/L on Main Command |
| `memory.review.created` | Crystal glows | Memory Archive | L1 `post_trade_review` | Review summary |
| `memory.outcome.settled` | Performance Lab wall updates | Performance Lab | L2 `post_trade_review` | Metrics with sample sizes |
| `wellbeing.load.updated` | Load bar on the vitals board | Habitat recovery zone | — | Per-agent load |
| `agent.degraded` | Flicker modifier on the agent | — | Slower animation, ⚠ badge | Degraded source listed |
| `agent.overloaded` | Badge → `overloaded` | Habitat recovery zone amber | Steam at its console; Medic persona walks over | Vitals board flags the agent |
| `agent.resting` | Badge → `resting` | Habitat recovery zone | Agent walks (or fades) to a pod | Cooldown countdown |
| `agent.rest.ended` | Badge → `idle` | — | Leaves the pod | — |
| `budget.warning` | Quartermaster gauge turns amber | Main Command (budget console) | Quartermaster persona at the gauges | Budget used vs limit |
| `system.paused` | Ship dims; "PAUSED" banner | All rooms | Everyone freezes in place (`paused`) | Screens frozen with reason |
| `system.resumed` | Lights restore | All rooms | Agents resume their telemetry states | — |
| `circuit_breaker.tripped` | Ship goes RED | Risk Control Room lever drops (display only); door panel shows BREAKER TRIPPED; outbox dark | P3 at the lever; others stop working animations | Breaker panel: tripped, rule, value vs limit; "Only the owner can reset (owner command)" |
| `circuit_breaker.reset` | RED clears to the current alert level | Door panel clears | P3 raises the lever | Reset time and owner reason |

---

## 12. Ambient life

- **Eligibility:** only agents whose runtime state is `IDLE` or `OFF_DUTY`, after an idle delay (a
  UI setting).
- **Activities:** café, lounge conversation, window bench, billiards, rest zone, walking the
  Habitat ring (all zones of `H-HAB`).
- **Selection:** a seeded generator keyed on time and agent ids (layer design §5.3 rule 5), so
  replays match. The generator is the ported `clock-rng` (mulberry32 / fnv, audit S5) with an
  injected clock: seed = station seed + agent id + time bucket. **No `Math.random`, `Date.now` or
  `performance.now`** in the adapter, engine-layer or ambient modules; a determinism lint enforces
  this (audit S6; §21).
- **Reproducible:** the same event fixture, seed and frozen clock produce the same ambient scene,
  frame for frame, in tests and in replay mode (§21).
- **Beat budget:** a station-level cap on how many ambient beats (a conversation, a billiards game,
  a walk to the window) may start per time window, so the station never looks busier than the
  engine is. The cap is a UI setting (VW-9).
- **Pre-emption:** the moment a task event arrives for an ambient agent, its badge updates at once
  and the agent leaves the activity **immediately** (no "finish the animation" delay); if its walk
  would exceed the maximum walk time it fades and reappears at the work position. Ambient agents
  always yield anchors and corridor right of way to operational agents (§16). Ambient behaviour
  **never** delays a task, a badge or a screen.
- **Not derived from StarNet:** StarNet's idle "sentience" engine (needs, curiosity, social
  encounters, mourning, quirks; audit S27) is **not copied or adapted**. It is non-deterministic,
  uses emotion language and is part of StarNet's product character. Stellar's ambient scheduler is
  small and written for this plan.
- **No implied emotions:** ambient scenes show routine activity (drinking coffee, playing billiards,
  looking out of the window). They never display moods, satisfaction, fatigue or "happiness" as
  facts about an AI agent. Tooltips on ambient activity read "ambient animation".
- **Separation of pods:** cosmetic rest pods are ambient; **recovery pods (Habitat recovery zone)
  mean a real cooldown** (`agent.resting`). They look different (recovery pods show a countdown and
  the vitals link).

---

## 13. Wellbeing visualization

Wellbeing is operational health (layer design §3.9, §6.5). It can **never** change a trade or risk
decision; its only real effects are pauses and cooldowns decided in the engine.

| Input (from telemetry) | Visual |
|---|---|
| Latency vs the agent's baseline | Pulse speed on its vitals row |
| Retry rate, model / API errors | Retry counter; ⚠ markers |
| Request queue length | Queue bar at the Supervisor's console and in the Habitat recovery zone |
| Rate limits (429s) per provider | Provider row turns amber |
| Cost budget | Quartermaster fuel-cell gauges |
| Repeated failures | `error` badges; Medic visits |
| Workload (load score) | Load bar per agent |
| Idle time | Utilisation per agent |

| Outcome | Condition (from engine events) | Visual |
|---|---|---|
| **normal** | No warnings | Green-check row, calm room lighting |
| **busy** | High load, below overload | Faster working animations; row amber-free |
| **overloaded** | `agent.overloaded` | ♨ badge; Medic persona visits |
| **recovering** | `agent.resting` … `agent.rest.ended` | Pod with countdown |
| **paused** | `system.paused` | Ship dimmed; "PAUSED" with reason |

---

## 14. Art direction

### 14.1 Identity

An **original** Stellar Agents look: a calm, optimistic exploration-vessel interior that is also
unmistakably a **trading command centre**. Stylised, not photorealistic; a miniature living world
you can read at a glance.

**Must avoid:**
- StarNet artwork, sprites, branding or visual identity;
- Star Trek sets, uniforms, insignia, delta badges, logos, props, ship silhouettes, typefaces, and
  the LCARS interface style (rounded colour-bar "elbows" and block layouts);
- voxel / blocky / Minecraft-like forms; pixel art.

### 14.2 Materials

- Warm off-white composite wall panels with soft seams; brushed titanium trim; dark smoked glass for
  displays; matte deep-navy floors.
- Secondary: dark graphite for consoles, technical areas and accents. The vessel is never fully
  dark (Visual Bible C1).
- **Risk Control Room (L10):** gunmetal structural elements combined with warm off-white panels and
  graphite technical accents, on the approved grating floor; cooler and more focused through
  materials and lighting, never a black military bunker. Visible hull ribs and restricted
  markings; no armoured bulkhead, blast door or airlock (security is logical). See the L10 design
  sheet RC-1 and RC-2.
- **Habitat:** light wood-like laminates, fabric, plants, warm light.

### 14.3 Lighting

- Soft indirect cove lighting along curved ceilings; pools of light over consoles.
- Environment light may be cyan / blue, but **lighting alone never communicates a data state**:
  data colours follow the Screen Registry (Visual Bible C7).
- Station alert level tints the cove lighting (GREEN neutral-white, BLUE cool accent, AMBER warm
  strips, RED deep red pulses), always paired with a banner and icon.
- Windows show space, distant stars and a slowly turning planet; optional day/night tint tied to FX
  sessions (layer design LD-6).

### 14.4 Screen language

- Large, clean data panels: generous margins, a restrained sans-serif, tabular numerals.
- A consistent colour grammar: teal = live data, gold = decisions, violet = checks, red-orange =
  blocked / alert, green = approved / healthy; every state also has an icon.
- Charts are simple and legible at small size: candles, lines, bars; no 3D charts.
- Every value shows its age when stale.

### 14.5 Floors, walls, consoles

- Curved walls and rounded corners throughout; corridors with light strips that point toward the
  hub doors.
- Consoles: gently curved desks with a tilted upper display and a flat touch surface; standing
  consoles in the Technical Deck; a circular command table in Main Command.
- Each room has one **hero object** readable in overview: command chair, lab dome, family
  desks, chart table, evidence stage, breaker panel, launch tubes, reactor, crystal shelves, metric wall,
  rest pods, billiard table.

### 14.6 Agents

- Slightly stylised humanoid crew, about 6–7 heads tall, simple faces, clear silhouettes readable at
  small size.
- Original uniforms: department colour on a shoulder panel plus a department **shape icon**; no
  franchise insignia.
- Varied builds, skin tones, hair and ages across the crew.

### 14.7 Animation

- Smooth, economical, readable at a distance: a small set of poses per state (§6.2) plus transitions.
- No exaggerated cartoon squash; no idle fidgeting that could be read as a working state.
- Working animations loop calmly; alerts use brief, distinct motion (a stamp, a lever), never
  constant flashing.

### 14.8 Visual hierarchy

1. Station alert level and breaker state (always visible).
2. Decisions and risk outcomes (rating, approved / rejected).
3. Agents doing operational work (full contrast, badges).
4. Room screens (legible at room focus).
5. Ambient life (lower contrast).
6. Decoration (windows, plants, props).

---

## 15. Technical rendering options

| Option | Complexity | Performance | Animation | Pathfinding | Web integration | Deployment | Maintainability | Fit with the living-world concept |
|---|---|---|---|---|---|---|---|---|
| **A. Custom Canvas 2D / 2.5D** | High: we build scene graph, batching, sprite sheets, input | Good for simple scenes; degrades without WebGL batching | All hand-built | Hand-built | Native | Static files | Poor over time: a small custom engine to own | Possible, but costly |
| **B. PixiJS** (WebGL 2D) | Moderate: a rendering library, not a framework | Very good: batched sprites, thousands of objects | Sprite-sheet and skeletal (via plugins) animation | From the engine layer (§1.7, §16), not the renderer | Excellent: plain web app; HTML/React overlays for HUDs and panels | Static files served locally | Good: small, stable API; UI logic stays ours | **Strong**: pre-rendered 2.5D isometric art with live sprites fits the cutaway look |
| **C. Phaser** | Moderate: full game framework | Very good (WebGL) | Good built-ins | Plugins available | Good, but its scene/game loop model competes with a web-app UI | Static files | Good | Good, though geared to games (physics, levels) we don't need |
| **D. Three.js / React Three Fiber** | Higher: 3D scenes, lighting, models | Good, heavier on GPU and on art (3D models) | Rich 3D animation | Navmesh libraries | Excellent (R3F with React) | Static files | Moderate: 3D asset pipeline to maintain | Strong visually, but higher art and performance cost for V1 |
| **E. Godot / Unity desktop client** | High: separate app and language | Excellent | Excellent | Built-in | Poor: a second client beside the web UI; breaks "localhost web, read-only" simplicity | Desktop builds per OS | Two stacks to maintain | Visually strong, architecturally heavy |
| **F. StarNet's renderer** (Canvas 2D bake + WebGL CRT pass) | — | — | — | — | — | — | — | **Not adopted.** Its drawing code produces StarNet's protected look (procedural pixel art, CRT phosphor) and is top-down, not isometric (audit S33–S37) |

Whatever the renderer, navigation, movement and pathfinding come from the renderer-independent
**engine layer (§1.7)**, not from the renderer. That makes option A's "hand-built pathfinding"
cost disappear, and makes Canvas 2D a cheap fallback (audit §10, option B).

**Recommended V1 direction (not implemented, not locked): B. PixiJS** remains the leading
candidate, drawing the engine layer's output, in a local web app, with
- **pre-rendered 2.5D isometric art** (rooms and agent sprite sheets rendered from 3D models or
  painted at fixed isometric angles), which gives the semi-realistic stylised look without real-time
  3D;
- **HTML overlays** (e.g. a lightweight component framework) for HUDs, panels, text and
  accessibility, because text in HTML is sharper, scalable and screen-reader friendly;
- the adapter and the engine layer as plain modules independent of the renderer (language VW-12),
  so a later move to Canvas 2D or Three.js (option D) replaces only the renderer.

This matches the layer design's intent (LD-5: WebGL renderer with pre-rendered or 3D-modelled
rooms) and keeps the UI a read-only local web page.

**Renderer spike before lock-in (VW-2).** A small, time-boxed prototype (about one week, in the
engine-port stage V1-E, §19) decides between PixiJS and Canvas 2D:

- one 8×8-tile room and a corridor, isometric projection, grey-box placeholder art
  only;
- 20 animated placeholder agents walking via the ported pathfinding (§16) and driven by a recorded
  event fixture;
- the same engine-layer modules behind both renderers;
- measured on the owner's Mac: frame time percentiles (p50 / p95 / p99), time to first frame,
  memory, and the effort to add HTML overlays and isometric depth sorting.

PixiJS is kept unless the spike shows a material problem; the result and the measurements are
recorded in VW-2. Until then PixiJS is a planning assumption, not a decision.

---

## 16. Pathfinding and navigation

Navigation is part of the UI's **engine layer (§1.7)** and has **no connection to trading logic**.
It adopts StarNet's proven tile-grid approach (audit S13, S14, S18–S24; recommendations VR-5,
VR-6) instead of the navmesh + A* design of v0.1, applied to the single flat-vessel grid (Topology v2).

**Coordinates.** All navigation works in **logical coordinates**: `(tx, ty)` tiles on the one vessel grid and
sub-tile positions. They are renderer-independent. The **isometric view is a presentation-only
projection** applied by the renderer at draw time; no path, anchor, zone or collision rule ever uses
screen coordinates. A renderer change (VW-2) does not touch navigation.

| Element | Design |
|---|---|
| **Vessel grid** | **One navigation grid for the whole flat vessel** (Topology v2 §8). Rooms, hubs and corridors are rasterised by tile centre; `walkable` and an indexed tile → space lookup are built from the authored layout (layout format VW-15). Round rims and rotated R rooms are art shapes over stepped walk tiles |
| **Doors** | **Explicit doors only.** The 21 approved doors (Topology v2 §3) are the only crossings; StarNet's automatic doors on adjacency are **switched off**. Every step is checked by `canStep(from, to)` |
| **Restricted rooms** | There is no one-way door and no airlock. Entry to the Risk Control Room (L10) and the Execution Bay (L9) is a **per-role navigation permission** (Character Registry v2 §3); restricted anchors are reserved per role. An order capsule appears only after `risk.approved` + `order.created` |
| **Path search** | **BFS** over walkable tiles of the vessel grid, then **string-pulling** with a conservative line-of-sight check (`segmentClear`) that never cuts a corner or crosses a wall seam without a door. StarNet's art-tuned doorway clearances are not used (audit S15) |
| **Walking** | Eased speed, facing slew with hysteresis, corner arcs, stride phase from distance travelled; **8 facings** for isometric sprites; injected clock (audit S21) |
| **Zones** | Idle containment per agent: home room, Habitat zones, room leash (audit S18) |
| **Interaction points** | Named anchors per room (`risk.sizing_console`, `debate.podium_bull`, `habitat.cafe_seat_3`), each with an approach tile, a facing and a capacity (audit S19) |
| **Reserved seats** | Operational anchors are reserved per agent role (a podium belongs to its debater); ambient anchors are claimed first-come with a timeout, and released at once when an operational agent needs them (audit S25 pattern) |
| **Waiting anchors** | For `waiting` / `paused`: room waiting bench → own workstation → room anchor, clamped to the agent's zone (audit S20) |
| **Target points** | The adapter gives a room and an anchor; navigation computes the route |
| **Traffic and collision** | Pattern from StarNet, reimplemented with explicit arguments (audit S22–S24): corridor **right of way** (operational agents always pass before ambient ones; ties broken deterministically), **soft separation** between bodies, and a **containment backstop** that returns any body pushed off walkable tiles. No physics |
| **Path queue** | Each agent keeps at most one pending destination; a newer one replaces it |
| **Fallback** | If no path is found, or the walk exceeds its maximum visual time, **fade out and fade in** at the destination |
| **No deadlock** | A traffic jam is given up after a short timeout and the blocked agent teleports; door queues time out; ambient agents always yield to operational agents. Pathfinding and containment tests prove this (§21) |

The multi-deck model of v0.1 is **superseded**: the owner-approved floor plan (revision C) is one
flat vessel on one grid. Isometric depth sorting in the cutaway remains open (VW-13).

---

## 17. Owner interaction model

| Action | Result |
|---|---|
| Click an agent | Agent focus: expanded HUD and side panel (task, recent events, metrics with sample sizes) |
| Click a room | Room focus: full screens and interaction points |
| Inspect market | Family desk panel (one row per instrument / underlying agent): price, candles, specialist assessment, active setup |
| Inspect trade | Proposal timeline: setup → proposal → risk checks → orders → fills → close → review, linked by ids |
| Inspect debate | Transcript of turns, verdict, evidence cards with links to research and analysis |
| Inspect risk rejection | Rule-by-rule table: value vs limit, blocked reason, config version |
| Inspect historical decision | Replay mode for that run (a "REPLAY" watermark is always visible) |
| Toggle overview / focus | Camera modes (§2) |
| Pause ambient animations | Client-side only; affects cosmetic motion, never telemetry or the engine |

**Not available anywhere in the UI:** approving or rejecting trades, changing limits, sending or
cancelling orders, resetting the circuit breaker, or pausing / resuming the engine. The API is
read-only (R-5). Breaker reset is the owner's local command only.

---

## 18. Accessibility and performance

| Area | Plan |
|---|---|
| Reduced-motion mode | Walking replaced by fades; camera cuts instead of pans; no looping ambient motion |
| Lower-animation mode | Fewer simultaneous animations; ambient life off; screens update without transitions |
| Low-power mode | Lower frame rate; static room art; animation only for agents in view with operational states |
| Readable text | HTML overlays; minimum text size at every snap level; scalable UI (browser zoom and a UI scale setting) |
| Colour independence | Every state and risk indicator has an icon and a word; patterns (hatching) for "insufficient sample" and "stale" |
| Keyboard | Tab through rooms and agents; shortcuts for overview, focus, replay |
| Many agents | Sprite batching; agents off-screen are not animated (position updated only) |
| Event batching | The adapter applies all events received in a frame, then renders once |
| Off-screen throttling | Screens outside the viewport update their data but do not redraw until visible |
| Budget | Target 60 fps with the full roster on a mid-range laptop (layer design LD-6); animation never delays badges |
| Indexed lookups | Tile → room and tile → anchor maps built once from the layout and rebuilt only when it changes; no per-frame scans of rooms (audit S13) |
| Viewport culling | Only agents, props and screens intersecting the (isometric) viewport are drawn (audit S31) |
| Render-time instrumentation | The loop records per-frame render cost and exposes p50 / p95 / p99 percentiles and frame counts in a developer overlay and in test output (audit S32); used by the renderer spike (§15) and the V6 budget |
| Render-fault resilience | The render loop schedules its next frame **before** drawing, so an exception cannot stop it; a fault counter shows an **honest overlay** ("DISPLAY FAULT — telemetry unaffected; recovering") after repeated throws and clears it after a run of clean frames (audit S30). HTML badges, panels and the event log keep updating from WorldState while the canvas is faulted |

---

## 19. Visual development phases

Visual phases implement Foundation Phases 9 (Station V1) and 10 (Station V2). **Implementation of
V1 onward starts no earlier than the Foundation Phase 9 entry criteria (Foundation Phase 6 exit:
real events exist).** Non-code art exploration may happen earlier.

**Order of work (reuse architecture):** the engine layer (§1.7) is ported, adapted and validated
with placeholder art in a dedicated stage, **V1-E**, before any agent artwork, sprites or advanced
animation. Every phase from V1 on adds **golden screenshot** criteria: recorded event fixtures
replayed with a frozen clock and seeded ambient, compared by signature diff (§21).

| Phase | Goal | Dependencies | Test criteria | Explicitly deferred |
|---|---|---|---|---|
| **V0** | Final visual design and wireframes: this plan, room wireframes, persona sheet, style frames | Approved Phase 0 documents | Owner approval; layer design reconciliation of VX-1 to VX-4 | All code and final art |
| **V1** | Static ship layout; room navigation (camera modes, minimap); **live state badges** from the event stream; replay | Foundation Phase 6 exit; read-only API (`/snapshot`, `/events`, event stream; transport VW-14) with local frontend security (§20) | Badges match the event log exactly for recorded runs; stale / gap handling works; no write endpoints; §20 security tests pass; golden screenshots of the static layout and badge states | Agent movement, ambient life |
| **V1-E** | **Engine port / adaptation** (§1.7) with grey-box placeholder art: the flat vessel grid with the 21 explicit doors and restricted-room permissions, pathfinding, walking, collision / traffic, zones, workstation and waiting anchors, event-stream simulation from fixtures, reconnect and stale-state handling; the PixiJS vs Canvas 2D spike (§15) | V1; the StarNet-derived modules' provenance and notices in place (§22); layout format (VW-15) | Pathfinding, containment, traffic and no-deadlock tests pass; no route crosses a wall except at the 21 doors, and only permitted roles enter L9 / L10; reconnect, gap-reset and stale-state tests pass on a fake stream; deterministic replay produces identical golden screenshots on repeated runs; spike measurements recorded (VW-2) | Agent artwork, sprites, ambient life, advanced animation |
| **V2** | Agent sprites; movement between rooms on the V1-E engine layer (walking along computed paths, fade fallback); event-driven visual states | V1-E; persona registry; first sprite sheets | Every §11 event produces the specified badge and position; teleport-when-late verified; golden screenshots per visual state | Interactions, advanced animation |
| **V3** | Room screens: market displays, debate, risk and execution visualisation; Performance Lab and Wellbeing screens | V2; metrics API | Screen values equal journal / metrics values for recorded runs; stale values dimmed with age; decision-chain screens (§10.1) golden-tested for each stage | Ambient life |
| **V4** | Ambient life in the Habitat: café, lounge, billiards, window bench, rest zone | V3 | Ambient never delays a badge or task animation (measured); ambient yields immediately to operational tasks; replays of ambient scenes are identical (seeded; golden screenshots); determinism lint passes | Rich animation |
| **V5** | Richer animations, operational interactions (§8), polish | V4; anchors authored for all rooms | No visual deadlock in soak runs; interactions only appear with their triggering events; golden screenshots of interactions | — |
| **V6** | Performance, accessibility and low-power modes hardened (basic accessibility is required from V1) | V5 | 60 fps target met (render-time percentiles, §18); render-fault overlay and recovery tested; reduced-motion, colour-independence and keyboard checks pass; UI off → trading unchanged | — |

Mapping: V1, V1-E, V2 and V3 ≈ Foundation Phase 9 (Station V1, layer design LD-5); V4–V6 ≈
Foundation Phase 10 (Station V2, LD-6). Whether V1-E may start earlier on recorded or synthetic
fixtures is VW-7.

---

## 20. Local frontend security

V1 is single-user, local and read-only (layer design §8 Q8, R-5). "Localhost" alone is not a
security boundary: any web page the owner visits can try to reach a local port (DNS rebinding,
cross-site requests), and the event stream carries financial telemetry. The pattern below is
StarNet's (audit S12), **reimplemented** in the Stellar API; it adds **no write paths**.

| Provision | Rule |
|---|---|
| **Localhost only** | The API and the static UI bind to the loopback interface only (`127.0.0.1` / `::1`), never `0.0.0.0`. No remote or LAN access in V1 |
| **Host pinning** | Every request's `Host` header must name the loopback address and the configured port; anything else is refused (DNS-rebinding defence) |
| **Origin validation** | Requests carrying an `Origin` must match an allow-list containing only the UI's own local origin; cross-origin requests are refused and no permissive CORS headers are sent |
| **Local authentication token** | A random token generated **per launch**, held only in process memory and handed to the UI at load; required as a **custom header** on every API request. It never appears in a URL, a log, an event or a config file. Not a user account: V1 has none |
| **Protected event stream** | Header-less stream connections (e.g. `EventSource`, if SSE is chosen, VW-14) use a **single-use, short-lived ticket** obtained with the token; the master token is never put in a stream URL. A ticket is consumed on connect and expires if unused |
| **Read-only telemetry boundary** | Only `GET` endpoints (`/snapshot`, `/events`, `/runs/{id}`, the metrics reads) and the stream. The stream and snapshots are **redacted egress**: no secrets, broker credentials, bridge tokens or raw tool payloads, only the fields the UI needs |
| **No risk-bypassing endpoint** | No endpoint accepts UI state, approves or rejects trades, changes limits, sends or cancels orders, pauses the engine or resets the circuit breaker. Breaker reset is the owner's local command only (R-5). A contract test enumerates the API routes and fails on any non-read route |
| **Failure behaviour** | A refused request is logged locally (without the token) and the UI shows "not authorised"; security failures never affect the engine |

These rules extend layer design LD-5 ("localhost, read-only") and are reconciled with it as VX-6.

---

## 21. Testing and quality gates

All UI tests run headlessly and offline, from **recorded or synthetic event fixtures**, with a
frozen clock and a fixed seed. None touches the trading engine.

| Test family | What it proves |
|---|---|
| **Deterministic visual replay** | The same fixture + seed + clock produce the same WorldState and the same frames, run after run; replay mode equals live mode for the same events |
| **Pathfinding** | Every authored anchor is reachable on the vessel grid; smoothed paths never cross walls or seams without doors (checked against an independent dense-sampling oracle, not the path code itself); there are exactly 21 crossings (Topology v2 §3); no character without permission is ever routed into L9 or L10 |
| **Containment and traffic** | Bodies never end on non-walkable tiles; zones hold idle agents; two agents crossing in a 2-tile corridor both pass; operational agents win right of way; jams give up and teleport within the timeout (scenario ideas from audit S52, written as behavioural tests) |
| **Stale state** | Link-down after 1.5× the keepalive without data; per-agent "no update for N s" markers; working states are never animated as finished without an event |
| **Reconnect** | Against a fake stream: cursor resume, gap → `reset` → snapshot replace, duplicate and replayed events applied once, backoff capped, one stream at a time, "RECONNECTING — verifying state" until the snapshot is applied |
| **Golden screenshots** | Playwright captures of fixture replays at defined moments, compared by a small grayscale signature diff with a tight threshold (possible because replays are deterministic) (audit S49, S50). Goldens are grey-box until art exists and are re-approved by the owner when art changes |
| **Performance instrumentation** | Render-time percentiles and frame counts recorded per scenario; regressions beyond a tolerance fail the V6 gate |
| **Renderer fault** | An injected exception in drawing shows the fault overlay, keeps badges and panels live, and recovers after clean frames |
| **Security** | The §20 rules: wrong Host, wrong Origin, missing or wrong token, reused or expired ticket are all refused; the route list contains no write route |
| **Event contract** | The UI's event schema matches the engine catalogue; changes are additive only; unknown events are ignored and logged, never guessed |
| **Determinism lint** | No `Math.random`, `Date.now` or `performance.now` in the adapter, engine-layer or ambient modules; time and randomness are injected (audit S6) |

Stellar's UI modules are importable modules with injected dependencies, so StarNet-style
source-lock tests (regex or `Function()` extraction of source; audit S52) are not needed and not
used.

---

## 22. Licensing and provenance

StarNet's **code** is MIT-licensed; its name, logo, artwork, sprites and brand identity are
**not licensed** (audit §2). Stellar uses only code, and only for the engine layer (§1.7).

- **Attribution:** every file copied from or substantially derived from StarNet keeps StarNet's
  MIT copyright and permission notice.
- **Third-party notices:** `stellar_ui/` carries a third-party notices file listing each
  StarNet-derived file, its StarNet source file, and the MIT notice.
- **Source provenance per module:** each adapted module starts with a short provenance header:
  StarNet source path, pinned revision (`fbddbf99` unless VW-17 changes it), audit matrix id, and
  a one-line summary of what was changed. Reimplemented-pattern modules name the audit id as their
  design source.
- **No StarNet art or brand in Stellar:** a CI check fails the build if any StarNet image, sprite,
  font, sound, icon, logo or wordmark, any file from StarNet's `frontend/assets/`, or any StarNet
  art-producing module (for example its prop painters, station bake, surfaces, space background,
  CRT / phosphor shaders; audit S33–S40) enters the repository, detected by path, file name and
  content hash of StarNet's asset files. The StarNet name is not used in the product.
- **Third-party assets bundled with StarNet are not used:** the VT323 font, the Bleeoop interface
  sounds, the lobe-icons provider logos, and the PixelLab-generated sprites (audit S38, S54–S56).
  If Stellar ever wants similar assets, it licenses its own.
- **Procedural art code** is treated as artwork, not reusable code (audit Q1; VW-16).

---

## 23. Unresolved visual decisions

| # | Decision | Options | Safe default until decided |
|---|---|---|---|
| VW-1 | Approve the room extensions and home-room moves (VX-1, VX-2) and reconcile the layer design | Approve; amend | Layer design rooms remain canonical for anything outside this plan |
| VW-2 | Renderer for V1 (reconciled with the audit) | PixiJS (leading candidate); Canvas 2D (fallback); decided by the §15 spike in V1-E. StarNet's renderer is not an option (§15 F). Phaser and Three.js remain alternatives only if both fail | PixiJS assumed for planning only; nothing locked before the spike |
| VW-3 | Art production pipeline | 3D models rendered to isometric sprites; hand-painted art; commissioned artist; generated then retouched | Grey-box placeholder art in V1 |
| VW-4 | Persona names | Original defaults (proposed); owner's local override with franchise names; no names (role titles only) | Original defaults in the repository |
| VW-5 | Technical ids for M1, R*, V*, S*, T* | Confirm the proposed ids in Foundation Phase 1 | Proposed ids used in this document |
| VW-6 | Contradiction Checker in the Debate Chamber | Remote evidence-screen feed (proposed); a visiting hologram of P2 | **Decided:** remote / data feed only (`DSP-DEB-05` from `debate.completed`); no hologram (L3 sheet DC-10) |
| VW-7 | Start the V1-E engine port (and the renderer spike) before the Foundation Phase 9 entry, on recorded or synthetic event fixtures | Allow (needs a Foundation Plan amendment); wait | Wait; art exploration only |
| VW-8 | Sound | None; ambient only; event cues | None |
| VW-9 | Display-time values (transient states, idle delay before ambient, maximum walk time, ambient beat budget, keepalive interval, snapshot refresh cadence, stale-marker durations) | UI / API settings tuned in V1-E and V2 | Short fixed values, configurable; snapshot refresh at StarNet's 30 s until tuned |
| VW-10 | Day / night lighting tied to FX sessions | Yes (layer design LD-6); no | Off until V5 |
| VW-11 | How StarNet-derived modules enter Stellar (audit Q2) | Vendor (copy + adapt with MIT notices, §22); clean-room reimplementation from the audit's descriptions | Vendor with notices for the COPY + ADAPT items; nothing copied before approval |
| VW-12 | Language for `stellar_ui` (audit Q3) | TypeScript; JavaScript with JSDoc types | TypeScript assumed for planning |
| VW-13 | Isometric depth sorting (audit Q6). The multi-deck question (Q5) is **resolved** by Floor Plan revision C: one flat grid | Depth key per layer (floor, props, bodies, tall screens, walls) for the cutaway | Depth key decided in the spike |
| VW-14 | Event-stream transport | WebSocket (named in Foundation §4.28); SSE with the same cursor semantics (`epoch:seq`, `ready` / `reset`, data keepalive; StarNet pattern) | Transport-neutral adapter; Foundation's WebSocket until amended |
| VW-15 | Ship layout authoring (audit Q7) | Hand-written JSON layout (tiles, rooms, explicit doors, anchors, zones); a small internal editor later | JSON layout, validated by the pathfinding tests |
| VW-16 | Is StarNet's procedural art code "code" or "artwork"? (audit Q1) | Artwork (conservative); code | Artwork: not reused |
| VW-17 | StarNet revision to track, and whether its default branch is its release trunk (audit Q9, Q10) | Pin `fbddbf99`; re-audit a later revision before any copying | Pinned to `fbddbf99`; re-check before V1-E starts |
| VW-18 | Snapshot contents and semantics (audit Q8; §1.8 rule 7) | Adopt the §1.8 list in the Foundation API contract; extend it | §1.8 list proposed; reconciled with Foundation §4.28 under VX-6 |
