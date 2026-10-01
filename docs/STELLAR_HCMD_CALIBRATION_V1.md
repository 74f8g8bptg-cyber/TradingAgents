# H-CMD Calibration Room V1: reference-station visual adaptation

**Status:** in review. Nothing is committed.
**Direction:**
- [`STELLAR_STARNET_VISUAL_LANGUAGE_GUIDE_V1.md`](STELLAR_STARNET_VISUAL_LANGUAGE_GUIDE_V1.md), with the owner decisions SV-1…SV-6 (below);
- StarNet is the primary visual reference;
- the assets are **original Stellar drawings**. No StarNet art file or character is used.

**Scope:** `H-CMD` only. All other rooms are unchanged.

## 1. Owner decisions applied

| # | Decision | Applied as |
|---|---|---|
| SV-1 | Original assets following StarNet's design rules; no StarNet art or characters | Every form is procedural Stellar drawing code in `tools/visual_prototype/templates/visual_prototype.html` (block "H-CMD CALIBRATION ROOM V1"). The page check still rejects any external URL, image or StarNet reference |
| SV-2 | Dark industrial base, keeping the Stellar identity | Charcoal deck plates, gunmetal bulkheads and furniture, amber/brass hardware and hazard stripes, cyan screen glass. Titanium trim and command-red accent lines remain, so the room is not fully dark |
| SV-3 | Compare cameras; do not freeze | New **Oblique** view: a high overhead oblique camera in the StarNet style, with horizontal long edges and a vertical rise. It sits next to **Iso · right**, which is still the default. The camera is not frozen |
| SV-4 | Compact agents | H-CMD crew are 19 units tall with a large head, a dark outline, the Stellar charcoal uniform with the department yoke and cuffs, and the role shape icon |
| SV-5 | Keep the circular architecture | The rim keeps its circle and gains a **segmented bulkhead** treatment (`WAL-011`) |
| SV-6 | New visual assets allowed, registered and validated | See §3. Geometry re-validated with 0 issues |

## 2. Reference-station principles used (guide §1)

- **Dense perimeter, open centre (P7):** a continuous console bank around the rim, a clear circulation ring and an open floor around the dais.
- **Hero object (P7):** `TBL-001` is drawn as a tactical command table, with a bevelled gunmetal frame, brass bolts and a dark glass top showing a **neutral grid**: no values, no data.
- **Complete workstations (P8):** each role console is desk + chair + three monitor masses + keyboard + name plate. The glass is lit only by **occupancy**: its operator is shown at the console and their role has a producer. The budget console stays dark because `DSP-CMD-12` has no producer.
- **Screen placement (P9):** monitors are built into the desks. The approved displays keep their IDs and offline states.
- **Palette and materials (P2, P3):** broad gunmetal planes with seams, ribs, vents and cable trays. Amber hazard border, brass trim, cyan glass.
- **Room shell (P4):** heavy segmented rim with ribs every third segment, wall equipment (`DEC-008`) and cool wall fixtures (`LGT-010`).
- **Floors (P5):** deck plates, a tread-plate circulation ring, a hazard-stripe dais border (`FLR-009`), floor vents (`FLR-010`), and dashed lane markings toward the three doors.
- **Lighting (P11):** low deck ambient, cool rim fixtures, cyan spill from the table and the lit monitors. Lighting never carries a data state.
- **Agent presence (P10):** operators sit at their consoles, the Captain sits in the command chair and the Research Manager at the table head. **Name plates** on the desks show the role code and surname.
- **Truth (P8, P12):** occupancy is not work. No screen shows a value without telemetry, and the console displays keep AWAITING DATA / NOT AVAILABLE.

## 3. Asset list

**New, registered in `STELLAR_ASSET_REGISTRY.md`:**

| ID | Name | Footprint / nav | In H-CMD |
|---|---|---|---|
| `CON-030` | Perimeter console bank module: unassigned, dark glass, **no data, no anchor** | blocks 1–3 rim tiles | 26 modules (75 tiles) on the rim ring |
| `FLR-009` | Hazard-stripe border marking | walk-over | ring at the dais edge |
| `FLR-010` | Floor vent grille (decal) | walk-over | 4 on the walkway |
| `WAL-011` | Segmented bulkhead rim | wall (render) | whole H-CMD rim |
| `DEC-008` | Wall equipment panel (vents, cable trays; no data) | wall (render) | rim segments |
| `LGT-010` | Wall utility fixture (never a status light) | wall (render) | rim, every 6th segment |
| `SGN-008` | Workstation name plate (static) | none | the four role consoles |

**Existing assets newly used in H-CMD:**

| ID | Use | Count |
|---|---|---|
| `STO-001` | Wall lockers on the rim, flanking the doors. Registry "Where" now lists `H-CMD` | 6 |
| `SEA-002` | Console chairs at the four role consoles (approved H-CMD item) and at five table places | 9 |

The Room Registry H-CMD card gains a "Calibration additions (V1, in review)" row. The approved H-CMD items are unchanged: `TBL-001`, `SEA-001`, `CON-003` / `-004` / `-005` / `-022`, `SEA-005`, `FLR-002` and `DEC-007`. So are their positions, the anchors and `DSP-CMD-01`…`-12`.

## 4. Geometry and visual checks

| Check | Result |
|---|---|
| Geometry consistency (footprints, anchors, door approaches, connectivity, corridor widths, occlusion) | **0 issues** |
| New check: **H-CMD circulation ring** (radius 6.6–9.4 tiles between the dais and the consoles) is fully clear | pass |
| Door approaches of `DR-N-CMD`, `DR-S-CMD` and `DR-CMD-HAB`: the rim ring is left open within 4.5 tiles of each door | pass |
| H-CMD furniture density | **3 % → 10 %** (114 of 1094 floor tiles), concentrated on the rim. Two-agent passing share 0.98 |
| Visual / registry consistency | 0 failures. Every new asset ID is in the Asset Registry; 72 displays, 41 agents |
| Rebuild test (`build.py --check`) and browser smoke test (now including the Oblique view) | pass |
| Stellar tests / ruff | pass |

## 5. Not yet done (deliberately)

- **Other rooms:** they keep their V1 forms. The H-HAB, corridors and L-rooms beside H-CMD in the screenshots are unchanged.
- **Camera:** not frozen. Iso · right is still the default, and Oblique is available for comparison.
- **Animation:** no screen sweep, walking or idle motion yet.
- **Art finish:** this is the calibration room. It should be compared against the reference at 2× and 4× before the language is rolled out room by room (guide §8).

---

## 6. Calibration V2 (in review): reference construction pass

**Before implementation: comparison with the reference bridge.**

Calibration V1 still had four gaps against the reference:
- plain prisms without linework;
- no face detail (recessed panels, vent slats, amber light strips, brass rivets and knobs);
- keyboard-less desks with flat monitors;
- a single thin ring of equipment and a large, featureless deck.

The reference builds every object from modules: a dark outline, chamfered caps, plated tops, keyboards, thick monitor bezels, side pods with lamps, and amber utility strips. Its perimeter is two layers deep (banks plus chairs), with a tread-plate service strip in front of the banks.

**V2 changes (H-CMD only; original drawing code; no reference art file):**

| Area | V2 construction |
|---|---|
| Rendering | Dark linework and top-edge highlights on every H-CMD body. Face-mapped detail painters: recessed panels, vent slats, amber light strips, brass rivets and knobs, keyboards, bezelled screens, name plates |
| Role workstations (`CON-003` / `-004` / `-005` / `-022`) | Toe-kick plinth; vented, amber-lit base cabinet; desk with a brass front edge, two or three keyboards and a brass trackball; monitor housing with three bezelled screens and amber-slit pilasters; side pods with a cyan hardware lamp; **`SGN-008` plate on the housing, front and back**; padded chair pulled in to the desk; the operator seated with arms on the desk. Glass is lit by occupancy only, never by data; the `CON-022` budget console stays dark |
| Perimeter bank (`CON-030`) | Each module is built as a rim-oriented bridge console bank: base cabinet, keyboards, screen housing (dark glass, no data) and pods. **Unclaimed `SEA-002` chairs** at every other module make the perimeter two layers deep |
| Back and south banks (**new `CON-031`**) | Four secondary consoles with chairs, flanking the command axis and the budget console |
| Operations clusters (**new `SRV-005`**, **new `STO-005`**) | Six relay stacks with drawer modules, constant hardware lamps and brass feet; three vented equipment-bay cabinets with knobs and amber strips |
| Lockers (`STO-001`) | Double-door gunmetal lockers with vents, brass handles and an amber strip |
| Command table (`TBL-001`) | 16-segment chamfered frame: alternating amber-lit and vented segments, brass caps, a stepped pedestal, and glowing neutral-grid glass (no values). `DEC-007` globe kept decorative |
| Command chair (`SEA-001`) | Padded and quilted, with armrests, amber pad lamps and a command-red seam |
| Rim (`WAL-011` / `DEC-008` / `LGT-010`) | Protruding ribs with brass bolts; recessed vented panels with amber strips; a horizontal pipe run; a kick band; fixtures |
| Floor | Bolted deck plates, grille panels, a cross-hatched tread walkway ring with titanium edges, and the hazard dais border. **New `FLR-011`** cable conduit from the back bank to the dais. `FLR-009` hazard aprons at the four role consoles. A tread **service strip** with an amber edge in front of the whole perimeter. Dashed door lanes |
| Lighting | Cool rim fixtures alternating with warm amber utility glow, cyan spill from the table and lit monitors, amber glow at the operations clusters, low ambient |
| Agents | Compact crew with a stronger 0.7-unit outline, broader shoulders and a larger head. Seated on the chair, offset toward the desk, with arms forward at a console |

**Registered:** `CON-031`, `SRV-005`, `STO-005` and `FLR-011` in the Asset Registry (counts updated: 211 IDs, 185 active). The Room Registry H-CMD row lists the additions.

**Checks:**
- Geometry: **0 issues**; the circulation ring and door approaches are clear.
- Density: blocking footprints now cover 12 % of H-CMD, plus 30 non-blocking chairs and the service strip, floor markings and wall detail.
- Visual / registry: 0 failures.
- Rebuild test, smoke test, Stellar tests and ruff: green.

**Honest finding: scale.** At the same tile size, the reference bridge (about 22 × 18 tiles) fits inside H-CMD's dais-plus-walkway area. H-CMD is a 37-tile circle, about 2.7 times the reference's floor area. With a dense perimeter, a hero object and a clear circulation ring, a room this size keeps more open floor than the reference. Matching the reference's packed feel fully would need one of two owner decisions:
- more equipment islands between the walkway ring and the perimeter;
- or reconsidering the hub's size, which is a topology change and is **not** proposed here.

## 7. Calibration V3 (in review): recover V2 and adapt the reference construction

V3 keeps all of V2: the perimeter, workstations, banks, secondary consoles, bays, relays, lockers, floor, service strip, hazard markings, table, lighting, agents, registered assets, pipeline and checks.

**Unchanged:** room geometry, topology, room positions, doors and door openings, approved anchors, display and registry identities, room functions, approved circulation, and central hub geometry. Every addition is unoccupied furniture without anchors, placed only on free outer-deck tiles; the circulation ring stays clear.

| Area | Reference-station rule adapted | V3 change |
|---|---|---|
| Workstations (`CON-003/004/005/022`) | Pedestal desk, knee space, chamfered screen housing (main screen plus small stacked screens), keyboard, button clusters, knob | Multi-layer build: pedestals with drawers, modesty panel, chamfered slab with a brass edge, a taller housing (18.5) with a main screen and side stacks, a lamp band and a name plate. **The console's approved display now renders inside the main screen.** The floating billboard is gone. When the operator faces away from the camera, the same display is shown on a **rear repeater built into the housing**, not on a floating topper |
| Screens | A screen is a physical module, never a flat black square | `dScreenModule`: housing, bezel, mounting bolts, glass, status LED. Content is scaled to fit the glass. Unlit modules are dark glass with a reflection, with no data |
| Second row | The perimeter is backed by a layer of cabinets and plants | Odd perimeter modules get an inward item: four `PLT-001` planters (copper rim, ferns) near the 11/1/5/7 o'clock positions, and **new `STO-006`** red service cabinets with a hazard triangle elsewhere |
| East operations bay | Paired desks with chairs, plus a rack pair on the side wall | Two more `CON-031` desks with chairs and two more `SRV-005` relay stacks, so the east outer deck reads as layered equipment like the west |
| Seated agents | The chair back is in front of a seated operator seen from behind | Chair back lowered to shoulder height, with an outer shell (brass rim, padded panel). For an operator facing away from the camera, the back is drawn over the body, so head, collar and chair read clearly |
| Floor | More floor detail | Extra framed vents on the outer deck, and cable conduits from each role console out to the rim |

**Checks:** listed in the review summary. Geometry 0 issues, visual 0 failures, rebuild byte-identical, smoke test clean, Stellar tests and ruff green.

**Still open:** colours and materials (the owner said construction comes first); the north-west and south-west outer deck, kept clear for the corridor-door approaches; the scale finding above.

## 8. Calibration V4 (in review): construction-detail pass

V4 changes how the existing objects are built, not what is placed. It changes **no geometry, footprint, anchor, door, display identity, registry entry or camera**: `geometry.py` is untouched since V3, the furniture count is still 188, and no asset was added. The palette is kept roughly as in V3; the final materials and colour pass comes later.

**Studied first.** The reference station's prop source (its desk, console, bench-screen and rack builders, and its material kit for deck plates, sockets, cables, chamfers, bloom and spill), plus its industrial prop art (workstation front, rear and side views; console bank; equipment bay; tactical table; chair views; deck perimeter). These were studied for construction rules only. No art file was copied or loaded.

**Construction details missing from V3, now built (original drawing code):**

| Object | Reference rule | V4 construction |
|---|---|---|
| Workstations (`CON-003/004/005/022`) | Assembled from many castings: pedestals with corner posts, a raised control deck, a recessed keyboard tray, a massive housing with top clamps and lamp columns | Pedestal corner posts; framed drawer and door with amber pulls; modesty panel with a bolted service hatch, amber slot and cable loom; brass slab edge with an amber slot. **Raised chamfered control wings**: switch bank on the left; trackball, knobs and keypad on the right. Recessed keyboard tray. Housing with **two top clamps**, **hinge brackets** and **amber lamp columns** either side of one wide screen. Rear face with two grilles, a central hatch with a lamp, and a cable loom with clamps. Edge wear throughout |
| Screens (all) | A screen is a cast module, never a flat rectangle | `dScreenModule`: mounting tabs, a thick chamfered housing, a stepped bezel, recessed glass with internal shadow under the bezel, corner bolts, an indicator row, and a reflection. Dark glass keeps a faint etched frame line, never data. Approved content renders as before |
| Secondary desks (`CON-031`) | Same family, varied modules | Alternating wide-screen and stacked-screen housings; some carry a small instrument pod on the control wing |
| Perimeter bank (`CON-030`) | Repeated modules between pilasters, each with its own instrument mix; vented kick | **Three module variants** in rotation: screen stacks, a triple screen, and an instrument panel with rest-position gauges and a grille. Crown brackets; pilasters with a cap and a 5-lamp column; a control strip of keypads, button blocks and a small dark readout window. Kick panels alternate grilles and drawers |
| Equipment bay (`STO-005`) | Heavy bolted end pillars with lamps; grille, lamp row, drawers, kick grille | Rebuilt to that structure, with a vented top and a small dark readout window |
| Service cabinet (`STO-006`) | Plinth, hood, hinged door, detailed sides | Plinth, hood, hinge pins, a door seam, and side faces with vents, a label plate and a conduit |
| Relay stack (`SRV-005`) | Machinery bolted to the deck with a cable into a floor socket | All four faces detailed, with corner rails. Feed cables run down the far side to a deck socket. Hazard pad on the deck |
| Locker (`STO-001`) | Double door, vents, hood | Plinth, a vented top hood, grilles, hinge pins and a label plate |
| Command table (`TBL-001`, footprint unchanged) | Octagonal rim of segments with inset button panels and corner blocks; stepped base | Plinth; pedestals with access panels. Each segment has two inset control panels (buttons or toggles) and a grille. Raised **corner blocks** with brass caps; an inner bezel lip and a recessed glass edge. Segments are depth-sorted. The glass stays neutral and decorative |
| Chairs (`SEA-002`) | Headrest on brass posts, two-cushion back, armrests on posts with brass caps, gas column, 5-star base on casters | Built as described. **The headrest is omitted on an occupied chair**, so a seated operator's head always reads. Seen from behind, the chair back is drawn in front of the operator |
| Walls (`WAL-011` / `DEC-008` / `LGT-010`) | Every detail has a structural or technical reason | Bolted cornice band. Ribs flanked by twin conduits with clamps. Seven equipment kinds by segment: equipment recess with gauges, grille and lamps; electrical box with a conduit drop; **service door** with hinges, a window and a hazard kick; comms console; junction box with cable drops; grille; storage niche with boxes. Tray brackets, fixture housings, wear |
| Floor | Constructed deck | **Structural beams** under every fourth seam, with bolts. **Access hatches** with recessed pulls, kept off marked tiles. **Junction plates** where the conduits meet the perimeter. Hazard pads at the relay stacks. Central circulation unchanged |
| Lighting | Layered: low ambient, local task light, screen glow, amber technical light | Warm task pool at each operator position; small amber pools at bank pilasters; warm pools at secondary desks. A cyan screen-light rim on operators at lit consoles. Ambient unchanged |
| Agents | Belong in the room | Characters, uniforms, identities and positions unchanged. Integration only: chair construction, the operator seen from behind, and the screen-light rim |

**Not new assets.** Floor hatches, beams, junction plates and sockets are construction detail of the existing floor assets. They are not separate objects, so they are not registered.

## 9. Calibration V5 (in review): composed with the Stellar Visual Vocabulary

V4 is kept as the base; its backup is outside the repo. V5 moves all construction code into the reusable vocabulary (`docs/STELLAR_VISUAL_VOCABULARY_V1.md`, `tools/visual_prototype/templates/stellar_vocabulary.js`). H-CMD's template block now holds only its **composition**:
- which family each registered asset uses;
- the perimeter and wall rhythm;
- the deck plan;
- the local light.

**Unchanged:**
- room geometry, size and topology;
- doors, anchors and circulation;
- hub, dais, and the command table footprint;
- display identities and content, agent identities, room function;
- camera decisions.

**Composition changes:**

| Area | V5 |
|---|---|
| Perimeter (`geometry.py`) | Rhythm `3, 2, R, 3, G, 1, 2, R`: wide / double / single bank modules (`CON-030`); tall relay racks (`SRV-005`, already registered for H-CMD) between groups; a gap where the wall system shows. The cycle restarts per run. Lockers still close each run. Furniture 188 → 198, all unoccupied and without anchors |
| Bank modules | `SV.con.bank`: each bay carries unlike kit (screen, stack, instrument, switch, readout), with full-height dividers and a continuous crown |
| Workstations | CON-003/004/005 use **WS-standard** with an instrument pod, cable and floor socket. CON-022 uses **WS-heavy** (pods at both ends, double housing). CON-031 uses **WS-compact**. Rear repeaters as in V4 |
| Equipment | STO-005 → EQ-bay; STO-006 → EQ-service (red); SRV-005 alternates EQ-relay (open patch frame) and EQ-rack (blade tower); STO-001 → EQ-storage locker (olive) |
| Chairs | CH-operator at the role consoles, CH-standard elsewhere, CH-command for SEA-001 |
| Table | SV.table.tactical (V4 construction, now in the vocabulary) |
| Walls | Bay rhythm (`SV.wall.BAYS`): a rib every fourth segment; three-face bays around one feature; trays; a lamp fixture over alternate bays |
| Floor | Staggered two-tile deck plates (`SV.floor.panel`); beams, grilles, hatches, conduits, junction plates, hazard pads from `SV.floor` |
| Material | `prismX`: two-layer contact shadow, floor-line occlusion, warm key / cool rim; cap tops as separate castings |
| Light | Wall-lamp pools tied to the fixture rhythm; screen glow at the four role consoles; task pools; amber equipment and pilaster light |

**Tools:** `render.py` inlines the vocabulary at `/*VOCABULARY*/`. The page has a **Vocabulary** button (`?vocab=1`), and the smoke test covers it.

## 10. Calibration V5.1 (in review): whole-room composition and density

V5 stays the base: the vocabulary, construction, palette, agents and pipeline are unchanged. V5.1 changes the **composition** using the reference bridge's logic:
- equipment works in **groups**;
- the perimeter carries several equipment types;
- the room has **low / medium / high** layers;
- open floor is **designed**, as circulation runners and group zones, instead of left over.

**Unchanged:**
- geometry, room size, topology, hub;
- doors, anchors, circulation ring;
- command-table footprint;
- display and agent identities, room function, cameras.

Every addition is unoccupied furniture without anchors, using already-registered assets: `SRV-005`, `STO-005`, `STO-006`, `CON-031`, `SEA-002`, `FLR-011`. Furniture goes from 198 to 224.

| Layer | V5.1 |
|---|---|
| Perimeter (background) | Rhythm `3, 2, R, B, 3, G, 1, S, 2, R`: bank modules, racks, **ring-mounted equipment bays** (`STO-005`) and **service cabinets** (`STO-006`), and wall gaps cabled with a conduit stub. Lockers close each run |
| High layer | `SV.wall.upper` (new vocabulary module): **wall-hung cabinets, status monitors (dark, no data) and cable boxes on brackets** above the consoles, over the flanking faces of two bays in three |
| Workstation groups (midground) | **Rack pairs** beside each role workstation (north-west, north-east, south-west, south-east). **South command group:** budget console between two service cabinets. **South operations arc:** two compact desks with chairs. **West engineering island:** two side-facing compact desks around an equipment bay, between the two door approaches. **North-east line:** rack, equipment bay, rack |
| Foreground | Conduits from every group, and from each perimeter gap, out to the perimeter. **Group zones:** a hazard-bordered deck zone (chamfered) around each cluster of three or more midground blocks |
| Designed open space | **Treadway runners** from each door to the walkway ring (ribbed tread, lit hazard edges, inbound chevrons) replace the dashed lanes. A 3-tile corridor along each door approach is kept free of furniture. Every placement is checked so that no walkable tile becomes unreachable |
| Centre | Table and footprint unchanged. **Four technical channels** (cable trays with clamps) from the table base to the dais edge, ending in flush service plates with a lamp. **Deck lights** in the dais rim. The circulation ring stays clear |
| Light | One soft warm pool per group zone, on top of the V5 task, screen, equipment and wall-lamp pools |

## 11. Calibration V5.2 (in review): doors and corridor transitions

V5.1 is the base. No furniture was added. This pass changes the **renderer only**: geometry, door positions, door data, corridors, anchors and circulation are unchanged.

**Causes found:**
1. **H-CMD doors:** the curved rim's door gap is narrower and differently angled than the straight 2-tile door frame. Rim stubs stood inside the opening next to two white posts, a white lintel and the white corridor-wall ends, so the doors read as a "white arch" with stray wall pieces.
2. **Station-wide:** a door through a thick wall carries **two frame records** (one per wall face), and the renderer drew a complete door at each. DR-L1, DR-L2, DR-L3, DR-L4, DR-L5 and DR-L10 appeared as two doors per opening (DR-L10 with two RESTRICTED plaques).

**Fix:**
- **New vocabulary family `SV.door`:** **A** standard, **B** hub access, **C** restricted, plus a closed (reserved) leaf. One opening is one assembly:
  - a threshold plate with door track, grating, titanium edges and hazard bands;
  - two layered jamb columns, each with a leaf pocket showing the retracted, hazard-edged leaf, front panels with a lamp column, a kick band and bolts, and a door control box on one side;
  - a lintel drive housing with louvres, a status lamp and a destination plate (no numbers), and a hazard band under it;
  - on B/C, a crown and twin beacons.
- **H-CMD doors** (all three are hub access, `DOR-009`) use type B:
  - rim segments inside each door zone are no longer drawn, and dark bulkhead returns (with the wall band and a rib) close the wall from each jamb to the nearest kept rim end;
  - the H-CMD/H-HAB junction collar is restyled as dark bulkhead.
- **Other doors** keep their current style until their room's pass. A two-frame door is drawn as **one deep doorway** (jambs spanning the wall thickness, one lintel, one sign).

**Audit (live scene, both cameras):**

| Door | Location (world) | Type | Assemblies | Rim segments inside the opening | Corridor alignment | Iso · right | Oblique |
|---|---|---|---|---|---|---|---|
| DR-N-CMD | COR-N ↔ H-CMD (792, 564) | B hub access | 1 | 0 | The threshold spans the corridor width (2 tiles); the corridor walls end on the jambs; the H-CMD treadway runner ends at the threshold | Reads as a door: lintel, jambs and threshold | Seen side-on: heavy jamb with lamps and threshold; no arch |
| DR-S-CMD | COR-S ↔ H-CMD (780, 804) | B hub access | 1 | 0 | Same | Reads as a door | Side-on, as above |
| DR-CMD-HAB | H-CMD ↔ H-HAB (1200, 696) | B hub access | 1 | 0 | The threshold bridges both hub floors; the junction collar walls meet the jambs | Reads as a door | Side-on, as above |
| Station (21 doors) | | | Exactly 1 each (before: 6 doors had 2) | | | | |

**Note:** the oblique camera looks north, and all three H-CMD doors face east–west, so in that view they are seen side-on. They read as heavy jamb and threshold silhouettes, not as frontal doors. That is inherent to the camera angle.
