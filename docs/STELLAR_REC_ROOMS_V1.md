# Habitat Recreation Rooms V1: R1 Zen, R2 Cinema, R3 Decompression

**Owner approval:** R1 → Zen / Meditation (compatible with the wellbeing / coaching identity), R2 → small crew cinema, R3 → sound-isolated decompression room. L5, L8 and R4–R6 stay reserved and sealed.

**Unchanged:** geometry, topology, circulation, door positions, anchors, display and data rules. No characters, no audio playback and no behaviour.

**Doors:** `DR-R1`…`DR-R3` change from sealed to open. They are the same hub `SV.door` assemblies, with plates ZEN, CINEMA and QUIET.

**How they are built:** R1–R6 are render-only rooms off the H-HAB rim with no tile grid. Their furniture is drawn as scene items in room-local coordinates, using the shared vocabulary:
- **Walls:** the near (door) wall stays low; the other three are full bulkheads faced with `WAL-012` acoustic slats (R1 warm wood, R2 dark fabric) or `WAL-013` sound-isolation padding (R3).
- **Furniture:** the new `SV.rec.*` builders.

| Room | Construction |
|---|---|
| **R1 Zen Room · Wellbeing** | Warm wood floor with a tatami field; six meditation mats and cushions (`LEI-009`); a raked sand garden with stones and a small tree as the focal point (`LEI-011`); four ambient speaker columns (`LEI-010`, world-building only, no audio); two low benches; four small trees; warm acoustic slat walls with indirect lamp boxes; warm low light pools |
| **R2 Crew Cinema** | Dark carpet with a lit centre aisle; a wide physical screen (`LEI-012`, **no display identity, no content**) on the long wall; three stepped rows of recliners (`LEI-013`) facing it, with aisle lights on the risers; a media projector stand (`LEI-014`, dark); a storage bay; speaker columns; dark acoustic walls; very dim light |
| **R3 Decompression Room** | Soft padded floor with an open centre; a large soft centre mat; two floor cushions; a padded bench by the door (`LEI-015`); a lighting control panel at the door (dimmer and buttons, no data); thick tufted padded walls with sealed seam strips (`WAL-013`); a SOUND ISOLATED wall plate and floor marking; one subdued violet light pool. Safe, calm, mostly empty |

**Registry:**
- Asset Registry: `LEI-009`…`LEI-015` and `WAL-012`, `WAL-013` (231 IDs, 205 active).
- Room Registry: R1–R3 ACTIVE (habitat recreation); R4–R6 unchanged.
