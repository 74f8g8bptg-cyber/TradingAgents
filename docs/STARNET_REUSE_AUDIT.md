# StarNet Reuse Audit for Stellar Agents

| | |
|---|---|
| **Status** | v0.1 — audit only. No StarNet code or assets were copied into this repository. |
| **Date** | 2026-09-30 |
| **Audited repository** | `https://github.com/androoAGI/starnet` |
| **Revision audited** | `fbddbf992f8e7082196f07c3024781fcf1c276fc` (2026-09-28 15:29 −04:00, "fix(station.layout): the tool's clock is injected…"), the repository's default branch at clone time: `feat/harness-backend`. Desktop build version in `src-tauri/tauri.conf.json`: 0.12.5 |
| **Method** | Shallow read-only clone; code read directly (not inferred from filenames). Sizes are `wc -l` at this revision |
| **Compared against** | `docs/STELLAR_VISUAL_WORLD_PLAN.md` v0.1 (uncommitted), `docs/STELLAR_FOUNDATION_PLAN.md` v0.3, `docs/STELLAR_LAYER_DESIGN.md` v0.4 |
| **Later note** | Historical audit. Its deck / lift / airlock recommendations (for example VR-5) are superseded by the owner-approved flat vessel (`STELLAR_MASTER_FLOOR_PLAN_V1.md` revision C) and `STELLAR_STARNET_VISUAL_ADAPTATION.md`. Licence and asset findings remain valid |

---

## Contents

1. [Scope and method](#1-scope-and-method)
2. [License and asset restrictions](#2-license-and-asset-restrictions)
3. [StarNet architecture summary](#3-starnet-architecture-summary)
4. [Full system audit](#4-full-system-audit)
5. [Reuse matrix](#5-reuse-matrix)
6. [Directly reusable code candidates](#6-directly-reusable-code-candidates)
7. [Testing and QA reuse candidates](#7-testing-and-qa-reuse-candidates)
8. [What must not be copied](#8-what-must-not-be-copied)
9. [Comparison against the Stellar Visual World Plan](#9-comparison-against-the-stellar-visual-world-plan)
10. [Renderer decision, revisited](#10-renderer-decision-revisited)
11. [What StarNet does not solve for Stellar](#11-what-starnet-does-not-solve-for-stellar)
12. [Recommended changes to STELLAR_VISUAL_WORLD_PLAN.md](#12-recommended-changes-to-stellar_visual_world_planmd)
13. [Unresolved technical questions](#13-unresolved-technical-questions)

---

## 1. Scope and method

### 1.1 Files inspected (read, not just listed)

- **Licensing and orientation:** `LICENSE`, `NOTICE.md`, `README.md`, `CODE_MAP.md`,
  `frontend/assets/sfx/LICENSE.md`, `frontend/assets/brand/providers/LICENSE.lobe-icons.txt`,
  `docs/DECISIONS.md` (sprite provenance lines), `src-tauri/tauri.conf.json`, `package.json`.
- **Shared contract:** `shared/events.js`, `shared/schema.js`, `shared/emitter.js`,
  `shared/clock-rng.js`.
- **World model and pathfinding:** `frontend/app/worldmodel.js` (header, constants, room kinds,
  station factory, `projectGeometry` including walkability / BFS / string-pulling, public API,
  `migrate`).
- **World runtime:** `frontend/app/world.js`: header and state; gait and facing
  (`stepGait`, `gaitMove`, `finishGait`, `bucketDir`); `setActivity` / `setActivityFor` /
  `handoff`; camera helpers (`focusAgent`, `focusBody`, `lockBody`, cinecam header); path start
  and waypoint logic (`startBodyPath`, `setPathTo`, `nextWaypoint`, `intentTell`,
  `maybeStrollBeat`); traffic and separation (`movementBlockers`, `stepTraffic` and helpers,
  `nudgeBody`, `pushApart`); `crewEngineStep`, `containBody`, `stepCrew`; `tick` (opening);
  `frame` and render-fault handling; off-screen culling (`propOnScreen`); stale-state and
  reconciliation (`sweepStaleStates`, `normalizeSnapshot`, `reconcileFromSnapshot`); link
  health (`linkDown`, `pauseBridge`, `resumeBridge`, `linkState`); the SSE bridge
  (`connectChannelBridge`, `open`, `fetchSnapshot`). The full function index (581 top-level
  functions) was reviewed to map the rest.
- **Rendering stack:** `frontend/app/stationbake.js` (header, function index, exports),
  `frontend/app/worldrenderer.js` (full), `frontend/app/worldlight.js`,
  `frontend/app/worldsurface.js`, `frontend/app/propsprites.js`, `frontend/js/assets.js`,
  `frontend/app/spacebg.js` (headers).
- **UI and persistence:** `frontend/app/save.js` (full), `frontend/app/widgets.js` (header,
  index), `frontend/app/stationui.js` (header, pure helpers), `frontend/app/build.js` (header,
  tools), `frontend/app/app.js` (header, roster), `frontend/app/stationcommands.js`,
  `frontend/app/zones.js`, `frontend/app/propanchor.js`, `frontend/app/waitanchor.js`,
  `frontend/app/linewatch.js`, `frontend/app/floorstats.js` (headers),
  `frontend/js/util.js` (bus and random helpers).
- **Sidecar:** `sidecar/channels/sse.js` (full), `sidecar/index.js` (`handleChannelEvents`,
  routing handlers, listen addresses), `sidecar/apiauth.js` (threat model and guards),
  `sidecar/station-store.js` (header).
- **Tests and QA:** `test/worldmodel.test.js`, `test/path-smoothing.test.js`,
  `test/crew-containment.test.js`, `test/station-authority.test.js`,
  `test/events-contract.test.js`, `test/world-movement-continuity.test.js`,
  `test/world-seat-recovery.test.js`, `test/world-lifecycle.test.js`,
  `test/hallway-traffic.test.js`, `test/zones.test.js`, `test/save.test.js`,
  `test/golden.test.js`, `test/lint-determinism.js`, `test/stationbake.chunk.test.js` (headers
  and structure); `scripts/shoot.mjs`, `scripts/golden.mjs`, `scripts/lib/png.mjs` (API).

**Requested but absent at this revision:** `frontend/app/refit.js` does not exist. The REFIT
build mode is implemented in `frontend/app/build.js`.

### 1.2 Key sizes at this revision

| File | Lines |
|---|---|
| `frontend/app/world.js` | 10,967 |
| `frontend/app/stationui.js` | 9,875 |
| `frontend/app/propsprites.js` | 11,903 |
| `frontend/app/build.js` | 5,999 |
| `frontend/app/stationbake.js` | 5,486 |
| `frontend/app/app.js` | 5,326 |
| `frontend/app/worldmodel.js` | 2,822 |
| `frontend/app/widgets.js` | 977 |
| `frontend/app/worldsurface.js` / `worldlight.js` / `worldrenderer.js` | 703 / 651 / 198 |
| `frontend/app/zones.js` / `propanchor.js` / `waitanchor.js` | 233 / 104 / 85 |
| `frontend/app/save.js` | 124 |
| `shared/events.js` / `schema.js` / `emitter.js` / `clock-rng.js` | 295 / 75 / 34 / 49 |
| `sidecar/channels/sse.js` | 167 |
| `frontend/assets/` | 16,565 PNG files, about 1.3 GB |

---

## 2. License and asset restrictions

**Evidence** (quoted from the repository):

- `LICENSE`: MIT, "Copyright (c) 2026 Andrew Sims".
- `NOTICE.md`, section "StarNet's own name and artwork": *"That license covers the code only.
  The **StarNet** name, the logo, the station artwork and sprites, and the rest of the project's
  brand identity are owned by Andrew Sims and are not licensed with the code. No trademark or
  other brand right is granted … A fork or derivative must ship under its own name, logo, and
  artwork, and must not present itself as StarNet or as endorsed by it."*
- `README.md` "License" repeats this.

**Consequences for Stellar:**

1. **Code** may be copied and modified under MIT, provided the StarNet copyright and permission
   notice travel with every copied or substantially derived file (a `NOTICE` / third-party
   licenses file in Stellar listing each derived file).
2. **Artwork is not licensed:** the station artwork, sprites, logo and brand identity. StarNet
   draws much of its art **in code** (procedural pixel art in `propsprites.js`,
   `stationbake.js`, `worldsurface.js`, `spacebg.js`). This audit treats **code whose purpose is
   to produce StarNet's look as artwork**, and therefore not reusable. This is a conservative
   reading (§13 Q1).
3. **Third-party material inside StarNet keeps its own licence.** Stellar would need its own
   licence for any of it (§8).
4. **No StarNet name, logo, visual identity or resemblance** in Stellar.

---

## 3. StarNet architecture summary

- **One Node process** (`node sidecar/index.js`) serves the static frontend and an HTTP + SSE
  API on loopback (`127.0.0.1`), runs the agent loop, and streams events to the browser. The
  desktop app (Tauri 2) embeds Node and the same sidecar.
- **Frontend with no build step:** `frontend/index.html` loads about 120 `<script>` tags in
  dependency order. Modules are IIFEs exposing **browser globals** (`World`, `WorldModel`,
  `StationBake`, `U`, …); several also export under Node for tests. No framework and no
  rendering library.
- **Rendering:** **Canvas 2D**, with a single camera (pan / zoom). The static station is
  **procedurally baked** into cached canvases (floors, walls, hull, lighting), in
  viewport-sized **chunks** that re-bake incrementally. Props and bodies are drawn per frame and
  y-sorted. **WebGL is used only for a CRT barrel-warp / phosphor post-process**, with a CPU
  fallback. The view is a **top-down / three-quarter pixel-art plane on a 12 px tile grid**
  with tall north walls. It is **not isometric**.
- **Model:** `worldmodel.js` is a pure, serialisable **station document**: rooms made of tile
  rectangles, corridors, props with footprints, belts and pipeline edges. `projectGeometry()`
  produces the render and walk geometry: zone grid, auto-doors, walkability, BFS pathfinding with
  string-pulling.
- **Runtime world:** `world.js` owns bodies (a hero `agent` plus `crew[]`), the idle "life"
  engine, movement, traffic, seats, camera, event ingestion and drawing, all in **one closure**
  with shared mutable state (`self`, `agent`, `crew`, `geo`, `blocked`, `fnow`).
- **Events:** `shared/events.js` is a **frozen, additive-only** catalogue of about 60 event
  types with schemas. Events are validated at the bus boundary in both directions
  (`emitter.js`), delivered over **SSE** with `epoch:seq` cursors, bounded replay, and a
  `ready` control frame. Snapshot reconciliation plus TTL sweeps keep the view honest.
- **Product law** (README): *"the interface must never assert state the harness cannot prove."*
  This is the same principle as Stellar's "visuals never lie".

---

## 4. Full system audit

For each system: **how StarNet actually implements it**, then the **fit for Stellar**.

| System | How StarNet implements it (verified in code) | Fit for Stellar |
|---|---|---|
| **World rendering** | `world.js` `frame()` → `frameBody()` on `requestAnimationFrame`, Canvas 2D. Blits the baked base, draws y-sorted props and bodies through `WorldRenderer.drawEntities` (`sortedItems` by y), then lighting (`WorldLight`), glows, bloom and dust, then the CRT warp (WebGL shader or CPU LUT) | The architecture (bake static, draw dynamic, y-sort, post-process) is sound. The concrete drawing is pixel-art and brand-bound |
| **Room model** | `worldmodel.js` doc: `rooms{id:{kind,name,rects[],floorStyle,…}}`, `order[]`, `meta.spawnRoomId/trunkRoomId`; kinds hab / bridge / lab / factory / quarters / storage / corridor; min room 3 tiles, min hall 2; max span 240 | The rect-union room model and corridor-as-room idea fit. The kinds, materials and build rules are StarNet-specific |
| **Station geometry** | `projectGeometry()` → local frame with margin; `zoneGrid`; **auto-doors** wherever two zones touch orthogonally; `canStep` only across same zone or door; chamfered convex corners (art vs walkability separated); sealed-airlock rooms lose their doors | Auto-doors from adjacency, a per-tile zone grid and `canStep` are directly useful. Chamfer and airlock rules are StarNet semantics |
| **Bake / cache** | `stationbake.js` bakes base and light canvases; `chunkGrid`, `dirtyChunks`, `visibleChunks`, `bakeIncremental` re-bake only dirty or visible chunks; `worldsurface.js` paints materials | The chunked-cache concept is reusable. The painters are artwork |
| **Agent representation** | Plain mutable body objects `{px,py,dir,state,goal,target,pathPts,pathIdx,sitting,seated,working,…}`. Hero = `agent`; others in `crew[]` (`makeCrewBody`), keyed by `agentId` | Shape is similar to Stellar's agent visual record; Stellar needs a stricter separation of telemetry fields from animation fields |
| **Multi-agent** | `crew[]` bodies each run the same engine by temporarily binding `self = b` (`stepCrew`), then restoring `self = agent` | Works, but the rebinding of a closure variable is fragile. Stellar should pass the body explicitly |
| **Movement / walking** | `stepGait`: eased speed (accel 150 u/s²), facing angle slewed with angular acceleration, 4-way bucket with hysteresis, **arcing through corners** instead of stop-pivot-go, distance-phased stride odometer; `gaitMove` validates the arc against geometry, else the chord | High-quality, compact, and mostly self-contained. A strong candidate |
| **Pathfinding** | `geo.path()`: 4-neighbour **BFS** on the tile grid honouring `walkable` and `canStep`, per-query extra blocked set, then **string-pulling** (`smoothPath`) with a conservative line-of-sight check (`losClear` → `segmentClear`) that never crosses a seam without a door and never squeezes diagonally between blockers | Directly reusable after removing art-tuned foot / mouth-lane clearance |
| **Collision handling** | Plan-time: `movementBlockers` marks other bodies' tiles and targets. Run-time: **local right-of-way** (`stepTraffic`: follow slower walkers, yielder steps into a pocket, seated bodies are obstacles, 10 s plan expiry) plus **soft separation** (`separateBodies`, `PERSONAL_TILES` 0.8, four relaxation passes, pushes never violate containment, jam give-up after 2.5 s) | A proven pattern worth reimplementing. The code is entangled with world.js state |
| **Room containment** | `containBody` each tick: a standing body off walkable floor snaps to the nearest walkable tile within six rings, else re-homes; `ensureAgentValid` for the hero; origin-shift re-framing in `rederive` | Needed in Stellar too, especially with authored layouts and teleports |
| **Targets / seats / anchors** | `propanchor.js` (pure): approach tile and facing for a prop, front edge first. `waitanchor.js` (pure): an anchor ladder (airlock → board → own desk) with zone clamping. Seats: `occupiedSeats` set of `propId:slot`, `takeSeat` / `releaseSeat`, `planSeat` / `planCouchSit` | Pure modules extractable. The seat-reservation pattern matches Stellar's reserved anchors |
| **Idle behaviour** | A large "sentience engine": `decideIdle`, needs meters, curiosity and novelty, social encounters, gatherings, chase / mimic, quirks, sleeping, "mourning" a removed prop, speech bubbles; beat budget (`armBeat`, `crewBeatDamp`); `zones.js` confines roaming. **Uses `Math.random()`** via `U.irnd` / `U.chance` | Too big, personality-driven, uses emotion language (grief, mourning), and is **not deterministic**. Stellar's plan forbids implied emotions and requires seeded, replayable ambient life |
| **Sitting / workstation** | Work seizes idle: `setActivityFor(agentId,'task')` sets `working`, drops leisure, re-paths to the desk seat (`deskPropFor` / `deskSeat` / `stepCrewToSeat`); stands where it is if there is no reachable desk; `gripeNoCompute` if the room lacks compute | The "work always wins over idle" priority ladder is exactly Stellar's rule |
| **Agent state changes** | `activity` / `working` / `serverLit` / `awaitPrompt` flags driven by bus events (`agent.run.start`, `agent.tool_call`, `agent.run.end`, `permission.prompt`, …); a run-clock map with TTL | Pattern matches Stellar (runtime state from telemetry). StarNet's state is a set of flags; Stellar's §3.2 explicit state machine is cleaner |
| **Animation state machine** | Implicit: `state` ('idle' / 'walk'), `goal` (use, lounge, sleep, social, work, awaiting, …), `sitting` / `seated` / `working`; sprite frames chosen in `assets.js drawBody` by direction and odometer | Stellar should keep its explicit visual-state catalogue (plan §6) |
| **Props / consoles** | `propsprites.js` catalogue (id, label, footprint, blocks, animated, use descriptor) plus procedural draw functions; `CAP_PROP_MAP` binds prop types to capabilities | The catalogue-with-footprint idea fits. The art is not reusable; capability semantics are irrelevant |
| **Screens / widgets / HUD** | In-canvas: nameplates, run clocks, work glyphs, bubbles, a camera-HUD ticker narrating real events. Chrome: `widgets.js` rails with truthful-telemetry rules (show "—" until data arrives, provenance "who / when", "no signal" when stale); `stationui.js` floating windows | The truthful-telemetry rules transfer well. The DOM and CSS are StarNet chrome |
| **Frontend state store** | No central store: state lives in module closures (`World`, `App.agents` roster owned by the frontend, `Workstreams`, …); `U.bus` is a tiny synchronous emitter | Stellar's plan (a pure reducer into WorldState) is stricter and better for replay |
| **Event ingestion** | `U.bus.on(name, fn)` handlers inside `connectChannelBridge`; SSE messages are re-emitted onto the bus; the harness also re-emits sidecar events | Reuse the dedupe and reconnect logic; replace scattered handlers with a reducer |
| **SSE / NDJSON transport** | SSE hub (`sse.js`): `id: epoch:seq`, bounded replay history (≤ 1024 events / 2 MB), `resume` replays newer frames then sends `{stream:'ready', cursor, reset}`; backpressure eviction at 4 MB buffered; **keepalive as a DATA frame** (`data: {}`), because EventSource hides comments; `retry: 3000`. Client: single-stream guard, exponential backoff to 15 s, cursor dedupe, snapshot fetch on `ready`, 30 s periodic snapshot. NDJSON is used for per-request streams (`/api/run`) | Excellent and directly applicable. Stellar's backend is Python, so this is a port of the pattern |
| **Event schemas** | `shared/events.js` frozen map (deep-frozen), additive-only by convention, enforced by a snapshot contract test; `schema.js` validator (type, enum, required, properties, items, additionalProperties) | Pattern matches Foundation §10 exactly. StarNet's event names and catalogue are its own |
| **Replay / determinism** | Backend: injected clock and RNG (`clock-rng.js`, mulberry32 + fnv), lint that bans ambient time or randomness in `shared/` and `sidecar/`. SSE replay by cursor. **The frontend world is not deterministic** (lint excludes `frontend/app`; idle life uses `Math.random`) | Reuse the RNG and lint idea. Stellar must extend determinism to its world adapter and ambient layer |
| **Save / load** | `save.js`: localStorage envelope `{schema, version, …}` with forward-only migrations, a **forward-version guard** (refuses newer saves), pre-migrate backup; mirrored to the sidecar `savestore.js` with atomic write and stale-write refusal | The pattern is useful for UI preferences. Stellar's truth lives in the backend journal |
| **World persistence** | The station doc is saved (user-built layout) and validated server-side (`station-store.js`, which never trusts renderer-posted capability lists) | Stellar's layout is **authored and static** in V1; the UI never posts state |
| **Room editing / building** | `build.js` REFIT mode: ghost previews validated by model validators, rooms, halls, surfaces, props, belts, blueprints, undo / redo | Out of scope for Stellar V1 (read-only UI, authored ship) |
| **State restoration** | On (re)connect: `ready` → `GET /api/state/snapshot` → `reconcileFromSnapshot` rebuilds run clocks, work poses (including "orphan" runs started elsewhere), in-flight tool glyphs and prompts; a recent-run-end guard prevents stale snapshots overriding newer local truth | Directly matches Stellar's plan §1.4. Strong pattern to adopt |
| **Failure / stale-state** | `linkDown` (socket not open, or no data for > 40 s against a 25 s keepalive, or recovering until the snapshot reconciles); `sweepStaleStates` once per second (run TTL, per-run TTL, prompt TTL); render-loop try/catch with an **honest fault overlay** after repeated throws; `bootguard`, `friendlyerror` | Adopt the patterns wholesale |
| **Performance** | Chunked incremental bake; `propOnScreen` culling; indexed `roomAt` (tile → room map, rebuilt lazily); y-sort once per frame; render-cost percentiles (`WorldRenderer.stats`); WebGL probe with CPU fallback | Adopt culling, indexing and metrics. Pixi-specific equivalents are available if Pixi is used |
| **Rendering loop** | `frame()` schedules the next rAF **first** so a throw cannot kill the loop; fault counter; `tick(dt, now)` for simulation | Adopt |
| **Off-screen behaviour** | rAF pauses in hidden tabs; `propOnScreen` skips drawing off-screen props; simulation still ticks for all bodies | Adopt; Stellar adds screen-update throttling (plan §18) |
| **Testing** | Headless Node tests for pure modules (`worldmodel`, `zones`, `propanchor`, `waitanchor`, path smoothing); **source-lock tests** that regex `world.js` or extract function bodies with `Function()` to run them in isolation; event contract snapshot; save atomicity with a fake fs; about 364 steps in the fast gate | Pure-module tests are reusable. Source-lock tests exist only because world.js is a browser IIFE; Stellar should avoid needing them |
| **Golden / visual QA** | `shoot.mjs` boots a seeded sidecar, drives Chromium over CDP to known states, captures PNGs with a manifest, and exits non-zero on failure. `golden.mjs` reduces frames to a 64×40 grayscale signature and flags mean-absolute-difference above a threshold tuned over animation noise; a ledger dedups findings | Very applicable. Stellar can do it more deterministically (recorded event streams, seeded ambient, frozen clock) |
| **Desktop packaging** | Tauri 2 with embedded Node binary, CSP, NSIS / DMG, updater | Not needed for V1 (a local browser page on the Mac) |
| **Runtime ↔ frontend security** | Loopback-only listen; **Host pin** (DNS-rebinding defence), **Origin allow-list**, a **per-launch token** as a custom header on every `/api/*`, **single-use short-lived tickets** for header-less requests (EventSource, beacons); the master token is never in a URL; SSE egress **redacted** (`runTeeView` strips tool args and results) | Stellar's V1 read-only localhost API still needs Host pinning and a token, because the event stream carries financial data (§12) |

---

## 5. Reuse matrix

**Classes:** **KEEP AS-IS** = vendor the file unchanged (with notice). **WRAP** = vendor
unchanged but only use it through a Stellar module. **COPY + ADAPT** = copy the code (with
notice), then remove or rename StarNet specifics. **REIMPLEMENT (same pattern)** = write new
Stellar code following the proven design. **DO NOT USE** = art, brand, out of scope, or unsafe.
Time saved is a rough estimate of engineering days versus designing from zero.

| # | StarNet file(s) | Feature / system | Class | Why | What Stellar changes | Dependencies | Risks | Licence / asset concern | Time saved |
|---|---|---|---|---|---|---|---|---|---|
| S1 | `shared/schema.js` | Zero-dependency JSON-schema-lite validator | **WRAP** | Small, pure, hardened (own-property checks) | Wrap in a Stellar event validator fed by schemas generated from the backend's Pydantic models | none | Subset of JSON Schema only | MIT notice | ~1 d |
| S2 | `shared/emitter.js` | Validate-then-emit; never throws; logs malformed | **COPY + ADAPT** | 34 lines, exact behaviour Stellar wants on the UI bus | Point at Stellar's catalogue; log to the UI event log | S1 | none | MIT notice | ~0.5 d |
| S3 | `shared/events.js` | StarNet event catalogue | **DO NOT USE** | Different domain; Stellar's canonical names are fixed (Foundation §10.1) | — | — | Name collisions | Content is StarNet's | — |
| S4 | `test/events-contract.test.js` + fixture | Additive-only contract gate (snapshot diff) | **REIMPLEMENT (same pattern)** | Exactly what Foundation R-3 and "never rename" need | Implement for the Python catalogue and the UI mirror | S1 | none | — | ~1 d |
| S5 | `shared/clock-rng.js` | Injected clock, mulberry32 RNG, fnv hash | **KEEP AS-IS** | Generic, 49 lines, the basis for seeded ambient life | Use from the adapter and ambient modules; port the same algorithm to Python if backend and UI must agree | none | none | MIT notice | ~0.5 d |
| S6 | `test/lint-determinism.js` | Ban ambient time or randomness in pure code | **REIMPLEMENT (same pattern)** | Stellar needs it in Python (engine) **and** in the UI adapter and ambient code, which StarNet exempts | AST-based lint for Python; a JS scan for the adapter, navigation and ambient modules | — | False positives at injection roots | — | ~1 d |
| S7 | `sidecar/channels/sse.js` | SSE hub: `epoch:seq` ids, bounded replay, `ready` + `reset`, backpressure eviction, data keepalive | **REIMPLEMENT (same pattern)** | Best-in-class pattern; Stellar's API is Python | Port to the Stellar API (async), source from the event store rather than an in-memory ring only | Stellar event store | Async write semantics differ | — (pattern) | ~3–4 d |
| S8 | `sidecar/index.js` `handleChannelEvents` | SSE endpoint wiring (retry hint, resume by `Last-Event-ID` or `?cursor=`, keepalive timer, cleanup) | **REIMPLEMENT (same pattern)** | Same reason | Python handler | S7 | none | — | ~1 d |
| S9 | `frontend/app/world.js` `connectChannelBridge` → `open`, `fetchSnapshot` | Browser SSE client: single stream, backoff, cursor dedupe, snapshot on `ready`, periodic reconcile | **COPY + ADAPT** | The logic is precise and already debugged (orphan streams, double emits) | Extract into a standalone module; replace `U.bus` and `ApiTicket` with Stellar equivalents; feed the reducer instead of the bus | S2 | Extraction from a large closure | MIT notice | ~2 d |
| S10 | `world.js` `linkDown`, `linkState`, `pauseBridge`, `resumeBridge` | Link health honesty | **COPY + ADAPT** | Small and correct; encodes the data-keepalive lesson | Stellar thresholds: stale > 1.5× keepalive; the "recovering until snapshot" rule | S9 | none | MIT notice | ~0.5 d |
| S11 | `world.js` `sweepStaleStates`, `normalizeSnapshot`, `reconcileFromSnapshot`; sidecar `/api/state/snapshot` | TTL sweep plus authoritative snapshot reconciliation | **REIMPLEMENT (same pattern)** | Tied to StarNet's maps (run clocks, prompts); the idea is essential | Reducer-level: snapshot replaces WorldState; per-agent "no update for N s" markers (plan §1.4) | S9 | Snapshot / event race | — | ~2 d |
| S12 | `sidecar/apiauth.js`, `apitickets.js` | Loopback API security: Host pin, Origin allow-list, per-launch token, single-use SSE tickets | **REIMPLEMENT (same pattern)** | Stellar's read-only API still exposes financial telemetry to any web page the owner visits (DNS rebinding) | Python middleware; ticket for EventSource | — | Must not add write paths | — | ~2 d |
| S13 | `frontend/app/worldmodel.js` (`projectGeometry` zone grid, auto-doors, `canStep`, `walkable`, `bounds`, indexed `roomAt`) | Tile-grid room model | **COPY + ADAPT** | Generic and pure; tested | Remove belts, pipeline, capabilities, materials and blueprints; add **decks** and a lift graph; enforce the one-way Vault → Execution Bay door | `U` helpers (clamp, hash) | Hidden coupling to `U` and pipeline | MIT notice | ~4–6 d |
| S14 | `worldmodel.js` `path`, `smoothPath`, `losClear`, `segmentClear` | BFS + string-pulling pathfinding | **COPY + ADAPT** | Correct, conservative, tested (`path-smoothing.test.js`) | Keep `segmentClear` tile checks; drop the art-tuned `physical` foot / mouth-lane pass (S15); evaluate A* only if grids grow | S13 | Isometric projection must stay a render transform | MIT notice | ~3 d |
| S15 | `worldmodel.js` `footPoint`, `mouthLanes`, `wallClearance` | Foot-clearance tuned to StarNet's tall-wall pixel art | **DO NOT USE** | Encodes StarNet's art geometry (9 px wall faces, doorway returns) | Stellar authors clearance with its own art | — | — | Art-derived | — |
| S16 | `worldmodel.js` mutation API, undo / redo, `BLUEPRINTS`, `BAY_ROLES`, belts, pipeline edges, `CAP_PROP_MAP`, floor / wall / hull materials | Station building and capability semantics | **DO NOT USE** | Stellar's ship is authored; the UI is read-only | — | — | — | Materials are art data | — |
| S17 | `worldmodel.js` `migrate`, `freshDoc`, `schema` / `version` | Versioned, total-over-junk document loading | **REIMPLEMENT (same pattern)** | Stellar's authored layout file needs the same safety | Layout schema `stellar.ship` v1 | — | none | — | ~0.5 d |
| S18 | `frontend/app/zones.js` | Idle-containment zones (room / leash / multi / null) | **COPY + ADAPT** | Pure, 233 lines, 341-line test | Map zones to Stellar rooms and ambient areas (habitat promenade) | S13 | none | MIT notice | ~1–2 d |
| S19 | `frontend/app/propanchor.js` | Approach tile and facing for a prop | **COPY + ADAPT** | Pure, 104 lines, tested | Extend to named interaction points with capacity (plan §16) | S13 | Isometric facings (8-way) | MIT notice | ~1 d |
| S20 | `frontend/app/waitanchor.js` | Deterministic anchor ladder with zone clamping | **COPY + ADAPT** | Pure, 85 lines; the ladder fits `waiting` / `resting` anchors | Stellar ladder: waiting bench → workstation → room anchor | S18, S19 | none | MIT notice | ~0.5 d |
| S21 | `world.js` `stepGait`, `bucketDir`, `gaitMove`, `finishGait` (+ constants) | Eased walking, facing slew with hysteresis, corner arcs, stride odometer | **COPY + ADAPT** | High quality and largely self-contained | Accept `now` injected (no `performance.now`); 8-way buckets for isometric sprites; tune speeds to Stellar scale | S14 | Tuning for isometric scale | MIT notice | ~2–3 d |
| S22 | `world.js` `stepTraffic`, `trafficPocket`, `trafficRoute`, `clearTraffic` | Local right-of-way (yield pockets, follow slower walkers) | **REIMPLEMENT (same pattern)** | Solves visual deadlocks; code is entangled with closure state | Explicit body arguments; operational agents always have right of way over ambient ones | S14, S21 | Subtle edge cases (the hallway tests show many) | — | ~3 d |
| S23 | `world.js` `separateBodies`, `nudgeBody`, `pushApart` | Soft separation backstop respecting containment | **REIMPLEMENT (same pattern)** | Same | Same | S13 | none | — | ~1 d |
| S24 | `world.js` `containBody`, `ensureAgentValid`, `refootStranded`, `rederive` re-frame | Containment backstop | **REIMPLEMENT (same pattern)** | Essential invariant (no agent in the void) | Per deck; teleport fallback | S13 | none | — | ~1 d |
| S25 | `world.js` `occupiedSeats`, `takeSeat`, `releaseSeat`, `planSeat` | Seat reservation | **REIMPLEMENT (same pattern)** | Matches plan §16 reserved seats | Role-owned operational anchors plus claimable ambient anchors with timeouts | S19 | Leaks (StarNet fixed several) | — | ~1 d |
| S26 | `world.js` `setActivityFor`, `serverLit`, `handoff` | Work pose from real events; visible handoff | **REIMPLEMENT (same pattern)** | Right idea; StarNet's flags are ad hoc | Derive from Stellar's runtime-state events (plan §6.1) | reducer | none | — | ~1 d |
| S27 | `world.js` idle engine (`decideIdle`, social, gathering, chase, mimic, quirks, `maybeMourn`, needs, curiosity bubbles) | Rich ambient life | **DO NOT USE** | Non-deterministic (`Math.random`), emotion language, very large, StarNet personality | Build a small seeded ambient scheduler (plan §12) | — | — | Character behaviour is part of StarNet's identity | — |
| S28 | `world.js` `armBeat`, `crewBeatDamp`, station-level sweeps, "work seizes idle" ladder | Beat budget and priority ladder | **REIMPLEMENT (same pattern)** | Keeps ambient life rare and pre-emptible | Seeded; operational > ambient always | S5 | none | — | ~1 d |
| S29 | `world.js` `focusAgent`, `focusBody`, `lockBody`, `camLerp`, `cinecamTick` | Camera focus, follow-lock, idle director | **REIMPLEMENT (same pattern)** | Behaviour is good (user input always wins; reduced motion respected) | Overview, deck, room and agent modes (plan §2); cinecam optional later | renderer | none | — | ~2 d |
| S30 | `world.js` `frame`, `drawRenderFault` | Loop that survives throws, with an honest fault overlay | **REIMPLEMENT (same pattern)** | Small and important | Stellar overlay text and style | renderer | none | — | ~0.5 d |
| S31 | `world.js` `propOnScreen`; `worldrenderer.js` `visibleRect`, `intersects` | Viewport culling | **COPY + ADAPT** | Trivial and correct | Isometric bounds; Pixi has built-in culling if used | renderer | none | MIT notice | ~0.5 d |
| S32 | `worldrenderer.js` `sortedItems`, `percentile`, `stats`, `cameraReadout` | Painter's-order sort with stable ties; render-cost metrics; camera label | **COPY + ADAPT** | Generic helpers | Isometric depth key (x + y and layer), not y only | renderer | Depth sort differs for isometric | MIT notice | ~1 d |
| S33 | `world.js` `drawCRT`, `initGL`, `drawCurve*`, `buildLUT`; `worldrenderer.js` `PHOSPHOR`, `DETAIL_GLSL`, `sharpenSample` | CRT barrel warp, phosphor look | **DO NOT USE** | StarNet's signature look; wrong art direction for Stellar | — | — | — | Brand identity | — |
| S34 | `frontend/app/stationbake.js` (painters) | Procedural floors, walls, hull, lighting art | **DO NOT USE** | This is StarNet's station artwork in code | — | — | — | Artwork | — |
| S35 | `stationbake.js` `chunkGrid`, `dirtyChunks`, `visibleChunks`, `bakeIncremental` | Chunked, incremental cache of static layers | **REIMPLEMENT (same pattern)** | Useful if Stellar composes rooms at runtime; less needed with pre-rendered room art | Room-level static layers cached as textures | renderer | none | — | ~1 d |
| S36 | `worldsurface.js`, `industrialtextures.js`, `worldlight.js` | Material painters; ray-cast 2D lighting | **DO NOT USE** | Art-bound (materials) and top-down specific (lighting) | Stellar bakes lighting into pre-rendered art; alert-level tints as overlays | — | — | Artwork (surfaces) | — |
| S37 | `frontend/app/propsprites.js` | Prop catalogue plus procedural prop art | **DO NOT USE** | Art in code; StarNet props | Stellar's own prop catalogue (footprint, anchors, screens) | — | — | Artwork | — |
| S38 | `frontend/js/assets.js`, `frontend/assets/**` (sprites, skins, furniture, brand) | Sprite loading and recolouring; all image assets | **DO NOT USE** | Brand-protected artwork; sprites produced with a third-party generator (PixelLab) whose terms were not audited | — | — | — | Artwork / brand / unclear third-party terms | — |
| S39 | `frontend/app/spacebg.js` | Space backdrop registry | **DO NOT USE** | Artwork | Stellar's own backdrop art | — | — | Artwork | — |
| S40 | `frontend/app/build.js` | REFIT station editor | **DO NOT USE** | Out of scope (authored ship, read-only UI) | — | — | — | Art-heavy editor chrome | — |
| S41 | `frontend/app/save.js` | Versioned local envelope, forward-only migrations, forward-version guard, pre-migrate backup | **REIMPLEMENT (same pattern)** | Ideal for UI preferences (camera, reduced motion, pinned panels) | Stellar keys; no trading truth in local storage | — | none | — | ~0.5 d |
| S42 | `sidecar/station-store.js`, `savestore.js` | Server validation of renderer-posted station; atomic, stale-refusing saves | **DO NOT USE** | The Stellar UI never posts state; backend persistence is the journal (Foundation §4.24) | — | — | — | — | — |
| S43 | `frontend/app/widgets.js` | Truthful-telemetry widget rules ("—" until data, provenance, "no signal") | **REIMPLEMENT (same pattern)** | Principles fit Stellar screens (plan §10) | Apply to every room screen and HUD value | reducer | none | — | ~1 d |
| S44 | `frontend/app/stationui.js` `visibleTerminalRect`, `clampTerminalSize` | Pure floating-panel geometry | **COPY + ADAPT** | Small, pure | Stellar side panels | — | none | MIT notice | ~0.5 d |
| S45 | `stationui.js` (rest), `topbar.js`, `navdock.js`, `modeldock.js` | StarNet HUD chrome | **DO NOT USE** | Brand look and StarNet features | — | — | — | Visual identity | — |
| S46 | `frontend/app/linewatch.js`, `floorstats.js` | Pure folds of events into readouts (lamp status priority, honest "unknown") | **REIMPLEMENT (same pattern)** | Right discipline; different metrics | Stellar metrics come from the backend metrics API; UI folds only for live counters | reducer | none | — | ~0.5 d |
| S47 | `frontend/app/stationcommands.js` | Agent tools drive UI verbs | **DO NOT USE** | Stellar's UI is read-only; the engine never commands the UI | — | — | Would violate R-5 | — | — |
| S48 | `frontend/app/app.js` | Screen flow; frontend-owned roster | **DO NOT USE** | In Stellar the engine registry owns the roster | — | — | — | — | — |
| S49 | `scripts/shoot.mjs`, `scripts/lib/shootRun.mjs` | Boot to known states and capture PNGs over CDP | **REIMPLEMENT (same pattern)** | Proven QA approach | Playwright (Chromium is available) driving **recorded event streams** with a frozen clock and seeded ambient | fixtures | none | — | ~2 d |
| S50 | `scripts/golden.mjs`, `scripts/lib/png.mjs` | 64×40 grayscale signature diff with a noise-floor threshold | **COPY + ADAPT** | Small (81-line PNG helper) and effective | Tighter threshold, possible because Stellar replays are deterministic | S49 | none | MIT notice | ~1 d |
| S51 | `test/worldmodel.test.js`, `test/path-smoothing.test.js`, `test/zones.test.js`, `test/propanchor.test.js`, `test/waitanchor.test.js` | Headless tests of the pure modules | **COPY + ADAPT** | Tests travel with S13, S14 and S18–S20 | Remove belt, pipeline and material cases; add deck and one-way airlock cases | `test/_assert.js` (adapt) | none | MIT notice | ~2 d |
| S52 | `test/crew-containment.test.js`, `test/world-*.test.js`, `test/hallway-traffic.test.js` (source locks, `Function()` extraction) | Tests that regex or extract world.js source | **DO NOT USE** | Brittle; needed only because world.js is not modular. Stellar modules must be importable | Write behavioural tests against Stellar modules; use the **scenarios** (2-tile hall crossing, seat recovery) as test ideas | — | — | — | (ideas only) |
| S53 | `src-tauri/**` | Desktop packaging | **DO NOT USE** | Not needed in V1 | — | — | — | Icons and installer art are brand | — |
| S54 | `frontend/assets/fonts/vt323.woff2` | VT323 font (OFL 1.1) | **DO NOT USE** | Licence would allow it, but it is the CRT look Stellar must not resemble | — | — | — | OFL (permissive) | — |
| S55 | `frontend/assets/sfx/*` | UI sounds (Bleeoop "Interface Bleeps") | **DO NOT USE** | Separate third-party licence granted to StarNet's use, not transferable | License separately if wanted | — | — | Third-party licence | — |
| S56 | `frontend/assets/brand/providers/*` (lobe-icons) | Provider logos | **DO NOT USE** | Provider trademarks; not needed | — | — | — | MIT code, trademarked logos | — |
| S57 | `frontend/js/util.js` `U.bus` (only) | Tiny synchronous emitter that swallows handler throws | **COPY + ADAPT** | Trivial and correct | Keep the bus; **drop** `U.rnd` / `U.irnd` / `U.chance` (`Math.random`) in favour of S5 | S5 | none | MIT notice | ~0.1 d |

**Counts:** KEEP AS-IS **1** · WRAP **1** · COPY + ADAPT **15** · REIMPLEMENT (same pattern) **20** ·
DO NOT USE **20** (57 items).

---

## 6. Directly reusable code candidates

Only code generic enough to derive from. **Nothing is copied yet.** When it is, each derived file
carries the StarNet MIT notice, and Stellar keeps a third-party licenses file listing it.

| Source file | Functions / modules | Responsibility | Coupling | Must remove or rename | Extractable independently? | Tests adaptable? |
|---|---|---|---|---|---|---|
| `shared/schema.js` | `validate`, `typeOf` | Schema-lite validation | **None** (pure UMD) | UMD global name `SK` | Yes, as is | Write small Stellar tests |
| `shared/clock-rng.js` | `makeClock`, `makeRng` (mulberry32), `fnv` | Deterministic time and randomness | **None** | `SK` namespace | Yes, as is | Yes (trivial) |
| `shared/emitter.js` | `makeEmitter` | Validate-then-emit | Low (requires an events module) | Swap `events.js` for Stellar's catalogue | Yes | Yes |
| `frontend/js/util.js` | `U.bus` (`on` / `off` / `emit`) | Event bus | Low | Everything else in `U` | Yes (about 10 lines) | Trivial |
| `frontend/app/worldmodel.js` | `projectGeometry` core: zone grid, auto-doors, `canStep`, `walkable`, `segmentClear`, `losClear`, `smoothPath`, `path`; `normRect`, `rectsHit`, `inRect`; indexed `roomAt`; `migrate` skeleton | Tile world and pathfinding | **Medium.** The module mixes pure geometry with StarNet semantics (props-as-capabilities, belts, pipeline via `Pipeline`, materials, blueprints) and reads global `U` | Belts, pipeline edges, junction config, `CAP_PROP_MAP`, `BAY_ROLES`, `BLUEPRINTS`, all material tables, airlock / sealing semantics, `footPoint` / `mouthLanes` / `wallClearance` (art-tuned) | **Partly.** The geometry and path core (about 400–600 lines) can be lifted into a new module; the rest stays behind | Yes: `worldmodel.test.js` (subset) and `path-smoothing.test.js` |
| `frontend/app/zones.js` | whole module | Idle containment zones | **Low** (pure; inputs passed in) | StarNet wording (bay, hero) | Yes | Yes: `zones.test.js` |
| `frontend/app/propanchor.js` | `deriveAnchor`, `facingToward`, `sideTiles`, `frontOf`, `turnSide` | Approach tile and facing | **Low** (needs `geo.walkable`) | Four-way facing assumptions | Yes | Yes: `propanchor.test.js` |
| `frontend/app/waitanchor.js` | `resolve` | Anchor ladder | **Low** (injected dependencies) | StarNet prop types (airlock, mission board) | Yes | Yes: `waitanchor.test.js` |
| `frontend/app/world.js` | `stepGait`, `gaitMove`, `finishGait`, `bucketDir`, `angNorm`, gait constants | Walking and facing | **Medium.** Reads `performance.now()`, the body fields it owns, and `geo.clearFootSegment` / `blocked` in `gaitMove` | Inject `now`; pass `geo` / `blocked` explicitly; 8-way buckets | **Yes, with edits** (about 120 lines) | Partly (`world-movement-continuity` ideas) |
| `frontend/app/world.js` | `connectChannelBridge` → `open`, `fetchSnapshot`, `linkDown`, `linkState`, `pauseBridge`, `resumeBridge` | SSE client lifecycle | **High inside world.js** (module-level variables, `U.bus`, `ApiTicket`, ticker and floor handlers mixed into the same function) | All StarNet event handlers; ticker; floor stats | **Yes, but requires careful extraction** of the transport half from the handler half | New tests needed (fake EventSource) |
| `frontend/app/worldrenderer.js` | `visibleRect`, `intersects`, `sortedItems`, `percentile`, `stats` shape | Culling, painter order, perf metrics | **Low** for these helpers | `PHOSPHOR`, `DETAIL_GLSL`, `sharpenSample`, `IndustrialTextures` and `WorldLight` coupling | Yes (helpers) | Yes: `worldrenderer.test.js` (subset) |
| `frontend/app/stationui.js` | `visibleTerminalRect`, `clampTerminalSize` | Panel geometry | **None** (pure functions at file top) | — | Yes | Write small tests |
| `scripts/lib/png.mjs` | `decodePNG`, `signature`, `sigDiff`, `fileSignature` | Golden signatures | **None** | — | Yes | Yes: `golden.test.js` ideas |

**Deeply coupled, so not extractable (conservative):** the rest of `world.js` (idle engine,
traffic, separation, drawing), `stationbake.js`, `propsprites.js`, `worldlight.js`,
`build.js`, `app.js`, `stationui.js` (beyond the two helpers). These are either art or depend on
dozens of closure variables and globals.

---

## 7. Testing and QA reuse candidates

| Candidate | Reuse | Notes |
|---|---|---|
| `test/path-smoothing.test.js` | COPY + ADAPT | Its independent-oracle method (densely sample each smoothed segment and query `walkable`) is exactly how Stellar should test navigation |
| `test/worldmodel.test.js` (geometry and path parts) | COPY + ADAPT | Drop belt, pipeline and material sections |
| `test/zones.test.js`, `propanchor.test.js`, `waitanchor.test.js` | COPY + ADAPT | With the modules |
| `test/events-contract.test.js` | REIMPLEMENT | For the Python catalogue and UI mirror; fixture-snapshot additive-only gate |
| `test/lint-determinism.js` | REIMPLEMENT | Extend to UI adapter, navigation and ambient modules |
| `scripts/shoot.mjs` / `golden.mjs` / `png.mjs` | REIMPLEMENT / COPY + ADAPT | Drive **recorded event fixtures** with a frozen clock and seed. Stellar can reach near-zero animation noise, so goldens can be stricter than StarNet's |
| Scenario ideas from `hallway-traffic`, `world-seat-recovery`, `crew-containment`, `world-lifecycle` | Ideas only | Two-tile hall crossings, unreachable seats, origin shifts, despawn releasing seats. Rewrite as behavioural tests |
| StarNet's world.js source-lock testing style | DO NOT USE | Avoid needing it: Stellar world modules must be importable ES modules with injected dependencies |

---

## 8. What must not be copied

| Item | Location | Reason (evidence) |
|---|---|---|
| **StarNet name, logo, wordmark** | `frontend/assets/brand/starnet-*`, `.github/media/*`, `src-tauri/icons`, installer art | NOTICE.md "StarNet's own name and artwork" |
| **Station artwork and sprites** (images) | `frontend/assets/sprites/**`, `skin-study-*`, `agent-animation-*`, `furniture/**`, `industrial/**`, `website/**` | NOTICE.md; 16,565 PNGs |
| **Artwork expressed as code** | `propsprites.js` (procedural props), `stationbake.js` painters, `worldsurface.js`, `industrialtextures.js`, `spacebg.js`, `approved-sheet-effects.js`, `authored-*` config and motion files, `js/assets.js` recolouring recipes, CRT / phosphor parameters | Conservative reading: this code *is* the station artwork (§13 Q1) |
| **Visual identity** | CRT barrel warp, phosphor scanlines, VT323 terminal look, amber / green phosphor palette, "pixel-art station" style, `*-review.html` pages | Brand identity; also contrary to Stellar's art direction |
| **Character behaviour identity** | Idle "sentience" engine beats (mourning, chase the cursor, glyph dialects) | Part of StarNet's product character; also non-deterministic |
| **Third-party assets with separate licences** | `frontend/assets/sfx/*` (Bleeoop, royalty-free for StarNet's embedded use; resale forbidden); `fonts/vt323.woff2` (OFL 1.1); `brand/providers/*` (lobe-icons MIT, provider trademarks) | Their own licences; Stellar must license separately |
| **Licensing unclear** | Sprites generated with PixelLab (`docs/DECISIONS.md`: "Sprites: Pixellab"); any bundled `node_modules` (e.g. `codec-parser` LGPL-3.0 per NOTICE) | Generator terms not audited; LGPL component not needed |
| **Skill recipes and docs** | `sidecar/skills/library/*.md` (MIT, various authors, Hermes / Nous Research) | Irrelevant to Stellar; would carry many attributions |

---

## 9. Comparison against the Stellar Visual World Plan

**A** = StarNet already solves this adequately · **B** = partially solves · **C** = Stellar needs
a new implementation.

| Stellar subsystem (plan §) | Verdict | Detail |
|---|---|---|
| Visual architecture: engine → bus → adapter → renderer (§1.1) | **B** | StarNet has the same flow but scatters state across closures; Stellar's pure reducer is stricter. Reuse the transport and bus pieces (S1, S2, S5, S9, S57) |
| Stale / missing events (§1.4) | **A (pattern)** | StarNet's `linkDown` + data keepalive + `ready` / snapshot reconcile + TTL sweep is more complete than the plan. **Adopt** (S7–S11) |
| "Never invent actions" (§1.5) | **A (principle)** | Identical product law; StarNet's implementation details (run TTL, orphan runs) are worth copying as rules |
| Movement follows state; badge immediate; teleport when late (§1.6) | **B** | StarNet has teleport-when-late and work-seizes-idle; badges are in-canvas nameplates. Stellar keeps its rule set |
| Camera modes, minimap (§2) | **B** | Pan / zoom / focus / follow-lock / idle director exist (S29); no deck or room modes, no minimap |
| Ship layout, decks, cutaway (§3) | **C** | StarNet is a single flat plane with user-built rooms; Stellar needs an **authored multi-deck** ship |
| Agent visual model and persona registry (§4–5) | **C** | StarNet's frontend owns the roster with personas and skins; Stellar's contract differs |
| Visual states (§6) | **C** (with **B** inputs) | StarNet's implicit flags are a weaker model; reuse only its event-to-pose ideas (S26) |
| State → room movement (§7) | **B** | Work re-paths to the desk seat; waiting anchor ladder (S20); zones (S18) |
| Interactions (§8) | **B** | Handoff boxes and social beats exist; the operational vs ambient separation must be Stellar's |
| HUD (§9) and room screens (§10) | **C** | Trading content is Stellar-specific; truthful-telemetry rules reused (S43) |
| Telemetry → visual mapping (§11) | **C** | Different event catalogue |
| **Deterministic ambient life (§12)** | **B → flag** | StarNet provides the seeded RNG (S5) but **its world does not use it** (`Math.random`). Stellar must build seeded ambient life; do not port StarNet's idle engine |
| Wellbeing visuals (§13) | **C** | StarNet has "needs" meters (cosmetic), not operational health |
| Art direction (§14) | **C** | Must be original; StarNet's art is off-limits and stylistically opposite (pixel CRT vs clean semi-realistic) |
| **Renderer (§15, PixiJS)** | **B → revisit** | See §10: keep PixiJS as the drawing backend, but adopt StarNet's model, navigation and transport modules instead of building those from scratch |
| **Pathfinding / navigation (§16)** | **A → flag** | **The plan proposes navmesh polygons plus A* built from scratch. StarNet's tile-grid BFS with auto-doors, string-pulling and a conservative line-of-sight check already solves this, with tests.** Recommend adopting it per deck (S13, S14) plus a small lift graph between decks |
| Collision avoidance, no deadlock (§16) | **A (pattern) → flag** | StarNet's traffic right-of-way plus soft separation plus containment backstop (S22–S24) are more mature than the plan's "simple steering". Reimplement the same pattern |
| Reserved seats / anchors (§16) | **A (pattern)** | S19, S20, S25 |
| World state adapter (§1.3) | **B** | Build the reducer new; reuse the SSE client and link-health code (S9, S10) |
| Persistence (UI) | **B** | Save-envelope pattern for UI preferences (S41). World truth stays in the backend |
| Owner interaction, read-only (§17) | **B** | StarNet's UI is read-write (REFIT, commands). Stellar's read-only stance is stricter; reuse only inspection patterns |
| Accessibility and performance (§18) | **B** | Reduced motion respected throughout StarNet; culling, fault overlay and perf stats reused (S30–S32) |
| **Visual testing (§19 test criteria)** | **A (pattern) → flag** | The plan does not specify how goldens work. StarNet's shoot + signature-golden pipeline (S49, S50) is ready to adapt |
| Security of the read-only API | **A (pattern) → flag (gap in plan)** | The plan says "localhost, read-only". StarNet shows that is not enough: Host pinning, Origin checks and a token are needed against DNS rebinding and cross-site reads (S12) |

**Flags: planned from scratch, but StarNet already solves it adequately:**
1. Navigation (navmesh + A*) → use StarNet's tile BFS + string-pulling per deck.
2. Collision and deadlock → StarNet traffic + separation + containment pattern.
3. Stale / link honesty → StarNet's data keepalive + `ready` / snapshot + TTL scheme.
4. SSE transport details (cursors, replay, backpressure) → StarNet's hub pattern.
5. Visual QA → StarNet's shoot + signature-golden approach.
6. API security → StarNet's loopback guard pattern (missing from the plan).

---

## 10. Renderer decision, revisited

### 10.1 Options

| Option | What it means | Relative effort | Technical risk | Notes |
|---|---|---|---|---|
| **A. Adapt StarNet's Canvas world engine** | Fork `world.js` + `stationbake.js` + friends; replace the art and strip the StarNet systems | **High** (about 11k + 5.5k + 12k lines to understand and gut) | **High** | The engine's drawing *is* the protected art; top-down tall-wall geometry is baked into the navigation (foot and mouth lanes) and the draw order; closure-shared state makes partial extraction error-prone; residual resemblance to StarNet is a brand risk |
| **B. Port StarNet's world concepts and pure modules onto a thin renderer (PixiJS)** | Reuse the model, pathfinding, zones, anchors, gait, SSE client, link health, schema, RNG and golden tooling; write a small Stellar world loop; draw with PixiJS using Stellar's own pre-rendered isometric art | **Medium** | **Low–medium** | Keeps what StarNet proved (navigation, traffic, honesty) and drops what is protected or stylistically wrong |
| **C. New PixiJS engine from scratch** | Ignore StarNet | **Medium–high** | **Medium** | Re-derives solved problems (smoothing through doors, deadlocks, stale links); the plan's navmesh approach would be new, untested code |
| **D. B, but Canvas 2D instead of PixiJS** | Same as B with the StarNet-style Canvas loop | **Medium** | **Low–medium** | Viable: StarNet shows Canvas 2D handles a living station. But Stellar's larger, semi-realistic pre-rendered art (not 12 px pixel art), zoom levels and many layered sprites favour WebGL batching and texture management |

### 10.2 Recommendation

**Option B: port StarNet's world concepts and pure modules, with PixiJS as the drawing
backend.**

- The **world model, navigation, containment, anchors, gait, transport and link-health layers
  are renderer-agnostic TypeScript/JavaScript modules** (as StarNet's `worldmodel.js`,
  `zones.js` and `propanchor.js` already are), so a fallback to Canvas 2D (option D) remains
  cheap if the PixiJS spike disappoints.
- **Isometric is a projection, not a new world:** keep the logical tile grid per deck (as
  StarNet does) and project tiles to isometric screen space at draw time. Pathfinding stays on
  the grid.
- **Confirm with a one-week spike** before committing: an 8×8-tile room with 20 animated
  placeholder agents walking via the ported pathfinding, in both PixiJS and Canvas 2D, measuring
  frame time on the owner's Mac.
- **Estimated saving versus option C:** about 25–40 engineering days, mostly navigation,
  traffic, containment, SSE and link honesty, and visual QA (sum of §5 estimates for reused
  rows, discounted for integration).

---

## 11. What StarNet does not solve for Stellar

These remain Stellar-specific and are designed in the Visual World Plan and Foundation Plan:

- trading-specific room screens: market dashboards per instrument (XAU/USD, EUR/USD, USD/JPY,
  NAS100); price and candles; active setup;
- research summaries, source reliability and freshness; macro / causal driver boards;
- Buy/Sell **proposal** screens and the setup lifecycle board;
- the Risk Vault: rule checklist, blocked reasons, exposure bars, breaker state;
- the order lifecycle (created → sent → filled / rejected → closed) and paper vs demo mode;
- portfolio / P&L, drawdown, expectancy and trade history with sample-size warnings;
- market-specific desks and trading-focused visual states (`risk_review`, `approved`,
  `rejected`, `executing`, `post_trade_review`);
- an authored multi-deck cutaway ship with a one-way airlock enforced in navigation;
- a persona registry separate from technical ids;
- deterministic, seeded ambient life replayable from the event store;
- operational wellbeing visuals from real latency, retry, rate-limit and budget telemetry;
- a strictly read-only UI (no build mode, no commands).

---

## 12. Recommended changes to STELLAR_VISUAL_WORLD_PLAN.md

Not applied; for owner approval.

| # | Section | Change |
|---|---|---|
| VR-1 | Header / relationship | Add a "Reuse sources" row naming StarNet (MIT code only) and this audit; state that no StarNet artwork, brand or look is used |
| VR-2 | §1.4 stale / missing events | Adopt StarNet's scheme explicitly: `epoch:seq` cursors; a `ready` frame with `reset`; snapshot fetch on every (re)open and every 30 s; keepalive as a **data** frame (EventSource hides comments); "link down" if the socket is not open, if no data arrives for > 1.5× the keepalive, or while recovering until the snapshot reconciles; per-agent TTL sweeps |
| VR-3 | §1.3 / new §1.7 | Add **API security for the read-only UI**: loopback bind, Host pin, Origin allow-list, per-launch token header, single-use short-lived ticket for EventSource |
| VR-4 | §15 renderer | Replace "build a PixiJS renderer" with **option B**: port StarNet's pure world modules (model, pathfinding, zones, anchors, gait, SSE client, link health, schema, RNG) behind renderer-agnostic interfaces; PixiJS as the drawing backend, confirmed by a one-week spike against Canvas 2D |
| VR-5 | §16 navigation | Replace "per-room navmesh polygons + A*" with **a per-deck tile grid** (zone grid, auto-doors, `canStep`), **BFS + string-pulling** with a conservative line-of-sight check, and a **lift graph** between decks; the Vault → Execution Bay edge one-way at the grid level (`canStep`). Isometric is a render projection only |
| VR-6 | §16 collisions | Adopt the traffic right-of-way + soft separation + containment backstop pattern (with jam give-up and teleport fallback) |
| VR-7 | §12 ambient | State that ambient selection uses the ported `clock-rng` (mulberry32 / fnv) with **no `Math.random`**, enforced by a determinism lint over the adapter, navigation and ambient modules; add a station-level beat budget |
| VR-8 | §19 phases | Add a **V1.5 "engine port" step** (port pure modules with tests, before sprites), and give V1–V6 golden-image criteria using the signature-diff method on recorded event fixtures |
| VR-9 | §18 performance | Add render-fault resilience (the loop survives throws, with an honest overlay), render-cost percentiles, and indexed tile lookups |
| VR-10 | New section: third-party code | Require a `NOTICE` / third-party licenses file in `stellar_ui/` listing each StarNet-derived file with the MIT notice; a CI check that no file under `frontend/assets` of StarNet (or any StarNet art module) is present |
| VR-11 | §20 open decisions | Add the questions in §13 below |

---

## 13. Unresolved technical questions

| # | Question | Why it matters |
|---|---|---|
| Q1 | Is StarNet's **procedural art code** (props, walls, surfaces) "code" (MIT) or "artwork" (not licensed)? This audit treats it as artwork | Decides whether any drawing helpers could be reused. Conservative default: not reused |
| Q2 | Vendor StarNet-derived modules (copy + notice) or clean-room reimplement from this audit's descriptions? | Copying is faster; clean-room avoids any attribution and resemblance questions |
| Q3 | TypeScript or JavaScript for `stellar_ui`? | Porting StarNet's JS into TS adds typing work but catches coupling bugs |
| Q4 | PixiJS or Canvas 2D after the spike? | Final renderer choice (§10) |
| Q5 | Multi-deck model: one grid per deck with lifts, or a single grid with vertical offsets? | Pathfinding and camera design |
| Q6 | Isometric depth sorting with a cutaway (walls, consoles, tall screens) | StarNet's y-sort does not directly apply; needs a depth key per layer |
| Q7 | Authoring tool for the ship layout (tiles, anchors, rooms) given no REFIT editor | A simple JSON layout, or a small internal editor later |
| Q8 | Should the Stellar backend also expose `/api/state/snapshot` with the same semantics as StarNet's (active tasks, agents in working states, pending items)? | Needed for S11 reconciliation |
| Q9 | Which StarNet revision to track if modules are derived (pin `fbddbf99`)? | Future upstream fixes and attribution accuracy |
| Q10 | Is StarNet's default branch `feat/harness-backend` its release trunk? | Audit validity; a re-check before any copying |
