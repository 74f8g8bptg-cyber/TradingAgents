# Stellar Room Design Sheet — H-HAB Habitat Hub (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; StarNet review approved; Y1, HH-1, HH-5 and HH-6 decided (§8, §9). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `H-HAB` — Habitat (Room Registry v2 §3.3) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, doors, topology, the reserved R rooms, anchors, the screen list, and data rules. Placements are **provisional** (the tile scale is open) and use **clock sectors** (12 o'clock = top of the floor plan) |

---

## 1. StarNet-inspired world-building review

**Method.** I reviewed the StarNet audit (items S18–S28, idle engine S27) and read the local StarNet
checkout at the pinned revision `fbddbf99` **read-only** (`frontend/app/world.js`: the idle
"sentience" engine, couch / TV seating, bar joins, pool and arcade beats, social pair cooldowns,
station gatherings). **Nothing was copied:** no art, assets, characters, layouts, logos, interfaces,
text lines or code. Only the **ideas** below were extracted.

### 1.1 Concept review

| StarNet concept (as it exists) | Why it is useful | Fits Stellar? | Stellar adaptation |
|---|---|---|---|
| **Bar / café social spot:** idle agents sit at a bar, and a second agent occasionally "joins" an occupied bar (with a cooldown) | Gives idle agents a natural destination; makes the world feel inhabited | **Yes** | A **café counter with a host** (`LEI-002`, Bix). Idle agents may take a café seat. Joining an occupied table is **seeded and deterministic** (A14), with a cooldown; StarNet's random rolls are not used |
| **Couch + TV lounge:** an agent sits on a couch and "lights the TV" | A calm seated pose; a visible place to sit | **Partly** | **Sofas yes; TV no.** A TV would be a screen without a Screen Registry binding (an invented display). Stellar replaces it with a **window view** (`DEC-001` planet view) and plants |
| **Pool table with dwell / fidget timing:** agents line up, hold, then move on | A recognisable social object; the timing makes play look plausible | **Yes** | An **original billiard table** (`LEI-001`) with **seeded** dwell times. StarNet's pool "speech lines" are **excluded** (§1.3) |
| **Arcade cabinet** | Another leisure destination | **No (V1)** | No arcade asset exists in Stellar. It would add clutter and a screen-like object. Not added (§9, HH-5) |
| **Beds / sleeping bodies** | Downtime visuals | **No** | Sleep implies fatigue, an emotional or biological state Stellar does not simulate. Stellar has only **cosmetic rest pods** (a seat, no vitals) and **recovery pods** used **only** for real `agent.resting` |
| **Plants** | Warmth and life | **Yes** | A **central planter / tree** (`PLT-005`, hero) and a living wall (`PLT-004`): Habitat is a location style (Visual Bible C5) |
| **Social pair encounters** with per-pair cooldowns ("the same duo never loops") | Believable, non-repetitive conversation | **Yes (pattern)** | Idle-only conversation pairs, chosen by the **seeded** scheduler, with pair cooldowns, neutral `talk` / `listen` clips and **no text bubbles** |
| **Station-wide gatherings** (an assembly that owns the floor until it breaks up) | Big "moments" | **No (for ambient)** | Stellar group moments come **only from real events** (for example the `run.started` meeting in `H-CMD`). There are no ambient mass gatherings in the Habitat |
| **Zones / containment** for idle roaming | Keeps idle agents in plausible places | **Yes** | Habitat zones (§2.6) plus the containment backstop (A11, A8) |
| **Speech-bubble quips, personality lines, "needs" meters, curiosity, mourning, chase / mimic** | StarNet character identity | **No** | **Excluded:** non-deterministic, emotion-adjacent, and part of StarNet's identity (audit S27; adaptation A30) |

### 1.2 Stellar original decisions (not from StarNet)

- **Recovery zone:** real-cooldown pods and the Medic's vitals board, visibly separated from
  leisure.
- **Relationship to Main Command** as the **only** entry; the radial reserved R rooms and R1 as the
  future coaching room.
- **The operational / leisure boundary:**
  - no operational function in leisure objects;
  - wellbeing screens only in the recovery zone;
  - "work over idle" always pre-empts leisure.
- **All look and feel:** the materials, lighting, the circular plan with a central planter, the
  original billiard design, and the Habitat Host as a synthetic Stellar character.

### 1.3 Explicitly excluded from StarNet

- Art, sprites, props art, the couch / TV / arcade / pool **visuals**, and the station layout.
- The idle-engine code and its random selection (`Math.random`).
- Personality speech lines.
- Mourning, needs and curiosity.
- StarNet names and branding.

---

## 2. Room identity and architecture

### 2.1 Identity

| Aspect | Definition |
|---|---|
| **Purpose** | The living and recovery space: café, relaxation, games (billiards), plants and rest. It also holds the **recovery zone**, where agents in a **real** cooldown (`agent.resting`) are shown. **Not** a command, research or trading room: no decisions, analysis or orders happen here |
| **Atmosphere** | Warm, calm, comfortable, softly natural. An **ambient** space: lower visual contrast than working rooms (Visual World Plan §14.8) |
| **Visual identity** | A circular hub around a **central planter / tree**. A café arc with a counter, a lounge with sofas and a rug, an original billiard table, window benches, and a clearly separate recovery zone with pods. Six radial doors (R1–R6) on the rim; five are reserved rooms |
| **Importance level** | **Medium.** It is the third hub. Its hero (the planter) must read at overview, but its life is drawn below operational activity in the visual hierarchy |
| **Relationship with H-CMD** | The **only** entry: `DR-CMD-HAB` at 9 o'clock, where the two hub rims touch. Every agent reaching the Habitat crosses Main Command's walkway (Topology v2 §6) |
| **Relationship with H-LAB** | No direct connection. `H-LAB` → corridor → `H-CMD` → `H-HAB` (3 door crossings) |
| **Relationship with the rest of the vessel** | Serves **all departments** (Habitat is a location, not a department). It is the hub for R1–R6: **R1** is the designated future Performance & Wellbeing / Coaching Room; **R2–R6** are reserved for future agent teams. All R rooms are closed to entry in V1 |

### 2.2 Shape and entrances (approved; unchanged)

- **Shape:** circle (sketch diameter ≈ 360 px; about 22 tiles at the working scale, which is **not frozen**).
- **Doors (7, all ordinary 2-tile curved-rim doors `DOR-009`):**
  - `DR-CMD-HAB` at **9 o'clock**: **normal** indicator, the only open entry;
  - `DR-R1` at about **11**, `DR-R2` at **12**, `DR-R3` at **2**, `DR-R4` at **3**, `DR-R5` at **5**,
    `DR-R6` at **7 o'clock**. Each is a **reserved** room door: dark shell behind it, `SGN-007`
    "RESERVED" plate, **dimmed normal** indicator (Visual Bible VB-6). **Not** red and **not**
    amber. No agent enters in V1.
- **Cutaway** (Visual Bible C4): the camera-facing arc is cut away. The doors there keep a visible
  frame, threshold and opening.

### 2.3 Schematic (not to scale; clock sectors)

```
                               12  DR-R2 (reserved)
              DR-R1 (reserved)  .-~~~~~~~~~~~~~~~~~-.   CAFÉ ARC
          11  (future coaching) .'  LEI-002 counter  '.  (about 12:30–1:30)
             .'  RECOVERY ZONE      + LEI-003 dispenser '.   DR-R3 (reserved)  2
   10       /   EQP-004 pods x3     TBL-003 tables       \
           |    CON-021 vitals (Medic)                    |
           |    DSP-HAB-02/03/04                          |  DR-R4 (reserved)  3
  9 DR-CMD-HAB |            .-----------.                 |
  =========   |            /  PLT-005     \     GAMES ARC  |
  (from H-CMD)|           |   central tree |   LEI-001     |
           |               \  (plants)    /   billiards    |
   8       |    REST ZONE   '-----------'     STO-003 rack |  4
            \   LEI-005 cosmetic pods                     /
          7  '.  DR-R6 (reserved)     LOUNGE ARC        .'   DR-R5 (reserved)  5
                '.   SEA-006 sofas · TBL-004 · LEI-004 rug .'
                  '-~~ SEA-009 window benches (outer rim) ~~-'
                               6
    ( habitat.ring: clear circulation linking all 7 doors; no furniture on it or on any door approach )
```

### 2.4 Materials

| Surface | Material |
|---|---|
| **Floor** | **Warm wood-like habitat laminate** (`FLR-004`) is the **main floor identity** of the whole hub (owner decision Y1 / HH-1), so H-HAB clearly differs from H-CMD and H-LAB. **No deep navy flooring** here. The `habitat.ring` circulation is marked only by a subtle warm-grey inlay line (walk-over), never a navy band |
| Walls | **Warm off-white structural panels** (`WAL-002`), titanium trims. A **living wall** (`PLT-004`) on the rim between the rest and recovery zones. **Window benches** (`SEA-009`) with window sections (`WAL-003` + `DEC-001`) on the outer south rim (windows are allowed for H-HAB) |
| Accents | **Softer graphite** (lighter, warmer greys than Main Command) on the counter base, pod frames and furniture legs |
| Textiles | Fabric sofas and a soft rug (`LEI-004`) in warm greys, per the Habitat palette (warm grey, wood tones, green) |

### 2.5 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A low, soft dome with a **skylight ring** of diffuse light over the central tree (suggested only in the cutaway, never hiding agents) |
| General | **Warmer than H-CMD, softer than H-LAB:** a warm-white base with a subtle natural feel (as if daylight filters through the planter canopy) |
| Pendants | `LGT-006` warm pendants over the café tables and the billiard table |
| Recovery zone | A calmer, slightly cooler neutral tone, so it reads as distinct from leisure |
| Alert | The station alert tint on `LGT-001`, **always** with the word and icon (`DSP-HAB-01`). Lighting alone never carries a data state (Visual Bible C7). RED is visible here too |

### 2.6 Walkable areas and zones

| Zone | Placement | Rule |
|---|---|---|
| `habitat.ring` | Around the rim, linking all 7 doors | Clear: no furniture, no games clearance on it. Operational agents (for example the Medic) have right of way |
| `habitat.plants` | Centre | The planter blocks its footprint; a walkable inner ring around it |
| `habitat.cafe` | North-east arc, between the `DR-R2` (12) and `DR-R3` (2) approaches | Counter against the rim; tables inside the arc |
| `habitat.games` | East–south-east arc, between the `DR-R4` (3) and `DR-R5` (5) approaches | Billiard table plus its 1-tile play clearance, entirely **off** the ring and the door approaches |
| `habitat.lounge` | South arc, between `DR-R5` (5) and `DR-R6` (7) | Sofas facing the windows |
| `habitat.rest` | South-west, between `DR-R6` (7) and `DR-CMD-HAB` (9) | Cosmetic rest pods |
| `habitat.recovery` | North-west, between `DR-CMD-HAB` (9) and `DR-R1` (11) | Real-cooldown pods + the vitals console. Near the entry (short Medic walks) and next to R1, the future coaching room |
| Door approaches | All 7 doors | The 1-tile approach stays empty, including the reserved doors |

---

## 3. Main objects

| # | Object | Asset | Purpose | Approximate placement | Interaction role | Visual importance |
|---|---|---|---|---|---|---|
| 1 | **Central planter / tree** | `PLT-005` | Hero object: life, balance, the natural feel | Centre (`habitat.plants`) | Walk-around; ambient standing points on the inner ring | **Hero** (overview) |
| 2 | **Café counter** + host | `LEI-002`, `LEI-003` | Social heart; the Habitat Host serves | North-east rim, about 12:30–1:30 o'clock | `habitat.counter` (Bix) | High |
| 3 | **Café tables and chairs** | `TBL-003`, `SEA-007` (bar stools `SEA-008` at the counter) | Informal seating and conversation | Inside the café arc | `habitat.cafe_seat_1`…`_6` | Medium |
| 4 | **Billiard table** (original Stellar design) | `LEI-001`, `STO-003` cue rack, `PRP-008` cue | Social game; relaxation only | Games arc, about 3:30–4:30 o'clock | `habitat.billiards_1`, `_2` | High (the Habitat's second hero) |
| 5 | **Lounge** | `SEA-006` sofas, `TBL-004`, `LEI-004` rug | Relaxation; informal meetings while idle | South arc | `habitat.sofa_1`…`_4` | Medium |
| 6 | **Window benches** | `SEA-009` + window (`WAL-003`, `DEC-001`) | A quiet view of space; replaces the StarNet TV idea | Outer south rim (about 5:30–6:30 o'clock) | `habitat.window_1`, `_2` | Medium |
| 7 | **Cosmetic rest pods** | `LEI-005` | Ambient resting seat. **No countdown, no vitals** | Rest zone, south-west | `habitat.rest_pod_1`…`_3` | Low–medium |
| 8 | **Recovery pods** | `EQP-004` | **Real cooldown only** (`agent.resting`); a countdown and vitals link | Recovery zone, north-west | `habitat.recovery_pod_1`…`_3` | Medium; clearly different from object 7 |
| 9 | **Vitals console** | `CON-021` | Medic persona's station | Recovery zone | `habitat.vitals` | Medium |
| 10 | **Living wall** | `PLT-004` | Greenery on the rim | Between the rest and recovery zones (about 8:30 o'clock, clear of the `DR-CMD-HAB` approach) | none | Low–medium |
| 11 | Warm pendants, hanging plants, bookshelf nook | `LGT-006`, `PLT-002`, `LEI-006` (optional) | Atmosphere | Over the café and billiards; the nook in the lounge | none | Low |
| 12 | Coffee cup | `PRP-007` | Ambient hand prop | Carried from the counter | ambient only | Low |

**Clutter limit** (Visual Bible §12): medium detail; no object on the ring or on a door approach;
**no screens outside the recovery zone** except the one alert repeater.

---

## 4. Billiard / game area (original Stellar version)

| Aspect | Definition |
|---|---|
| Design | **Owner decision HH-6:** an **original Stellar design**. **Wood-tone frame**, **titanium details** (rail and corner caps), **deep teal cloth**. A low, rounded, soft-edged form. A small cue rack (`STO-003`) on the adjacent rim; warm pendant above. No StarNet or franchise design |
| Seating | Two bar stools (`SEA-008`) at the rim behind the table for the waiting player; the lounge sofas are nearby |
| Function | **Social object only; relaxation only.** It has **no operational function**, shows **no data**, has **no score system**, and does **no monitoring**. There is no screen on or near it |
| Play | Two idle agents: `habitat.billiards_1` and `_2`. Seeded dwell times; neutral `stand_idle` / lean / cue-stroke loop; turn-taking. An operational task ends the game at once (work over idle) |
| Other games | **Owner decision HH-5:** billiards is the **only** game / recreation object in V1. No arcade and no board-game table |

---

## 5. Character life and Habitat agents

### 5.1 Activities

All activity comes from **real events**, **normal idle behaviour**, or **seeded ambient scheduling**.
There is **no emotional simulation**.

| Activity | Trigger | Where | Clips |
|---|---|---|---|
| **Resting (real)** | `agent.resting` (no producer yet; shown only when it exists) | Recovery pod + countdown | `rest_pod` overlay |
| **Resting (ambient)** | `idle` + seeded ambient choice | Cosmetic rest pod, window bench | `sit_work` pose variant (neutral seat), no sleep |
| **Conversations** | `idle` pairs chosen by the seeded scheduler, with pair cooldowns | Café tables, lounge | `talk` / `listen` (neutral, no bubbles) |
| **Games** | Two `idle` agents, seeded | Billiard table | cue loop, `stand_idle` |
| **Walking** | Ambient destination or return; real `agent.resting` walk to a pod | `habitat.ring` | `walk` |
| **Relaxing** | `idle`, seeded | Sofas, window benches, café seats | seated idle |
| **Informal meetings** | Idle agents sharing a café or lounge table (seeded). **Not** operational meetings: those happen only in working rooms on real events | Café, lounge | `talk` / `listen` |
| **Host service** | Ambient, while any agent is seated in the café | Counter → tables | `walk`, `carry` (`PRP-007`) |
| **Medic attendance** | Real `error` / `overloaded` (Medic walks to the agent's room); real `agent.resting` (escort to a pod) | Recovery zone ↔ other rooms | `walk`, `stand_work` |

**Rules:**
- **Work over idle (A13):** an agent's real task pulls it out of the Habitat at once.
- **Ambient is seeded and replayable (A14).** There is a station beat budget, so the Habitat is never
  overcrowded.
- **Ambient agents** are drawn at lower contrast than working agents.
- **"Scheduled activities"** means the **deterministic ambient schedule** of the UI (seeded). The
  engine emits no leisure events, and nothing implies it does (§8, Y2).

### 5.2 Habitat agents

| Agent | Visual role | Relationship with departments | How the space is used |
|---|---|---|---|
| **Habitat Host** (Bix, `CHR-043`, SYN) | A floating synthetic host with white / cyan / metallic shell and a tray; no hair, no uniform (Character Bible §5; CB-8 open). **Cosmetic, no operational meaning** | Serves **every** department equally; never enters other rooms (`MP-HOST`: `H-HAB` only) | At the counter; brings cups to seated agents; returns |
| **Medic persona** (`CHR-041`, O2, OPS gold) | Operational figure in the recovery zone | Attends agents of any department, **only** on real events | Home at `habitat.vitals`; walks out to rooms; escorts real cooldowns to pods |
| **Idle crew** (all departments) | **Keep their department uniform:** Habitat is not a department (Visual Bible C5) | Mix freely | Café, lounge, billiards, window benches, cosmetic pods |
| **Agents in a real cooldown** | Their own uniform, in a recovery pod with a countdown | Any | Recovery pods only |
| Future **Coach** (`CHR-046`) | Not rendered; home R1 | Advisory | May later use the café or lounge for debrief walks (future) |

---

## 6. Screen design (Screen Registry v2 §5.11 is the authority)

Only the approved Habitat displays are used. **No** screens are added for games, leisure,
"happiness" or wellbeing scores.

| Display | Content | Placement | State today | Placeholder |
|---|---|---|---|---|
| `DSP-HAB-01` Alert repeater | Alert word + icon | Café arc, small panel beside the counter | P (derived) | **NO TELEMETRY** |
| `DSP-HAB-02` Agent load | Per-agent load / overload | Recovery zone wall | **N**: no producer | **NOT AVAILABLE · load** |
| `DSP-HAB-03` Retries & latency | LLM retries, failures, timings (runtime metrics) | Recovery zone wall | A | **UNKNOWN** for null totals; **STALE**; **LINK DOWN** |
| `DSP-HAB-04` Rest schedule | Real cooldowns | Recovery zone wall | **N**: no producer | **NOT AVAILABLE · rest schedule** |

**Rules:**
- **Never invent** statistics, wellbeing values or operational data. The recovery pods show a
  countdown **only** from `agent.resting`.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN**. **MODE UNKNOWN** is not used here: there is no mode
  plaque, since this is not a trading room.
- **Monitoring displays stay inside the recovery zone.** The café, lounge and games zones show no
  system data.
- All displays are read-only.

---

## 7. Visual difference between the three hubs

| | **H-CMD** Main Command | **H-LAB** Research Hub | **H-HAB** Habitat |
|---|---|---|---|
| Meaning | Command, decisions, coordination | Research, analysis, science | **Life, recovery, social interaction** |
| Hero | Circular command table on a dais; overview viewscreen | Lab dome ring | **Central planter / tree**; billiard table |
| Light | Clean white / cyan; subtle command red | Brighter blue / cyan | **Warm, soft, natural**; a cooler calm recovery zone |
| Floor | Deep navy | Deep navy | **Warm wood-like laminate** (the main floor identity, Y1) |
| Screens | Many; data-dense command walls | Many; research walls | **Few**: an alert repeater, plus wellbeing panels **only** in the recovery zone |
| Motion | Working, meetings (event-driven) | Research, validation (event-driven) | **Ambient** (seeded idle) + real cooldowns |
| Contrast | Full (operational) | Full (operational) | **Lower** (ambient), except real operational events (Medic, cooldowns) |
| Windows | None (HC-5) | Allowed (HL-4 open) | **Yes**: window benches on the outer rim |

---

## 8. Contradictions and owner decisions (all resolved)

| # | Topic | Resolution |
|---|---|---|
| **Y1 / HH-1** | Floor material (a deep navy request vs the wood-like habitat floor) | **Owner:** the Habitat **wood-like floor is the main floor identity**; H-HAB must differ visually from H-CMD and H-LAB. Keep wood-like habitat areas, softer graphite and warm lighting. **Do not force deep navy flooring** in the Habitat. Aligned: Visual Bible §5.1 notes the Habitat exception. The Asset Registry `FLR-004` and Visual World Plan §14.2 already agree |
| **Y2** | "Scheduled activities" | The deterministic, seeded UI ambient schedule only; no engine leisure events are implied |
| **Y3** | Games "no monitoring" vs the Habitat monitoring screens | Not a conflict: monitoring stays in the recovery zone |
| **Y4 / HH-5** | Games beyond billiards | **Owner:** billiards only in V1; **no arcade** |
| **HH-6** | Billiard table | **Owner:** original Stellar design; wood-tone frame; titanium details; deep teal cloth; no score system; no monitoring |

**StarNet review (owner-approved):**
- **Kept:** café / social area, sofas, plants, billiard table, and seeded social interaction
  **without dialogue simulation**.
- **Excluded:** artificial needs, sleep simulation, random personality quotes, and the arcade in V1.

No remaining conflicts with:
- the topology;
- the Visual Bible (with the Habitat floor exception);
- the Character Bible;
- the Screen Registry;
- the StarNet exclusions.

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| HH-1 | Floor | **Closed:** wood-like habitat floor as the main identity (Y1) |
| HH-2 | Exact dimensions: planter size, zone arcs, ring width | **Open** (after the tile scale, VB-3) |
| HH-3 | Ceiling in the cutaway: skylight ring suggestion only, or a partial dome edge | **Open** (default: skylight ring only) |
| HH-4 | Window extent on the outer rim | **Open** (default: south arc only) |
| HH-5 | Games beyond billiards | **Closed:** billiards only in V1; no arcade |
| HH-6 | Billiard table design | **Closed:** original Stellar design, wood-tone frame, titanium details, deep teal cloth, no score, no monitoring |
| HH-7 | Habitat Host form | **Open** (Character Bible CB-8) |
| HH-8 | Exact colour values | **Open** (visual production, VB-4) |
