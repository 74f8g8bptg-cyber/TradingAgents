# H-HAB Calibration V1: the habitat, composed with the Stellar Visual Vocabulary

**Baselines:** H-CMD V5.3, H-LAB, Wing V1.

**Scope:** H-HAB only, in one dedicated pass.

**Unchanged:**
- geometry, the ring circulation, R-door approaches, the billiards clearance;
- anchors, displays (`DSP-HAB-01`…`04`), doors and functions;
- the recovery-pod rule: a countdown only from `agent.resting`; cosmetic pods never show vitals.

## 1. Reference principles adapted

The reference station's lounge props (bar, couch, recliner, coffee table, brewer, pod chair, stool, billiards, rug, planters) were studied for construction only:
- **One room, one edge:** lounge pieces share a softer edge tint instead of the near-black outline.
- **Glass table:** the lower shelf reads through the pane.
- **Bar:** counter, kick rail and back shelf, with a material that is not service steel.
- **Pod chair:** a shell only reads as a shell when you see inside it.
- **Brewer:** one chamfered column, an overhanging cap, and a lit alcove as the only warm emissive.
- **Billiards:** seen from above, wood carcass, felt bed, pockets.
- **Rug:** a soft bound rim, never a black lip.
- **Planters:** distinct silhouettes.

## 2. Composition (by approved zone)

| Zone | Construction |
|---|---|
| `habitat.plants` (centre, hero) | `PLT-005` → hexagonal bulkhead-built planter: plinth, wood seating ledge, brass rim, layered tree, rim lights, brass floor ring |
| `habitat.cafe` (north) | `LEI-002` → bar (fluted wood front, brass kick rail, stone top, back shelf); `LEI-003` → brewer; `TBL-003` → pedestal café tables; `SEA-007` → shell chairs; stone tile floor with a brass border; planters flanking the counter |
| `habitat.lounge` (south) | `SEA-006` → sofas (frame, cushions, brass-capped arms); `TBL-004` → glass coffee table; `LEI-004` → bound woven rug; planters |
| `habitat.games` (east) | `LEI-001` → billiard table (turned legs, wood carcass, felt, pockets); `STO-003` → cue rack; wood floor field with a brass border (the clearance stays clear) |
| `habitat.rest` (south-west) | `LEI-005` → cosmetic rest pods (reclined shells); a soft round rug |
| `habitat.recovery` (north-west) | `EQP-004` → recovery pods (clinical base, bed, glass canopy, status strip dim without `agent.resting`); `CON-021` → compact workstation; a service cabinet; clinical plate floor with a cyan border |
| Rim | Warm wood-panel bays in bulkhead frames with brass trim and sconces; ribs; recessed lamp boxes. **Viewport bays** (DEC-001/002) on the south window arc; a planted **living-wall** bay (PLT-004). No upper equipment layer |
| Doors | `DR-CMD-HAB` (hub assembly, shared with H-CMD) with a wood runner. **R1–R6 doors:** closed `SV.door` assemblies built into the rim (the rooms stay sealed reserved shells) |
| Rim-edge dressing | Planters (`PLT-001`) and shelves (`STO-003`) only, never in the R-door approaches, window or living-wall arcs, rim displays, billiards clearance, or next to anchors |
| Light | Warm ambient; LGT-006 pendant pools over café tables, the lounge, the bar and billiards; planter light; a clinical white recovery bay; cool window spill; warm sconce pools |

**New vocabulary:** `SV.hab` (bar, dispenser, cafeTable, shellChair, sofa, glassTable, rug, pool, rack, restPod, recoveryPod, planter, bench) and the wall faces `SV.wall.warm`, `SV.wall.viewport`, `SV.wall.living`. No new asset IDs.
