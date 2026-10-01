# Stellar × StarNet Visual Language Adaptation Guide V1

| | |
|---|---|
| **Status** | Proposal for owner review. **Nothing is implemented.** No renderer, geometry, registry or camera change is made by this document |
| **Purpose** | Reset the visual direction: Stellar adopts and adapts StarNet's existing visual language instead of inventing a new style |
| **Keeps** | Stellar architecture, rooms, room functions, doors, topology, anchors, display identities and engine-truth rules |
| **Does not copy** | StarNet functions, StarNet product behaviour, StarNet character skins or brand |
| **StarNet source studied** | `/home/user/androoagi/starnet` at `fbddbf99` (read-only) |

StarNet sources read for this guide:
- `docs/station-remaster/DIRECTION.md`, `STYLE_LOCK.md`, `PROP-INVENTORY.md`, `DEFAULT-STATIONS.md`, `SURFACE_MOUNTS.md`, `WORKSTATION-ANIMATION.md` and `camera-audit/README.md`;
- `docs/clean-style/README.md` and `cadet-master.png`;
- the bridge reference `docs/station-remaster/bridge-reference.png`, the approved prop sheet `frontend/assets/industrial/complete-sheet/starnet-props-full-sheet.png`, the live room capture `docs/station-remaster/corners-bays/live-room.png` and the seat audit `authored-furniture/native-seat-audit.png`;
- `.github/media/station-iso.png`;
- the spatial constants already verified in `docs/STELLAR_SPATIAL_SCALE_V1.md`.

**It supersedes, if approved:** the H-CMD "Visual V2" art pass, which is uncommitted (§8). It also reopens the Visual Bible and Character Registry rules listed in §2.

---

## 1. StarNet visual principles extracted

| # | Principle | What StarNet does (source) |
|---|---|---|
| **P1** | **Camera** | One fixed, high, overhead **oblique** camera with **horizontal long edges**, a consistent vertical rise and grounded silhouettes (DIRECTION "Preserve the reference"; PROP-INVENTORY "Projection and proportion rules"). Default zoom is 2× (range 0.5×–6×). The runtime station is **not** a 45° isometric diamond. `station-iso.png` is a marketing render, and the live room capture is oblique |
| **P2** | **Palette** | Near-black gunmetal and charcoal plates; desaturated olive structure; **muted amber / aged brass** hardware and worn hazard markings; **bounded cyan / teal screens**. Rejected: white / minimal stations (DIRECTION, 2026-09-13), giant neon bloom, photographic microtexture (STYLE_LOCK) |
| **P3** | **Materials** | Broad painted planes, deep recesses, restrained bevels, controlled edge highlights. "Detail supports the main shape instead of covering every surface." Leisure areas use real material variety: stained wood, coloured upholstery, ceramic, glass, foliage (STYLE_LOCK) |
| **P4** | **Room shell** | Heavy structural bulkheads: thick, ribbed walls with vents, cabling, fasteners and chamfered corners. Wall light fixtures are spaced along the shell. The hull exterior reads as solid mass against a starfield / nebula background (bridge reference; live room) |
| **P5** | **Floors** | Dark deck plates with panel seams, tread and grate panels, floor vents, **amber hazard-stripe borders** marking zones and walkways, and lane markings (bridge reference) |
| **P6** | **Room proportions** | Standard room **18 × 11 tiles**, which the owner keeps (rejected widening). Built stations combine several of these rooms with corridors. Large rooms such as the bridge deck run around 22 × 18 |
| **P7** | **Room composition** | **Dense perimeter, open centre.** Equipment banks line the back and side walls, a single hero object (tactical table) sits in the centre, and the command chair sits at the centre of the back bank. Chairs sit at every console. Clear door approaches (bridge reference; DEFAULT-STATIONS) |
| **P8** | **Workstations** | Every workstation is a **desk + chair + separate monitor masses + keyboard**. Desks are 3 tiles wide in the remaster; there are console 2×1, long console 3×1, bench 4×1 and docks 2×2. A seat anchor sits in front, centred. Screens are **dark when unoccupied**. A seated body powers the cyan glass and a slow phosphor sweep. Real work heat comes only from real activity (WORKSTATION-ANIMATION) |
| **P9** | **Screen placement** | Screens are built into furniture (console monitors, desk screens, table surfaces) and into **wall banks above consoles**. Free-floating billboards do not exist. Screen art must not invent progress, balances or results (STYLE_LOCK rule 7) |
| **P10** | **Agent scale and presence** | Agent standing height **19 world px** (0.25 × 76 source). Compact, readable body: about 2.5–3 heads, large clean head, simple limbs, dark outline. Bodies are small next to furniture (a 3-tile desk is about 36 px wide; an agent is about 10 px). Agents **sit** at desks, recliners, booths and benches with correct seat anchors (seat audit). A **name plate on the workstation** identifies who works there (live room: "CREW BOLT", "ENGINEER") |
| **P11** | **Lighting** | Physical wall fixtures: **cool** in command / lab, **warm** in quarters. Soft virtual room fill, low deck ambient (about 0.08 lift), **screen spill** from console banks and tactical tables onto nearby surfaces, contact shadows and area-light occlusion. Lighting never fakes work (camera-audit "Lighting") |
| **P12** | **Object density** | Readable at game size. Variety comes from construction and function within one palette, not from unrelated styles. "Do not treat more detail as an improvement." Decorative / atmospheric motion (fish, steam, lamps) is never proof of work (PROP-INVENTORY) |
| **P13** | **Mounting and contact** | Tabletop objects lift exactly 8 world px onto valid table hosts. Every prop has measured floor contact and correct sort order. Seated bodies and furniture backs occlude correctly (SURFACE_MOUNTS) |

These match Stellar's own engine-truth rules: screens show nothing that did not happen, and occupancy is not work.

---

## 2. Conflicts with approved Stellar decisions (owner decisions required)

Adopting the StarNet visual language contradicts several approved Stellar documents. Nothing changes until the owner decides.

| # | Topic | Approved Stellar position | StarNet language | Proposal |
|---|---|---|---|---|
| **SV-1** | **Artwork rights** | Adaptation A31: StarNet art, sprites, props, painters, CRT, fonts, sfx and brand are **DO NOT USE**. `STARNET_REUSE_AUDIT.md` §2 quotes StarNet's `NOTICE.md`: the MIT licence covers **code only**, and the station artwork, sprites, logo and brand belong to Andrew Sims and are **not licensed** | Raster art in `frontend/assets/industrial/…` and character frames | **Adapt the language, not the pixels.** Stellar draws its own assets to StarNet's rules (§1). Reusing StarNet's actual art files requires written confirmation from the art's owner that Stellar may use it. Even then, the franchise-likeness skins in `frontend/assets/agent-demo` (for example `harrypotter`, `robocop`, `xenomorph`, `morpheus`, `vaultboy`, `ricksanchez`, `pepe`) are **never** used |
| **SV-2** | **Palette** | Visual Bible C1: "balanced identity… must not become a fully dark vessel". Warm off-white structural panels, titanium trims, deep navy floors | Near-black gunmetal, amber / brass hardware, cyan screens | Adopt StarNet's dark industrial base. Keep Stellar's identity through restrained accents: thin titanium trim, department accents (CMD red, SCI blue, OPS gold), and the Habitat's warm wood. The off-white panels are retired as the main wall material. Needs a C1 revision |
| **SV-3** | **Camera** | Iso · right (north-east, 45°), frozen | High overhead oblique, horizontal long edges (P1) | StarNet's whole prop and room language is authored for the oblique camera. **Recommended:** make the oblique view (the current "Plan" view with a vertical rise, from the south) the presentation camera. Keep Iso · right only if the owner prefers the angle, accepting that every StarNet-style asset then needs a new projection. **This reopens the frozen camera decision** |
| **SV-4** | **Character proportions** | Character Registry §1: "slightly stylised humanoids (about 6–7 heads tall)" | Compact, about 2.5–3 heads at 19 px | Adopt StarNet's compact readable proportions at the **same 19-unit height** and keep Stellar's identity layer (§5). Needs a Character Registry §1 revision |
| **SV-5** | **Hub shapes** | Circular hubs and radial R rooms (approved topology) | Rectangular rooms with chamfered corners | **Keep the topology.** Render hub rims in StarNet's bulkhead language as heavy segmented rims with chamfered joints, ribs and fixtures. No hub becomes a rectangle |
| **SV-6** | **Density / new furniture** | Room sheets list a minimal set. Geometry V1 frozen with 87 footprints | Dense perimeter banks (P7) | Density needs **new registered assets and footprints**: perimeter banks, cabinets, wall equipment. Each addition goes through the Asset Registry and a geometry re-check, with no fake data on any screen. Proposed per room after approval (§6) |

---

## 3. Mapping: StarNet room type → Stellar room

StarNet's room kinds (Adaptation A28) are hab, bridge, lab, quarters and storage. Its station builds add workshop, review, analysis, archive, communications, planning and library / lounge rooms. The **visual solution** is borrowed; the **function** always stays Stellar's.

| Stellar room | Function (unchanged) | StarNet visual equivalent | Visual solutions to adopt | Do **not** copy |
|---|---|---|---|---|
| `H-CMD` Main Command | Decision hub; PM, Research Manager, Supervisor, Trader, Proposal Builder, budget | **Bridge** (bridge reference) | Perimeter console banks on the far rim; the central tactical-table treatment for `TBL-001`; command chair at the bank's centre; chairs at every console; cool fixtures; screen spill | Bridge "ship" fiction; decorative fake tactical data |
| `H-LAB` Lab / Research Hub | Research collection, validation, macro | **Lab + analysis room** | Lab benches, specimen / analysis hardware look, a central projector (dome ring); cool fixtures | Lab experiments, fake readouts |
| `H-HAB` Habitat | Rest, café, games, recovery | **Quarters + lounge** | Warm fixtures, wood and upholstery, couch / recliners, pool table, bar counter, plants, rugs | Arcades, jukebox, trophies and achievements (not in Stellar's approved list) |
| `L1` Market Specialists | Family desks | **Analysis room** | Three-tile desks with chair and monitors, name plates, glass partitions | — |
| `L2` Technical Deck | Technical analysis | **Planning / analysis** | Wall consoles with chairs, a tactical-table look for `TBL-002` | Fake charts (only real candles, via `DSP-TEC-01`) |
| `L3` Debate Chamber | Bull / bear / risk review | **Review room** | Review desk, podium consoles, central stage table with restrained spill | Courtroom / arena dressing |
| `L4` Data Core | Snapshot validation, journal | **Storage / server room** | Server racks, memory core, cable runs, dense vents | Capability-surge behaviour |
| `L6` Memory Archive | Trade history, replay | **Archive / library** | Shelving and file cabinets in the dark-steel language, reading table | Decorative achievements |
| `L7` Performance Lab | Metrics | **Review / analysis** | Terminal and review table | Rankings / leaderboards |
| `L9` Execution Bay | Paper pre-flight and execution | **Workshop + outbox dock** | Dispatch Tube in the outbox-dock language (conveyor mouth, armoured collar); hazard-stripe launch deck | StarNet outbox counts (Stellar uses its own events) |
| `L10` Risk Control | Intake, rules, sizing, breaker | **Intake dock + operations room** | Intake counter in the intake-dock language; grating floor; hazard borders around `risk.core` | Security theatre; fake alarms |
| `COR-N` / `COR-S` | Transit | **Corridors** | 3-tile corridors with lane lines, wall ribs, fixtures and floor decals | — |
| L5, L8, R1–R6 | Reserved | **Unfurnished room shell** | Dark bulkhead shell, sealed door, RESERVED plate | — |

---

## 4. Furniture and workstation rules

1. **Footprints stay Stellar's** (Geometry V1 is approved). StarNet supplies the **construction and look**, not new sizes. Any footprint change is a geometry change and needs approval.
2. **Every workstation is a set:** body + desktop + **separate monitor masses** + keyboard / input surface + **chair** at the anchor. Approved Stellar consoles (`CON-*`) take this form.
3. **Screens follow P8 and Stellar truth:**
   - glass is **dark when nobody is seated**;
   - a seated agent powers **neutral cyan glass with a slow sweep**. This is occupancy, not work;
   - content appears only through the approved `DSP-*` displays and their real sources;
   - no StarNet-style decorative UI art that looks like data.
4. **Wall-bank rule:** displays belong **in or on furniture and wall banks**, not as floating panels. Room-sheet wall displays sit in a framed bank recess on the wall above the related console. The approved `DSP-*` identities and positions stay.
5. **Hero object per room:** one central object carries the room's identity:

   | Room | Hero object |
   |---|---|
   | H-CMD | `TBL-001` command table |
   | H-LAB | `EQP-005` dome ring |
   | H-HAB | `PLT-005` central tree |
   | L2 | `TBL-002` chart table |
   | L3 | `TBL-007` stage |
   | L4 | `EQP-001` column |
   | L9 | `EQP-002` Dispatch Tube |
   | L10 | `CON-012` intake |

   It gets the strongest silhouette and the restrained screen spill.
6. **Materials:**
   - work furniture is gunmetal / charcoal with amber-brass hardware and department-accent trim lines;
   - leisure furniture (H-HAB) uses wood, upholstery and plants;
   - no white ceramic furniture;
   - no glossy neon.
7. **Mounting:** tabletop items lift 8 world units onto valid hosts. Every prop has a measured floor contact and a contact shadow. Furniture backs occlude seated agents.
8. **Name plates:** every assigned workstation carries a small plate with the role code and name (for example "T3 · STRUCTURE"). This is Stellar's existing role-plate rule, drawn the StarNet way.
9. **Seats:** operators **sit** at their consoles. The command chair, judge seat, café seats, sofas, benches and pods use seated poses with correct anchors.

---

## 5. Agent presentation rules

| Rule | Value |
|---|---|
| Standing height | **19 world units** (unchanged; matches StarNet 19 px) |
| Proportions | Compact and readable: about **2.5–3 heads**, large clean head, simple limbs, a 1-unit dark outline (StarNet clean-cadet construction). Subject to SV-4 |
| Identity layer (Stellar's own) | Charcoal two-tone uniform with the **department colour** on yoke and cuffs (CMD red / burgundy, SCI blue, OPS gold, SYN white-cyan) and the **shape icon** on the chest (hexagon / circle / square / diamond). Varied skin tones, hair and builds. No rank insignia |
| Faces | Minimal and readable at game size: a simple face or none. No likeness of real people or franchises (SV-1) |
| Facings and poses | 8 facings; idle, walk, sit, work-at-console and gesture. Seated whenever the role sits at a console |
| Presence | Workstation name plate (P10) and a small state badge (idle / no producer / role state). Badges never replace the plate |
| Truth | Active work poses only from real events (Adaptation A20). "Idle · no producer" stays visibly distinct |
| Not copied | StarNet skins, the cadet image itself, sentience / idle personality (A30) |

---

## 6. Density rules

### Measured today (Geometry V1, blocking footprint tiles ÷ floor tiles)

| Room | Floor tiles | Blocked | Density | Items |
|---|---:|---:|---:|---:|
| H-CMD | 1094 | 33 | **3 %** | 7 |
| H-LAB | 723 | 29 | **4 %** | 10 |
| H-HAB | 707 | 27 | 4 % | 26 |
| L1 | 135 | 7 | 5 % | 3 |
| L2 | 126 | 25 | 20 % | 8 |
| L3 | 150 | 17 | 11 % | 8 |
| L4 | 81 | 9 | 11 % | 5 |
| L6 | 72 | 7 | 10 % | 3 |
| L7 | 72 | 4 | 6 % | 2 |
| L9 | 150 | 9 | 6 % | 4 |
| L10 | 150 | 13 | 9 % | 6 |

StarNet reference points:
- **Default room** (18 × 11 = 198 tiles, 8 props): about 9 %, concentrated on the walls.
- **Bridge-scale room:** about 15–20 %, with the perimeter fully lined and the centre held by one hero table.

### Rules

1. **Perimeter band:** in working rooms, the wall-adjacent 1-tile band of the back and side walls (the walls that stay visible from the camera) should be **60–80 % occupied** by equipment: console banks, cabinets, racks and wall equipment. The camera-facing wall stays clear, since it is cut away.
2. **Open centre:** keep a central floor, or the hero object on its own, with a **2-tile clear ring** around it.
3. **Walkways:** keep every door approach (2 tiles) and every anchor route clear. Two-agent passing stays where Geometry V1 provides it.
4. **Target density:**

   | Room type | Target |
   |---|---|
   | L-rooms | 12–25 % |
   | Work hubs (H-CMD, H-LAB) | 8–15 %, mostly perimeter |
   | Habitat | 8–12 %, spread out as social clusters |

5. **Detail sits inside objects:** vents, ribs, cabling and keyboards are part of each object, not scattered clutter. Use floor decals (hazard borders, vents, cable runs) for texture without blocking.
6. **Every added item must be a registered asset** with a footprint, and pass the geometry checks. Screens on added banks are either one of the approved `DSP-*` displays or **dark glass**. They never show decorative data.
7. **Wall-mounted equipment** (panels, vents, cable trays, fixtures) has no footprint. It adds density without blocking, which matches StarNet's wall detail.

---

## 7. Example redesign concept: H-CMD

This concept is drawn in the StarNet bridge language. Topology, doors, anchors and the 7 approved H-CMD items keep their positions. Items marked **NEW** need asset registration and a geometry check (SV-6), and none of them carries data.

```
                     (far rim — fully lined bulkhead bank)
        ╔═══════════════ NEW perimeter console bank (dark glass) ═══════════════╗
        ║  DSP-CMD-03     [CON-003 ops + chair]   DSP-CMD-01 MAIN    [CON-004 trader + chair]  DSP-CMD-02  ║
        ║  wall bank       name plate "O1 · OPS"  VIEWSCREEN bank     "U4 · TRADER"         wall bank   ║
  DR-N-CMD ▓                                        DSP-CMD-04 band                                    ║
        ║   NEW cabinets           ▒▒▒ hazard-stripe border around the dais ▒▒▒                       DR-CMD-HAB
        ║                       ┌──────────── FLR-002 dais (raised) ────────────┐                      ║
        ║                       │ SEA-001 command chair (back bank centre axis)  │                      ║
        ║                       │   TBL-001 command table: thick bevelled frame, │                      ║
        ║                       │   dark glass surface, restrained cyan spill,   │                      ║
        ║                       │   DEC-007 decorative globe (no data)           │                      ║
        ║                       └────────────────────────────────────────────────┘                      ║
  DR-S-CMD ▓   [CON-005 proposal + chair]                                      SEA-005 bench, DSP-CMD-05 ║
        ║      "P1 · PROPOSAL"        [CON-022 budget + chair, monitors dark]       wall bank            ║
        ╚══════════ near rim: cut away (camera-facing), low bulkhead cap, door frames kept ══════════════╝
```

| Element | Concept (StarNet language) | Approval |
|---|---|---|
| Rim | Heavy segmented gunmetal bulkhead ring, chamfered joints, ribs, vents, cable trays. Amber utility fixtures every 3–4 tiles, cool white in command. Starfield beyond the hull | Visual only (rim already approved) |
| Floor | Dark deck plates with panel seams. **Amber hazard-stripe border** around the dais and the console aprons. Floor vents. Walkway lane markings between the three doors | Visual only |
| Dais + table | Raised `FLR-002`. `TBL-001` as a StarNet-style tactical table: thick bevelled gunmetal frame with brass hardware, dark glass top, a **neutral grid** surface (no values), restrained cyan spill on the dais. `DEC-007` globe stays decorative | Visual only |
| Command chair | Heavy high-back chair on the back-bank centre axis, burgundy accent (CMD) | Visual only |
| Role consoles | `CON-003` / `-004` / `-005` / `-022` as 3-tile StarNet-style desks: dark body, brass trim, two or three monitor masses, keyboard, chair, **name plate**. Glass is dark until seated, then neutral cyan; the `CON-022` monitors stay dark (no producer). Their `DSP-CMD-09`…`-12` appear in the desk screens, not as floating boards | Visual only |
| Wall displays | `DSP-CMD-01` main viewscreen, `-04` pipeline band, `-07` alert band, `-08` mode plaque, `-02` / `-03` / `-05` / `-06` walls, mounted **in framed bank recesses** on the rim at their approved clock positions. They show their offline states | Visual only (positions unchanged) |
| **NEW** perimeter bank | A continuous low console bank along the far rim between the role consoles, at a 1-tile depth: dark glass, no data, no anchors. It gives the bridge-style "fully lined" perimeter | Needs a new asset ID, footprints and a geometry re-check |
| **NEW** storage cabinets | Two or four gunmetal cabinets near the doors (StarNet storage language) | Needs a new asset ID and footprints |
| Lighting | Cool wall fixtures, low deck ambient, screen spill from the banks and table, contact shadows. Red only as thin CMD accent lines | Visual only |
| Agents | Compact StarNet-proportion crew at 19 units, seated at consoles, U8 in the command chair, U3 at the table head; department colour plus shape icon | Needs SV-4 |
| Density | About 3 % today. About 8–12 % with the perimeter bank and cabinets, concentrated on the far rim, with the centre ring and all door approaches clear | Needs SV-6 |

---

## 8. Proposed sequence (after owner decisions)

1. **Decide SV-1 to SV-6.** The camera (SV-3) and palette (SV-2) decisions drive everything else.
2. **Park the uncommitted H-CMD "Visual V2" pass.** Its off-white / navy look and 6–7-head figures conflict with this guide. Recommendation: discard it, and keep only its harmless structural ideas (seat insets, split chair backs for correct occlusion).
3. **H-CMD calibration room:** build the shell, floor, table, one console set, the chair and one agent to the StarNet rules. Compare it beside the StarNet bridge reference at 2× and 4× before anything else, as StarNet itself does ("one representative asset at a time").
4. Register any new H-CMD assets (perimeter bank, cabinets). Rerun the geometry and visual checks, then finish H-CMD.
5. Roll out room by room following §3. Each room is checked against its StarNet equivalent at playable zoom before moving on.
6. Keep `tools/visual_prototype/build.py --check` and the smoke test green at every step. Stellar truth rules apply throughout: no fake data, occupancy ≠ work, and no-producer displays stay NOT AVAILABLE.
