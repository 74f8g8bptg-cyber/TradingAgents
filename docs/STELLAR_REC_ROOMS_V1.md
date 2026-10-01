# Habitat Recreation Rooms V1: R1 Zen, R2 Cinema, R3 Decompression, R4 Dog Play

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
- Room Registry: R1–R3 ACTIVE (habitat recreation); R4 see below; R5–R6 unchanged.

---

## R4 Dog Play · Canine Room

**Owner approval:** R4 only, as an indoor dog activity and play room off H-HAB. R5 and R6 stay sealed and reserved. The H-HAB park, the fountain and the resident dog (`DEC-009`) are unchanged; the dog stays decorative, with no AI or behaviour, and is not duplicated into R4. R4 is the dog's dedicated room, so the park's former dog corner (`LEI-008`) is retired. **Occupancy:** the dog may be anywhere in H-HAB or in R4 and nowhere else (Room Registry §3.3a).

**Unchanged:** geometry, topology, anchors, door positions, every other room, display and data rules. `DR-R4` opens (the same hub `SV.door` assembly, plate DOG PLAY).

**Reference use:** an agility-playground photo set the principles only (compact course, obstacle silhouettes, soft surfaces). Nothing is copied from it. Every piece is built from the station grammar: steel frames on bolted feet, rubber-coated decks and fabric in the station palette (slate-teal decks, amber contact zones, gunmetal frames).

**Scale:** sized to the resident dog (about 10 units sitting; agents are 19 units):

| Piece | Size |
|---|---|
| A-frame apex | 11 |
| Jump bar | 4.5 |
| Weave poles | 9 |
| Tunnel | Ø 8.4 |
| Ring | Ø 7.2 at 8.5 |
| Pause platform | 4 |
| Bridge arch | 5 |

**Composition** (room-local s along the axis from the door, t across):

| Zone | Construction |
|---|---|
| **Entry and circulation** | A clear lane from the door to the centre, and a clear ring lane between the centre mat and the course; a light paw-print trail marks both (`FLR-013`) |
| **Open centre** | A soft teal play mat with piping and a faint paw emblem; scattered toys (balls, rope toy, ring toy; `LEI-025`). Nothing stands on it |
| **Course (U around the centre, on a turf band)** | Far side: A-frame (`LEI-017`), suspended ring (`LEI-019`) and weave poles (`LEI-020`). Far end: a curved tunnel (`LEI-016`), kept clear of the tall end bulkhead so it reads from the default camera. Near side: a low ramp to a pause platform (`LEI-018`), a curved balance bridge (`LEI-022`) and a low jump (`LEI-021`) |
| **Quiet rest corner** | By the door, behind a low felt REST screen, on its own carpet: a raised cot bed with a bolster and blanket (`LEI-023`) and a water station (`LEI-024`). It sits apart from the active course |
| **Storage** | By the door on the far side: the existing wall locker (`STO-001`, built with `SV.eq.locker`, shorter) and a wooden toy bin (`LEI-025`) |
| **Walls** | The near (door) wall is low; the others use `WAL-014`: warm acoustic slats over a padded dog-height bumper dado, with a brass rail, indirect lamp boxes and a DOG PLAY · K9 plate |
| **Floor** | Durable interlocking rubber tiles, a turf course band, a rest-corner carpet and the centre play mat (`FLR-013`) |
| **Light** | Warm pools over the mat, the course and the tunnel; a softer, warmer pool over the rest corner |

**Vocabulary:** the new `SV.dog.*` family (`tunnel`, `aframe`, `ramp`, `ring`, `weave`, `jump`, `bridge`, `bed`, `screen`, `water`, `toyBin`, `toys`, `ball`, `paw`) and `SV.wall.kennel`. These are shown in the Vocabulary view next to the resident dog for scale. Reused: `SV.eq.locker`, `SV.small.lampBox`, `SV.wall.acoustic`, `SV.door`, and the shared primitives.

**Registry:**
- Asset Registry: `LEI-016`…`LEI-025`, `WAL-014`, `FLR-013` (243 IDs, 216 active; `LEI-008` retired).
- Room Registry: R4 ACTIVE (habitat recreation); R5–R6 reserved.
