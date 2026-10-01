# Stellar Visual Vocabulary V1

**Status:** in review. Not committed until the owner approves.

**What this is:** a reusable construction vocabulary for every Stellar room. It is original Stellar drawing code, in `tools/visual_prototype/templates/stellar_vocabulary.js`, and `render.py` inlines it into the prototype page. H-CMD is the first room composed with it (`docs/STELLAR_HCMD_CALIBRATION_V1.md` §9).

**Review:** the **Vocabulary** button (or `?vocab=1`) renders every family on a plain deck.

**Source rule (SV-1):** the reference station was studied for its construction language only:
- its prop source: the desk, console, rack, relay, cabinet, locker, screen and table builders, and its material kit;
- its industrial prop and material art.

No art file, sprite or character is copied or loaded. Every Stellar family is new drawing code that follows the same rules.

## 1. What the reference station's construction vocabulary actually is (Phase 1 inventory)

| # | Element | How the reference builds it (rule extracted) |
|---|---|---|
| 1 | Workstation | Two pedestal cabinets with drawers and an amber slot-lamp pull. A recessed modesty panel with a lit slot. A chamfered slab. A deck split into a **left switch bank**, a **recessed keyboard tray** and a **right trackball/knob bank**. A massive chamfered monitor housing with **top clamps**, **amber lamp columns** either side of one wide screen, and hinge brackets. The rear view has two grilles, a hatch and a **cable loom**; the side view shows the housing depth. Bronze edge wear on every exposed edge |
| 2 | Compact workstation | The same parts, narrower. The screen is smaller, but the side pods and lamp pips are kept |
| 3 | Console bank | Modules split by **full-height dividers**. Each bay carries *unlike* kit: screen, stacked screens, switch matrix, bar readout ("any prop wider than ~3 tiles is a horizon unless you break its rhythm"). Lower doors with slot lamps, a vented kick, a continuous crown |
| 4 | Equipment bay | A lid of **three plates**. Three bays: louvre pair, a control panel (slot lamps, brass dial, lamp row), louvre pair. Corner posts, kick slot lamps |
| 5 | Storage | **Locker:** olive steel, read by its verticals (a louvre head plus a full-height handle on each door). **Drawer bank:** 2×4 drawers with amber pulls, on feet. **Data cabinet:** two unequal columns, and a **cap wider than the body**. **Rack:** countable blades with reveals, falling off in light down the stack |
| 6 | Tactical table | An octagonal rim of segments. Each segment carries inset button rows. Corner blocks, a stepped base with an access hatch, recessed glass |
| 7 | Chairs | A headrest on two posts, a two-cushion back, armrests on posts with brass caps, a brass gas column, and a 5-star base on casters. **The steel-over-upholstery contrast reads as padding in a frame** |
| 8–9 | Wall modules, ribs | Framed bulkhead bays with heavy top and bottom bands carrying lamp pips. Inner panels with vertical channels, grille insets, side pipe columns. A bolted **crown band** with a recessed slot channel. Ribs as structural uprights |
| 10–13 | Floor perimeter, plates, grilles, hazard | Broad **staggered** rolled-steel plates, low contrast. A bevel ladder: dark channel, lit lip on N/W, shaded lip on S/E. Framed grilles. A hazard border with chamfered corners |
| 14–15 | Screens, housings | A thick chamfered bezel, a stepped recess and glass that is "never dead black". **Amber lamp pips either side** of each screen. Content has hierarchy: header band, side columns, a central reticle |
| 16–18 | Controls, lamps | Square buttons (amber/red/white), toggles, a knob, a trackball, a keypad. **The LEDs are the smallest thing on a prop, never its subject** |
| 19–22 | Cables, junctions, service panels, beams | **One** sagging lead does more than any surface detail. Machinery is **bolted to the deck**: a base plate plus a floor socket the cable runs into. Service hatches, beams under the deck |
| 23 | Small technical props | Pods, boxes and sockets that attach to bigger furniture. They are not freestanding clutter |
| 24 | Characters | Compact, a large head, a strong outline. Seated characters read through the chair back |
| 25 | Lighting | A warm key from the ceiling strips (high, west) and a cool sky rim on the shade side. Emissives **bloom** in three rings and **spill** down the surface below them. Floor-line occlusion under every prop. Never solved by global brightness |
| 26 | Material | Dark gunmetal at several layers, brass/bronze hardware and wear, olive and blue-steel storage families, amber light, cyan glass, darker cavities, brighter edges, grime |
| 27 | Layering | Plinth → body → panels → controls → housing → crown → cap. Every layer is a separate casting with its own top plane |
| 28 | Room composition | Back-wall console bank; desks with chairs flanking; a tactical table at the centre with chairs both sides; planters in the back corners; rack pairs on the side walls; a drawer bank. Dense perimeter, clear centre, one hero |

## 2. Stellar prop families (Phase 2)

Each family below has a visible use in a room composition. Variants exist only where they change the silhouette or role.

| Family | Variants | Built from (grammar) | First use |
|---|---|---|---|
| **WS** (`SV.ws.build`) | `standard`, `compact`, `heavy` | **standard:** plinth, two pedestals (framed drawer + door, slot lamps, corner posts), modesty panel (hatch, slot lamp, loom), slab (brass edge, amber slot), raised wings (switch bank / trackball + knobs + keypad) with shoulder blocks, recessed keyboard tray, hinge brackets, housing (top clamps, lamp columns, one wide screen, plate), rear face (grilles, hatch, loom). Side module: an instrument pod with cable and floor socket. **compact:** one pedestal + leg frame, stacked-screen housing. **heavy:** pods at both ends, double housing (main screen + status screen, rest-position gauges, button row) | CON-003/004/005 (standard), CON-022 (heavy), CON-031 (compact) |
| WS side / rear | (views) | The same construction, seen from other cameras. The rear face is built, and shows a **rear repeater** of the approved display when the operator faces away | All cameras |
| **CON** (`SV.con.bank`) | `single`, `double`, `wide` (1–3 bays) | Per bay: a door with a slot lamp or a louvre pair, a control strip, a chamfered upper housing with its own kit. **Full-height dividers** with lamp pips between bays; a continuous crown with brackets. Kits: `screen`, `stack`, `instrument`, `switch`, `readout`. `CON-instrument` is a one-bay instrument kit | CON-030 perimeter |
| **SCR** (`dScreenModule`, `SV.screen`) | `info`, `tactical`, `instrument`, `status`, `multi` | Mounting tabs → housing → bezel → frame → glass → UI surface → shadow cavity → reflection → corner bolts → indicator row. `dScreenBay` adds lamp pips either side | Every screen |
| **EQ** (`SV.eq`) | `rack`, `relay`, `bay`, `service` (red / olive / steel), `locker`, `drawers` | **rack:** blades in two columns on a vented plinth with feet, cap wider than the body. **relay:** an open patch frame (combs with countable pins) and one patch lead. **bay:** three-plate lid, three bays, corner posts. **service:** plinth, hood, hinged door, detailed sides. **locker:** olive double doors. **drawers:** 2×N on feet | SRV-005, STO-005, STO-006, STO-001 |
| **CH** (`SV.chair.build`) | `standard`, `operator`, `command` | Casters, brass star base, gas column + lever, seat pan + cushion, armrests on posts with brass caps, two-cushion back on a chamfered shell, headrest on posts. **operator:** armrest control pads. **command:** wide, quilted, armrest consoles, command-red seam | SEA-002, SEA-001 |
| **TBL** (`SV.table.tactical`) | `tactical` | Plinth; pedestals with access panels; octagonal segments with two inset control panels and a grille; corner blocks with brass caps; an inner bezel lip; neutral grid glass (decorative) | TBL-001 |
| **WALL** (`SV.wall`) | `panel`, `rib`, `grille`, `service`, `console`, `equipment`, `storage`, `junction`; **`upper`** (the high layer: wall-hung `cabinet` / `monitor` / `cable` modules on brackets) | A kick band and a bolted cornice on every face. Ribs flanked by twin conduits. Bays (`SV.wall.BAYS`) group three faces around one feature. Trays with brackets; lamp fixtures | WAL-011 / DEC-008 / LGT-010 |
| **FLR** (`SV.floor`) | `panel`, `grille`, `vent`, `hatch`, `conduit`, `junction`, `hazard`, `beam` | Staggered two-tile plates with bevel lips, rivets and per-plate tone; framed grilles and vents; hatches with recessed pulls; conduit channels with clamps; junction plates; hazard aprons; structural beams | FLR-009/010/011, the deck |
| **DOOR** (`SV.door`) | `standard` (A), `hub` (B), `restricted` (C), closed leaf | One opening = one assembly: threshold (track, grating, titanium edges, hazard bands) → two layered jambs (leaf pocket with the retracted hazard-edged leaf, lamp column, kick band, door control box) → lintel drive housing (louvres, status lamp, destination plate, hazard band) → crown and beacons (B/C). Restricted only where the layout already marks it | H-CMD doors (B) |
| **Small props** (`SV.small` + face painters) | instrument pod, service box, control box, junction box, lamp, indicator, bracket, conduit, socket | Attached to bigger furniture or walls, never scattered alone | Workstations, walls, relays |

## 3. Construction grammar (Phase 3)

The primitives are named in the vocabulary header:
- frame (`frameRect`/`frameCham`);
- corner block / post;
- bevel (chamfer);
- recessed panel (`dRecess`);
- raised panel (`dRaised`);
- grille (`dGrille`, `dLouvrePair`);
- bolt (`dRivets`);
- hinge (`dHinges`);
- handle / slot lamp (`dSlotLamp`);
- control strip;
- lamp (`dAmber`, `dLampCol`, `dLampPips`);
- indicator (`dIndicator`);
- cable (`cable3`, `dLoom`);
- conduit (`dConduit`);
- bracket (`dBracket`);
- bezel and glass (`dScreenModule`);
- shadow cavity;
- drawer;
- access hatch (`dHatch`);
- support leg / feet (`feet`);
- plinth (`plinth`);
- cap top (`capTop`);
- edge wear (`dWear`).

A family is **frame + modules + panels + housing + controls + supports + small details**, never one block.

## 4. Material language (Phase 4)

`SV.M` holds the palette:
- three gunmetal layers (`gunLo` / `gun` / `gunHi`);
- olive and blue-steel storage steels;
- brass hardware;
- amber light;
- cyan glass;
- `cavity` for recesses;
- brighter `edge`.

`prismX` adds, on every cast block:
- a two-layer contact shadow;
- floor-line occlusion rising up the face;
- a warm key on lit faces and a cool rim on shaded faces;
- a dark outline and a lit top edge.

Face painters add edge wear and small grime patches. Cap tops are separate castings, each with a bolted inset.

## 5. Screen language (Phase 5)

Every screen is a physical module (§2, SCR). Content rules:
- **Approved content** (registry displays) renders through the module unchanged. A console whose operator faces away from the camera shows the same approved display on the housing's rear repeater.
- **No data:** the glass shows an **inactive UI surface**. This is etched structure only: panes and mullions (`multi`), header rule and column divider (`info`), reticle frame (`tactical`), a single ring (`instrument`), a header rule (`status`). It never shows values, numbers or invented telemetry.
- **Occupancy standby** (an agent present, a producer exists): corner brackets and a faint scan only. Occupancy ≠ work.

## 6. Composition language (Phase 6)

A room is composed in five depths: **large structure → medium objects → small objects → micro details**.

- **Wall:** a rib every fourth segment; a bay of three faces around one feature; trays; lamp fixtures over alternate bays.
- **Perimeter:** a rhythm of bank modules (3 / 2 / 1 tiles), tall racks between groups, and occasional **gaps** where the wall system shows through. Lockers close each run.
- **Workstation:** body, screen, chair, side pod, cable, floor socket, hazard apron, task light.
- **Midground:** secondary desks, equipment bays, relay frames on hazard pads, service cabinets backing the perimeter.
- **Foreground:** deck plates and beams, grilles, hatches, conduits ending in junction plates.
- **Centre:** one hero, kept clear by the circulation ring.

## 6b. Layers and groups (added in V5.1)

- **Layers:**
  - LOW: floor modules, plinths, cabinets.
  - MEDIUM: desks, consoles, bays, storage.
  - HIGH: racks, `SV.wall.upper` modules, screens, ribs, lamps.
  A room composes all three, never one flat band.
- **Groups:** equipment that works together sits together: a workstation with a rack pair, a service cabinet or an equipment bay. A group gets a hazard-bordered deck zone, one light pool, and a conduit to the perimeter.
- **Designed open space:** circulation is drawn as treadway runners with hazard edges, not left as bare deck.

## 7. Reuse plan (the same modules, different functional compositions)

| Room | Composition with the vocabulary (proposal, for owner approval per room) |
|---|---|
| H-LAB | WS-compact research benches; CON-wide with `instrument`/`readout` kits; EQ-rack pairs; SCR `multi` on wall consoles; the projector column as an EQ-relay-like open frame |
| H-HAB | Mostly lounge furniture outside this vocabulary. Uses WALL `panel`/`storage`, EQ-locker (olive), FLR panels with softer tone, warm lamp pools |
| L1 Market Specialists | WS-standard per specialist; SCR `info` with approved displays; a CON-double behind |
| L2 Technical Deck | WS-heavy for the lead; CON-wide `instrument`; EQ-rack row |
| L3 Debate Chamber | Two facing WS-compact rows; TBL-tactical (smaller) as the moderator table; WALL `console` |
| L4 Data Core | EQ-rack and EQ-relay rows on hazard pads, FLR conduits and junction plates; a CON-single per aisle |
| L6 Memory Archive | EQ-drawers and lockers in rows; WS-compact archivist desk |
| L7 Performance Lab | CON-wide `readout`/`instrument`; WS-standard |
| L9 Execution Bay | WS-heavy; CON-double; EQ-service (red); hazard aprons |
| L10 Risk Control Room | WS-heavy; WALL `equipment` with rest-position gauges; EQ-service (red) |
| Corridors | WALL faces (panel, rib, grille, service door, junction), FLR treadway and conduits, lamp fixtures; no furniture beyond the approved repeaters |

Rule: rooms change **composition and function**, never the construction language. A new variant is added only when a room needs a silhouette the families cannot make.
