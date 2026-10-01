# Stellar Life System V1 (ambient activity, movement, doors, event hooks)

**Status:** implemented in the Visual Prototype. The visual baseline stays frozen at `92db7fc`: no room, furniture, door, anchor, room function, dog rule or reserved-room status changed.

**Files:**
- `tools/visual_prototype/templates/stellar_life.js`: the engine. It is pure: no DOM, no drawing, no clock, no `Math.random`. `render.py` inlines it into the page.
- The page renderer hooks are in `templates/visual_prototype.html` (the "LIFE LAYER" block).
- Tests:
  - `tools/visual_prototype/life_test.js` (Node, headless);
  - life cases in `smoke_test.js` (browser).

**In the page:**
- Life is **on** by default. The **Life** button, or `?life=0`, shows the static baseline.
- `?seed=` changes the seeded scene.
- `?lifeT=SECONDS` jumps to a fixed simulated time and freezes it (for screenshots and goldens).
- `?speed=` scales time.

## The governing rule: ambient, never operational

The prototype has **no engine link**, so every agent's runtime state is `idle`. The approved Visual World Plan says:
- §1.5: the UI never invents operational actions;
- §12: ambient life is only for `IDLE` / `OFF_DUTY` agents, and is labelled as such;
- Character Registry §3: ambient behaviour stays inside the agent's own room and the Habitat.

So everything in this layer is **ambient**:
- The status badge keeps the runtime truth ("idle", "idle · no producer"). Movement never changes it.
- The inspector adds an "Ambient life … ambient animation, no task" row.
- Every event carries `ambient: true`.
- **`WORKING`** means *at its own workstation, no task*. When the telemetry adapter exists, real `agent.task.*` events drive the same hook with `ambient: false`, and a real task pre-empts ambient behaviour at once (`life.preempt(id)`).
- No emotion language. No moods, needs or "happiness".
- The real-cooldown **recovery pods are never used** by ambient life. Only the cosmetic rest pods are.

## A. What already existed

| Capability | Where | Reused as |
|---|---|---|
| **Navigation model** | `geometry.py`: one tile grid for the station, `walkable`, wall `seams`, explicit door `lanes` (the only crossings), `can_step`, BFS connectivity, reserved rooms | Exported unchanged to the page (`D.nav`). The engine mirrors `can_step` exactly |
| **Anchors** | `geometry.py` (88 anchors: role-owned workstations plus unowned habitat / visitor anchors) | Work spots (own anchor), stroll spots (unowned anchors in the home room) and habitat spots (café seats, sofas, billiards, window benches, cosmetic rest pods). **No anchor was added or moved** |
| **Furniture footprints** | `geometry.py` (`block` / `seat` / `floor` kinds) | Obstacles. Seats may start or end a route, never be walked through |
| **Access classes** | Character Registry §3 (`MP-FREE`, `MP-RISK`, `MP-EXEC`, `MP-HOST`, …) | Per-actor room permission (§E) |
| **Dog occupancy** | `D.occupancy` (Room Registry §3.3a) | The dog's only allowed rooms |
| **Doors** | 15 tile doors plus 6 radial doors (R1–R4 open, R5 / R6 reserved) | Door state and events. **The door artwork is unchanged** |
| **Agents and characters** | 41 rendered characters, home rooms and anchors (`D.agents`) | The actors; plus the resident dog `DEC-009` |
| **Not yet existing** | Simulation clock, activities, movement, events, door logic, any live animation | Built here, small and seeded |

## B. What the reference station's architecture influenced

These are patterns only. Nothing was copied, and the page contains no reference-station name, art or code. Source: the engine-layer reuse audit and plan §1.7.

| Pattern | Use here |
|---|---|
| Seeded randomness (S5) | mulberry32 + fnv, keyed on `(seed, actor, beat)` |
| Tile-grid world, explicit doors, BFS + string-pulling with a conservative segment check (S13 / S14) | The station grid with door lanes only. Smoothing never cuts a corner or crosses a seam, a seat or a door without its waypoint |
| Idle containment zones (S18) | Per-class allowed rooms |
| Interaction points with seat reservation (S19 / S25) | Spots claimed first-come and released on leaving |
| Beat budget, "work over idle" (S28) | Station caps on how many agents are away. `preempt()` |
| **Not adopted** | The reference station's idle "sentience" engine (needs, moods, encounters), its renderer and all of its art |

## C. Stellar life architecture

```
D (page data: tiles, nav lanes/seams, anchors, furniture, agents, rRooms, occupancy)
   └─ StellarLife.buildWorld(D)        one navigation model: station tiles + R1–R4 room-local grids + portals
        └─ StellarLife.create(world, {seed})
             ├─ step(dtMs)             fixed 100 ms ticks; injected time (the renderer passes frame deltas)
             ├─ activities / spots     seeded selection, caps, reservation
             ├─ movement               BFS → smoothing → waypoint walking (fade fallback)
             ├─ doors                  open on approach, close 1.5 s after the last user
             ├─ cinema session         EMPTY → PREPARING → SCREENING → ENDING (clock-driven)
             ├─ bus                    on(type | "*", fn), events log
             └─ snapshot()             positions, pose, state for the renderer
renderer: static scene cached once per camera; moving actors are slotted into the depth order and only small
clipped regions are repainted each frame (about 50 fps at every zoom, headless)
```

**Radial rooms R1–R4** have no station tiles. Each has a **room-local grid** (12-unit cells in the same s / t frame the renderer uses), with obstacle footprints that mirror the drawn furniture. The browser test cross-checks every drawn item against these footprints. Each grid is joined to H-HAB by a **portal through its open door**.

R5 and R6 have no grid and no portal, so they can never be entered.

## D. Agent states

`IDLE` · `WALKING` · `WORKING` (at its own workstation, ambient) · `SITTING` · `STANDING` · `RESTING` (cosmetic rest pod) · `SOCIAL` (café, lounge) · `RECREATION` (billiards) · `MEDITATING` (R1) · `WATCHING_CINEMA` (R2) · `DECOMPRESSING` (R3) · `PLAYING_WITH_DOG` (R4).

Each activity has:
- an actor;
- an activity type;
- a location (room and spot);
- a target spot;
- a start (walk, then arrive);
- a current state;
- a duration, or a completion condition (the cinema ends with the session; dog play ends when the dog leaves R4);
- a next activity, chosen by the seeded selector.

**Poses:**
- `desk`: the existing seated or standing pose at the anchor;
- `sit`: chairs, sofas, benches, pods, recliners;
- `floor`: cross-legged on mats and cushions;
- `stand`;
- `walk`: a small stride bob plus a facing that follows the path.

The characters are the existing ones. They were not redesigned.

## E. Movement and navigation

- **Route:**
  - BFS on the navigation graph, then string-pulling within one region;
  - door waypoints are always kept;
  - a radial-room crossing passes through the door point itself.
- **Respects:**
  - walls and seams;
  - furniture (no route crosses a `block` tile; seats only at the ends);
  - explicit doors only;
  - room boundaries;
  - permissions:
    - `MP-FREE`, `MP-COURIER`, `MP-SUPERVISOR`, `MP-MEDIC`, `MP-RISK`, `MP-EXEC`: their **own room** + public transit (COR-N, COR-S, H-CMD, H-LAB, H-HAB) + the **Habitat** (H-HAB, R1–R4). They are never routed into another L room, L9 / L10 (unless home), L5, L8, R5 or R6;
    - `MP-HOST` (the café host): **H-HAB only**;
    - **the dog:** H-HAB and R4 only, read from `D.occupancy`.
- **Fallback:** if there is no route, or a walk takes longer than 150 s, the actor fades out and in at the destination (plan §16).
- **Leaving a seat that sits inside furniture** (cinema recliner, R3 bench, dog bed): the actor first returns to the seat's approach cell.
- **Not built yet:** traffic right-of-way and soft body separation (plan §16). Spots are reserved, so destinations never overlap, and the caps keep corridors light.

## F. Room activities

| Room | Activity | Behaviour |
|---|---|---|
| Own room | `WORKING` | At its own anchor (6–15 min dwell). The first dwell is staggered so departures spread out |
| Own room | `STROLL` (STANDING) | To an unowned anchor in its own room (visitor spot, table side) |
| H-HAB | Café, lounge, billiards, window bench, cosmetic rest pod, park bench, fountain side, park walk (a loop of park waypoints) | Seats and positions come from the existing anchors and park furniture |
| H-HAB | Café host round | The host leaves the counter to stand by the café tables, then returns |
| R1 Zen | `MEDITATING` | On one of the six mat cushions, cross-legged, facing the garden. **At most 3 people** (calm) |
| R2 Cinema | `WATCHING_CINEMA` | The session cycle is EMPTY (6 min) → PREPARING (3 min) → SCREENING (13 min) → ENDING (2 min). At PREPARING the session **invites** 2–4 agents from their workstations (an event source), and others may join. Viewers take free recliner seats facing the screen and leave during ENDING. **No content is ever shown on the screen.** At most 8 viewers |
| R3 Decompression | `DECOMPRESSING` | On a cushion, the centre mat or the bench. **At most 2** (quiet, not social) |
| R4 Dog Play | `PLAYING_WITH_DOG` | Only while the dog is in R4 and not resting. Ends if the dog leaves. **At most 2 people** |

**Distribution:**
- After a work dwell, an agent has a 50 % chance to go away (if the **away budget** of 12 allows), a 20 % chance to stroll in its own room, and otherwise stays.
- After an away activity it usually returns to work. In the Habitat, there is a 25 % chance of one more habitat beat.
- H-HAB holds at most 10 visitors.
- In a 2-hour soak, most agents remain at work, and the peak occupancy is within every cap.

## G. Dog behaviour

| State | Where |
|---|---|
| `DOG_IDLE` | A spot anywhere on the H-HAB floor (18 spread spots plus its home tile), sitting |
| `DOG_WALKING` | Between spots, inside H-HAB, or through `DR-R4` |
| `DOG_RESTING` | Its bed in R4 |
| `DOG_DRINKING` | The water station in R4 |
| `DOG_PLAYING` | Runs between 8 play spots on the R4 mat and course |

The occupancy rule is enforced three times:
1. by navigation (the dog's graph contains only H-HAB and R4);
2. by the Node test, which checks the dog's position every 100 ms over the soak;
3. by the browser test.

The dog has no AI: it moves through simple seeded transitions. There is still only one dog.

## H. Event hooks

Subscribe with `life.on(type, fn)` (or `"*"`). Each event is `{ type, t, ambient: true, actor?, room?, door?, spot?, … }`. All types are in `StellarLife.EVENTS`:

`AGENT_ENTER_ROOM`, `AGENT_EXIT_ROOM`, `AGENT_START_WORK`, `AGENT_STOP_WORK`, `AGENT_SIT`, `AGENT_STAND`, `AGENT_START_REST`, `AGENT_END_REST`, `AGENT_START_ACTIVITY`, `AGENT_END_ACTIVITY`, `DOOR_OPEN`, `DOOR_CLOSE`, `MEDITATION_START`, `MEDITATION_END`, `CINEMA_STATE`, `CINEMA_START`, `CINEMA_END`, `DECOMPRESSION_START`, `DECOMPRESSION_END`, `DOG_ENTER_R4`, `DOG_ENTER_HHAB`, `DOG_START_PLAY`, `DOG_STOP_PLAY`.

**Doors:**
- A door opens when an actor on a route through it comes within 26 units, and closes 1.5 s after the last user. Its state is in `life.doors`.
- The door **artwork is unchanged**: the open assemblies already read as doorways in the frozen baseline. The door cycle is exposed as state and events, ready for a future door animation and sound.

## I. Future sound integration points

Sound V1 now subscribes to this bus (`docs/STELLAR_SOUND_SYSTEM_V1.md`). The Life engine itself still plays no audio. `StellarLife.SOUND_HOOKS` suggests one cue per event:

| Event | Cue |
|---|---|
| `AGENT_START_WORK` | `workstation.wake` |
| `AGENT_STOP_WORK` | `workstation.sleep` |
| `AGENT_SIT` | `seat.creak` |
| `AGENT_STAND` | `seat.release` |
| `DOOR_OPEN` | `door.open` |
| `DOOR_CLOSE` | `door.close` |
| `MEDITATION_START` | `zen.chime` |
| `CINEMA_START` | `cinema.start` |
| `CINEMA_END` | `cinema.end` |
| `DECOMPRESSION_START` | `quiet.enter` |
| `DOG_START_PLAY` | `dog.play` |
| `DOG_STOP_PLAY` | `dog.settle` |
| `DOG_ENTER_R4` | `dog.pawsteps` |
| `DOG_ENTER_HHAB` | `dog.pawsteps` |
| `AGENT_START_REST` | `rest.pod` |

Events carry the room and the actor, so a spatial mixer can place each cue. `ambient: true` lets the mixer keep ambient cues quieter than future operational ones.

## J. Tests and validation

**`node tools/visual_prototype/life_test.js`** (headless, deterministic):

| # | Scenario | Checks |
|---|---|---|
| 1 | Agent goes to work | Returns to its exact home anchor; `AGENT_START_WORK` |
| 2 | Agent leaves its workstation | `AGENT_STOP_WORK`, `AGENT_EXIT_ROOM` |
| 3 | Corridor | The L1 → H-HAB route enters `COR-*` |
| 4 | H-HAB | Enters H-HAB and sits at a café seat (`AGENT_SIT`) |
| 5 | R1 | `MEDITATING`, `MEDITATION_START` |
| 6 | R2 | The cinema reaches PREPARING; the viewer sits, stays through SCREENING (`CINEMA_START`) and leaves after `CINEMA_END`; all session states are emitted |
| 7 | R3 | `DECOMPRESSING`, `DECOMPRESSION_START` |
| 8 | R4 | The dog enters R4 (`DOG_ENTER_R4`, `DOG_START_PLAY`); a person plays with it |
| 9 | Dog rule | The allowed set is exactly {H-HAB, R4}. No dog route to L1, H-CMD, COR-N, H-LAB, R1, R2 or R3. The dog's position is checked every tick of a 2-hour soak |
| 10 | Reserved rooms | No route into L5 / L8; no R5 / R6 cells or portals; an L1 agent is never routed into L2, L9 or L10; the host cannot be sent to R1 |
| 11 | Furniture | Every actor, every 100 ms over the soak: never on a `block` tile, never over a seat except at its own spot, never through an R-room footprint (an oracle independent of the path code) |
| 12 | Doors | `DR-L1` opens before the agent enters the corridor and closes after it has passed. `DR-CMD-HAB` opens for it |

Also tested:
- **Caps:** away ≤ 12, R1 ≤ 3, R3 ≤ 2, R4 ≤ 2 people, the cinema draws an audience of 2–8.
- **Coverage:** every soak event is in the catalogue, and all the key hooks fire.
- **Work:** most agents stay at work.
- **Determinism:** the same seed gives an identical event log and snapshot; a different seed differs.
- **Lint:** the determinism lint (no `Math.random`, `Date.now` or `performance.now` in the engine) and the no-reference-name check.

**`smoke_test.js`** adds `life_off_baseline` (life off = the static baseline) and three frozen life scenes. Each checks that:
- 42 actors are running;
- nobody is in L5, L8, R5 or R6;
- the dog is only in H-HAB or R4;
- every drawn R1–R4 furniture item has a matching navigation footprint.

**Performance:**
- The static scene is cached per camera, and only small clipped regions are repainted around moving actors.
- At low zoom, actors are drawn over the cache, each clipped to its own box.
- About 50 fps headless at every zoom (it was 5 fps when the whole scene was redrawn).
- One fixed-step simulation tick; path searches only when an activity changes; no timers and no DOM updates per frame.

## Not built yet (next steps)

- Traffic right-of-way and soft separation in corridors (plan §16).
- An animated door leaf.
- Real telemetry driving `WORKING`, plus the `agent.resting` recovery pods.
- A day / night clock (the clock abstraction is `step(dtMs)` and `t`; work and rest periods can be layered on it).
