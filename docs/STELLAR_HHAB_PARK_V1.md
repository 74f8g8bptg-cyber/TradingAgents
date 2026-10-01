# H-HAB Enrichment V1: central park, fountain and resident dog

**Baseline:** H-HAB calibration V1 (`1879deb`) and the global audit (`d9cf015`).

**Scope:** one habitat world-building pass. No geometry, topology, door, anchor, display, function or circulation changes. All placements obey the H-HAB keep rules: anchors and their neighbours, R-door approaches, billiards clearance, door lanes, and full reachability of every walkable tile.

## 1. Central indoor park (`habitat.plants`)

| Element | Asset | Construction |
|---|---|---|
| Park ground and paths | `FLR-012` (new, walk-over) | Soft green ground in an oval around the central tree; gravel paths ringing the tree and the fountain, joining them, and opening north, south and east; lit path edges |
| Central tree (hero, approved) | `PLT-005` | Unchanged hexagonal planter |
| Fountain | `LEI-007` (new) | Octagonal basin on a bolted metal skirt with recessed lights; stone cap; water with a lit surface and ripple rings; two-tier stone column with a brass stem and falling water arcs. Decorative, no data |
| Park trees × 5 | `PLT-007` (new) | Stone ring, trunk, layered canopy |
| Garden beds × 6 | `PLT-006` (new) | Low stone-edged beds with ferns, grasses and a few flowers |
| Benches × 2 | `SEA-009` (existing) | Facing the fountain |
| Light | | Cyan and warm pools at the fountain; warm pools under the trees |

The park is about 15 × 9 tiles, between the lounge, café, games and recovery zones. It keeps the ring circulation open and leaves the habitat a lounge, not a botanical garden.

## 2. Resident station dog

| Element | Asset | Construction |
|---|---|---|
| Dog corner | `LEI-008` (new) | Wood-framed cushioned dog bed, food and water bowls on a mat, a toy basket, a small two-door storage cabinet, a ball on the floor |
| The dog | `DEC-009` (new) | A sitting tan dog in the crew's compact outlined style, with a teal collar and a brass tag. Next to its corner at the park's south-east edge. **World-building only:** not a character, no AI, no behaviour, no data |

## 3. Zen room, cinema, decompression room: room selection (not built)

The station inventory has **no genuinely available room**:
- every non-reserved room is ACTIVE with an approved function (L1–L4, L6, L7, L9, L10);
- every other room is formally RESERVED (L5 FUTURE_RESEARCH, L8 FUTURE_OPERATIONS, R1 DESIGNATED Performance & Wellbeing / Coaching, R2–R6 FUTURE_AGENT_TEAM).

Per the instruction not to change a reserved room without approval, these three rooms are **proposed, not built**:

| Function | Proposed room | Why | Conflict to approve |
|---|---|---|---|
| Zen / meditation room | `R1` (M, door to H-HAB) | Its designation (Performance & Wellbeing) is the closest match; quiet location off the habitat | Merges a wellbeing quiet room into the designated coaching room, or changes its designation |
| Small cinema / media room | `R2` (M, door to H-HAB) | Same size and access as R1; next to the café | Releases one FUTURE_AGENT_TEAM slot |
| Decompression room (sound-isolated) | `R3` (M, door to H-HAB) | Private, off the habitat ring | Releases a second FUTURE_AGENT_TEAM slot |

An alternative is `L8` (M, FUTURE_OPERATIONS) for the cinema. It is off `COR-S` near the work rooms, which is less suitable for leisure.
