# Stellar Spatial Scale V1: geometry adaptation

**Status:** draft for owner review. Nothing here is committed yet.
**Scope:** physical dimensions only. The approved Floor Plan topology, room locations, doors, room purposes, anchors, furniture identities, characters and movement routes are **unchanged**.
**Preview:** [`preview/STELLAR_GEOMETRY_PREVIEW_V1.html`](preview/STELLAR_GEOMETRY_PREVIEW_V1.html). It is a self-contained page with a pan/zoom camera. It is a geometry preview, not final art.

## 1. Approved global scale

| Quantity | Value | StarNet reference (pinned `fbddbf99`, inspiration only) |
|---|---|---|
| Tile | **1 tile = 12 world units** (1 Stellar tile = 1 StarNet tile) | `worldmodel.js` `TILE = 12` |
| Floor Plan | **1 sketch px = 1 world unit** | — |
| Agent reference height | **19 units** (≈ 1.58 tiles) | standing sprite 19 px |
| Agent personal spacing | **0.8 tile** (9.6 units) | `PERSONAL_TILES = 0.8` |
| Corridor baseline | **3 tiles** (36 units) | — |
| Doors | **2 tiles** (24 units), unchanged | the 24 px door markers on the Floor Plan |
| Camera | default **2×**, range **0.5×–6×** | `world.js` scale 2, `MINZ 0.5`, `MAXZ 6` |

Sanity check: an agent of ≈ 1.75 m gives 1 tile ≈ 1.1 m. Tile coordinates are `col = floor(x / 12)` and `row = floor(y / 12)`. A tile belongs to a room when its **centre** lies inside the room's Floor Plan outline.

## 2. Rasterisation rules (no topology change)

1. **Hubs** are the tile discs of the approved circles: `H-LAB` (280, 689) r 182, `H-CMD` (975, 692) r 224, `H-HAB` (1377, 692) r 180.
2. **Rooms and corridors** are the tiles whose centres fall inside the approved rectangles. Where a corridor end runs into a hub circle, the hub keeps the tile. The corridor ends at the rim, as on the Floor Plan.
3. **Normalisation.** `COR-N` is drawn about 47 px (≈ 4 rows) tall and is normalised to the **3-tile baseline** (rows 45–47). Its south edge moves from y 585 to y 576. The freed row (48) becomes the wall band north of L4/L5. `COR-S` is already 3 rows (66–68).
4. **Walls are seams between tiles** (StarNet-style), not tiles. The 18–24 px gaps between some rooms and the corridors are wall thickness. A door across such a gap becomes a **2-tile-wide threshold** (a short walkable passage); otherwise the door is a seam opening.
5. **Doors** use the two tile lanes whose centres are nearest the approved door centre. Movement crosses a room boundary **only** through an open door. L5, L8 and R1–R6 are reserved: they are not walkable, and their doors are drawn sealed.
6. R1–R6 are drawn rotated and radial (Floor Plan Q5). They are not rasterised because they are reserved.

## 3. Key asset footprints (Stellar-adapted)

Footprints are in tiles (**along the wall × depth**). These are **Stellar sizes for Stellar furniture**. StarNet prop sizes were used only as a plausibility check (desk 2×1, holotable 4×2, rack 2×1, bench 4×1, couch 5×1). No StarNet art or prop is copied.

**Height classes** (used for camera occlusion):
- *Low:* the agent stays visible behind it.
- *Mid:* console height.
- *Tall:* hides an agent standing directly north of it.

| Asset | Room | Footprint | World units | Height | Why this size |
|---|---|---|---|---|---|
| `CON-002` technical console | L2 ×6 | **1×2** on the side wall | 12×24 | mid | One analyst per station. Wall-mounted, so the centre stays free for `TBL-002` |
| `TBL-002` holo chart table | L2 | **3×4**, long axis N–S | 36×48 | low | Spans the T3/T4 and T6/T7 consoles, as in the L2 schematic. Leaves a 1-tile aisle on each side |
| `CON-010` session-clock pedestal | L2 | 1×1 | 12×12 | mid | Pedestal |
| `CON-011` podium | L3 ×5 | 1×1 | 12×12 | mid | Standing podium. The agent stands behind it |
| `TBL-007` evidence stage | L3 | **3×3** | 36×36 | low | Low stage between the inner podiums (DC: no tiers) |
| `CON-023` review desk | L3 | 3×1 | 36×12 | low | Low review desk. `SEA-003` judge seat behind it |
| `CON-009` desks | L1 ×3 | FX **3×1**; metals and indices **1×2** | 36×12 / 12×24 | mid | The FX desk is the widest bay (two runtime agents behind one desk) |
| `EQP-001` snapshot column (+ `SCR-006`) | L4 | 1×1 | 12×12 | tall | Central column |
| `CON-018` validator | L4 | 2×1 | 24×12 | mid | South of the column, facing north |
| `SRV-001` / `SRV-002` racks | L4 | 1×2 each | 12×24 | tall | East wall |
| `CON-027` reconciliation console | L4 | 2×1 | 24×12 | mid | SW corner |
| `CON-019` / `CON-020` terminals | L6 / L7 | 1×2 | 12×24 | mid | West wall |
| `STO-004` record shelf | L6 | 1×3 | 12×36 | tall | East wall |
| `TBL-005` table | L6 / L7 | 2×1 | 24×12 | low | One reader |
| `CON-016` pre-flight console | L9 | 1×2 | 12×24 | mid | West wall by the entry |
| `CON-017` execution console | L9 | 1×2 | 12×24 | mid | E1 faces west, over the console, to the tube |
| `EQP-002` Dispatch Tube | L9 | 1×2 | 12×24 | tall | West wall |
| `EQP-003` docking board | L9 | 3×1 | 36×12 | mid | South wall |
| `CON-012` intake counter | L10 | 3×1 | 36×12 | mid | The courier drops on the door side |
| `CON-001` contradiction desk | L10 | 1×2 | 12×24 | mid | West wall |
| `CON-029` outbox | L10 | 1×2 | 12×24 | mid | East wall by the entry |
| `CON-015` breaker panel | L10 | 1×1 | 12×12 | mid | West wall |
| `CON-014` sizing console | L10 | 1×2 | 12×24 | mid | East wall |
| `CON-013` rule-checklist console | L10 | 3×1 | 36×12 | mid | South wall |
| `TBL-001` circular table | H-CMD | **disc, 5-tile diameter** (21 tiles) | ≈ 60 Ø | low | Six places: chair, head, n1, n2, s1, s2 |
| `FLR-002` dais | H-CMD | disc r ≈ 5.6 tiles | ≈ 134 Ø | floor | Walk-over |
| `CON-003` / `CON-004` / `CON-005` / `CON-022` | H-CMD | 3×1 each | 36×12 | mid | Rim consoles in the approved clock sectors |
| `SEA-005` waiting bench | H-CMD | 2×1 seat | 24×12 | seat | `command.bench_1` and `_2` |
| `CON-006` feed consoles | H-LAB ×6 | 1×2 | 12×24 | mid | West bank in two columns of three (R1–R3, R4–R6) |
| `CON-007` validation bench | H-LAB | 4×1 | 48×12 | mid | Four stations, V1–V4 |
| `CON-008` driver board | H-LAB | 3×1 | 36×12 | mid | 12 o'clock |
| `EQP-005` lab dome ring | H-LAB | 3×3 | 36×36 | low | Registry marks it blocking |
| `SCR-006` projector column (`DSP-LAB-05`) | H-LAB | 1×1 | 12×12 | mid | Registry: blocks 1 × 1; at the dome ring's east edge (added in the Visual Prototype V1 pass) |
| `PLT-003` desk plants | L1 | none (on the `CON-009` desks) | — | — | Registry: "on desks", no footprint (corrected in the Visual Prototype V1 pass; it was a floor tile) |
| `PLT-005` central tree | H-HAB | 3×3 | 36×36 | tall | Hub centre |
| `LEI-002` counter + `LEI-003` dispenser | H-HAB | 3×1 + 1×1 | 36×12 + 12×12 | mid | Café arc; the host stands behind the counter |
| `TBL-003` café tables + `SEA-007` | H-HAB | 1×1 table + two 1×1 seats, ×3 | — | low / seat | `cafe_seat_1`…`_6` |
| `LEI-001` billiards | H-HAB | **3×2**, plus a **1-tile clearance ring** (5×4 kept free) | 36×24 | low | Games arc |
| `STO-003` cue rack | H-HAB | 2×1 | 24×12 | tall | Rim, outside the clearance ring |
| `SEA-006` sofas, `TBL-004`, `LEI-004` rug | H-HAB | sofas 1×2 ×2; table 1×2; rug 5×3 (floor) | — | seat / low | `sofa_1`…`_4` |
| `SEA-009` window benches | H-HAB | 2×1 ×2 | 24×12 | seat | Outer south rim |
| `EQP-004` recovery pods | H-HAB | 1×2 ×3 | 12×24 | tall | Agent-occupied (real cooldown) |
| `LEI-005` rest pods | H-HAB | 1×1 ×3 | 12×12 | seat | Cosmetic |
| `CON-021` vitals | H-HAB | 1×1 | 12×12 | mid | Medic |

**Modelling conventions (please review):**
- **Seats and pods** (`SEA-*`, `EQP-004`, `LEI-005`) are tiles that one agent occupies. They are not walls; the anchor sits on the seat.
- `WAL-005` (L1 glass partition) is a wall seam with a 3-tile opening, not a tile.
- Wall displays (`DSP-*`), lights (`LGT-*`), the overhead `DEC-007` globe and floor finishes (`FLR-*`, `LEI-004`) have **no** floor footprint.
- The L10 "low divider" in the schematic has **no asset ID** in the Asset Registry. It is drawn as a floor marking only; no asset is invented.

## 4. Room dimensions at the approved scale

| Room | Tiles (W × D) | World units | Floor tiles | Free tiles | Door(s) | Two-agent passing share* | Longest single-file stretch on a door → anchor route |
|---|---|---|---|---|---|---|---|
| `L1` | 9 × 15 | 108 × 180 | 135 | 128 | DR-L1 (threshold 1) | 0.95 | 0 |
| `L2` | 9 × 14 | 108 × 168 | 126 | 101 | DR-L2 (threshold 2) | **0.83** (lowest) | **3** (to `station_t3`) |
| `L3` | 10 × 15 | 120 × 180 | 150 | 133 | DR-L3 (threshold 2) | 0.89 | 2 (to `podium_bear`) |
| `L4` | 9 × 9 | 108 × 108 | 81 | 72 | DR-L4 (threshold 1, north) | 0.89 | 1 |
| `L6` | 9 × 8 | 108 × 96 | 72 | 65 | DR-L6 (seam) | 0.95 | 0 |
| `L7` | 9 × 8 | 108 × 96 | 72 | 68 | DR-L7 (seam) | 0.97 | 0 |
| `L9` | 10 × 15 | 120 × 180 | 150 | 141 | DR-L9 (seam, north) | 0.97 | 0 |
| `L10` | 10 × 15 | 120 × 180 | 150 | 137 | DR-L10 (threshold 1, north) | 0.88 | 2 |
| `COR-N` | 38 × 3 | 456 × 36 | 97 | 97 | 7 room doors + 2 hub doors | 0.98 | — (31 of 34 columns are full width; the narrower columns are the hub-rim ends) |
| `COR-S` | 38 × 3 | 456 × 36 | 92 | 92 | 5 room doors + 2 hub doors | 0.98 | — (30 of 32 columns are full width) |
| `H-LAB` | ⌀ 30 | ⌀ 364 | 723 | 695 | DR-N-LAB, DR-S-LAB | 0.97 | 1 |
| `H-CMD` | ⌀ 37 | ⌀ 448 | 1094 | 1061 | DR-N-CMD, DR-S-CMD, DR-CMD-HAB | 0.99 | 1 |
| `H-HAB` | ⌀ 30 | ⌀ 360 | 707 | 680 | DR-CMD-HAB (+ R1–R6 sealed) | 0.95 | 2 |

\* **Passing share** is the share of free tiles that lie in a free 2×2 block. On such a tile two agents can pass side by side at a 1-tile spacing (≥ 0.8). An agent standing at a working anchor counts as an obstacle.

Room-local layouts (tile coordinates from each room's north-west tile) are listed in the preview data. They follow each approved room-sheet schematic: same walls, same order, same facing.

## 5. Checks run (all pass)

| Check | Result |
|---|---|
| Every footprint lies inside its room floor; no two blocking footprints overlap | pass |
| Every anchor is on a walkable tile inside its room, alone on its tile, and next to (or on) the furniture it serves | pass (88 anchors) |
| Every anchor is reachable from the station corridors (4-neighbour BFS that crosses rooms only through open doors) | pass |
| Every walkable tile is connected; reserved L5, L8 and R1–R6 are unreachable | pass |
| Door approach: 2 tiles deep on both sides of every open door have no furniture and no anchor | pass |
| H-HAB: the hub side of every reserved R-door (≤ 30 units) is clear (H-HAB sheet: nothing on any door approach) | pass |
| H-HAB billiards: the 1-tile clearance ring holds no other furniture | pass |
| Corridors: 3 tiles wide along their full length, except where the hub rims clip the ends | pass |
| Camera occlusion: no character's anchor sits directly north of a tall footprint | pass |

## 6. Rooms that cannot fit their approved contents

**None.** Every room holds all of its approved furniture and anchors at the 12-unit tile. Tight spots, reported honestly:

- **L2 (tightest).** At 9 tiles wide, each side has wall console, operator, then a **1-tile aisle** beside `TBL-002`. With operators at their consoles, the aisles are single file for up to 3 tiles. Passing still works:
  - an agent yields into the gaps between consoles (StarNet-style side-step, 1 tile ≥ 0.8 spacing);
  - the entry zone (rows 12–13) and the north strip (rows 0–1) are fully two-way.

  If the owner wants two-way side aisles, the only option that does not touch the Floor Plan is `TBL-002` at **2×4** instead of 3×4. Widening L2 would change the approved Floor Plan, so it is **not** proposed.
- **L3.** The bear-side route squeezes past the evidence stage (2 tiles). It is acceptable.
- **L10.** The breaker and sizing consoles sit beyond the `risk.core` line (2 tiles). It is acceptable.
- **Doors.** A 2-tile door is single-file under StarNet's mouth-lane rule. This matches the Corridor Design (CD) and needs no change.
- **Thresholds.** DR-L2 and DR-L3 have **2-tile-deep** thresholds (the Floor Plan's wall band between the room bottoms and `COR-N`). DR-L1, DR-L4 and DR-L10 have 1-tile thresholds. Their width (2) is unchanged.

## 7. Camera setup

| Setting | Value |
|---|---|
| Default zoom | **2×**: 1 tile = 24 px; agent = 38 px tall |
| Range | **0.5×–6×** (wheel zoom about the cursor; drag to pan) |
| At 2× on 1920 × 1080 | 960 × 540 world units visible (80 × 45 tiles). Every room fits on one screen; the largest, `H-CMD` (448 units), is 896 px |
| At 0.5× | the whole station (x 98–1736, y 333–1041 ≈ 1638 × 708 units) is ≈ 819 × 354 px: a full overview |
| Projection | top-down, sprites standing up from the StarNet-style foot point (x·12 + 6, y·12 + 11). In this top-down preview the camera-facing (south) walls are cut away per the Visual Bible C4. The isometric presentation camera is frozen as Iso · right, from the north-east (Visual Prototype V1 §0) |

## 8. Ready for the first station render

The following are ready:
- the station tile grid (3,881 tiles, including reserved rooms and door thresholds);
- walls as seams, 15 approved doors (13 open, 2 reserved) plus 6 sealed R-doors;
- 87 furniture footprints for the approved assets and 88 anchors (after the Visual Prototype V1 corrections: `SCR-006` added in H-LAB, `PLT-003` moved onto the L1 desks);
- **41 representative characters** at their Character Registry home anchors. Deferred, future and retired characters are not drawn.

Everything is source-checked against the approved Floor Plan and room sheets.

Not included, as instructed: final art, audio, chat, the owner avatar, events or live data. No StarNet art is used.

**Open points for the owner:**
1. The L2 `TBL-002` size: 3×4 (as drawn) or 2×4.
2. The modelling conventions in §3: seats as occupied tiles, `WAL-005` as a seam, and the L10 divider as a marking only.
3. Hub furniture positions inside the approved clock sectors (H-CMD, H-LAB, H-HAB) are first proposals.
4. Whether the generator script (Python; it rasterises the plan and runs the checks) should live in the repository. It is currently kept outside the repo.
