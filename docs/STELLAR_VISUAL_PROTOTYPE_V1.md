# Stellar Visual Prototype V1

**Status:** first visual pass, for owner review. Nothing here is committed yet.
**File:** [`prototype/STELLAR_VISUAL_PROTOTYPE_V1.html`](prototype/STELLAR_VISUAL_PROTOTYPE_V1.html). It is one self-contained page: no server, no network and no external assets.
**Builds on:**
- the approved geometry ([`STELLAR_SPATIAL_SCALE_V1.md`](STELLAR_SPATIAL_SCALE_V1.md): 1 tile = 12 units, agent 19 units, 0.8-tile spacing);
- the Visual Bible V1;
- the approved room sheets, the Corridor Design;
- the Screen, Character and Asset registries.

StarNet was used as a spatial and technical reference only. No StarNet art, sprite or UI is used.

## 0. Camera decision (frozen)

**Owner decision (camera freeze):** the preferred default presentation is **Iso · right**.

| View | Status | Camera | Camera-facing (cut-away) walls |
|---|---|---|---|
| **Iso · right** | **Default; preferred presentation** | Isometric, from the **north-east**: H-LAB on the right, H-HAB lower left, depth rising toward the upper right | **North** and **east** walls; the **north / north-east** arc of each hub rim |
| Iso · left | Alternative / debug | Isometric, from the south-east (the first-pass view) | South and east walls; the south / south-east arc |
| Plan | Unchanged | Top-down, Floor Plan north up | South walls |

- This is a camera transform only. The Floor Plan coordinates, room positions, doors, anchors and topology are unchanged.
- The camera **elevation** stays open (Visual Bible VB-2). Only the direction is frozen here.
- The cutaway rule itself is unchanged: a wall is lowered only where it would hide the floor behind it, and doors in a cut-away wall keep their frame, threshold and opening (C4).

## 1. Launch

| Option | Command / URL |
|---|---|
| Open the file directly | open `docs/prototype/STELLAR_VISUAL_PROTOTYPE_V1.html` in any current browser (Chrome, Edge, Firefox, Safari) |
| Local server | `python3 -m http.server 8000 --directory docs/prototype`, then <http://localhost:8000/STELLAR_VISUAL_PROTOTYPE_V1.html> |
| Deep links | `?focus=L2`, `?focus=Station`, `?view=plan`, `?z=4`, `?grid=1`, `?anchors=1`, `?preview=1`, `?labels=0`, `?x=…&y=…` (world units) |

## 2. Camera and controls

| Control | Action |
|---|---|
| Default | **2×**: 1 tile = 24 px, agent ≈ 38 px; camera range **0.5×–6×** |
| Mouse wheel / pinch / `+` `−` | Zoom about the cursor |
| Drag / arrow keys | Pan |
| Focus panel (right) | Fly to the station, H-CMD, H-LAB, H-HAB, COR-N, COR-S, L1–L4, L6, L7, L9, L10, L5, L8 or R1–R6. Clicking a room label also focuses it. `0` = station overview |
| Iso · right / Iso · left / Plan | **Iso · right (default):** the camera looks from the north-east, so H-LAB sits on the right and the depth rises toward the upper right. In this view the north and east walls are the cut-away walls. **Iso · left:** the first-pass view, with the camera from the south-east (Visual Bible §4.1) and the south and east walls cut away. **Plan:** top-down, in the Floor Plan's north-up orientation. All three are camera transforms only: the Floor Plan coordinates, rooms, doors and topology are unchanged. Deep link: `?view=isoR`, `?view=iso` or `?view=plan` |
| Minimap (bottom left) | The Floor Plan, north up, with the current view outlined. Click to move there |
| Grid (`G`) | Geometry debug: the tile grid, blocked tiles (red) and door lanes (yellow) |
| Anchors | Debug: every anchor; names from 3× |
| Hover / click | Tooltip and inspector for agents, displays, furniture and doors (IDs, sources, registry status) |
| State preview | **Design sample only**: producer-backed agents take their working pose, their console pool light (`LGT-002`) and their first role-state word. A banner marks it as *not telemetry*. Off by default |

## 3. What is implemented (first visual pass)

1. **Station floor:**
   - `FLR-001` deep navy working floors with soft panel seams.
   - `FLR-003` grating in L10.
   - `FLR-004` warm wood laminate in H-HAB.
   - `FLR-005` corridor floor with a titanium lane inlay and the `LGT-004` guide strip toward both corridor ends (CD-7).
   - The `FLR-002` dais (lighter navy, titanium band, thin command-red line) and the `FLR-008` launch-deck marking.
   - Titanium inlays from the room sheets: the L1 aisle, the L2 chart-table frame, the L3 stage ring, the L4 column ring, the H-CMD walkway ring and the H-LAB core ring.
2. **Walls and boundaries:**
   - Warm off-white panels (`WAL-001` / `WAL-002`) with soft seams, a titanium base trim and the `LGT-001` cove line on full-height walls.
   - L10 alternates gunmetal ribs with off-white panels (RC-2). Corridors carry a light rib rhythm (`DEC-005`).
   - Graphite door niches. Solid hull infill (`WAL-009`) between rooms.
   - **Cutaway (C4):** a wall is lowered to a cap only where it would hide the floor behind it. Each wall's height is computed from the active camera, so outer walls stay tall. With the default Iso · right camera, the north and east walls face the camera (§0).
   - The hub rims are smooth curves drawn over the tile edge (Asset rule 2.5). The H-HAB rim carries window sections (`WAL-003` + `DEC-001`) on the outer south rim and the living wall (`PLT-004`).
3. **Doors (all 21):**
   - Visible frame, threshold strip and opening in every wall (C4). Normal indicator in cyan-white.
   - `DR-L9` / `DR-L10` use the restricted variant (`DOR-008`): the `SGN-006` icon plate, a hatched threshold marking and an amber indicator. They read correctly without colour.
   - Hub doors are curved-rim doors (`DOR-009`).
   - L5, L8 and R1–R6 doors are closed, with the dimmed normal indicator and the `SGN-007` RESERVED plate (VB-6).
4. **Corridor surfaces:** both corridors at 3 tiles, evenly and brightly lit. With Iso · right the corridors' **north** walls face the camera and carry nothing; the two alert repeaters sit on the south walls (Corridor Design CD-11).
5. **Furniture visual forms:** all 87 approved footprints get Stellar forms that follow the room-sheet materials. Examples:
   - graphite consoles with a department-accent edge on the operator side;
   - the low L2 chart table with a restrained projection surface;
   - slim L3 podiums and the low review desk;
   - the L4 information column (not a reactor) and its low cabinets;
   - the L6 low record shelf **with empty slots** (no Record Crystal is shown without a journaled trade);
   - the L9 clean pneumatic Dispatch Tube;
   - the H-CMD circular table with the decorative globe (`DEC-007`), the H-LAB dome ring;
   - the H-HAB central tree, café, billiards, lounge, pods and benches.

   Dormant feed consoles (R3–R6) are grey.
6. **Agent visual forms:**
   - All 41 rendered characters stand at their Character Registry home anchors, at the 19-unit scale.
   - Each wears a charcoal base with a department-colour yoke and cuffs, plus the chest shape icon (CMD hexagon, SCI circle, OPS square, SYN diamond). The Habitat host is a white and cyan synthetic.
   - Builds, skin tones and hair vary. Agents face their console; seated agents sit.
   - **Active / idle distinction:**
     - Agents whose role has a producer are shown in full colour.
     - Agents the registry marks *no producer / not built / dormant* are desaturated, with a dashed badge reading "idle · no producer".
     - With no telemetry, every agent is shown at home in the default idle pose. State preview shows the working variant, clearly labelled as a sample.
7. **Screens / displays:**
   - 72 displays: every non-planned row of the Screen Registry, at its room-sheet position. The 9 `PLANNED` IDs are not rendered (Screen Registry §1.6).
   - Each shows **its approved offline state**, because the prototype has no engine link:
     - **NOT AVAILABLE · feed** for the 11 no-producer displays;
     - **MODE UNKNOWN** (amber + `?`) on the mode plaques;
     - **NO TELEMETRY** on the alert band and repeaters;
     - **AWAITING DATA** on everything whose producer exists.
   - Partial displays also show their approved sub-lines (live quotes, drawdown, reward:risk, XAG, the order steps without a producer: NOT AVAILABLE / NOT CONFIGURED).
   - The pipeline band shows the engine's stage order, unlit. The L2 session ring shows UTC from the UI clock, as the registry allows.
   - **No value, price, P&L or count is shown anywhere.**
8. **Room lighting:**
   - H-CMD: neutral white.
   - H-LAB: the cool dome light (`LGT-009`).
   - H-HAB: warm skylight and pendants (`LGT-006`).
   - L10: cold panel light (`LGT-005`).
   - Research rooms: cool white. OPS rooms: neutral white.
   - Corridors: even and bright.
   - Reserved shells stay unlit. Lighting never encodes a data state (C7), and there is no alert tint (no telemetry).
9. **Room labels:** screen-space plates that never cover a room interior and avoid each other. Hubs have the strongest labels, then rooms, then corridors and reserved slots, each with its department colour dot.
10. **Reserved rooms:** L5, L8 and R1–R6 are dark, unlit shells with sealed doors and RESERVED plates. R1–R6 stay rotated and radial (Floor Plan Q5).
11. **Visual hierarchy:**
    - Hubs are the largest volumes, with hero objects (dais table, dome ring, central tree) and the strongest light.
    - Rooms are mid-scale with department accents. Corridors are neutral circulation.
    - Hull infill reads as solid mass, and reserved slots are dark.
12. **Camera and zoom controls:** see §2.

## 4. Placeholders (not final)

- Every form is procedural **placeholder art**: simple prisms and cylinders, with no textures, final models or character art (VB-7 hero objects, the Character Bible).
- Agents are simple figures. They have no walk cycles, no animation and no expression.
- Exact colour values (VB-4) and the exact camera elevation (VB-2) are working values. The camera **direction** is frozen (§0).
- The L10 core rail (RC-4) has no asset ID in the Asset Registry, so it is drawn as a dashed floor marking only.
- The `habitat.ring` circulation marking and the H-LAB window band (HL-4, open) are not drawn.
- Not implemented, as instructed: telemetry or engine link, chat, owner avatar, MT5, live trading, audio, final animation and effects, packaging.

## 5. Checks

| Check | Result |
|---|---|
| Geometry consistency (footprints, anchors, door approach, BFS connectivity, corridor width, occlusion), rerun after the two corrections below | **0 issues** |
| Displays: every non-planned registry row rendered once, none of the 9 planned, room and hardware match, the no-producer rows show NOT AVAILABLE, **no digit in any display text** | pass (72 / 9) |
| Characters: rendered set = registry ACTIVE characters with a home anchor (41); deferred, future and retired not rendered; home room, anchor and department match | pass |
| Furniture: every asset ID exists in the Asset Registry and none is RETIRED | pass (87) |
| Doors: 21 doors; restricted = `DR-L9`, `DR-L10`; `DOR-001` ×8, `DOR-008` ×2, `DOR-009` ×11 as in the Asset Registry; L5 / L8 sealed | pass |
| Self-contained: no external URL, image or StarNet reference | pass |
| Stellar tests / ruff | 891 passed / all checks passed |

## 6. Geometry findings from this pass

1. **`SCR-006` in H-LAB was missing from the geometry.** It is the `DSP-LAB-05` projector column, which the Asset Registry lists as "blocks 1 × 1". It is now placed at the dome ring's east edge, and all checks still pass.
2. **`PLT-003` desk plants** were a floor tile in L1. The Asset Registry says they sit "on desks" with no footprint, so they are now drawn on the `CON-009` desks. L1 gains one free tile.
3. **The H-CMD and H-HAB rims overlap slightly** (the approved circles meet in a ±20-unit lens). The prototype closes the lens with a short junction collar around `DR-CMD-HAB`. Needs an owner decision: use `WAL-010` (defined for the R-room junctions) or a new junction piece.
4. **Displays on camera-facing walls (updated for the frozen Iso · right camera).** In the default view the north and east walls and the north / north-east rim arcs face the camera, so their displays are drawn as raised standing panels at their approved wall positions instead of wall-mounted. 30 displays are affected:
   - **H-CMD:** `DSP-CMD-01` main viewscreen, `-02`, `-03`, `-04` pipeline band, `-05`, `-07` alert band, `-08` mode plaque (north / north-east rim);
   - **H-LAB:** `DSP-LAB-06`, `-07`, `-08`; **H-HAB:** `DSP-HAB-01`, `-04`;
   - **L2:** `DSP-TEC-02`…`-06`; **L3:** `DSP-DEB-02`, `-04`, `-06`; **L4:** `DSP-DCR-02`, `-06`;
   - **L6:** `DSP-MEM-01`, `-02`; **L7:** `DSP-PRF-01`, `-02`, `-04`, `-05`; **L9:** `DSP-EXB-02`, `-03`;

   The south-wall displays of L9 and L10 (`DSP-EXB-01` / `-05`, `DSP-RSK-03` / `-08`) and the south-rim displays of H-CMD and H-LAB now sit on full back walls, so the earlier question about them is closed.

   **Owner decisions (camera presentation, closed):**
   - **H-CMD main viewscreen** (`DSP-CMD-01`): **stays on the north rim** as a standing panel. Not moved.
   - **Corridor repeaters** (`DSP-CRN-01`, `DSP-CRS-01`): **moved to the corridors' south walls** (Corridor Design CD-11), clear of the door niches: `COR-N` midway between `DR-L4` and `DR-L5` (≈ x 613), `COR-S` midway between `DR-L9` and `DR-L10` (≈ x 676). Same IDs, content and function; geometry, topology and anchors unchanged. 30 displays remain drawn as standing panels.
5. The Floor Plan centres of the hub doors lie about 15 units inside the drawn rim. The frames are placed on the tile seam, so there is no topology change.
