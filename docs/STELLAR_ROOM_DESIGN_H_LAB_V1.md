# Stellar Room Design Sheet — H-LAB Research Hub (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; X1–X4 resolved (§8, §9). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `H-LAB` — Lab / Research Hub (Room Registry v2 §3.1) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2 |
| **Not changed here** | Room position, shape, doors, topology, room assignments, anchors, the screen list, and data rules. Placements are **provisional** (the tile scale is open) and are given as **clock sectors** (12 o'clock = top of the floor plan) |

---

## 1. Room identity

| Aspect | Definition |
|---|---|
| **Purpose** | The scientific and analytical heart of Stellar: the **shared upstream research team** (collectors R1–R6, validators V1–V4, and the Causal / Macro Analyst M1). Information is collected, validated, separated into fact / reaction / interpretation, and synthesised into macro context that feeds **all three market families**. **It is not a trading room**: no orders, no positions and no P&L are shown here |
| **Atmosphere** | Bright, quiet, focused discovery. A clean scientific space with a stronger blue / cyan research light than the rest of the vessel; never a dark laboratory |
| **Visual identity** | A domed circular hub with a **lab dome ring** hero at the centre. Feed consoles form an arc on the west rim, a validation bench runs along the south, and a macro driver board sits on the north. Screens are brighter and denser than in other rooms (Visual Bible §6.2) |
| **Importance level** | **High** (the second hub after Main Command). Its hero object must read at overview zoom |
| **Relationship with Main Command** | **Physical:** there is no direct door. H-LAB reaches `H-CMD` along **either** corridor: `DR-N-LAB` → `COR-N` → `DR-N-CMD`, or `DR-S-LAB` → `COR-S` → `DR-S-CMD` (Topology v2 §6; two independent routes).<br>**Functional:** H-LAB is the **start** of the analysis chain. Its output goes along `COR-N` to the Market Specialists (L1) and the Debate Chamber (L3), and reaches the Central Trader in `H-CMD`. The Technical Deck (L2) runs **before** the research stage on market data alone; the specialists use its technical evidence together with the research (engine order, L2 sheet TA-2). H-LAB never makes decisions |

---

## 2. Architecture

### 2.1 Shape and entrances (approved; unchanged)

- **Shape:** circle (sketch diameter ≈ 364 px; about 22 tiles at the working scale, which is **not frozen**).
- **Doors (2):** both are ordinary 2-tile curved-rim doors (`DOR-009`) with the normal indicator,
  and both sit on the **east rim**:
  - `DR-N-LAB` at about **2 o'clock**, leading to `COR-N` (the upper corridor, toward L1–L5);
  - `DR-S-LAB` at about **4 o'clock**, leading to `COR-S` (the lower corridor, toward L6–L10).
- **No other openings.**
- **Cutaway** (Visual Bible C4): the camera-facing (south / south-east) arc is cut away. `DR-S-LAB`,
  if it falls in that arc, keeps a visible frame, threshold and structural opening.

### 2.2 Schematic (not to scale; clock sectors)

```
                               12
                 .-~~ DSP-LAB-06 MACRO CONTEXT ~~-.
            11 .'  CON-008 driver board (M1)        '. 1
  DSP-LAB-08  /   [DSP-LAB-07 specialist views at 1] \
 (hypotheses)/          lab.macro                     \
   10       |                                          |  DR-N-LAB  2
            |   lab.feeds          .------------.      |=========
  DSP-LAB-01|   CON-006 x6        /  EQP-005     \     |
  9 (feeds) |   (R1-R6; R3-R6    |  LAB DOME RING |     |  lab.walkway   3
  window?   |    dormant, grey)  |  DEC-007 globe |     |  (east arc,
  DSP-LAB-04|                     \ DSP-LAB-05   /     |   between doors)
   8        |                      '------------'      |  DR-S-LAB  4
             \  lab.experiment_bench                  /=========
          7   \  (FUTURE: empty,           lab.validation
               '. not rendered)    CON-007 bench (V1-V4)
                 '-~~ DSP-LAB-02 VALIDATION / DSP-LAB-03 EVIDENCE ~~-'   5
                               6
```

### 2.3 Materials (Visual Bible C1)

| Surface | Material |
|---|---|
| Floor | **Deep navy** matte deck (`FLR-001`), with a lighter navy disc under the dome ring and a thin titanium inlay ring marking the core edge (walk-over) |
| Walls | **Warm off-white structural panels** (`WAL-002`, curved rim), soft seams, **titanium** base and cove trim |
| Technical elements | **Graphite** console bodies, bench frame, dome-ring supports and screen bezels |
| Accent | **Science blue / cyan** accent lines on consoles and the bench edge (department colour; static) |
| Windows | Allowed on this hub (`WAL-003` + `DEC-001` planet view; Asset Registry lists `H-LAB` outer rims). Proposed: one window band on the **west rim above the feed-console arc**, at about 9 o'clock (open decision HL-4) |

### 2.4 Ceiling

- A **higher dome** than Main Command, with the **dome light** (`LGT-009`) as a soft ring above the
  core.
- In the cutaway view, only the dome rim and the light ring are suggested; the ceiling never hides
  agents or the core.

### 2.5 Lighting

| Layer | Treatment |
|---|---|
| General | Clean **white / cyan**, slightly **bluer and brighter** than the vessel baseline (the Research department mood) |
| Research accent | Blue / cyan glow from the dome ring and screen faces. Screens are the main light sources at room focus |
| Work pools | `LGT-002` over active consoles only while the console's agent works (telemetry) |
| Dormant | The consoles of the deferred roles (R3–R6) are **dim and grey**: no pool light, no screen glow |
| Alert | The station alert tint on `LGT-001`, **always** paired with a word and icon. Lighting alone never communicates a data state (Visual Bible C7) |

### 2.6 Walkable areas

| Area | Rule |
|---|---|
| **`lab.walkway`** (east arc) | Clear floor between `DR-N-LAB` and `DR-S-LAB`, so corridor-to-corridor traffic through the hub never enters the work arcs. No furniture |
| Inner ring | A clear ring between the core and the work arcs (feeds, bench, driver board), linking every anchor |
| Door approaches | The 1-tile approach in front of each door stays empty |
| Core | The dome ring blocks its footprint. Its approach points are walkable (§3) |
| `lab.experiment_bench` (south-west) | **FUTURE:** clean, empty, walkable floor with no furniture, anchors or screens until the Research Lab exists. Not fenced and not dark: it is simply unused |

---

## 3. Main objects

| # | Object | Asset | Purpose | Approximate placement | Interaction role | Visual importance |
|---|---|---|---|---|---|---|
| 1 | **Lab dome ring** | `EQP-005` | Hero object: a ring-shaped scientific structure around the core; the H-LAB silhouette at overview | Centre (`lab.core`) | Decorative; approach points for the collaboration area (object 6) | **Hero** |
| 2 | **Holo globe** (decorative) | `DEC-007` | Atmosphere. **Decorative only:** no real data, no fake status, no charts or metrics (same rules as H-CMD) | Inside the dome ring, low | none | High (ambient) |
| 3 | **Feed consoles** × 6 | `CON-006` | One per collector role R1–R6; R3–R6 dormant (grey) while deferred in the engine | West arc (`lab.feeds`), about 7:30–10:30 o'clock, facing inward | `lab.feed_r1`…`lab.feed_r6` | High (the "research wall") |
| 4 | **Validation bench** (4 stations) | `CON-007` | V1–V4: source, freshness, duplicate / consistency, and fact / reaction / interpretation checks | South arc (`lab.validation`), about 5–6:30 o'clock | `lab.bench_1`…`lab.bench_4` | High |
| 5 | **Macro driver board** | `CON-008` + `DSP-LAB-06` | M1 causal / macro synthesis | North arc (`lab.macro`), about 11–1 o'clock | `lab.driver_board` | High |
| 6 | **Collaboration area** | *no dedicated asset; no table in V1* (owner decision X2) | Where research roles meet on a **real** shared task (for example a hand-off at the bench) | The inner ring beside the dome ring, south side (between the core and the bench) | Uses existing anchors (`lab.bench_*`, `lab.visitor_1`, `lab.visitor_2`) | Medium |
| 7 | **Research snapshot pulse** | `SCR-006` (`DSP-LAB-05`) | A projector column pulsing **only** on `research.snapshot.created` | At the dome ring's east edge, facing the walkway | Look target | Medium |
| 8 | **Specialist views repeater** | `SCR-003` (`DSP-LAB-07`) | Latest view per family, so research sees how its output is used | North-east rim, about 1–1:30 o'clock, above the walkway toward `DR-N-LAB` | Look target (NAV) | Medium |
| 9 | Freshness clock ring | `SCR-010` (`DSP-LAB-04`) | Age of the newest item per role | West rim, above the feed arc (about 8 o'clock) | Look target | Medium |
| 10 | Hand-off point | anchor `lab.handoff_n` | Where the macro hand-off leaves toward L1 | Inside `DR-N-LAB` (off the approach tile) | Hand-off anchor | Low |
| 11 | Chairs, planters, lockers | `SEA-002`, `PLT-001`, `STO-001` | Seating; softening; storage | At consoles; planters and lockers on the rim between screens, never in the walkway | Seats | Low |

**No central research table in V1** (owner decision X2): collaboration uses the research stations
and the collaboration area beside the core. **No trading objects:** no order, position, P&L or execution
display exists in H-LAB.

---

## 4. Agent and specialist placement

### 4.1 Research team (home: H-LAB)

| Agents | Workstation | Usual position | Movement pattern | Interaction |
|---|---|---|---|---|
| **Collectors** R1–R6 (`CHR-012`–`CHR-017`) | `CON-006` · `lab.feed_rN` | Seated at the west-arc feed consoles. **R3–R6 are shown `idle` at dim consoles** while deferred in the engine | Mostly stationary. On `research.item.accepted` a collector may carry the item card (`PRP-002`) to the bench, then return | With the validators (item hand-off, only on a real event) |
| **Validators** V1–V4 (`CHR-018`–`CHR-021`) | `CON-007` · `lab.bench_1`…`4` | At the south bench | Stationary while `validating`. A short step along the bench when two validators work on the **same** item (real shared task) | Side by side on shared items. Pass / fail marks appear only from real events |
| **Causal / Macro Analyst** M1 (`CHR-011`) | `CON-008` · `lab.driver_board` | North arc, at the driver board | At the board while `analysing`. When a macro assessment is consumed downstream, a hand-off walk: `lab.handoff_n` → `DR-N-LAB` → `COR-N` → L1 (data crystal `PRP-001`), then back | Receives validated items; hands macro context to the specialists |

### 4.2 Market specialists (home: **L1**, not H-LAB; owner decision X1)

**Owner decision (X1):** the three **family desks** stay in the **Market Specialists Room (L1)**,
on `COR-N` next door to H-LAB, and are **not** moved. **H-LAB** remains research, analysis,
validation and macro context. **L1** remains specialist market analysis. Their L1 workstations and
their behaviour **in relation to H-LAB** are:

| Desk | Home workstation (L1) | Scope | Relationship with H-LAB |
|---|---|---|---|
| **Metals Desk** `CHR-022` | `specialists.desk_metals` | Gold (XAU); silver (XAG) is `NOT CONFIGURED` | Receives macro context from M1 (a `PRP-001` walk into L1). May visit `lab.visitor_1` / `2` **only** on a real task that involves research items |
| **FX Desk** `CHR-023` · **INTERIM ADAPTER** | `specialists.desk_fx` | Represents **several runtime agents**: today S2 (EUR/USD) **and** S3 (USD/JPY) | **Never merged:** each underlying agent keeps its own task, state and activity (one panel and one chip each; split pip; no single state). In H-LAB, `DSP-LAB-07` lists EUR/USD and USD/JPY as **separate rows**. The FX figure does not "visit as one agent" on behalf of both; any visit is tied to one underlying agent's real task and labelled with it |
| **Indices Desk** `CHR-025` | `specialists.desk_indices` | NAS100 first; extensible | As Metals |

Movement between L1 and H-LAB follows the corridor: `DR-L1` → `COR-N` → `DR-N-LAB`. It is always
event-driven, and specialists never use H-LAB consoles.

---

## 5. Screen design (Screen Registry v2 §5.2 is the authority)

| Request category | Display | Content | Placement | Main placeholders |
|---|---|---|---|---|
| **Research status** | `DSP-LAB-01` Source feeds | New items per collector role, source, age; deferred roles dormant | West rim above the feed arc (about 9–10 o'clock) | **AWAITING DATA** per role; dormant roles grey |
| | `DSP-LAB-02` Source validation board | Accepted / rejected with reasons | South rim above the bench (about 5–6 o'clock) | **AWAITING DATA** |
| | `DSP-LAB-03` Evidence board | Claims labelled FACT / REACTION / INTERPRETATION, with citations | South rim, beside `DSP-LAB-02` (about 6–7 o'clock) | **AWAITING DATA** |
| | `DSP-LAB-04` Freshness clocks | Age per role | West rim (about 8 o'clock) | **STALE** |
| | `DSP-LAB-05` Research snapshot pulse | Snapshot id, counts | Projector at the core's east edge | **AWAITING DATA** |
| **Market analysis** | `DSP-LAB-06` Macro context | Drivers, direction, strength, cited claims, coverage | North rim above the driver board (about 11–1 o'clock) | **AWAITING DATA**; shown with its age between cycles |
| **Specialist screens** | `DSP-LAB-07` Specialist views (repeater) | Latest view per family. **FX shows one row per underlying agent** | North-east rim (about 1–1:30 o'clock) | **AWAITING DATA**; unconfigured instruments **NOT CONFIGURED** |
| | *(the full specialist desk screens `DSP-SPC-01`…`03` stay in L1; H-LAB receives only the approved repeater, owner decision X4)* | | | |
| Hypotheses | `DSP-LAB-08` | Research hypotheses | North-west rim (about 10:30–11 o'clock) | **NOT AVAILABLE · hypotheses** (no producer) |
| **Comparison displays** | `DSP-LAB-13` Regime comparison (and `-10`, `-11`, `-12`, `-14`) | Research Lab experiments | South-west future zone | **PLANNED only: not rendered** (owner decision X3). Unavailable systems are never rendered |

**Screen rules for this room:**
- **Never invent data.** Every value comes from the registry's sources, with its age.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **MODE UNKNOWN** has
  no use here: there is no mode plaque, because H-LAB is not a trading room.
- On link loss, all walls **freeze and grey** with **LINK DOWN · age**.
- No screen sits over a door or its approach (the east rim between 2 and 4 o'clock stays clear,
  apart from `DSP-LAB-07` above the `DR-N-LAB` side).
- No trading screens: no orders, positions, P&L or execution mode.
- All displays are read-only or navigation-only.

---

## 6. Character life

All activity comes from **real tasks**, **real events** or **normal idle behaviour**. There is **no
emotional simulation** (Character Bible K6).

| Activity | Trigger | Who / where | Clips |
|---|---|---|---|
| Research | `agent.task.started` … `completed` for R1 / R2 (R3–R6 dormant) | Collectors at the feed consoles | `sit_work` |
| Studying screens | The display bound to the agent's task updates | Any research role, facing its wall | `look_screen` |
| Validation | `research.item.collected` → `accepted` / `rejected` | Validators at the bench; the marks light per real result | `stand_work`, `checklist_sweep` |
| **Comparing information** | Two validators work on the **same** item (real shared task) | Adjacent bench stations | `look_screen` + `stand_work` |
| **Discussion / collaboration** | A real hand-off (for example `research.item.accepted` from a collector to a validator), or ambient talk **only while idle** | Collaboration area beside the core | `talk` / `listen` (neutral) |
| Macro synthesis | `analysis.created` (macro) in progress | M1 at the driver board | `stand_work`, `look_screen` |
| **Moving between desks** | An item hand-off (`PRP-002`) or a macro hand-off (`PRP-001`) | Inner ring; hand-off out via `DR-N-LAB` | `walk`, `carry` |
| Through-traffic | Corridor-to-corridor routes | The east walkway only | `walk` |
| Idle | No task | At the home anchor; after the idle delay, optional seeded ambient (the Habitat, via `H-CMD`) | `stand_idle` |

The room never shows research activity, validation results or hand-offs that did not happen.
Dormant roles stay dormant until their engine role is enabled.

---

## 7. Style guardrails

- **Keep:** warm off-white architecture; titanium trims; a deep navy floor; graphite technical
  elements; a brighter blue / cyan research light; clean, organised scientific shapes.
- **Avoid:** a dark military laboratory; clutter; trading imagery; red used as decoration.
- **Originality:** no Star Trek science-station layouts, consoles, LCARS panels or props. No StarNet
  art or look.

---

## 8. Contradictions and owner decisions (all resolved)

| # | Topic | Owner decision |
|---|---|---|
| **X1 / HL-1** | Specialist desks in H-LAB? | **Keep the Metals, FX and Indices desks in L1.** Do not move them. H-LAB = research, analysis, validation, macro context; L1 = specialist market analysis. The Room Registry is unchanged |
| **X2 / HL-2** | Central research table | **None in V1.** Use research stations and collaboration areas |
| **X3** | Comparison displays | Research Lab screens (`DSP-LAB-10`…`14`, including regime comparison) stay **planned only**. Unavailable systems are **not rendered** |
| **X4** | Specialist screens in H-LAB | The specialist screens stay in **L1**. H-LAB receives only the **approved repeaters** (`DSP-LAB-07`) |

No conflicts with:
- the topology (both doors on the east rim; routes to `H-CMD`; no direct CMD door);
- the Visual Bible (materials, lighting, windows allowed on H-LAB, doors, screen-state authority);
- the Character Bible (figures, the FX interim rules, no emotion);
- the Screen Registry (display list, sources, placeholders).

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| HL-1 | Specialist desks location | **Closed:** L1 (X1) |
| HL-2 | Central research table | **Closed:** none in V1 (X2) |
| HL-3 | Exact dimensions: dome-ring diameter, arc lengths, walkway width | **Open** (after the tile scale, VB-3) |
| HL-4 | Window band on the west rim above the feed consoles, or a solid rim | **Open** |
| HL-5 | Ceiling in the cutaway: dome rim + light ring only, or a partial translucent dome | **Open** (default: dome rim + light ring only) |
| HL-6 | Visual treatment of the empty future experiment-bench zone | **Open** (default: plain floor) |
| HL-7 | Exact colour values | **Open** (visual production, VB-4) |
