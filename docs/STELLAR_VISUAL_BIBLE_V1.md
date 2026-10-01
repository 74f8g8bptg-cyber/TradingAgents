# Stellar Visual Bible V1

**Visual identity & 2.5D world design rules**

| | |
|---|---|
| **Status** | V1, owner draft with **owner decisions C1–C7 applied** (Part C). Visual design specification only: no code, no assets, no runtime change |
| **Purpose** | Define the visual identity of the Stellar station before character, room and asset production |
| **Integrates with** | `STELLAR_MASTER_FLOOR_PLAN_V1.md` (revision C, the physical source of truth), `STELLAR_VISUAL_WORLD_PLAN.md`, `STELLAR_CHARACTER_REGISTRY.md` v2, `STELLAR_ASSET_REGISTRY.md` v2, `STELLAR_SCREEN_REGISTRY.md` v2, `STELLAR_STATION_TOPOLOGY.md` v2, `STELLAR_ROOM_REGISTRY.md` v2 |
| **Precedence** | The Bible is the **visual direction document** (look and feel). The approved Floor Plan and the registries remain the source of truth for **geometry and system behaviour**: the floor plan for geometry, the Screen Registry for data states, Topology v2 for doors and access. The owner resolved conflicts C1–C7 (Part C); amended lines in Part A are marked *(owner decision Cn)* |

Part A is the owner's draft, formatted, with the owner's C1–C7 decisions applied in place. Parts
B–D are integration notes.

---

# Part A — Owner draft

## 1. Core visual identity

### 1.1 Vision

Stellar is a living AI operations vessel.

The visual goal is:
- futuristic but believable;
- advanced but not cold;
- professional but alive;
- inspired by classic science-fiction exploration vessels;
- combined with modern game-like 2.5D readability.

The viewer should immediately understand:
- where agents work;
- which department they belong to;
- what the station is doing;
- which areas are important.

## 2. Style direction

### 2.1 Rendering style

**Target:** Stylized 2.5D Isometric Sci-Fi.

Characteristics:
- isometric camera;
- modular environment;
- clean shapes;
- readable silhouettes;
- realistic proportions simplified for clarity;
- detailed enough for close views;
- optimized for many agents moving simultaneously.

**Not:**
- realistic AAA spaceship simulation;
- voxel style;
- flat 2D map;
- cartoon comedy style.

## 3. Visual references

### Inspiration categories

**Exploration / Federation feeling.** Inspired by:
- organized scientific vessel;
- teamwork;
- exploration;
- advanced technology;
- peaceful intelligence.

**Modern simulation / game readability.** Inspired by:
- clear rooms;
- visible workflows;
- characters with understandable roles;
- interactive environment.

**Stellar identity.** Must remain original. Do not copy:
- Star Trek uniforms;
- logos;
- ships;
- rooms;
- interfaces;
- visual assets.

## 4. Camera rules

### 4.1 Default camera

Camera:
- elevated isometric angle;
- approximately 45 degrees horizontal;
- enough height to see furniture and walking paths;
- not too high like a blueprint.

The player should feel inside the vessel.

### 4.2 Room visibility

Rules:
- walls may disappear or be cut when necessary;
- important objects must never be hidden;
- doors must always remain visible;
- corridors must remain readable.

The camera must preserve:
- navigation understanding;
- room identity;
- agent movement.

## 5. Vessel material language

### 5.1 Main materials

*(owner decision C1: a balanced Stellar identity. The ship must not become a fully dark vessel; it
keeps a premium exploration / science-vessel feel.)*

**Primary:**
- warm off-white structural panels;
- titanium / light metallic trims;
- deep navy floors (in working spaces; **exception:** `H-HAB` uses the warm wood-like habitat floor as
  its main floor identity, per the H-HAB design sheet HH-1);
- transparent technology surfaces.

**Secondary:**
- dark graphite for consoles, technical areas and accents;
- cyan light strips;
- department colors;
- warm habitat materials.

## 6. Lighting system

### 6.1 General vessel lighting

Default:
- clean white / cyan illumination;
- soft shadows;
- high readability.

The ship should feel:
- active;
- maintained;
- advanced.

*(owner decision C7)*
- **Environment lighting** may use cyan / blue freely.
- **Data meaning** (teal / cyan data colours on screens) follows the Screen Registry rules.
- **Lighting alone never communicates a data state.** Station alert tints are always paired with a
  banner and an icon (Visual World Plan §14.3).

### 6.2 Department lighting

| Area | Mood | Lighting |
|---|---|---|
| **Command** | confident; central; important | neutral white; subtle red accents |
| **Research** | discovery; analysis; intelligence | blue / cyan; brighter screens |
| **Risk** | controlled; precise; secure | darker environment; amber / red warning accents only when needed |
| **Habitat** | human comfort; recovery; relaxation | warmer; softer; plants and natural elements |

## 7. Department color system

| Department | Color | Meaning |
|---|---|---|
| **Command** | deep red; burgundy; dark neutral | Leadership / coordination |
| **Research / Science** | blue; cyan | Knowledge / analysis |
| **Risk / Operations** | gold; amber; charcoal | Control / safety |
| **Synthetic / System** | white; cyan; metallic | AI systems / infrastructure |
| **Habitat** *(environment palette only; owner decision C5)* | warm grey; wood tones; green plants | Recovery / balance. A **location style**, not a uniform department |

*(owner decision C5)* Character uniform departments remain exactly four: **Command**,
**Research / Science**, **Risk / Operations**, **Synthetic / System** (Character Registry v2 §2).
No fifth uniform department exists.

## 8. Architecture rules

### 8.1 Hubs

Three visual identities:

**H-LAB**
- Shape language: scientific; organized; analytical.
- Objects: research stations; analysis screens; data consoles.

**H-CMD** — the heart of Stellar.
- Objects: central command table; large overview displays; coordination stations.
- Must feel like: *"The place where everything connects."*

**H-HAB** — the living area.
- Objects: café; tables; plants; games; relaxation spaces.
- Must feel different from work areas.

## 9. Door rules

**Critical: doors are functional objects.**

Rules:
- every real passage has a visible door;
- decorative doors do not exist;
- no automatically generated doors;
- doors follow the approved floor plan.

Door states:

| State | Indicator | Rule |
|---|---|---|
| Normal | white / cyan indicator | Ordinary door (all 21 doors are physically ordinary; Topology v2 §3) |
| Restricted | **icon + marking** (`SGN-006`), optional amber indicator | *(owner decision C3)* Must read correctly **without colour**. Applies to `DR-L9` and `DR-L10` (logical access, Topology v2 §9) |
| Blocked | red indicator **+ icon + text** | *(owner decision C2)* Allowed **only** while a real system state exists: breaker tripped; a security event; a real access denial. **Never** decoration or invented danger. The visual UI never locks a door |

Today only **breaker tripped** has a producer (`circuit_breaker.tripped`, shown by `DSP-RSK-09`).
The engine emits no security-event or access-denial telemetry yet, so those two sources cannot
turn a door red until a producer exists (Screen Registry §2.1).

**Doors in cutaway walls** *(owner decision C4)*. A door in a cut-away, camera-facing wall keeps a
**visible door frame, a threshold and a structural opening**. The cutaway must never make a real
door look like a random gap in the floor.

## 10. Screen design rules

Screens must look like real Stellar systems.

Never:
- fake random numbers;
- fake trading information;
- invented status.

States *(owner decision C6: the Screen Registry is the authority; this list references it and does
not replace it)*:
- LIVE
- AWAITING DATA
- STALE
- LINK DOWN
- MODE UNKNOWN
- NOT AVAILABLE
- NOT CONFIGURED
- UNKNOWN

Their definitions, treatment and full list (including `PLANNED` and "DISPLAY FAULT") are in
`STELLAR_SCREEN_REGISTRY.md` §3.

## 11. Character visual rules

Agents must be recognizable.

Requirements:
- department color;
- unique silhouette;
- role-based accessories;
- readable from distance.

Avoid:
- identical clones;
- overly realistic humans;
- unnecessary details.

## 12. Environment detail level

**Target:** medium detail.

Visible:
- chairs;
- desks;
- screens;
- plants;
- consoles;
- small objects.

Avoid:
- thousands of decorative objects;
- clutter;
- details that reduce performance.

## 13. Future production order

After this Bible:
1. Character Bible
2. Main Command room design
3. Lab design
4. Habitat design
5. Risk / Execution design
6. Asset library
7. Full station visual prototype

*End of the owner draft.*

---

# Part B — Integration with the approved documents

| Bible section | Where it lands | Status |
|---|---|---|
| §1 Vision; §2 style; §3 originality | Visual World Plan §14.1; Asset Registry §2 rules 2.1–2.2; Character Registry §1 | **Consistent.** Stylised 2.5D isometric; not voxel, flat 2D or photoreal; original; no Star Trek or StarNet material (adaptation A31) |
| §4.1 Camera | Visual World Plan §2.1 (fixed isometric, cutaway); Asset Registry rule 2.1 (one fixed angle) | **Consistent.** The exact angle is an open decision (Part D, VB-2) |
| §4.2 Room visibility | Asset Registry rules 2.3 (topology untouchable) and 2.6 (cutaway); Visual World Plan §2.4 | **Consistent** (C4 resolved: door frame, threshold and opening stay visible; Asset rule 2.6 updated) |
| §5 Materials | Visual World Plan §14.2 | **Consistent** (C1 resolved; §14.2 gains the graphite secondary line) |
| §6.1 General lighting | Visual World Plan §14.3 (cove light, alert tint on `LGT-001`) | **Consistent** (C7 resolved: lighting never carries data meaning) |
| §6.2 Department lighting | Room Registry v2 room cards (H-CMD red accent, H-LAB cool dome light, L10 cold panel light, H-HAB warm pendants) | **Consistent** |
| §7 Color system | Character Registry v2 §2 (CMD red / burgundy, SCI blue, OPS gold / yellow on charcoal, SYN white / cyan / metallic) | **Consistent** (C5 resolved: Habitat is an environment palette only) |
| §8 Hubs | Floor Plan revision C; Room Registry v2 §3.1–§3.3 | **Consistent.** `H-CMD` is the through-hub (Topology v2 §6), which matches "the place where everything connects" |
| §9 Door rules (passages) | Topology v2 §3 (21 explicit doors), §7 (no hidden connections); Asset Registry `DOR-001` / `DOR-008` / `DOR-009` | **Consistent:** explicit doors only, no automatic or decorative doors |
| §9 Door states | Topology v2 §9 (logical access); Asset Registry `DOR-008` ("does not lock physically"); Screen Registry `DSP-RSK-09` | **Consistent** (C2 and C3 resolved: red only from real system states; restricted = icon + marking) |
| §10 Screen rules | Screen Registry v2 §1 (never fabricate), §3 (states) | **Consistent** (C6 resolved: the Screen Registry is the authority) |
| §11 Characters | Character Registry v2 §1–§2; Visual World Plan §14.6 (6–7 heads tall, stylised, varied); shape icon plus colour | **Consistent** |
| §12 Detail level | Asset Registry rule 2.12 (culling, cached static layers); Visual World Plan §14.8 (visual hierarchy) | **Consistent** |
| §13 Production order | Visual World Plan §19 (phases V1–V5) | Compatible. The Bible order is for art and design, inside those phases |

**Topology check.** Nothing in the Bible adds, moves or removes a door, room, corridor or hub. The
Bible does not mention the ten L rooms, the six R rooms or the reserved slots. They follow the Room
Registry v2 assignments. Reserved rooms follow VB-6 (Part D).

---

# Part C — Conflicts and owner decisions (all resolved)

| # | Topic | Owner decision | Documents aligned |
|---|---|---|---|
| **C1** | Materials | **Balanced identity.** Primary: warm off-white structural panels, titanium / light metallic trims, deep navy floors. Secondary: dark graphite for consoles, technical areas and accents. Not a fully dark vessel; a premium exploration / science vessel | Bible §5.1; Visual World Plan §14.2 (graphite secondary line added) |
| **C2** | Blocked (red) door | Doors are never physically locked by the visual UI. Red **only** while a real system state exists (breaker tripped; security event; real access denial). Never decoration or fake danger | Bible §9. Consistent with Topology v2 §3 and §9 and `DOR-008`. Only the breaker has a producer today |
| **C3** | Restricted door | Icon + marking, with an optional amber indicator; readable without colour | Bible §9. Consistent with Asset rule 2.9 and `SGN-006` |
| **C4** | Doors in cutaway walls | Keep door visibility: a visible frame, threshold and structural opening; never a random floor gap | Bible §9; Asset Registry rule 2.6 updated |
| **C5** | Habitat colour | An environment palette / location style only; no fifth uniform department | Bible §7. Consistent with Character Registry v2 §2 |
| **C6** | Screen states | The Screen Registry is the authority. All of LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN, NOT AVAILABLE, NOT CONFIGURED and UNKNOWN are kept; the Bible references the registry | Bible §10. Consistent with Screen Registry §3 |
| **C7** | Cyan lighting vs teal data | Environment cyan / blue is allowed. Data colours follow the Screen Registry. Lighting alone never communicates a data state | Bible §6.1; Visual World Plan §14.3 (one line added) |

---

# Part D — Future visual decisions

| # | Decision | Status |
|---|---|---|
| VB-1 | Resolve C1–C7 | **Closed** (Part C) |
| VB-2 | Exact camera elevation (about 45° horizontal is set) | **Open** (elevation only). The camera **direction** is frozen: **Iso · right**, from the north-east (Visual Prototype V1 §0) |
| VB-3 | Exact tile scale | **Open** (Topology v2 TP-1) |
| VB-4 | Exact colour values: uniforms, lighting, door indicators, tested under the alert tints and colour-blind simulation | **Open** |
| VB-5 | Door indicator rules | **Closed**: normal / restricted (icon + marking, optional amber) / blocked (red + icon + text, only from real system states: today `circuit_breaker.tripped`) |
| VB-6 | Reserved rooms (L5, L8, R1–R6) | **Closed**: a dark, unlit shell with an `SGN-007` "RESERVED" plate; the door shows the **normal** indicator dimmed. There is no red (no system state) and no amber (not an access restriction; the plate carries the meaning) |
| VB-7 | Hero-object designs (H-CMD command table and overview displays, H-LAB lab dome, H-HAB central planter) | **Open** (production steps 2–4) |
| VB-8 | Specialist family desks while the interim adapter is active | **Closed at the rule level:** one desk character, one task row and state chip per runtime agent, a split pip in overview, no merged state (Character Registry v2 §5.2). Art detail goes to the Character Bible |
| VB-9 | Renderer choice (PixiJS vs Canvas 2D spike) | **Open** (VW-2) |
| VB-10 | Generated-art provenance and tool policy | **Open** (Visual World Plan §22, VW-3) |
| VB-11 | Performance budget (agents and props per screen at medium zoom) | **Open** (measured in the renderer spike) |
| VB-12 | Character Bible scope | **Closed:** body bases and silhouettes per department; role accessories; the four uniform departments; the family-desk representation (VB-8); the future Coach and Lab roles; state animation sets (Character Registry v2 §8) |

**Still open (7):** VB-2 camera elevation, VB-3 tile scale, VB-4 colour values, VB-7 hero objects,
VB-9 renderer, VB-10 generated-art provenance, VB-11 performance budget.
