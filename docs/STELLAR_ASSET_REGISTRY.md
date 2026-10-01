# Stellar Agents — Asset Registry v2

| | |
|---|---|
| **Status** | v2.0, rebuilt on Floor Plan revision C. Stable IDs for asset **types**. **No art exists**; nothing here is final art |
| **Builds on** | Visual World Plan §14–§15, §22; `STELLAR_STATION_TOPOLOGY.md` v2; `STELLAR_ROOM_REGISTRY.md` v2; `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Hard rules** | Original Stellar art only. No StarNet artwork, sprites, painters-as-code, CRT look, fonts, sounds or branding (adaptation A31), and no franchise sets, uniforms, insignia, logos or LCARS styling. No voxel, no pixel art |
| **ID policy** | v1 type IDs are **kept** where the type still makes sense. Types that only served the stacked-deck model are **RETIRED** (listed, never reused). New types take the next free number |

---

## 1. Types and instances

- An **asset type** (`CON-004`) is one reusable model or sprite set.
- An **instance** is a placed copy named in its room's anchor namespace (for example
  `command.console_trader`). Instances are placed only when the grid is generated; room
  positions are provisional (Room Registry §6).
- Each type below records:
  - its purpose and likely room / hub;
  - its **interaction role**;
  - its **navigation implication**;
  - whether it is **required for V1**;
  - whether it is **reusable across rooms**.

**Navigation codes:**

| Code | Meaning |
|---|---|
| `blocks` | The footprint is not walkable; an approach anchor sits on a free adjacent tile (A9) |
| `seat` | Blocks, but has claimable seat anchors (A12) |
| `walk-over` | Low item on a walkable floor |
| `wall` | Mounted on a wall edge; occupies no floor |
| `crossing` | A door: the only kind of step between spaces (A2) |
| `solid` | Non-walkable structure |
| `none` | Decorative, or ceiling-mounted |

**V1 codes:** `Y` required · `opt` optional · `FUT` future (not rendered) · `—` retired.

---

## 2. 2.5D art rules

| # | Rule |
|---|---|
| 2.1 | **Stylised 2.5D isometric**, one fixed camera angle for the whole vessel. Modular, game-like, a living-world feel, readable at medium zoom |
| 2.2 | **Not photorealistic, not voxel, not flat 2D** as the final rendering. A flat technical diagram is allowed only to validate geometry |
| 2.3 | **Topology is untouchable:** the 2.5D conversion keeps the approved geometry exactly (Topology §2–§7). Art may round a hub rim or rotate an R room; it never adds, moves or hides a door, and never opens a gap |
| 2.4 | **Art shape vs walk shape:** round rims and radially rotated R rooms are drawn smooth, while the walk tiles stay stepped underneath (A4). Furniture inside an R room follows that room's own axis |
| 2.5 | **Modular footprints** in whole tiles, in the room's own axis. Walls sit on tile edges. Curved rim walls (`WAL-002`) are drawn over the rasterised rim edge |
| 2.6 | **Cutaway:** camera-facing walls use `WAL-008`, so interiors are always visible. A door in a cutaway wall keeps a **visible door frame, a threshold and a structural opening**; it must never read as a random gap in the floor (Visual Bible C4) |
| 2.7 | **Four orientations** for rotatable furniture (eight for R-room furniture, which follows the room axis); **eight facings** for characters |
| 2.8 | **Depth layers:** floor → decals → low props → bodies / mid props → tall props / screens → walls → ceiling. The depth key is x + y plus the layer (A21); it is decided in the renderer spike |
| 2.9 | **State is never colour alone:** every rendered state pairs colour with an icon, text or shape |
| 2.10 | **Screens carry no baked content:** no numbers, charts, prices or mode text in the art. Content comes only from the Screen Registry binding |
| 2.11 | **Alert tint at run time** on `LGT-001`, so every asset reads under GREEN, BLUE, AMBER and RED |
| 2.12 | **Performance:** each room is a cacheable static layer (A22, deferred); off-screen props are culled (A21). Hero objects must still read at the vessel-overview zoom |
| 2.13 | **Provenance:** every produced asset records author, tool, source and licence (Visual plan §22) |

---

## 3. Category summary

| Prefix | Category | IDs | Retired | Active types |
|---|---|---|---|---|
| `CHR` | Characters (Character Registry) | 46 | 1 | 45 (3 FUTURE, 1 DEFERRED) |
| `CON` | Consoles and workstations | 31 | 2 | 29 (2 FUTURE) |
| `SCR` | Screen hardware | 13 | 1 | 12 |
| `DOR` | Doors | 9 | 6 | 3 |
| `COR` | Corridor modules | 9 | 6 | 3 |
| `LFT` | Lifts | 5 | 5 | **0 (category retired)** |
| `TBL` | Tables | 8 | 0 | 8 (2 FUTURE) |
| `SEA` | Seating | 9 | 0 | 9 |
| `LGT` | Lighting | 10 | 1 | 9 |
| `DEC` | Decoration | 9 | 0 | 9 |
| `SRV` | Servers and conduits | 5 | 0 | 5 |
| `WAL` | Walls and structure | 11 | 1 | 10 |
| `FLR` | Floors | 12 | 1 | 11 |
| `STO` | Storage | 7 | 0 | 7 |
| `PLT` | Plants | 7 | 0 | 7 |
| `SGN` | Signage | 8 | 2 | 6 |
| `LEI` | Leisure furniture | 8 | 0 | 8 |
| `EQP` | Hero equipment | 7 | 0 | 7 |
| `PRP` | Hand-held and moving props | 8 | 0 | 8 |
| **Total** | **19 prefixes (18 in use)** | **222** | **26** | **196** |

---

## 4. Asset types

### `CHR` — Characters
`CHR-001`…`CHR-046` (`CHR-024` RETIRED). Each is one character asset with 8 facings and the state
set of Character Registry §8. Body bases are shared by build; uniforms are coloured by department.
Interaction: they occupy anchors. Navigation: dynamic bodies with traffic and separation (A8).

### `CON` — Consoles and workstations

| ID | Name | Purpose | Likely room | Interaction | Nav | V1 | Reusable | v2 |
|---|---|---|---|---|---|---|---|---|
| `CON-001` | Standard seated console | General workstation | L10 (contradiction desk), others | work anchor, 1 seat | blocks | Y | yes | kept |
| `CON-002` | Standing console | Technical stations | L2 | work anchor | blocks | Y | yes | kept |
| `CON-003` | Wide operations console | Supervisor run lifecycle | `H-CMD` | work anchor | blocks | Y | no | kept |
| `CON-004` | Central Trader console (triple display) | Multi-opportunity queue | `H-CMD` | work anchor (R) | blocks | Y | no | purpose changed |
| `CON-005` | Proposal assembly console | P1 proposal build | `H-CMD` | work anchor (R) | blocks | Y | no | kept |
| `CON-006` | Research feed console | R1–R6 feeds (dormant state for deferred roles) | `H-LAB` | work anchor | blocks | Y | yes | room changed |
| `CON-007` | Validation bench (4 stations) | V1–V4 | `H-LAB` | 4 work anchors | blocks | Y | no | room changed |
| `CON-008` | Driver-board station | Macro synthesis | `H-LAB` | work anchor | blocks | Y | no | room changed |
| `CON-009` | Market-family desk | One per family (Metals / FX / Indices) | L1 × 3 | work anchor (R per specialist) | blocks | Y | yes (future families) | was "instrument desk" |
| `CON-010` | Session-clock pedestal | T2 | L2 | work anchor | blocks | Y | no | room changed |
| `CON-011` | Debate podium | Debaters | L3 × 5 | work anchor (R) | blocks | Y | no | kept |
| `CON-012` | Risk intake counter | The courier drops proposals here | L10 | drop anchor (courier) + desk anchor (P2) | blocks | Y | no | was the armoured Vault intake window |
| `CON-013` | Rule-checklist console | Risk rules | L10 | work anchor (R: P3) | blocks | Y | no | kept |
| `CON-014` | Sizing console | Risk sizing | L10 | work anchor (R: P3) | blocks | Y | no | kept |
| `CON-015` | Breaker panel with lever | Breaker state (**display only**: the UI cannot reset it) | L10 | work anchor (R: P3) | blocks | Y | no | "sealed door" state removed |
| `CON-016` | Pre-flight console | P4 | L9 | work anchor (R) | blocks | Y | no | kept |
| `CON-017` | Launch console | E1 | L9 | work anchor (R) | blocks | Y | no | kept |
| `CON-018` | Reactor control console | T1 | L4 | work anchor (R) | blocks | Y | no | kept |
| `CON-019` | Archive terminal | L1 reviewer | L6 | work anchor | blocks | Y | no | kept |
| `CON-020` | Metrics terminal | L2 attribution | L7 | work anchor | blocks | Y | no | kept |
| `CON-021` | Vitals console | Medic persona | `H-HAB` recovery | work anchor | blocks | Y | no | room changed |
| `CON-022` | Budget console | Quartermaster persona | `H-CMD` | work anchor | blocks | Y | no | room changed |
| `CON-023` | Judge lectern | Debate judge | L3 | seat anchor | blocks | Y | no | kept |
| `CON-024` | Lift call panel | — | — | — | — | — | — | **RETIRED** (no lifts) |
| `CON-025` | Airlock control panel | — | — | — | — | — | — | **RETIRED** (no airlock) |
| `CON-026` | Experiment bench | Research Lab | `H-LAB` future zone / L5 | work anchors | blocks | FUT | no | kept (future) |
| `CON-027` | Reconciliation console | Reconciliation view | L4 | work anchor | blocks | Y | no | moved from the Execution Bay |
| `CON-028` | Coaching console | Coach | R1 | work anchor | blocks | FUT | no | **new** |
| `CON-029` | Risk outbox counter | Approved order pickup | L10 | pickup anchor (R: E1) | blocks | Y | no | **new** (replaces the airlock hand-off) |
| `CON-030` | Perimeter console bank module (H-CMD calibration V1) | Bridge-style equipment band on the hub rim; **unassigned, dark glass, no data, no anchor** | `H-CMD` rim ring; `H-LAB` (H-LAB calibration V1) | none | blocks (1–3 rim tiles) | Y | yes | **new** |
| `CON-031` | Secondary console (H-CMD calibration V2) | Unassigned bridge console with two monitors; **dark glass, no data, no anchor** | `H-CMD` back and south banks; `H-LAB` (H-LAB calibration V1) | none (unclaimed chairs) | blocks (2 × 1) | Y | yes | **new** |

### `SCR` — Screen hardware
Display instances (`DSP-…`) are defined in the Screen Registry. Every screen is `wall` or mounted
on furniture; none blocks the floor except `SCR-006` and `SCR-007`.

| ID | Name | Purpose | Likely room | Nav | V1 | Reusable | v2 |
|---|---|---|---|---|---|---|---|
| `SCR-001` | Main curved viewscreen | Hero status surface | `H-CMD` north rim | wall | Y | no | kept (placement: north rim) |
| `SCR-002` | Large wall panel | Main room displays | most rooms | wall | Y | yes | kept |
| `SCR-003` | Medium wall panel | Secondary displays | most rooms | wall | Y | yes | kept |
| `SCR-004` | Console-mounted display | Per-console content | on consoles | none | Y | yes | kept |
| `SCR-005` | Status band | Bands and strips | `H-CMD`, L2, L10 | wall | Y | yes | kept |
| `SCR-006` | Holographic projector column | Pulses | `H-LAB`, L4 | blocks (1 × 1) | Y | yes | kept |
| `SCR-007` | Floor kiosk display | Optional kiosk | hubs | blocks (1 × 1) | opt | yes | kept |
| `SCR-008` | Lift indicator | — | — | — | — | — | **RETIRED** |
| `SCR-009` | Mode plaque / hull marking | Execution-mode text from telemetry | `H-CMD`, L9 | wall | Y | yes | kept |
| `SCR-010` | Clock ring | Session clock | L2 | wall | Y | no | kept |
| `SCR-011` | Small wall panel / alert repeater | Alert repeaters, door status panel | corridors, `H-HAB`, L10 door | wall | Y | yes | kept |
| `SCR-012` | Holographic table surface | Chart table, evidence stage | L2, L3 | none (on a table) | Y | yes | kept |
| `SCR-013` | Screen-cluster column (one cast column, three dark screen heads; **no display identity, no data**) | Equipment groups | `H-LAB` feeds and macro groups (calibration V1) | blocks (1 × 1) | Y | no | **new** |

### `DOR` — Doors (21 instances: exactly the approved doors)

| ID | Name | Purpose | Instances | Interaction | Nav | V1 | v2 |
|---|---|---|---|---|---|---|---|
| `DOR-001` | Sliding door, straight wall (2 tiles) | Ordinary room door | 8: `DR-L1`…`DR-L8` | opens as a body approaches | crossing | Y | kept |
| `DOR-002` | Open archway (corridor ↔ lobby) | — | — | — | — | — | **RETIRED** |
| `DOR-003` | Vault blast door | — | — | — | — | — | **RETIRED** (no blast door) |
| `DOR-004` | Airlock inner hatch | — | — | — | — | — | **RETIRED** |
| `DOR-005` | Airlock outer hatch | — | — | — | — | — | **RETIRED** |
| `DOR-006` | Central-lift landing door | — | — | — | — | — | **RETIRED** |
| `DOR-007` | Secure decision-lift door | — | — | — | — | — | **RETIRED** |
| `DOR-008` | Sliding door with restricted marking (2 tiles) | Same geometry as `DOR-001`; carries the `SGN-006` marking. **Does not lock physically**; access is a navigation rule | 2: `DR-L9`, `DR-L10` | opens only for permitted classes (navigation never routes others through it) | crossing | Y | **new** |
| `DOR-009` | Curved-rim sliding door (2 tiles) | Door set in a hub rim | 11: the 4 corridor-end doors, `DR-CMD-HAB`, `DR-R1`…`DR-R6` | as `DOR-001` | crossing | Y | **new** |

### `COR` — Corridor modules

| ID | Name | Purpose | Where | Nav | V1 | v2 |
|---|---|---|---|---|---|---|
| `COR-001`…`COR-006` | Spine segment, spine end cap, archway transition, lobby floor, promenade segment, lift guide rail | — | — | — | — | **RETIRED** |
| `COR-007` | Door niche | Frames a room door on the corridor side | both corridors | walk-over | Y | kept |
| `COR-008` | Corridor segment (width per scale, equal for both corridors) | Corridor body | `COR-N`, `COR-S` | walk-over | Y | **new** |
| `COR-009` | Corridor-to-hub junction | The corridor end entering a hub rim through `DOR-009` (never a sealed end cap) | 4 (both ends of both corridors) | walk-over / crossing | Y | **new** |

### `LFT` — Lifts (category retired)
`LFT-001`…`LFT-005` are **RETIRED**. The vessel has no lifts.

### `TBL` — Tables

| ID | Name | Likely room | Interaction | Nav | V1 | Reusable | v2 |
|---|---|---|---|---|---|---|---|
| `TBL-001` | **Circular** command table | `H-CMD` centre | 4 seat anchors + head | seat | Y | no | shape set to circular (H-CMD design sheet HC-1) |
| `TBL-002` | Holographic chart table | L2 | 2 anchors | blocks | Y | no | kept |
| `TBL-003` | Round café table | `H-HAB` | seats | seat | Y | yes | kept |
| `TBL-004` | Lounge coffee table | `H-HAB` | — | blocks | Y | yes | kept |
| `TBL-005` | Small work table | L6, L7 | 1–2 anchors | blocks | Y | yes | kept |
| `TBL-006` | Shape-comparison holo bench | `H-LAB` future zone / L5 | anchors | blocks | FUT | no | kept (future) |
| `TBL-007` | Evidence stage | L3 | projector base | blocks | Y | no | kept |
| `TBL-008` | Debrief table | R1 | seats | seat | FUT | no | **new** |

### `SEA` — Seating (all kept)

| ID | Name | Likely room | Nav | V1 | Reusable |
|---|---|---|---|---|---|
| `SEA-001` | Command chair (raised) | `H-CMD` dais | seat (R: PM) | Y | no |
| `SEA-002` | Console chair | at consoles | seat | Y | yes |
| `SEA-003` | Judge seat | L3 | seat | Y | no |
| `SEA-004` | Tier bench | L3 (optional, if the room depth allows) | seat | opt | no |
| `SEA-005` | Waiting bench | `H-CMD`, hub rims | seat | Y | yes |
| `SEA-006` | Lounge sofa | `H-HAB` | seat | Y | yes |
| `SEA-007` | Café chair | `H-HAB` | seat | Y | yes |
| `SEA-008` | Bar stool | `H-HAB` | seat | Y | yes |
| `SEA-009` | Window bench | `H-HAB` outer rim (was the Observation Deck bench); park benches facing the fountain (H-HAB park V1) | seat | Y | yes |

### `LGT` — Lighting

| ID | Name | Where | V1 | v2 |
|---|---|---|---|---|
| `LGT-001` | Cove light strip (carries the alert tint) | everywhere | Y | kept |
| `LGT-002` | Console pool light | over active consoles | Y | kept |
| `LGT-003` | Alert beacon (real `error` / RED only) | any room | Y | kept |
| `LGT-004` | Floor guide strip (points toward the hub doors) | corridors | Y | purpose changed (was "toward the lift") |
| `LGT-005` | Cold panel light | L10 | Y | room changed |
| `LGT-006` | Warm pendant | `H-HAB` | Y | kept |
| `LGT-007` | Podium spotlight (neutral light; side icon + text; no side colour) | L3 | Y | kept |
| `LGT-008` | Airlock status lamp | — | — | **RETIRED** |
| `LGT-009` | Dome light | `H-LAB` | Y | room changed |
| `LGT-010` | Wall utility fixture (cool white in command; never a status light) | `H-CMD` rim (calibration V1) | Y | **new** |

### `DEC` — Decoration (Nav `none`, or `wall`)

| ID | Name | Where | V1 | v2 |
|---|---|---|---|---|
| `DEC-001` | Planet view (behind window walls) | outer rims of `H-LAB` and `H-HAB` (**not `H-CMD`**: no windows, HC-5) | Y | kept |
| `DEC-002` | Star field | window walls, backdrop | Y | kept |
| `DEC-003` | Abstract wall art panel (original) | any | opt | kept |
| `DEC-004` | Vessel scale model (**carries no data**) | `H-CMD` or `H-HAB` | opt | renamed (was the station model) |
| `DEC-005` | Hull rib trim | L9, L10, corridors | Y | reused |
| `DEC-006` | Department emblem plaque (shape icons only) | room doors | Y | kept |
| `DEC-007` | Holo globe (**decorative only**: no real data, no fake system status, no charts or metrics) | `H-CMD`, `H-LAB` centres | opt | **new** |
| `DEC-008` | Wall equipment panel (vents, cable trays, junction boxes; **no data**) | `H-CMD` rim segments (calibration V1); `H-LAB` rim (H-LAB calibration V1) | Y | **new** |
| `DEC-009` | Resident station dog (world-building only: a visual resident of the habitat; **no AI, no behaviour, carries no data**) | `H-HAB` dog corner (H-HAB park V1) | Y | **new** |

### `SRV` — Servers and conduits

| ID | Name | Where | Nav | V1 | v2 |
|---|---|---|---|---|---|
| `SRV-001` | Server rack | L4 | blocks | Y | kept |
| `SRV-002` | Journal archive rack | L4, L6 | blocks | Y | kept |
| `SRV-003` | Data conduit trunk | **only inside non-walkable gap space**; must read as solid, never as a passage | solid | opt | re-scoped (was a vertical deck conduit) |
| `SRV-004` | Overhead cable tray | ceilings | none | opt | kept |
| `SRV-005` | Relay stack (decorative hardware tower; constant hardware lights, **never status or data**) | `H-CMD` operations clusters (calibration V2) perimeter racks between bank groups (calibration V5) and rack pairs in the equipment groups (calibration V5.1); `H-LAB` (H-LAB calibration V1); L1–L4, L6, L7, L9, L10 wall equipment (wing calibration V1) | blocks (1 × 1) | Y | **new** |

### `WAL` — Walls and structure

| ID | Name | Where | Nav | V1 | v2 |
|---|---|---|---|---|---|
| `WAL-001` | Straight wall panel | L rooms, R rooms, corridors | solid | Y | kept |
| `WAL-002` | Curved wall panel | hub rims | solid | Y | kept (main use now) |
| `WAL-003` | Window wall | outer rims of `H-LAB` and `H-HAB` (**not `H-CMD`**: its rim carries screens and information surfaces, HC-5) | solid | Y | kept |
| `WAL-004` | Armoured bulkhead | — | — | — | **RETIRED** (no armoured vault) |
| `WAL-005` | Glass partition | L1 desk bays | solid | Y | room changed |
| `WAL-006` | Hull wall | outer hull | solid | Y | kept |
| `WAL-007` | Corner piece | everywhere | solid | Y | kept |
| `WAL-008` | Cutaway wall cap | camera-facing walls | solid | Y | kept |
| `WAL-009` | Structural gap infill | The non-walkable hull between small rooms and between the L-block and the hubs (Q4). Must read as solid mass, never as a corridor | solid | Y | **new** |
| `WAL-010` | Radial junction collar | Where a rotated R room meets the `H-HAB` rim around `DOR-009` | solid | Y | **new** |
| `WAL-011` | Segmented bulkhead rim (gunmetal panels, ribs, titanium cap) | `H-CMD` rim (calibration V1) | solid | Y | **new** |

### `FLR` — Floors

| ID | Name | Where | Nav | V1 | v2 |
|---|---|---|---|---|---|
| `FLR-001` | Standard deck floor | most rooms | walk-over | Y | kept |
| `FLR-002` | Raised dais (walkable step) | `H-CMD` centre | walk-over | Y | kept |
| `FLR-003` | Grating | L10 | walk-over | Y | room changed |
| `FLR-004` | Habitat laminate | `H-HAB` | walk-over | Y | kept |
| `FLR-005` | Corridor floor with guide inlay | corridors | walk-over | Y | kept |
| `FLR-006` | Tier steps | L3 (optional) | walk-over | opt | kept |
| `FLR-007` | Lift landing plate | — | — | — | **RETIRED** |
| `FLR-008` | Launch-deck marking | L9 | walk-over | Y | kept |
| `FLR-009` | Hazard-stripe border marking (amber / charcoal) | `H-CMD` dais edge (calibration V1) | walk-over | Y | **new** |
| `FLR-010` | Floor vent grille (decal) | `H-CMD` walkway (calibration V1); `H-LAB` (H-LAB calibration V1) | walk-over | Y | **new** |
| `FLR-011` | Cable conduit (floor channel, decal) | `H-CMD` back bank to the dais (calibration V2); `H-LAB` (H-LAB calibration V1) | walk-over | Y | **new** |
| `FLR-012` | Park ground and garden paths (decal) | `H-HAB` park (H-HAB park V1) | walk-over | Y | **new** |

### `STO` — Storage (kept)

| ID | Name | Where | Nav | V1 |
|---|---|---|---|---|
| `STO-001` | Wall locker | L6, L9, L10, `H-LAB`, `H-CMD` (rim, flanking the doors; calibration V1) | wall / blocks | opt |
| `STO-002` | Crate stack | L4 | blocks | opt |
| `STO-003` | Shelf / cue rack | `H-HAB` (cue rack; rim-edge shelves, H-HAB calibration V1) | blocks | Y |
| `STO-004` | Crystal archive shelf | L6 | blocks | Y |
| `STO-005` | Equipment bay cabinet (low, vented) | `H-CMD` operations clusters (calibration V2), perimeter rhythm and equipment groups (calibration V5.1); `H-LAB` (H-LAB calibration V1); L1–L4, L6, L7, L9, L10 wall equipment (wing calibration V1) | blocks (2 × 1; 1 × 2 when side-facing) | Y |
| `STO-006` | Service cabinet (1 × 1; hazard-marked door, vents) | `H-CMD` second row behind the rim bank (calibration V3), perimeter rhythm and the south command group (calibration V5.1); `H-LAB` (H-LAB calibration V1); L1–L4, L6, L7, L9, L10 wall equipment (wing calibration V1); `H-HAB` recovery bay (H-HAB calibration V1) | blocks (1 × 1) | Y |
| `STO-007` | Sample cart (open-shelf trolley on casters, sample vials, printout stacks; decorative) | `H-LAB` validation group (calibration V1) | blocks (1 × 1) | Y |

### `PLT` — Plants

| ID | Name | Where | Nav | V1 | v2 |
|---|---|---|---|---|---|
| `PLT-001` | Floor planter (1 × 1) | hubs, rooms | blocks | Y | kept |
| `PLT-002` | Hanging plant | ceilings | none | opt | kept |
| `PLT-003` | Desk plant | on desks | none | opt | kept |
| `PLT-004` | Living wall panel | `H-HAB` | wall | Y | kept |
| `PLT-005` | Central planter / tree (hero) | `H-HAB` centre (`habitat.plants`) | blocks | Y | **new** |
| `PLT-006` | Garden bed (low planted bed, stone edge) | `H-HAB` park | blocks | Y | **new** |
| `PLT-007` | Park tree (planted tree in a stone ring) | `H-HAB` park | blocks | Y | **new** |

### `SGN` — Signage (static; never a data display)

| ID | Name | Where | V1 | v2 |
|---|---|---|---|---|
| `SGN-001` | Room name plate | by each active room's door | Y | kept |
| `SGN-002` | Vessel directory board | hub side of each corridor end | Y | re-scoped (was the deck directory) |
| `SGN-003` | Wayfinding arrow | corridors, hubs | Y | kept |
| `SGN-004` | Lift deck number | — | — | **RETIRED** |
| `SGN-005` | One-way airlock placard | — | — | **RETIRED** |
| `SGN-006` | Restricted-area marking | `DR-L9`, `DR-L10` | Y | reused (was the Vault marking) |
| `SGN-007` | "RESERVED" plate | doors of L5, L8, R1–R6 | Y | **new** |
| `SGN-008` | Workstation name plate (role code + role; static text, never data) | assigned `H-CMD` workstations (calibration V1) | Y | **new** |

### `LEI` — Leisure (all in `H-HAB`, kept)

| ID | Name | Nav | V1 |
|---|---|---|---|
| `LEI-001` | Billiard table (hero; +1 tile play clearance) | blocks + 2 play anchors | Y |
| `LEI-002` | Café counter | blocks + host anchor | Y |
| `LEI-003` | Drink dispenser | blocks | Y |
| `LEI-004` | Lounge rug | walk-over | Y |
| `LEI-005` | Cosmetic rest pod (no countdown, no vitals) | seat | Y |
| `LEI-006` | Bookshelf nook | blocks | opt |
| `LEI-007` | Park fountain (hero: stone basin, central column, water; **decorative, no data**) | blocks | Y |
| `LEI-008` | Dog corner (dog bed, food and water bowls, toy basket, small storage) | blocks | Y |

### `EQP` — Hero equipment

| ID | Name | Where | Behaviour | V1 | v2 |
|---|---|---|---|---|---|
| `EQP-001` | Reactor column | L4 | pulses **only** per `snapshot.created` | Y | kept |
| `EQP-002` | Launch tube | L9 | animates only on `order.*` | Y | kept |
| `EQP-003` | Docking board frame | L9 | | Y | kept |
| `EQP-004` | Recovery pod (**real cooldown**: countdown and vitals link) | `H-HAB` recovery zone | only from `agent.resting` | Y | room changed |
| `EQP-005` | Lab dome ring (hero) | `H-LAB` | decorative | Y | re-scoped (was the observatory dome) |
| `EQP-006` | Optics column (bolted sealed column with a constant lens light; decorative, **no data**) | `H-LAB` core, around the dome ring (calibration V1) | decorative | Y | **new** |
| `EQP-007` | Specimen tank (glass tank on a stand with a pump housing; decorative, **no data**) | `H-LAB` validation group (calibration V1) | decorative | Y | **new** |

### `PRP` — Hand-held and moving props (appear only when their event exists)

| ID | Name | Appears only when | Route | v2 |
|---|---|---|---|---|
| `PRP-001` | Data crystal | a hand-off implied by `analysis.created` → the next consumer | for example `L2` → L1 (T3, technical evidence), `H-LAB` → L1, L1 → `H-CMD` | route changed |
| `PRP-002` | Item card | `research.item.accepted` hand-off | inside `H-LAB` | kept |
| `PRP-003` | Proposal card | `trade.proposed` | courier `H-CMD` → `DR-S-CMD` → `COR-S` → L10 `risk.intake_drop` | route changed (was the decision lift) |
| `PRP-004` | Evidence card | `debate.turn.completed` whose paired `agent.task.completed` case cites evidence | inside L3: placed on the central evidence stage (never passed between podiums) | kept |
| `PRP-005` | Order capsule | `risk.approved` **and** `order.created` | E1 collects it at L10 `risk.outbox_pickup` → `COR-S` → L9 | route changed (was the airlock) |
| `PRP-006` | Review crystal | `trade.closed` | → L6 shelf | kept |
| `PRP-007` | Coffee cup | ambient only | `H-HAB` | kept |
| `PRP-008` | Billiard cue | ambient only | `H-HAB` | kept |

No prop ever suggests a decision that did not happen (Visual plan §1.5).
