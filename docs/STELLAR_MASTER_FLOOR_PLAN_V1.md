# Stellar Master Floor Plan V1 — revision C (owner sketch, geometry decisions confirmed)

> **Owner confirmation (Q1):** every red rectangle in the sketch is a real doorway, including the four
> corridor-end doors into LABO and Main Command. The earlier sealed-end rule belonged to the older
> layout and is superseded. The door topology in §6–§9 is **confirmed**; the geometry questions left
> are in §14.
> **Owner decisions Q3–Q11** are recorded in §14. **No geometry question remains open.** Exact scale
> is intentionally not frozen (§14, Q8).
> **Status:** geometry owner-confirmed; awaiting formal approval of this revision. Physical topology only: no room functions (beyond the three
> hubs), no furniture, characters, consoles or screens placed, no art, no renderer.
> **Source of truth:** the owner's sketch (IMAGE 1), SHA-256
> `0bd5489f9f1bfe1d877364a018b289ada5666e0144fd82b33f523d3b260e473e`, 2000 × 1195 px.
> **Style reference only:** the 2.5D concept image (IMAGE 2), SHA-256
> `632f68c90c9054ae54ca87267c3cd3a9d44200bab4b45c7f67e84248d75ad60f`.
> **Replaces:** revisions A and B of this file (drawn without the sketch), and the stacked five-deck
> model in `STELLAR_STATION_TOPOLOGY.md`. The five Visual Foundation registries are **not modified**
> (their rebuild status is in §12).
> **Method:** the sketch was decoded pixel by pixel (headless Chromium, scratch script, not
> committed). Door markers, corridor lines, and room and hub extents are measured from it, not
> estimated. Coordinates below are **sketch pixels** (x right, y down).

---

## 1. Interpretation of IMAGE 1

- **Legend used by the sketch:**
  - grey fill = a space (room or hub);
  - a pair of black horizontal lines = a corridor;
  - **red square = a door**;
  - white = outside the vessel (void or hull).
- **Shape:** one flat, horizontal vessel. From left to right: a circular **LABO** hub, a corridor
  complex with ten rectangular rooms, a large circular **central hub** (unlabelled in the sketch;
  the owner names it Main Command), and a circular **right hub** (Habitat) with six rooms around it.
- **Left complex (between LABO and the central hub):**
  - two horizontal corridors, upper and lower, each running from LABO to the central hub;
  - L1, L2, L3 above the upper corridor;
  - L4, L5 below the upper corridor;
  - L6, L7 above the lower corridor (L4 over L6 and L5 over L7, each pair sharing one wall);
  - L8, L9, L10 below the lower corridor.
- **Right hub:** R1–R6 stand **radially** around the Habitat hub, like spokes, each opening straight
  into it. There is no corridor on the right side.
- **21 red door markers** (measured). Every room has exactly one. The other five sit where a corridor
  meets a hub (four) or where the central hub meets the Habitat hub (one).
- **No end walls are drawn.** Both corridors run into LABO at one end and into the central hub at
  the other, and each of the four corridor ends carries a red marker, which the owner has confirmed
  is a doorway (Q1 resolved).

## 2. How IMAGE 2 is used

IMAGE 2 is a **presentation reference only**. It sets:
- the stylised 2.5D isometric look;
- modular sci-fi rooms with thick hull walls;
- warm habitat lighting against cool lab and command lighting;
- furniture density;
- game-like readability at medium zoom;
- a living-world feel.

It is **not** used for any door, corridor, connection, room count or position. (For the record, a
comparison found no conflict with IMAGE 1. That match is noted, not relied on.) Details that exist
only in IMAGE 2 are **not** adopted as topology. These include the exterior struts or docking arms,
the gap between the L4/L6 and L5/L7 columns drawn as a structural channel, and the
wall-mounted screens.

---

## 3. Master floor plan (schematic)

Schematic and not to scale; exact positions are in §4–§9. The radial rooms R1–R6 are drawn
upright at their clock positions; in the sketch they are rotated to face the hub (§5).

```
                      +--------+ +--------+ +--------+                              +------+  +------+
                      |        | |        | |        |                              | R1   |  | R2   |
                      |   L1   | |   L2   | |   L3   |            ooooooooo         |      |  |      |
                      |        | |        | |        |          ooo       ooo       +----D-+  +--D---+
       ooooooo   =====+---DD---+=+---DD---+=+---DD---+======  ooo           ooo          D ooooooDoo     +-------+
    ooo       ooD............. COR-N (upper corridor) ......Doo               oo         Doo       ooo   |       |
   oo           o=========+---DD---+=+---DD---+=============oo                 oo      ooo           ooo |  R3   |
  oo             oo       |        | |        |            oo                   oo    oo               oDD       |
 oo               oo      |        | |        |            o                     o   oo                 o|       |
 o                 o      |   L4   | |   L5   |           oo                     oo  o                   +-------+
o                   o     |        | |        |           o                       o oo                   oo
o                   o     |        | |        |           o                       oDo                     o+-------+
o     LABO          o     +--------+ +--------+           o      COMMAND          oDo      HABITAT        o|       |
o    (H-LAB)        o     |        | |        |           o      (H-CMD)          o o      (H-HAB)        DD  R4   |
o                   o     |        | |        |           o                       o oo                   oo|       |
 o                 o      |   L6   | |   L7   |           oo                     oo  o                   o +-------+
 oo               oo      |        | |        |            o                     o   oo                 oo
  oo             oo       |        | |        |            oo                   oo    oo               oo
   oo           o=========+---DD---+=+---DD---+=============oo                 oo      ooo           ooo
    ooo       ooD............. COR-S (lower corridor) ......Doo               oo         Doo       ooo
       ooooooo   =====+---DD---+=+---DD---+=+---DD---+======  ooo           ooo         D  ooooooooD
                      |        | |        | |        |          ooo       ooo      +----D--+   +---D---+
                      |   L8   | |   L9   | |   L10  |            ooooooooo        |  R6   |   |  R5   |
                      |        | |        | |        |                             |       |   |       |
                      +--------+ +--------+ +--------+                             +-------+   +-------+
```

| Symbol | Meaning |
|---|---|
| `o` | Hub wall (circle) |
| `+ - \|` | Room wall |
| `=` | Corridor wall |
| `.` | Corridor floor |
| `D` | Door (red marker in the sketch) |

---

## 4. Room slots (provisional numbering)

| Slot | ID | Kind | Sketch extent (px) | Door | Opens to | Function |
|---|---|---|---|---|---|---|
| 1 | `H-LAB` | circular hub | centre (280, 689), r ≈ 182 | `DR-N-LAB`, `DR-S-LAB` | `COR-N`, `COR-S` | Lab / Research (owner) |
| 2 | `H-CMD` | circular hub | centre (975, 692), r ≈ 224 | `DR-N-CMD`, `DR-S-CMD`, `DR-CMD-HAB` | `COR-N`, `COR-S`, `H-HAB` | Main Command / Central Operations (owner) |
| 3 | `H-HAB` | circular hub | centre (1377, 692), r ≈ 180 | `DR-CMD-HAB`, `DR-R1`…`DR-R6` | `H-CMD`, R1–R6 | Habitat / café / relax / games / plants / billiards / rest (owner) |
| 4 | `L1` | room | x 420–533, y 345–522 | `DR-L1` | `COR-N` | unassigned |
| 5 | `L2` | room | x 550–664, y 343–520 | `DR-L2` | `COR-N` | unassigned |
| 6 | `L3` | room | x 689–803, y 341–518 | `DR-L3` | `COR-N` | unassigned |
| 7 | `L4` | room | x 489–603, y 588–694 | `DR-L4` | `COR-N` | unassigned |
| 8 | `L5` | room | x 620–734, y 588–694 | `DR-L5` | `COR-N` | unassigned |
| 9 | `L6` | room | x 489–603, y 697–788 | `DR-L6` | `COR-S` | unassigned |
| 10 | `L7` | room | x 620–734, y 697–788 | `DR-L7` | `COR-S` | unassigned |
| 11 | `L8` | room | x 428–541, y 832–1009 | `DR-L8` | `COR-S` | unassigned |
| 12 | `L9` | room | x 557–671, y 833–1010 | `DR-L9` | `COR-S` | unassigned |
| 13 | `L10` | room | x 690–805, y 836–1015 | `DR-L10` | `COR-S` | unassigned |
| 14 | `R1` | radial room | bbox x 1144–1322, y 351–558; about 11 o'clock | `DR-R1` | `H-HAB` | unassigned |
| 15 | `R2` | radial room | bbox x 1355–1487, y 333–521; about 12–1 o'clock | `DR-R2` | `H-HAB` | unassigned |
| 16 | `R3` | radial room | bbox x 1504–1714, y 456–641; about 2 o'clock | `DR-R3` | `H-HAB` | unassigned |
| 17 | `R4` | radial room | about x 1545–1736, y 665–800; about 3 o'clock | `DR-R4` | `H-HAB` | unassigned |
| 18 | `R5` | radial room | bbox x 1387–1557, y 835–1041; about 5 o'clock | `DR-R5` | `H-HAB` | unassigned |
| 19 | `R6` | radial room | bbox x 1156–1335, y 815–1024; about 7 o'clock | `DR-R6` | `H-HAB` | unassigned |

The owner's labels (LABO, L1–L10, R1–R6) are kept as IDs. The `H-` prefix is added only to the
hubs, which are unlabelled or labelled `LABO` in the sketch.

## 5. Geometry notes

- L1–L3 and L8–L10 are **tall** rooms (about 114 × 177 px); L4–L7 are **short** (about 114 × 92–106 px).
  All ten are the same width.
- R1–R6 are about 115 × 185 px rectangles. Each stands on the Habitat hub's rim, with its long axis
  pointing out from the hub centre. Their door bearings, measured from the hub centre (0° = right,
  clockwise positive), are:

  | Room | Door bearing |
  |---|---|
  | R1 | −124° |
  | R2 | −81° |
  | R3 | −36° |
  | R4 | +8° |
  | R5 | +71° |
  | R6 | +122° |

- The central hub is the largest shape (diameter ≈ 448 px). LABO and the Habitat are about 360 px.
- The central hub and the Habitat hub **touch**; their shared door is at the contact point.

---

## 6. Doors (21)

Every door is a red marker in IMAGE 1. No other door exists.

| # | Door | Centre (px) | Joins | Wall |
|---|---|---|---|---|
| 1 | `DR-L1` | (473, 525) | L1 ↔ `COR-N` | L1 south / corridor north |
| 2 | `DR-L2` | (604, 526) | L2 ↔ `COR-N` | L2 south / corridor north |
| 3 | `DR-L3` | (737, 524) | L3 ↔ `COR-N` | L3 south / corridor north |
| 4 | `DR-L4` | (548, 587) | L4 ↔ `COR-N` | L4 north / corridor south |
| 5 | `DR-L5` | (678, 586) | L5 ↔ `COR-N` | L5 north / corridor south |
| 6 | `DR-L6` | (542, 783) | L6 ↔ `COR-S` | L6 south / corridor north |
| 7 | `DR-L7` | (682, 786) | L7 ↔ `COR-S` | L7 south / corridor north |
| 8 | `DR-L8` | (480, 834) | L8 ↔ `COR-S` | L8 north / corridor south |
| 9 | `DR-L9` | (612, 834) | L9 ↔ `COR-S` | L9 north / corridor south |
| 10 | `DR-L10` | (741, 833) | L10 ↔ `COR-S` | L10 north / corridor south |
| 11 | `DR-N-LAB` | (388, 563) | `COR-N` west end ↔ `H-LAB` | corridor end / hub rim |
| 12 | `DR-N-CMD` | (801, 566) | `COR-N` east end ↔ `H-CMD` | corridor end / hub rim |
| 13 | `DR-S-LAB` | (383, 809) | `COR-S` west end ↔ `H-LAB` | corridor end / hub rim |
| 14 | `DR-S-CMD` | (817, 805) | `COR-S` east end ↔ `H-CMD` | corridor end / hub rim |
| 15 | `DR-CMD-HAB` | (1194, 692) | `H-CMD` ↔ `H-HAB` | contact point of the two hub rims |
| 16 | `DR-R1` | (1274, 538) | R1 ↔ `H-HAB` | R1 inner end / hub rim |
| 17 | `DR-R2` | (1403, 522) | R2 ↔ `H-HAB` | R2 inner end / hub rim |
| 18 | `DR-R3` | (1525, 586) | R3 ↔ `H-HAB` | R3 inner end / hub rim |
| 19 | `DR-R4` | (1558, 718) | R4 ↔ `H-HAB` | R4 inner end / hub rim |
| 20 | `DR-R5` | (1433, 850) | R5 ↔ `H-HAB` | R5 inner end / hub rim |
| 21 | `DR-R6` | (1286, 840) | R6 ↔ `H-HAB` | R6 inner end / hub rim |

Door counts per space:
- `COR-N` 7 and `COR-S` 7;
- `H-HAB` 7, `H-CMD` 3, `H-LAB` 2;
- every L and R room exactly 1.

The markers are about 24 × 31 px, roughly the same size everywhere (door width: **2 tiles** for V1, owner decision Q9).

## 7. Corridors (2)

| ID | Sketch extent (px) | West end | East end | Doors on it |
|---|---|---|---|---|
| `COR-N` (upper) | x 367–823, y 538–585 (about 456 × 47) | enters the LABO rim, marker `DR-N-LAB` | enters the central-hub rim, marker `DR-N-CMD` | L1, L2, L3 (north); L4, L5 (south) |
| `COR-S` (lower) | x 371–829, y 790–828 (about 458 × 38) | enters the LABO rim, marker `DR-S-LAB` | enters the central-hub rim, marker `DR-S-CMD` | L6, L7 (north); L8, L9, L10 (south) |

The lower corridor is drawn a little narrower (38 px against 47 px). By owner decision (Q8) **both
corridors have the same width**; the difference is a drawing tolerance.

## 8. Closed walls and corridor ends

**Closed walls:** every wall without a red marker is closed. In particular:

| Wall | Status |
|---|---|
| L1 \| L2, L2 \| L3, L8 \| L9, L9 \| L10 | Separate rooms; the gap between them (about 15–25 px) is **non-walkable hull / structure** (Q4); no door |
| L4 \| L5, L6 \| L7 | Separate columns; the gap (x 604–619) is **non-walkable hull / structure** (Q4); no door |
| L4 / L6, L5 / L7 | **Shared wall** (the line at y ≈ 695); no door |
| L-block ↔ LABO (x 462–488) and L-block ↔ central hub (x 735–753) | Gap; no contact, no door |
| L10's north-east corner ↔ central-hub rim | **Closed wall contact** (owner decision Q3); no door, no passage |
| Corridor side walls | Closed except the ten room doors |
| LABO rim | Closed except `DR-N-LAB`, `DR-S-LAB` |
| Central-hub rim | Closed except `DR-N-CMD`, `DR-S-CMD`, `DR-CMD-HAB` |
| Habitat rim | Closed except `DR-CMD-HAB` and `DR-R1`…`DR-R6` |
| R rooms | Closed except their one inner door; no door between R rooms, and none to the central hub. The gaps between R rooms are non-walkable hull / structure (Q4) |
| LABO ↔ central hub | No direct connection (the L complex lies between them) |
| Outer hull | No exterior door, hatch or dock anywhere |

**Corridor ends:** there are **no sealed corridor ends**. Each of the four corridor ends meets a
hub through a doorway (owner-confirmed): `COR-N` west → LABO (`DR-N-LAB`), `COR-N` east → Main
Command (`DR-N-CMD`), `COR-S` west → LABO (`DR-S-LAB`), `COR-S` east → Main Command (`DR-S-CMD`).
The earlier sealed-end rule applied to the superseded layout and no longer applies.

## 9. Hub connections

| Connection | Evidence | Status |
|---|---|---|
| `H-CMD` ↔ `H-HAB` (`DR-CMD-HAB`) | Red marker at the contact of the two rims | **Confirmed** (IMAGE 1 + owner) |
| `H-HAB` ↔ R1…R6 (6 doors) | Red marker on each room's inner end | **Confirmed** (IMAGE 1 + owner) |
| `H-LAB` ↔ `COR-N` (`DR-N-LAB`) | Red marker at the corridor end, inside the LABO outline | **Confirmed** (IMAGE 1 + owner) |
| `H-LAB` ↔ `COR-S` (`DR-S-LAB`) | Same | **Confirmed** (IMAGE 1 + owner) |
| `H-CMD` ↔ `COR-N` (`DR-N-CMD`) | Same | **Confirmed** (IMAGE 1 + owner) |
| `H-CMD` ↔ `COR-S` (`DR-S-CMD`) | Same | **Confirmed** (IMAGE 1 + owner) |
| `H-LAB` ↔ `H-CMD` directly | Not drawn | **None** |
| Any hub ↔ exterior | Not drawn | **None** |

With all 21 doors, every space is reachable: 19 slots plus 2 corridors in one
connected graph (verified).

## 10. Unresolved geometry points

**None.** Every question (Q1–Q11) has an owner decision (§14). The only item intentionally left open is
the exact tile scale, which the owner has chosen not to freeze yet (Q8): proportions stay close to
the sketch.

### 10.1 Navigation representation (from Q5, Q8, Q9)

The simplest deterministic grid that keeps the approved geometry:

1. **One flat tile grid** for the whole vessel (no decks, no lifts).
2. **Rasterise by tile centre:** a tile is floor of a space when its centre lies inside that space's
   sketch shape (circle, rectangle, or the rotated rectangle of an R room), after scaling. Ties go
   to no space, so a tile is never shared.
3. **Art and walk are separate:** R1–R6 stay visually rotated and radial, and the hub rims stay
   round. Only the walkable tiles are stepped.
4. **Doors are the only crossings:** each of the 21 doors becomes a 2-tile opening on the shared
   boundary, centred on its sketch marker. No other tile pair between two spaces is steppable (no
   automatic doors).
5. **Everything else is solid:** room gaps, the L10 corner contact, and the space around the hubs
   are non-walkable.
6. **Corridors:** `COR-N` and `COR-S` get the same width.
7. **Acceptance checks when the grid is generated:**
   - each L and R room has exactly one 2-tile door, on its approved wall;
   - the hubs have exactly their approved doors (LABO 2, Main Command 3, Habitat 7);
   - no two rooms are connected;
   - every walkable tile is reachable;
   - a flood fill from any room crosses only the approved doors.

## 11. Room count

| Group | Count |
|---|---|
| Circular hubs | 3 |
| L rooms | 10 |
| R rooms | 6 |
| **Room slots** | **19** (geometry owner-confirmed; scale not frozen) |
| Corridors | 2 |
| Doors | 21 |
| Sealed corridor ends | 0 (owner-confirmed) |

The earlier counts (17, 18, and the 19 slots of revision B, which had a different make-up) do not
apply. The equal total of 19 is a coincidence.

---

## 12. Effect on the visual documents

Following owner approval of this revision, the Visual Foundation was **rebuilt on it (v2)**. These
documents now follow this floor plan and are current:

| Document | Status |
|---|---|
| `STELLAR_STATION_TOPOLOGY.md` | **v2**: the flat vessel, 21 doors, the access graph, logical access; provisional scale |
| `STELLAR_ROOM_REGISTRY.md` | **v2**: 19 slots, 11 active, 8 reserved; Risk = L10, Execution = L9, Coaching reserved = R1 |
| `STELLAR_ASSET_REGISTRY.md` | **v2**: lift and airlock types retired; hub-rim doors, corridor junctions and structural infill added |
| `STELLAR_CHARACTER_REGISTRY.md` | **v2**: characters re-homed; logical movement classes; specialist family desks with an interim adapter |
| `STELLAR_SCREEN_REGISTRY.md` | **v2**: displays re-homed; truthful-data rules and producer audit kept |
| `STELLAR_VISUAL_WORLD_PLAN.md` | Updated to point to this floor plan as the topology source of truth; deck, lift, airlock and automatic-door text replaced |
| This file, revisions A and B | Superseded by this revision |

The v1 registries (stacked decks, lifts, vault airlock) are void.

## 13. Things this revision does not do

- It assigns no room function beyond the three hubs.
- It places no furniture, consoles, screens or characters.
- It does not set the tile scale or the final proportions.
- It does not change the owner's layout to make navigation easier.

## 14. Owner decisions (all questions resolved)

| # | Owner decision | Open |
|---|---|---|
| ~~Q1~~ | ~~Corridor-end markers: doors or sealed hull?~~ **Resolved by the owner: doors.** | — |
| ~~Q2~~ | **Resolved by the owner:** LABO connects only to the two corridors; there is no direct LABO ↔ Main Command or LABO ↔ Habitat link | — |
| ~~Q3~~ | **Owner:** L10 touching the Main Command rim is a **closed wall contact**; no door, no passage | — |
| ~~Q4~~ | **Owner:** the gaps between the small rooms are **non-walkable hull / structural space**, not corridors or hidden passages | — |
| ~~Q5~~ | **Owner:** R1–R6 stay visually rotated / radial; navigation uses the simplest deterministic grid that keeps the approved entrances and walkable geometry (§10.1) | — |
| ~~Q6~~ | **Resolved by the owner:** R1–R6 each have one doorway into the Habitat; R6 is a normal room | — |
| ~~Q7~~ | **Resolved by the owner:** the central hub is MAIN COMMAND | — |
| ~~Q8~~ | **Owner:** upper and lower corridors have the **same width**; proportions stay close to the sketch; exact scale **not yet frozen** | — |
| ~~Q9~~ | **Owner:** door width = **2 tiles** for V1 | — |
| ~~Q10~~ | **Owner:** the old secure lift and isolated Risk geometry are **not recreated**; risk isolation comes later through room assignment and access-control rules | — |
| ~~Q11~~ | **Owner:** the four corridor-end hub doors are **ordinary doors**, not airlocks | — |
