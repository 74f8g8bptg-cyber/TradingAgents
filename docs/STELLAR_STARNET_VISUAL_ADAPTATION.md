# StarNet → Stellar Visual Adaptation (recovery pass)

> **Status:** DRAFT, documentation only. **No StarNet code, art or asset is copied** by this pass.
> **Purpose:** recover every useful StarNet mechanic already studied, and map it onto the new flat
> vessel (`STELLAR_MASTER_FLOOR_PLAN_V1.md` revision C) before any visual system is designed.
> **Builds on:** `STARNET_REUSE_AUDIT.md` (items S1–S57, recommendations VR-1 to VR-11) and
> `STELLAR_VISUAL_WORLD_PLAN.md` (§1.7 engine layer, §6 states, §12 ambient, §16 navigation,
> §20 security, §21 testing). Neither file is modified.

---

## 1. Sources inspected and identifiers verified

| Item | Value | Verified from |
|---|---|---|
| StarNet repository | `androoAGI/starnet` | `STARNET_REUSE_AUDIT.md` header |
| Audited revision | `fbddbf992f8e7082196f07c3024781fcf1c276fc` (2026-09-28, "fix(station.layout): the tool's clock is injected…") | Audit header, **and** the local checkout `/home/user/androoagi/starnet`, whose `HEAD` is exactly this commit |
| Stellar audit commit | `4c991e1` "docs: add StarNet reuse audit and Stellar visual world plan" | `git log` of this repository |
| Stellar documents read | `STARNET_REUSE_AUDIT.md` (all); `STELLAR_VISUAL_WORLD_PLAN.md` (§1.7 reuse table, §6–§8, §16, §21, §22, §23); the five Visual Foundation registries | This repository |
| StarNet code spot-checked in this pass (read-only) | `frontend/app/worldmodel.js`: auto-doors (lines ≈2049–2073), airlock room-seal (≈96–106, 2038–2051), chamfer / art-vs-walk split (≈2076–2100), indexed `roomAt` (≈888–921), `ROOM_KINDS` (≈313–321). The `test/` directory listing (goldens, path smoothing, anchors, traffic, seats, containment, link honesty) | Local checkout at `fbddbf99` |

## 2. Licensing and art restrictions (from the audit, unchanged)

- **Code is MIT**, "Copyright (c) 2026 Andrew Sims". Any copied or substantially derived file must
  carry the StarNet copyright and permission notice. Stellar keeps a third-party licenses file
  listing each derived file (audit §2, VR-10; plan §22).
- **Not licensed:**
  - the StarNet name, logo and wordmark;
  - the station artwork and sprites;
  - the brand identity (`NOTICE.md`, "StarNet's own name and artwork").
- **Art expressed as code counts as art (conservative reading, audit Q1):**
  - `propsprites.js`, the `stationbake.js` painters, `worldsurface.js`, `industrialtextures.js`, `spacebg.js`;
  - the recolouring recipes, the CRT / phosphor shaders and parameters;
  - the art-tuned doorway clearances (`footPoint`, `mouthLanes`, `wallClearance`).
- **Third-party material keeps its own licence:**
  - the sound effects (Bleeoop; not transferable);
  - VT323 (OFL; excluded anyway because it is the CRT look);
  - the provider logos (trademarks);
  - PixelLab-generated sprites (terms not audited);
  - an LGPL `codec-parser`.
- **Identity:**
  - no StarNet name, logo or look, and no resemblance;
  - no CRT or phosphor look, and no pixel-art station style;
  - StarNet's "sentience" idle behaviour (mourning, chase, glyph dialects) is part of StarNet's character and is not used.
- **Scope rule of this pass:** reuse is **not** widened beyond the audit's matrix. Every row below
  cites its audit item.

---

## 3. Mechanics recovered (by area)

| Area | StarNet mechanic (as implemented) | Audit id |
|---|---|---|
| Room system | Rooms as unions of tile rectangles; corridor as a room kind; per-tile zone grid; indexed tile → room lookup; room kinds (hab, bridge, lab, quarters, storage, corridor) as functional identity | S13 |
| Room system | Art shape separated from walk shape (chamfered corners are art only; walkability stays on tiles) | S13 (spot-checked) |
| Corridors | Corridor = walkable tile strip that is its own zone; hallway traffic rules | S13, S22 |
| Doors / doorways | Door = a permitted step between two zones (`doorDefs`, `canStep`); **auto-doors** wherever two zones touch; room **sealing** (a sealed room loses its boundary doors, so no body path can cross) | S13 (spot-checked) |
| Pathfinding | 4-neighbour BFS on the tile grid honouring `walkable` and `canStep`; string-pulling with a conservative line-of-sight check that never crosses a wall seam without a door; per-query blocked set | S14 |
| Agent movement | Eased speed; facing slew with hysteresis; corner arcs; stride odometer | S21 |
| Traffic / collision | Local right of way (yield pockets, follow slower walkers, 10 s plan expiry); soft separation with jam give-up; containment backstop (snap to walkable, re-home) | S22, S23, S24 |
| Anchors / zones | Approach tile and facing per prop; waiting-anchor ladder; idle containment zones (room / leash / multi) | S18, S19, S20 |
| Seats / workstations | Seat reservation (`propId:slot`); work seizes idle and re-paths to the desk; stand in place if no reachable desk | S25, S26, S28 |
| Functional objects | Prop catalogue entry = id, label, footprint, blocks, use descriptor (art excluded) | S37 (catalogue idea only) |
| Screens / displays | Truthful-telemetry widget rules: "—" until data, provenance (who / when), "no signal" when stale; pure event folds with an honest "unknown" | S43, S46 |
| Agent visual states | Work poses from runtime events; visible hand-off | S26 |
| Ambient | Beat budget and priority ladder; seeded RNG (mulberry32 / fnv) exists, but StarNet's own world does not use it | S5, S28 (S27 excluded) |
| Event system | Frozen, additive-only catalogue with a contract snapshot test; validate-then-emit; tiny bus | S1, S2, S4, S57 |
| Transport / reconnect | SSE `epoch:seq` ids, bounded replay, `ready` + `reset`, backpressure eviction, **data-frame keepalive**; client single-stream guard, backoff, cursor dedupe, snapshot on `ready`, 30 s periodic snapshot | S7, S8, S9 |
| Stale / disconnected | `linkDown` (socket closed, no data for more than 1.5× keepalive, or recovering until the snapshot reconciles); TTL sweeps; snapshot reconciliation including orphan runs and a recent-run-end guard | S10, S11 |
| Performance | Chunked, incremental static-layer cache; viewport culling; painter's-order sort with stable ties; render-cost percentiles; indexed lookups; rAF paused when hidden | S31, S32, S35 |
| Render resilience | Loop schedules the next frame first; fault counter; honest fault overlay | S30 |
| Camera | Focus, follow-lock, idle director; user input always wins; reduced motion respected | S29 |
| Persistence (UI only) | Versioned local envelope, forward-only migrations, forward-version guard, pre-migrate backup; total-over-junk layout loading | S17, S41 |
| Testing | Headless pure-module tests; independent-oracle path test; seeded shoot → PNG → 64 × 40 signature golden diff; determinism lint | S6, S49, S50, S51 |
| Security | Loopback bind, Host pin, Origin allow-list, per-launch token, single-use EventSource tickets, redacted egress | S12 |
| Leisure / human space | Room kinds `hab` / `quarters`; couch / recliner seats and seat recovery (tests `recliner-side-seat`, `toast-seat`) | S25 (idle engine S27 excluded) |
| Lab / research space | Room kind `lab` with its own floor identity; the capability-to-prop idea (`CAP_PROP_MAP`) | S13 (kind only); S16 excluded |

---

## 4. StarNet → Stellar adaptation matrix

**Decision:**
- **REUSE** = vendor unchanged with the notice (audit KEEP AS-IS / WRAP);
- **ADAPT** = copy with the notice, then strip StarNet specifics (audit COPY + ADAPT);
- **REIMPLEMENT** = new Stellar code following the proven pattern;
- **DEFER** = useful, but not before a later visual phase;
- **DO NOT USE** = excluded.

| # | StarNet concept | What StarNet does | Why useful | Stellar adaptation | Stellar system | Decision |
|---|---|---|---|---|---|---|
| A1 | Tile-rect room model + zone grid (S13) | Rooms are unions of tile rectangles, each tile belonging to one zone | Deterministic, testable walk geometry | **One flat vessel grid** (no decks, no lift graph). Hubs are rasterised discs (row-wise rect unions); L rooms are rects; radial R rooms are rasterised rotated rects (floor-plan Q5) | Layout / navigation | ADAPT |
| A2 | Auto-doors on adjacency (S13) | Opens a door wherever two zones touch | Convenience in a user-built station | **Replaced by an explicit door list.** Only the 21 drawn doors exist; touching walls stay closed (L4/L6, L10's corner, the room gaps). `canStep` is true only across a listed door | Navigation | ADAPT (auto-doors switched off) |
| A3 | Room seal (S13 airlock) | A sealed room loses its boundary doors, so no body path crosses | Makes a state-driven lockout physical, not just visual | Available for **state-driven closures** (for example a room locked while the breaker is `TRIPPED`), driven only by real telemetry and never by the UI. Which rooms (if any) is decided with room functions | Navigation + adapter | ADAPT (DEFER use) |
| A4 | Art vs walk separation (S13 chamfer) | Rounded art corners never change walkable tiles | Circles and rotated rooms can look smooth while navigation stays on tiles | Hub rims and radial rooms are **art shapes**; walk tiles sit strictly inside them | Art + navigation | REIMPLEMENT |
| A5 | Indexed `roomAt` (S13) | Tile → room map, rebuilt lazily | Fast room lookup for every placement and hover | Built once from the authored layout (static in V1) | Navigation / UI | ADAPT |
| A6 | BFS + string-pulling (S14) | Grid path, then a line-of-sight smoothing that never cuts through a wall | Proven, tested, no navmesh needed | As is, on the single vessel grid; drop the art-tuned clearance (S15) | Pathfinding | ADAPT |
| A7 | Gait (S21) | Eased walking, facing slew, corner arcs, odometer | Natural movement cheaply | Injected clock; **8 facings** for 2.5D sprites; speeds tuned at layout time | Agent movement | ADAPT |
| A8 | Traffic, separation, containment (S22–S24) | Yield pockets, soft push-apart, snap back to floor | No visual deadlocks | Operational agents always have right of way over ambient; deterministic tie-break; jam → fade fallback. The two long corridors are the main traffic test | Movement | REIMPLEMENT |
| A9 | Prop anchor (S19) | Approach tile and facing for a prop | Agents stand at the right side of a console | Named anchors with capacity (`<room>.<anchor>`), 8-way facing | Anchors / workstations | ADAPT |
| A10 | Waiting ladder (S20) | Airlock → board → own desk, zone-clamped | Deterministic waiting spots | Waiting bench → own workstation → room anchor | Anchors | ADAPT |
| A11 | Zones (S18) | Idle containment areas | Keeps ambient agents in plausible places | Per-agent home room; **Habitat hub + R rooms** as the ambient area; corridors as transit only | Ambient / movement | ADAPT |
| A12 | Seat reservation (S25) | `propId:slot` claims, released on leave | No two agents in one chair | Role-owned operational seats; claimable ambient seats with timeout, released at once for operational use | Workstations / leisure | REIMPLEMENT |
| A13 | Work seizes idle + beat budget (S26, S28) | Real work pre-empts idle; ambient beats are rare | Operational truth always visible first | State-driven priority: operational > ambient; station beat budget; seeded | Agent states / ambient | REIMPLEMENT |
| A14 | Seeded RNG (S5) | mulberry32 + fnv, injected clock | Reproducible ambient life | The only randomness in the UI; keyed by seed, agent id and time bucket | Ambient | REUSE |
| A15 | Determinism lint (S6) | Bans ambient time and randomness in pure code | Keeps replays identical | Extended to the adapter, navigation and ambient modules (StarNet exempts its world) | Testing | REIMPLEMENT |
| A16 | Event catalogue discipline (S1, S2, S4, S57) | Frozen additive-only catalogue; validate-then-emit; tiny bus | Contract safety | Stellar's own catalogue (`stellar.telemetry.catalogue`); schema-lite validator; bus without `Math.random` helpers. StarNet's event names are **not** used (S3) | Event system | REUSE (S1) / ADAPT (S2, S57) / REIMPLEMENT (S4) |
| A17 | SSE hub + client (S7–S9) | Cursors, replay, `ready` / `reset`, data keepalive, backoff, dedupe | Robust live stream | Python server side; browser client extracted from the StarNet pattern | Event transport | REIMPLEMENT (S7, S8) / ADAPT (S9) |
| A18 | Link health + reconciliation (S10, S11) | Honest "link down"; snapshot rebuild; TTL sweeps | Never shows invented state | Screens **freeze and grey** with "LINK DOWN · age"; gap reset → "AWAITING"; per-agent "no update for N s" | Stale handling / screens | ADAPT (S10) / REIMPLEMENT (S11) |
| A19 | Truthful widgets and folds (S43, S46) | "—" until data, provenance, "no signal", honest "unknown" | Same law as Stellar's "never fabricate" | Typed placeholders: NOT AVAILABLE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN, UNKNOWN (Screen Registry §3) | Screens | REIMPLEMENT |
| A20 | Work poses from events (S26) | Runtime events set work poses and hand-offs | Agents visibly do what the engine did | Stellar's explicit state catalogue (plan §6.2); hand-offs only on real events | Agent visual states | REIMPLEMENT |
| A21 | Culling, painter sort, perf stats (S31, S32) | Skip off-screen props; y-sort; frame-cost percentiles | Performance at medium zoom | Isometric depth key (x + y and layer); culling per room | Renderer (engine layer) | ADAPT |
| A22 | Chunked static cache (S35) | Re-bake only dirty or visible chunks | Cheap static layers | **Per-room static layer cache** (floors, walls, fixed furniture); the three hubs as separate layers | Renderer | DEFER (until the renderer spike) |
| A23 | Render-fault resilience (S30) | Loop survives throws; honest fault overlay | A crash never looks like a frozen market | Stellar overlay text: "DISPLAY FAULT", never a frozen value without a label | Renderer | REIMPLEMENT |
| A24 | Camera focus / follow / director (S29) | Focus, follow-lock, idle director; user input wins | Readable overview of a wide vessel | Modes: vessel overview → hub → room → agent; director optional; reduced motion respected | Camera | DEFER (director) / REIMPLEMENT (modes) |
| A25 | Versioned loading and UI envelope (S17, S41) | Migrations, forward-version guard, backup | Safe layout and preference files | Layout schema `stellar.vessel` v1; local UI preferences only, **no trading truth** | Layout file / UI preferences | REIMPLEMENT |
| A26 | Visual QA (S49–S51) | Seeded shoot → PNG → signature diff; pure-module tests | Regression safety | Recorded Stellar event fixtures, frozen clock, seeded ambient → golden PNGs; independent-oracle path tests on the new vessel grid (every door, closed wall, the corridors) | Testing | REIMPLEMENT (S49) / ADAPT (S50, S51) |
| A27 | Loopback API security (S12) | Host pin, Origin, token, tickets, redacted egress | The read-only stream carries financial data | Python middleware; no write endpoint exists | Security | REIMPLEMENT |
| A28 | Room kinds (S13) | hab / bridge / lab / quarters / storage | Functional identity drives look and behaviour | Stellar room function = a **real runtime responsibility** (which agents work there, which events drive it). Hubs: Lab / Command / Habitat; L and R rooms assigned later | Room system | REIMPLEMENT (concept) |
| A29 | Leisure seating and seat recovery | Couch / recliner seats; recovery when blocked | Habitat must feel alive without fake emotion | Habitat hub and R rooms: seated ambient anchors, claimable, seeded, no emotion language | Leisure / ambient | REIMPLEMENT |
| A30 | Idle "sentience" engine (S27) | Needs, grief, chase, mimic, `Math.random` | — | — | — | DO NOT USE |
| A31 | Art, sprites, props art, painters, CRT, fonts, sfx, brand (S15, S33, S34, S36–S39, S45, S53–S56) | StarNet's look | — | Stellar's own 2.5D art only | — | DO NOT USE |
| A32 | REFIT editor, station store, UI commands, frontend roster (S16, S40, S42, S47, S48) | User-built stations; UI drives the engine | — | The Stellar UI is read-only; the engine owns the roster | — | DO NOT USE |
| A33 | Source-lock tests (S52) | Regex and `Function()` extraction of `world.js` | — | Importable Stellar modules instead; keep the scenario ideas | Testing | DO NOT USE (ideas only) |
| A34 | Floating panel geometry (S44) | Pure panel clamp helpers | Side panels on small screens | Stellar side panels | UI chrome | DEFER |

**Mechanics adapted for the new vessel:** A1, A2, A4, A6, A8, A11, A28, A29, together with the
single-grid simplification (the old per-deck grids and lift graph are gone).

**Deferred:** A3 (room seal, until room functions exist), A22, A24 (director), A34.

**Prohibited:** A30–A33, plus S3, S15, S16, S27, S33, S34, S36–S40, S42, S45, S47, S48, S52–S56.

---

## 5. Agent visual states

The states the owner lists all exist in the Stellar catalogue (Visual World Plan §6.2). No new
state is needed:
- idle, walking, researching, validating, analysing, monitoring, debating;
- reviewing, waiting, risk_review, approved, rejected, executing;
- post_trade_review, resting, overloaded, paused, error, offline.

StarNet contributes only the event-to-pose pattern (A20) and "work seizes idle" (A13). Its implicit
flags are not used (audit §4).

---

## 6. Useful StarNet concepts the current Stellar visual docs forgot or contradict

| # | Concept | Where Stellar's docs stand | Recommendation |
|---|---|---|---|
| F1 | **Doors only where authored.** StarNet's auto-doors are a convenience | The Visual World Plan §16 and its §1.7 table said "automatic doors between corridors and ordinary rooms". **Corrected** in the final consistency pass: explicit doors only | Explicit door list only (A2); the owner's sketch is the door list |
| F2 | **Art shape vs walk shape** (chamfer split) | Not mentioned; the old plan had only rectangles | Needed for the three circular hubs and the six rotated R rooms (A4) |
| F3 | **Room sealing as a navigation fact** (a sealed room has no doors in `canStep`) | Old docs modelled a sealed blast door visually only | Keep as a telemetry-driven mechanism, and decide its use with room functions (A3) |
| F4 | **Snapshot reconciliation details**: orphan runs started elsewhere, and the recent-run-end guard (a stale snapshot must not undo newer local truth) | The plan has reconciliation, but not these two rules | Add them to the adapter rules (A18) |
| F5 | **Transport details**: bounded replay size, backpressure eviction, data-frame keepalive | The plan names the transport (VW-14) and keepalive, but not bounded replay or backpressure | Add them to the transport design (A17) |
| F6 | **Static layer cache** (chunked or per room) | Not in the plan | Per-room cache, decided in the renderer spike (A22) |
| F7 | **UI preference envelope** with a forward-version guard | Not in the plan | UI preferences only (A25) |
| F8 | **Versioned, junk-tolerant layout loading** | The plan has a layout format (VW-15), but no migration or guard | `stellar.vessel` v1 with migrations (A25) |
| F9 | **Camera follow-lock / director with "user input always wins"** | The plan has camera modes, but no follow or director rules | Add; director deferred (A24) |
| F10 | **Seat recovery scenarios** (blocked seat, despawn releases seat) | Not in the test plan | Add as behavioural tests (A12, A26) |
| F11 | **Leisure seating mechanics** without an emotion engine | Old docs had leisure rooms, but no seat mechanics | Habitat anchors (A29) |
| F12 | **Room kind = functional identity** | The Room Registry had functions per old room | Re-base on the new slots once assigned (A28) |

---

## 7. Carry-forward rules for the visual layer (unchanged, restated)

- The architecture stays **engine → protected event / state layer → visual-state adapter →
  visual world / renderer**. The renderer consumes state and never produces trading authority.
- The visual layer must never create trades, change RiskPolicy, reset the circuit breaker, approve
  orders, bypass Risk, modify trading state, or fabricate trading data.
- Screens show real Stellar data only. Where no producer exists, they show a typed placeholder
  (NOT AVAILABLE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN).
