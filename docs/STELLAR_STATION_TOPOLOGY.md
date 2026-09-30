# Stellar Station Topology — v2 (flat vessel)

| | |
|---|---|
| **Status** | v2.0, Visual Foundation rebuilt on the owner-approved floor plan. Documentation only: no renderer, no art |
| **Physical source of truth** | `STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C** (owner sketch, all geometry questions resolved) |
| **Mechanics source** | `STELLAR_STARNET_VISUAL_ADAPTATION.md` (matrix rows A1–A34) |
| **Replaces** | v1 of this file (five stacked decks, a central lift and a secure decision lift). v1 was never committed, and **all of its geometry is void** |
| **Companion files** | `STELLAR_ROOM_REGISTRY.md`, `STELLAR_ASSET_REGISTRY.md`, `STELLAR_CHARACTER_REGISTRY.md`, `STELLAR_SCREEN_REGISTRY.md` |

This file keeps three kinds of statement strictly apart. Every section is tagged with one of them.

| Tag | Meaning | Can change without owner approval? |
|---|---|---|
| **[APPROVED]** | Geometry from the owner-approved floor plan: spaces, doors, contacts, connectivity | **No** |
| **[PROVISIONAL]** | Scale and grid values that the owner has deliberately left open | Yes, within the approved geometry |
| **[FUTURE]** | Reserved functionality, not built and not rendered | Only by assigning it later |

---

## 1. ID conventions (carried over from v1)

| Kind | Pattern | Example |
|---|---|---|
| Hub | `H-<CODE>` | `H-CMD` |
| Small room | the owner's label | `L7`, `R3` |
| Corridor | `COR-<N/S>` | `COR-S` |
| Door | `DR-<room>` for small-room doors; `DR-<corridor>-<hub>` for corridor-end doors; `DR-CMD-HAB` | `DR-L10`, `DR-N-LAB` |
| Anchor | `<namespace>.<name>` (namespaces in the Room Registry) | `risk.intake` |
| Asset type / character / display | `<CAT>-NNN` / `CHR-NNN` / `DSP-<code>-NN` | `CON-013`, `CHR-037`, `DSP-RSK-02` |

IDs are never reused for a different thing. Retired IDs stay listed as RETIRED.

---

## 2. The vessel [APPROVED]

- **One flat, horizontal vessel** on one level. There are **no decks, no lifts, no stairs, no
  shafts**, and no exterior access.
- From left to right:
  - **`H-LAB`**, a circular hub;
  - the **left complex**: two parallel corridors `COR-N` and `COR-S` with ten small rooms, L1–L10;
  - **`H-CMD`**, the largest circular hub;
  - **`H-HAB`**, a circular hub that touches `H-CMD`, with six radial rooms R1–R6 around it.

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

The schematic is not to scale. R1–R6 are drawn upright here; in the vessel they are **rotated
radially** around `H-HAB` (owner decision Q5).

### 2.1 Spaces (21: 19 room slots + 2 corridors)

| Space | Kind | Sketch reference | Doors | Degree |
|---|---|---|---|---|
| `H-LAB` | circular hub | Floor Plan §4, slot 1 | `DR-N-LAB`, `DR-S-LAB` | 2 |
| `H-CMD` | circular hub (largest) | slot 2 | `DR-N-CMD`, `DR-S-CMD`, `DR-CMD-HAB` | 3 |
| `H-HAB` | circular hub | slot 3 | `DR-CMD-HAB`, `DR-R1`…`DR-R6` | 7 |
| `COR-N` | corridor (upper) | §7 | `DR-N-LAB`, `DR-L1`…`DR-L5`, `DR-N-CMD` | 7 |
| `COR-S` | corridor (lower) | §7 | `DR-S-LAB`, `DR-L6`…`DR-L10`, `DR-S-CMD` | 7 |
| L1, L2, L3 | tall rooms north of `COR-N` | slots 4–6 | one each | 1 |
| L4, L5 | short rooms south of `COR-N` | slots 7–8 | one each | 1 |
| L6, L7 | short rooms north of `COR-S` | slots 9–10 | one each | 1 |
| L8, L9, L10 | tall rooms south of `COR-S` | slots 11–13 | one each | 1 |
| R1–R6 | radial rooms on the `H-HAB` rim | slots 14–19 | one each | 1 |

---

## 3. Doors (21) [APPROVED]

Every door is an **ordinary 2-tile sliding door** (owner decisions Q9, Q11). There are no airlocks,
hatches, lifts or one-way doors. A door being restricted is an **access rule** (§9), never a
property of the geometry.

| # | Door | Joins | Position (Floor Plan §6) | Door asset |
|---|---|---|---|---|
| 1 | `DR-L1` | L1 ↔ `COR-N` | L1 south wall | `DOR-001` |
| 2 | `DR-L2` | L2 ↔ `COR-N` | L2 south wall | `DOR-001` |
| 3 | `DR-L3` | L3 ↔ `COR-N` | L3 south wall | `DOR-001` |
| 4 | `DR-L4` | L4 ↔ `COR-N` | L4 north wall | `DOR-001` |
| 5 | `DR-L5` | L5 ↔ `COR-N` | L5 north wall | `DOR-001` |
| 6 | `DR-L6` | L6 ↔ `COR-S` | L6 south wall | `DOR-001` |
| 7 | `DR-L7` | L7 ↔ `COR-S` | L7 south wall | `DOR-001` |
| 8 | `DR-L8` | L8 ↔ `COR-S` | L8 north wall | `DOR-001` |
| 9 | `DR-L9` | L9 ↔ `COR-S` | L9 north wall | `DOR-008` (restricted variant; same geometry) |
| 10 | `DR-L10` | L10 ↔ `COR-S` | L10 north wall | `DOR-008` (restricted variant; same geometry) |
| 11 | `DR-N-LAB` | `COR-N` west end ↔ `H-LAB` | on the `H-LAB` rim | `DOR-009` |
| 12 | `DR-N-CMD` | `COR-N` east end ↔ `H-CMD` | on the `H-CMD` rim | `DOR-009` |
| 13 | `DR-S-LAB` | `COR-S` west end ↔ `H-LAB` | on the `H-LAB` rim | `DOR-009` |
| 14 | `DR-S-CMD` | `COR-S` east end ↔ `H-CMD` | on the `H-CMD` rim | `DOR-009` |
| 15 | `DR-CMD-HAB` | `H-CMD` ↔ `H-HAB` | contact point of the two rims | `DOR-009` |
| 16–21 | `DR-R1`…`DR-R6` | R`n` ↔ `H-HAB` | each room's inner end, on the `H-HAB` rim | `DOR-009` |

**Door asset split:** `DOR-001` × 8 (straight walls) · `DOR-008` × 2 (straight walls, restricted
marking) · `DOR-009` × 11 (curved hub rims). Total: **21**.

---

## 4. Corridor adjacency [APPROVED]

The order along each corridor, west to east, by door centre:

| `COR-N` (upper) | `COR-S` (lower) |
|---|---|
| west end: `DR-N-LAB` → `H-LAB` | west end: `DR-S-LAB` → `H-LAB` |
| `DR-L1` (north side) | `DR-L8` (south side) |
| `DR-L4` (south side) | `DR-L6` (north side) |
| `DR-L2` (north side) | `DR-L9` (south side) |
| `DR-L5` (south side) | `DR-L7` (north side) |
| `DR-L3` (north side) | `DR-L10` (south side) |
| east end: `DR-N-CMD` → `H-CMD` | east end: `DR-S-CMD` → `H-CMD` |

- Both corridors have the **same width** (owner decision Q8).
- Neither corridor has a sealed end. Both ends of each corridor are doors into a hub.
- The two corridors **never meet** except through `H-LAB` or `H-CMD`.

## 5. Hub connections [APPROVED]

| Connection | Door |
|---|---|
| `H-LAB` ↔ `COR-N` | `DR-N-LAB` |
| `H-LAB` ↔ `COR-S` | `DR-S-LAB` |
| `H-CMD` ↔ `COR-N` | `DR-N-CMD` |
| `H-CMD` ↔ `COR-S` | `DR-S-CMD` |
| `H-CMD` ↔ `H-HAB` | `DR-CMD-HAB` |
| `H-HAB` ↔ R1…R6 | `DR-R1`…`DR-R6` |
| `H-LAB` ↔ `H-CMD` directly | **none** |
| `H-LAB` ↔ `H-HAB` | **none** |
| any hub ↔ exterior | **none** |

---

## 6. Physical access graph [APPROVED]

Nodes are spaces; edges are doors. There are **21 nodes and 21 edges**.

```
                 L1   L2   L3                          R1  R2  R3
                  \    |    /                             \  |  /
H-LAB ──DR-N-LAB── COR-N ──DR-N-CMD── H-CMD ──DR-CMD-HAB── H-HAB ── R4
  │               /    \                │                    /  \
  │             L4      L5              │                  R6    R5
  │                                     │
  └───DR-S-LAB── COR-S ──DR-S-CMD───────┘
                / | | | \
             L6 L7 L8 L9 L10
```

Adjacency list (complete):

| Node | Neighbours |
|---|---|
| `H-LAB` | `COR-N`, `COR-S` |
| `COR-N` | `H-LAB`, L1, L2, L3, L4, L5, `H-CMD` |
| `COR-S` | `H-LAB`, L6, L7, L8, L9, L10, `H-CMD` |
| `H-CMD` | `COR-N`, `COR-S`, `H-HAB` |
| `H-HAB` | `H-CMD`, R1, R2, R3, R4, R5, R6 |
| each of L1–L5 | `COR-N` only |
| each of L6–L10 | `COR-S` only |
| each of R1–R6 | `H-HAB` only |

**Verified properties** (graph check, scratch script):
- The graph is **connected**: every space is reachable from every other.
- **16 leaves:** every small room is a dead end with exactly one door.
- **Articulation spaces:**
  - `H-CMD` is the **only route** between the west side (`H-LAB`, corridors, L rooms) and the Habitat side;
  - `H-HAB` is the only route to R1–R6;
  - each corridor is the only route to its five rooms.
- `H-LAB` is **not** an articulation space: the two corridors give two independent LAB ↔ CMD routes.
- **Door crossings on the shortest route:**

  | Route | Door crossings |
  |---|---|
  | `H-LAB` → `H-CMD` | 2 |
  | L10 → `H-CMD` | 2 |
  | L9 → L10 | 2 |
  | `H-LAB` → `H-HAB` | 3 |
  | L1 → `H-HAB` | 3 |
  | L1 → L10 | 4 |

**Consequence for layout:** all traffic between the west side and the Habitat crosses `H-CMD`.
`H-CMD` therefore needs a clear **through-walkway** from its three doors that avoids the command
table and the restricted anchors (Room Registry §3.2).

---

## 7. Closed contacts and non-walkable space [APPROVED]

| Contact / area | Rule |
|---|---|
| L4 / L6 and L5 / L7 (shared walls across the block centre line) | Solid wall, no opening |
| Gaps between L1 \| L2 \| L3, L4 \| L5, L6 \| L7, L8 \| L9 \| L10, and between R rooms | **Non-walkable hull / structure** (Q4). Not corridors, not passages |
| Space between the L-block and `H-LAB`, and between the L-block and `H-CMD` | Non-walkable hull / structure |
| L10 north-east corner touching the `H-CMD` rim | **Closed wall contact** (Q3): no door, no passage |
| R rooms and `H-CMD` | No contact, no door |
| Hub rims | Closed except their listed doors |
| Outer hull | Closed everywhere |

**No hidden connections:** no step between two spaces exists except through the 21 doors of §3.
Navigation enforces this: there are no automatic doors (StarNet adaptation A2).

---

## 8. Scale and navigation grid [PROVISIONAL]

The owner has deliberately **not frozen the tile scale** (Q8). Only these are fixed:

| Fixed | Value |
|---|---|
| Door width | **2 tiles** (Q9) |
| Corridor widths | **equal** for `COR-N` and `COR-S` (Q8) |
| Proportions | close to the owner sketch |

**Working proposal (not frozen):** 1 tile ≈ 16 sketch px.

| Space | Approximate size at the proposed scale |
|---|---|
| Tall L room | about 7 × 11 tiles |
| Short L room | about 7 × 6 tiles |
| R room | about 7 × 11 tiles |
| Corridor | about 3 tiles wide, about 29 tiles long |
| `H-LAB` / `H-HAB` | about 22 tiles across |
| `H-CMD` | about 28 tiles across |

**Grid representation:** the rules of Floor Plan §10.1 (owner decision Q5).
- One flat tile grid.
- Rasterise by tile centre.
- The drawn shape (round rims, rotated R rooms) is kept separate from the stepped walk tiles.
- The 21 doors are the only crossings.
- Everything else is solid.

**StarNet mechanics applied here** (adaptation matrix):

| Row | Mechanic |
|---|---|
| A1 | Rect-union / raster room model on one grid |
| A2 | Explicit door list, with StarNet's automatic doors switched off |
| A4 | Art shape kept separate from walk shape |
| A5 | Indexed tile → space lookup |
| A6 | BFS + string-pulling pathfinding that never crosses a wall except at a door |
| A8 | Traffic, soft separation, and a containment backstop |

The isometric view is a **render projection only**; no path or rule uses screen coordinates.

**Grid acceptance checks** (run when the grid is generated; they must all pass before any art is placed):
1. There are exactly 21 door openings, each 2 tiles wide, each on its approved wall.
2. L1–L10 and R1–R6 have exactly one door each. The hubs have exactly 2 / 3 / 7 doors
   (LAB / CMD / HAB). Each corridor has exactly 7.
3. A flood fill from any space crosses only listed doors. No two small rooms are connected.
4. Every walkable tile is reachable, and no tile belongs to two spaces.
5. The Q3 and Q4 contacts are solid.
6. An independent-oracle test (A26) samples every smoothed path segment against `walkable`.

---

## 9. Logical access layer (separate from geometry)

The doors are physically ordinary. **Access is logical** (owner decision Q10): it is enforced in
navigation as a per-character room permission and anchor reservation, and shown visually with
static markings (`SGN-006`, `DOR-008`). It never changes the geometry.

| Access class of a space | Spaces | Rule |
|---|---|---|
| **Public** | `COR-N`, `COR-S`, the public zones of the three hubs, and the active rooms not listed below | Any rendered character with a reason to be there |
| **Restricted** | L10 (Risk Control Room), L9 (Execution Bay) | Only the movement classes the Character Registry §3 allows; restricted anchors are reserved per role |
| **Restricted anchors in public spaces** | For example the command chair and the trader console in `H-CMD` | Reserved for their role; others path around them |
| **Reserved** | L5, L8, R1–R6 (Room Registry §2) | No character enters in V1; the door shows a static "RESERVED" plate |

The access graph of §6 is the same for everyone. Permissions only **remove** destinations for a
given character; they never add an edge.

---

## 10. Future reserved functionality [FUTURE]

| Item | Where | Status |
|---|---|---|
| Research Lab experiment bench (explorer and validator roles) | `H-LAB` zone `lab.experiment_bench`; expansion room L5 | FUTURE_RESEARCH, not rendered |
| Performance & Wellbeing / Coaching Room | R1 | Designated reservation, not rendered |
| Future operations expansion | L8 | FUTURE_OPERATIONS |
| Future agent teams | R2–R6 | FUTURE_AGENT_TEAM |
| MT5 / demo execution (E2) | none (would share the Execution Bay) | Deferred by the owner; not rendered |

Reserved rooms keep their doors and walls exactly as approved. Filling one later assigns a function
to an existing slot; it never adds doors or rooms.

---

## 11. Removed from v1 (the old stacked-deck model)

- Five stacked decks and the per-deck 80 × 36 grids.
- The deck lobbies, spine corridors, and the deck-5 promenade.
- `LIFT-CENTRAL`, `LIFT-DECISION` and the lift graph.
- The Risk Vault reachable only by lift, its antechamber and blast door.
- The one-way airlock to the Execution Bay.
- The old 18-room list and its room codes (RSO, MNO, MAW, VLT, OBS, WEL, CAF, LNG, BIL, RST, QRL).
- All v1 coordinates, portals, and decisions ST-1 to ST-6.

The Visual World Plan now points to Floor Plan revision C as the topology source of truth. Its
deck, lift, airlock and automatic-door text in §3, §7 and §16 has been replaced.

## 12. Open decisions

| # | Decision | Default |
|---|---|---|
| TP-1 | Final tile scale (the owner left it open) | 1 tile ≈ 16 sketch px, working value |
| TP-2 | ~~Updating Visual World Plan §3, §7, §16~~ | **Done** (final consistency pass) |
| TP-3 | Layout file format (`stellar.vessel` v1, adaptation A25) | Decided when the grid is generated |
