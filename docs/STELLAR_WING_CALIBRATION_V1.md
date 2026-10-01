# Wing Calibration V1: department rooms, corridors and their doors

**Status:** in review.

**Baselines:** H-CMD V5.3 (`607e70d`) and H-LAB (`ff66010`).

**Scope:** one grouped pass with the Stellar Visual Vocabulary over:
- `L1`, `L2`, `L3`, `L4`, `L6`, `L7`, `L9`, `L10`;
- `COR-N`, `COR-S`;
- every door into them.

## 1. Grouping plan (multi-room phase)

| Pass | Rooms | Why grouped / separate |
|---|---|---|
| **This pass: wing** | L1–L4, L6, L7, L9, L10 + COR-N, COR-S + their 15 doors | Same rectangular construction: straight bulkhead walls, a tile deck, perimeter wall equipment, workstation families. The rooms share walls and doors with the corridors, so walls and doors must change together to stay coherent |
| Reserved shells | L5, L8 (and R1–R6) | Kept as dark sealed shells (registry: reserved, not rendered). Their doors become **closed** `SV.door` assemblies |
| Next: **H-HAB** (separate) | H-HAB | Large hub with a different visual logic (habitat, lounge, recovery, warm wood deck, windows, living wall). Needs its own composition pass |

## 2. What changed

**Unchanged:**
- geometry, topology, doors and anchors;
- displays (identities, placements, approved offline states);
- room functions and reserved zones;
- corridor rules (no corridor furniture beyond the approved repeaters);
- cameras.

**Walls:**
- Straight walls owned by these rooms and corridors are dark bulkheads with a lit crown.
- Each visible face uses the hub bay rhythm (rib every 4 tiles, three-face bays, cable trays) and a recessed lamp box on every other rib.
- **Upper layer:** a wall-hung monitor above a workstation, or a cabinet above wall equipment.
- No upper module is placed behind a registered wall display.
- Reserved-shell walls are unchanged.

**Doors:**
- Every door into the wing is **one** `SV.door` assembly spanning the full wall thickness (both frame records): 15 doors.
- Restricted styling (type C) only on `DR-L9` and `DR-L10`, which the layout already marks restricted.
- `DR-L5` and `DR-L8` (reserved) get a closed leaf.

**Floors:**
- Staggered `SV.floor` deck plates with beams, grilles and hatches, plus a service strip in front of wall equipment.
- `L10` keeps its `FLR-003` grating.
- **Corridors:** a central treadway with hazard edges, the CD-7 guide chevrons, and vents.
- Hero bands: hatched frames around the L2 chart table, L3 evidence stage, L4 reactor column and L9 launch deck (`FLR-008`); the L10 risk-core line becomes a hazard band.

**Furniture (registered assets, built with the vocabulary):**

| Room | Approved items → construction | Perimeter rhythm (new, decorative, no anchors) |
|---|---|---|
| L1 | `CON-009` × 3 → WS-standard; **`SEA-002` × 3 (mandatory, previously missing)** | bays, cabinets, racks |
| L2 | `CON-002` × 6 → WS-compact; `TBL-002` → **TBL-chart** (rectangular tactical table); `CON-010` → pedestal | racks, cabinets |
| L3 | `CON-011` × 5 → **EQ-podium**; `TBL-007` → **TBL-stage**; `CON-023` → WS-compact lectern; `SEA-003` → operator chair | cabinets, racks (debate floor kept clear) |
| L4 | `EQP-001` → **EQ-reactor** (constant light; the registered pulse stays event-driven); `CON-018` → WS-heavy; `CON-027` → WS-compact; `SRV-001/002` → EQ-rack | dense racks, a bay, a cabinet |
| L6 | `CON-019` → WS-compact; `STO-004` → EQ-rack (archive); `TBL-005` → **TBL-work** | lockers, bays |
| L7 | `CON-020` → WS-compact; `TBL-005` → TBL-work | bays, cabinets, racks |
| L9 | `CON-016/017` → WS-standard; `EQP-002` → **EQ-tube**; `EQP-003` → 3-bay readout bank | lockers, a cabinet (launch deck kept clear) |
| L10 | `CON-012/029` → WS-compact; `CON-001/013/014` → WS-standard; `CON-015` → steel breaker cabinet | lockers, cabinets, racks |

**Perimeter placement rules** (enforced in `geometry.py`):
- only wall-adjacent tiles;
- never within 2 tiles of a door lane;
- never on an anchor or its four neighbours, or directly south of an anchor;
- never on floor markings;
- never where blocking would cut off any walkable tile.

**Displays:** console displays render inside their workstation's housing. The breaker panel keeps its standing display.

**Light:**
- low room ambient;
- task pools at staffed anchors;
- cyan only at consoles with a live producer;
- amber at wall equipment;
- hero light at the chart table, stage, reactor and tube;
- corridor lamps;
- the L10 cold panel light is kept.

**New vocabulary entries:** `SV.table.chart`, `SV.table.stage`, `SV.table.work`, `SV.eq.reactor`, `SV.eq.podium`, `SV.eq.tube`. No new asset IDs.
