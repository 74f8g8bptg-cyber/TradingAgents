# H-LAB Calibration V1: composed with the Stellar Visual Vocabulary

**Status:** in review. Not committed until the owner approves.

**Baseline:** H-CMD V5.3 (`607e70d`).

**Scope:** H-LAB only. One substantial composition pass, using the vocabulary in `docs/STELLAR_VISUAL_VOCABULARY_V1.md`.

**Unchanged:**
- room geometry, size, topology;
- doors (`DR-N-LAB`, `DR-S-LAB`), anchors (R1–R6, V1–V4, M1, hand-off, visitors), identities;
- room function and zones;
- display identities and placements (`DSP-LAB-01`…`08`), approved offline states;
- camera decisions.

Every addition is unoccupied furniture without an anchor. Seats are added at existing work anchors only.

## 1. Reference elements adapted

The reference station's lab family was studied for construction only (its sample cart, core lens, trend pillar, screen cluster, specimen tank and holo table builders). None of its art or code is used.

| Reference construction rule | Stellar adaptation (vocabulary) |
|---|---|
| Screen cluster: one cast column, a crossbar, a wide head and two lower heads with different content ("never three identical cells") | `SV.screen.cluster` (`SCR-013`): dark heads with inactive surfaces (info, instrument, status); no display identity, no data |
| Sample cart: freestanding trolley, open shelves, cross-brace; the vials carry the colour, printouts are matte | `SV.eq.cart` (`STO-007`) |
| Core lens: bolted optics column whose lens is its only light | `SV.eq.optics` (`EQP-006`): constant lens light, no data |
| Tank: light from the rim down through water; caustics, a bright surface line, pump housing on the stand | `SV.eq.tank` (`EQP-007`) |
| Holo table: a lit volume in a well; cyan lives in the light, the hardware stays steel | `SV.eq.dome` (`EQP-005` hero): stepped plinth, 12 instrument segments, a lit well, a glass dome; the `DEC-007` globe is decorative |
| Projector column | `SV.eq.projector` (`SCR-006`, carries `DSP-LAB-05` as before) |

## 2. Composition (by approved zone)

| Zone | Composition |
|---|---|
| `lab.feeds` (west) | R1–R6 consoles as **WS-compact** workstations with operator chairs. Screen clusters in the gaps of each column; rack caps at the column ends; one hazard-banded group zone per column; conduits to the rim |
| `lab.macro` (north) | The driver board as **WS-heavy**, flanked by two screen clusters. A west macro desk (compact) with chairs; an east rack-pair and equipment-bay group |
| `lab.core` (centre, hero) | The dome ring hero; four optics columns on pads at the corners; the projector column; a hatched ring band and deck lights |
| `lab.validation` (south) | The 4-station bench as a 4-bay console module (screen / instrument / stack / readout) with chairs; a sample cart; two specimen tanks |
| East (inside the walkway) | An analysis island facing the core: two compact desks around a screen cluster. A north-east analysis group: cabinet, desk, rack |
| `lab.walkway` (east arc between the doors) | **Kept clear:** treadway deck with hazard edges (designed open space), door runners |
| `lab.experiment_bench` (south-west, FUTURE_RESEARCH) | **Kept clear and not rendered**, as the registry requires |
| Perimeter | Rhythm `2, R, 3, B, 1, G, 2, S, 3, R, B`: bank modules, racks, equipment bays, service cabinets, gaps, lockers. Walkway and door approaches excluded. The upper wall layer (screen band, cabinets, cable boxes) follows the equipment, but **not behind registered rim displays**. A perimeter rack under a rim display is built half-height so the display stays readable |
| Doors | `SV.door` hub assemblies (one per opening), bulkhead returns |
| Floor / light | `SV.floor` deck plan, beams, grilles, hatches, conduits with junction plates, paired grates. LGT-009 cool dome light, wall-lamp pools, task pools, cyan spill only at feed and driver consoles with a live producer, amber equipment light |

## 3. New registered assets

`SCR-013` screen-cluster column, `STO-007` sample cart, `EQP-006` optics column, `EQP-007` specimen tank. All are decorative and carry no data. Asset Registry totals: 216 IDs, 190 active.

## 4. Checks

Geometry 0 issues, visual 0 failures, rebuild byte-identical, smoke test passed (H-LAB oblique added), Stellar tests passed, ruff clean.
