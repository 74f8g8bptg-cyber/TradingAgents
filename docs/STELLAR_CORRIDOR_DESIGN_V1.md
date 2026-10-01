# Stellar Corridor Design Sheet — COR-N and COR-S (V1)

## 1. Status

| | |
|---|---|
| **Status** | V1, **approved by the owner**; CD-1…CD-8 and CD-11 decided, CD-9 / CD-10 open (§13, §14). Visual design specification only: no code, no images, no assets, no audio, no runtime change, no trading logic |
| **Spaces** | `COR-N` (upper corridor) and `COR-S` (lower corridor), both ACTIVE transit spaces (Room Registry v2 §5; Floor Plan rev C §7) |
| **Source of truth** | Geometry and doors: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C §6–§8, `STELLAR_STATION_TOPOLOGY.md` v2 §3, §7–§8. Function: `STELLAR_ROOM_REGISTRY.md` v2 (corridor rows). Movement rules: `STELLAR_CHARACTER_REGISTRY.md` §3. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2 §2.2, §5.13. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Movements: every approved `STELLAR_ROOM_DESIGN_*_V1.md` sheet. Engine: `stellar/src/stellar/telemetry/catalogue.py` and the producers named in §6. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Corridor positions, widths, doors, topology, closed walls, the access model, the screen list and the movement rules of the Character Registry. Positions are **provisional** (the tile scale is open, TP-1 / VB-3) |
| **Hard boundary** | The corridors carry **only** movement that follows a real event (or the approved seeded ambient transit, §9). They never show a hand-off, courier, queue or alert that did not happen |

**StarNet (read-only, `fbddbf99`; structural ideas only, nothing copied):**

| StarNet concept | Structural idea | Stellar adaptation | Rejected |
|---|---|---|---|
| Door-aware BFS + string-pulled paths (`worldmodel.js` `path`, `smoothPath`, audit S14) | Agents path through doors only | Paths use only the 21 listed doors (A2); corridor walks are straight and legible | Adjacency auto-doors (S13, replaced by the explicit door list) |
| Traffic, yield and separation (S22–S24; adaptation A8) | No visual deadlocks | Operational right of way, deterministic tie-break, jam → fade (Character Registry §3) | Push-apart jitter as a visible behaviour |
| Watchable hand-off inside a real dispatch window (`world.js` hand-off boxes, S26) | A transfer is shown only while it really happens | Carried props (`PRP-*`) appear only between the triggering event and the drop | Flying boxes; conveyor belts (S16) |
| Idle containment zones (`zones.js`, S18) | Idle bodies stay in their zone | The corridor is **not** an idle zone; ambient bodies only pass through (§8) | — |
| "Border" and "huddle" social beats (`world.js`) | Two bodies meet where zones touch | — | **Rejected:** no meetings, chats or social beats in corridors |

---

## 2. COR-N identity

| Aspect | Definition |
|---|---|
| **Role** | Transit for the **analysis side**: `H-LAB` ↔ L1, L2, L3, L4 (L5 reserved) ↔ `H-CMD` |
| **Engine-true flow along it** | L2 technical evidence → L1; `H-LAB` macro → L1; L1 → `H-CMD` (only when the Trader's task starts); `H-CMD` ↔ L3 (Research Manager); Supervisor and Medic visits (§6) |
| **It is not** | A work room, social room, command area, idle area or meeting area |
| **Character** | A clean, bright passage; quiet between real walks |

## 3. COR-S identity

| Aspect | Definition |
|---|---|
| **Role** | Transit for the **decision and aftermath side**: `H-CMD` ↔ L10, L9, L7, L6 (L8 reserved) ↔ `H-LAB` |
| **Engine-true flow along it** | `H-CMD` → L10 (proposal card); L9 ↔ L10 (order capsule); L9 → L6 (Record Crystal); Supervisor visits to the L9 / L10 entries; Medic visits (§6) |
| **It is not** | A work room, social room, command area, idle area or meeting area |
| **Character** | Same as `COR-N`; the restricted markings of `DR-L9` / `DR-L10` are the only difference |

---

## 4. Topology (approved; unchanged)

| Item | `COR-N` | `COR-S` |
|---|---|---|
| Sketch extent (Floor Plan §7) | x 367–823, y 538–585 (≈ 456 × 47 px) | x 371–829, y 790–828 (≈ 458 × 38 px) |
| Width | **Equal for both corridors** (owner Q8; the 47 / 38 px difference is a drawing tolerance); working proposal ≈ **3 tiles** (Topology §8, not frozen) |
| Length | ≈ 29 tiles at the proposed scale |
| West end | `DR-N-LAB` (388, 563) into the `H-LAB` rim, via a `COR-009` junction | `DR-S-LAB` (383, 809) into the `H-LAB` rim, via a `COR-009` junction |
| East end | `DR-N-CMD` (801, 566) into the `H-CMD` rim, via a `COR-009` junction | `DR-S-CMD` (817, 805) into the `H-CMD` rim, via a `COR-009` junction |
| Doors on it | 7 (Topology §3) | 7 |
| Side walls | Closed except the room doors (Floor Plan §8) | same |

- **No junction between the corridors.** They meet only through `H-LAB` (west) or `H-CMD` (east).
- **No link to `H-HAB`:** the Habitat is reached only through `H-CMD` (`DR-CMD-HAB`).
- The gaps between rooms along both corridors are **non-walkable hull** (`WAL-009`), never side
  passages (Topology §7).

## 5. Room connections

| Corridor | Wall | Door | Centre (px) | Room | Door asset | Marking |
|---|---|---|---|---|---|---|
| `COR-N` | north | `DR-L1` | (473, 525) | L1 Market Specialists | `DOR-001` | `SGN-001` |
| `COR-N` | north | `DR-L2` | (604, 526) | L2 Technical Deck | `DOR-001` | `SGN-001` |
| `COR-N` | north | `DR-L3` | (737, 524) | L3 Debate Chamber | `DOR-001` | `SGN-001` |
| `COR-N` | south | `DR-L4` | (548, 587) | L4 Data Core | `DOR-001` | `SGN-001` |
| `COR-N` | south | `DR-L5` | (678, 586) | L5 (reserved) | `DOR-001` | `SGN-007` "RESERVED" |
| `COR-N` | west end | `DR-N-LAB` | (388, 563) | `H-LAB` | `DOR-009` | — |
| `COR-N` | east end | `DR-N-CMD` | (801, 566) | `H-CMD` | `DOR-009` | — |
| `COR-S` | north | `DR-L6` | (542, 783) | L6 Memory Archive | `DOR-001` | `SGN-001` |
| `COR-S` | north | `DR-L7` | (682, 786) | L7 Performance Lab | `DOR-001` | `SGN-001` |
| `COR-S` | south | `DR-L8` | (480, 834) | L8 (reserved) | `DOR-001` | `SGN-007` "RESERVED" |
| `COR-S` | south | `DR-L9` | (612, 834) | L9 Execution Bay (restricted) | `DOR-008` | `SGN-001` + `SGN-006` |
| `COR-S` | south | `DR-L10` | (741, 833) | L10 Risk Control (restricted) | `DOR-008` | `SGN-001` + `SGN-006` |
| `COR-S` | west end | `DR-S-LAB` | (383, 809) | `H-LAB` | `DOR-009` | — |
| `COR-S` | east end | `DR-S-CMD` | (817, 805) | `H-CMD` | `DOR-009` | — |

- Each room door sits in a **door niche** (`COR-007`) on the corridor side, with its department
  emblem plaque (`DEC-006`).
- **Door behaviour:** the listed doors open as a body approaches (Asset Registry `DOR-001` /
  `-008` / `-009`). This is **not** StarNet's adjacency auto-door, which Stellar replaced by the
  explicit door list (A2). `DOR-008` never locks; restriction is a navigation rule.
- **Reserved doors** (`DR-L5`, `DR-L8`): normal indicator dimmed, `SGN-007` plate, never opened
  (no agent is routed in; VB-6).

---

## 6. Movement audit (every movement documented in the approved sheets)

Direction is along the corridor (W = toward `H-LAB`, E = toward `H-CMD`).

| # | From | To | Character / object | Trigger | Event | Corridor, direction | Real producer? |
|---|---|---|---|---|---|---|---|
| M1 | L2 | L1 (`specialists.visitor`) and back | T3 `CHR-027` + technical crystal `PRP-001` | The specialist's task starts after the technical analysis | `analysis.created` (T3–T5) → `agent.task.started` (specialist) | `COR-N`, W and back E | **Yes** (runtime technical stage; pipeline) — only when the specialist LLM step runs |
| M2 | `H-LAB` | L1 and back | M1 `CHR-011` + macro crystal `PRP-001` | The macro assessment is consumed by a specialist | `analysis.created` (macro) → specialist `agent.task.started` | `COR-N`, E and back W | **Yes** (pipeline) — conditional as M1 |
| M3 | L1 | `H-CMD` (`command.visitor_1` / `visitor_2`) and back | Specialist desk figure + `PRP-001` | The Trader's task starts | specialist `analysis.created` → trader `agent.task.started` | `COR-N`, E and back W | **Yes, conditional**: the Trader LLM runs only when a selection is needed |
| M4 | `H-CMD` | L3 judge seat and back | Research Manager `CHR-002` | Debate start; return after the verdict or run end | `debate.started`; `decision.research_plan.created` / `run.*` | `COR-N`, W and back E | **Yes** |
| M5 | `H-CMD` | L10 `risk.intake_drop` and back | Proposal Builder `CHR-005` + proposal card `PRP-003` | A proposal is built | `trade.proposed` | `COR-S`, W (short) and back E | **Yes** |
| M6 | L9 | L10 `risk.outbox_pickup` and back | Paper Execution Agent `CHR-039` + order capsule `PRP-005` | Approval and order creation | `risk.approved` **and** `order.created` | `COR-S`, E and back W | **Yes** |
| M7 | L9 | L6 `archive.shelf` and back | `CHR-039` + Record Crystal `PRP-006` | A trade closes | `trade.closed` | `COR-S`, W and back E | **Yes** |
| M8 | `H-CMD` | L1 entry and back | Supervisor `CHR-003` | Research-stage failure **when no debate was running** | `run.failed` (`RESEARCH_FAILED`) (CD-3) | `COR-N` | **Yes** |
| M9 | `H-CMD` | L2 entry and back | Supervisor | Technical / setup failure | `run.failed` (`TECHNICAL_FAILED`, `SETUP_FAILED`) | `COR-N` | **Yes** |
| M10 | `H-CMD` | L3 `debate.visitor` and back | Supervisor | Research-stage failure **while a debate was running** (`debate.started` without `debate.completed`) | `run.failed` (`RESEARCH_FAILED`) (CD-3) | `COR-N` | **Yes**; never together with M8 |
| M11 | `H-CMD` | L4 `datacore.visitor` and back | Supervisor | Market-data failure | `run.failed` (`MARKET_DATA_FAILED`) | `COR-N` | **Yes** |
| M12 | `H-CMD` | L9 entry and back | Supervisor | Paper broker / preflight failure | `run.failed` (`PAPER_BROKER_FAILED`, `PAPER_PREFLIGHT_FAILED`) | `COR-S` | **Yes** |
| M13 | `H-CMD` | L10 entry and back | Supervisor | Risk / authorisation failure | `run.failed` (`RISK_FAILED`, `ORDER_AUTHORISATION_FAILED`) | `COR-S` | **Yes** |
| M14 | `H-HAB` (via `H-CMD`) | Entry of the affected room and back | Medic persona `CHR-041` | An agent task fails | `agent.task.failed` → state `error` | Either corridor | **Yes** (pipeline, trader desk); `overloaded` has **no producer** |
| M15 | A room (via `H-CMD`) | `H-HAB` recovery pod | Medic escorting a figure | A real cooldown | `agent.resting` | Either corridor | **No producer: NOT AVAILABLE** |
| M16 | Home room | `H-HAB` (via `H-CMD`) and back | Idle agents (seeded ambient) | Idle delay; return on real work | none (seeded ambient; Character Registry §3, A13, A14) | Either corridor | **Not an event**: approved seeded ambient transit (§13, K2) |
| M17 | Anywhere on ambient | Own station | Any agent | A real task for that agent | the agent's real event (work over idle) | Either corridor | **Yes** |
| M18 | L1 | `H-LAB` `lab.visitor_1` / `visitor_2` | Specialist desk figure | "A real task that involves research items" (H-LAB sheet) | **none named** | `COR-N` | **No trigger defined** (§13, K5) |
| — | Removed movements | PM → L3; `CHR-033` → L7; `CHR-034` → L6; `run.started` command meeting | — | — | — | — | **Not used** (no producer; L3 DC-5, L7 DP-6, H-CMD HC-10) |

## 7. Hand-off routes

| Hand-off | Object | Start (pick-up) | Corridor path | End (drop) | Visible only between |
|---|---|---|---|---|---|
| Technical evidence (M1) | `PRP-001` | T3 at `technical.station_t3` | `DR-L2` → `COR-N` (W, ≈ 8 tiles) → `DR-L1` | `specialists.visitor` | The specialist's `agent.task.started` and arrival |
| Macro context (M2) | `PRP-001` | M1 at `lab.handoff_n` | `DR-N-LAB` → `COR-N` (E) → `DR-L1` | `specialists.visitor` | The specialist's `agent.task.started` and arrival |
| Specialist view (M3) | `PRP-001` | Desk in L1 | `DR-L1` → `COR-N` (E, full length) → `DR-N-CMD` | `command.visitor_1` / `visitor_2` | The Trader's `agent.task.started` and arrival |
| Proposal (M5) | `PRP-003` | `command.console_proposal` | `DR-S-CMD` → `COR-S` (W, ≈ 5 tiles) → `DR-L10` | `risk.intake_drop` | `trade.proposed` and the drop |
| Order (M6) | `PRP-005` | `risk.outbox_pickup` (E1 walks there empty) | `DR-L10` → `COR-S` (W, ≈ 8 tiles) → `DR-L9` | `execbay.launch` | Pick-up at the outbox and arrival |
| Record (M7) | `PRP-006` | `execbay.launch` | `DR-L9` → `COR-S` (W, ≈ 4 tiles, across the corridor) → `DR-L6` | `archive.shelf` | `trade.closed` and the filing |

- A carried prop is **visible in the carrier's hands** for the whole walk and never travels alone.
- Hand-offs begin and end **inside rooms** at the named anchors; the corridor never hosts a drop,
  queue or waiting point.
- **No conveyor, tube or pipeline** exists or is drawn in the corridors (S16 rejected).
- When one carrier owes two real hand-offs (for example E1: M6 and M7), they run **in journal
  order**, one after the other; the badge updates at once (badges first) and a late walk fades
  (Character Registry §3).

---

## 8. Traffic rules

| Rule | Specification |
|---|---|
| **Transit only** | No stopping, standing, talking, waiting or loitering in a corridor. No furniture in the path (Room Registry) |
| **Lanes** | Two travel lanes by direction: **keep to the right** of the direction of travel; the centre stays free for passing. **Provisional** until the corridor width is frozen (CD-6) |
| **Hand-off lane** | **None separate.** Carriers are operational and use their travel lane with right of way |
| **Visitors** | Same lanes and rules as everyone (Supervisor, Medic) |
| **Right of way** | Operational over ambient; then the agent already moving in the corridor over one stepping out of a door; ties broken deterministically (Character Registry §3, A8) |
| **Crossing** | An agent leaving a door waits **inside the room's door approach**, not in the corridor, until the lane is clear; a moving agent does not stop for a crossing |
| **Opposing traffic** | Passes lane to lane; no face-off. A jam gives up after a timeout and fades (Character Registry §3) |
| **Door approaches** | The 1-tile approach on the corridor side of every door stays clear |
| **Corridor ends** | The hub-door junctions (`COR-009`) stay clear |
| **Reserved doors** | Never used; nobody is routed to `DR-L5` or `DR-L8` |
| **Restricted doors** | `DR-L9` / `DR-L10` are entered only by permitted classes (Character Registry §3); others pass by |

## 9. Character movement

- **No corridor resident.** No agent is ever assigned to a corridor anchor (none exists).
- A figure appears in a corridor **only** in one of two separate kinds of movement:
  - **Operational movement (event-driven):** a real task (M17), a real hand-off (M1–M7) or a real
    visit (M8–M14). It always has right of way.
  - **Ambient transit (not an event):** the approved seeded walk to or from `H-HAB` while idle
    (M16; CD-2). It is idle behaviour only: the figure never stops, loiters, carries a prop or
    looks busy, and a real task pre-empts it at once (work over idle).
- **Walking:** eased gait, 8 facings (A7), straight along the lane; `walk` clip, plus `carry` while
  holding a prop.
- **Destination and return:** every trip ends at a named room anchor; the return trip follows the
  same corridor back after the drop, visit or task.
- **No real event:** the corridors are **empty**. No random walking, no "busy" animation, no
  patrols.

## 10. Alert repeaters

| Repeater | Placement | Content | What it receives today |
|---|---|---|---|
| `DSP-CRN-01` (`SCR-011`) | `COR-N` **south** wall, midway between `DR-L4` and `DR-L5` (≈ x 613), clear of both door niches (moved from the north wall by CD-11) | Station alert **word + icon** (steady; CD-4) | The **derived** station alert level (Screen Registry §2.2); no event of its own |
| `DSP-CRS-01` (`SCR-011`) | `COR-S` **south** wall, midway between `DR-L9` and `DR-L10` (≈ x 676), clear of both door niches (moved from the north wall by CD-11) | same | same |

**Engine facts:**
- `station.alert_level.changed` has **no producer**; the level is **derived** from real inputs:
  - RED: `circuit_breaker.tripped` (**producer exists**), or a `FAILED` health report (on-demand
    `health()`);
  - AMBER: `risk.review.requested` (**producer exists**), a `DEGRADED` / `BLOCKED` health report or a
    reconciliation issue (on demand);
  - BLUE: a run in progress (`run.started` without a terminal `run.*`; **producer exists**);
  - GREEN: none of these, and fresh telemetry.
- **Why PARTIAL:** there is no alert-level producer; part of the inputs are on-demand reports, and
  "fresh telemetry" depends on the future UI link window (not defined yet).
- **Honest V1 states:** the derived word + icon when the UI link has real events; **NO TELEMETRY**
  when no events have arrived or the link is down past its window. NO TELEMETRY is **not** the only
  honest state: the derived level is honest while its inputs are real.
- **Behaviour:** a steady word + icon; **no flashing, sound or light show** (H-CMD HC-15). The
  corridor cove light (`LGT-001`) follows the same derived level, always paired with the repeater's
  word and icon (Visual Bible C7).

---

## 11. Visual / material design

| Element | Specification |
|---|---|
| Floor | **Deep navy** corridor floor with a guide inlay (`FLR-005`, laid as `COR-008` segments); the inlay marks the two lanes with a thin **titanium** line; the floor guide strip (`LGT-004`) runs along the inlay and guides toward **both** corridor ends (CD-7); it never implies a single hub direction |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium** base and cove trims; **graphite** door niches (`COR-007`); the camera-facing wall is cut away (`WAL-008`): the **north** wall under the frozen default camera **Iso · right** (Visual Prototype V1 §0; it was the south wall for the earlier camera), and its doors keep frame, threshold and opening (Visual Bible C4). No screens or signs on a cut-away wall |
| Hull gaps | Solid infill (`WAL-009`) between room doors where the hull shows; never a passage |
| Ceiling | A flat ceiling with the continuous cove light (`LGT-001`); not drawn over the floor in the cutaway |
| Lighting | Even, bright, neutral white; the derived alert tint only with the repeater's word and icon. No flicker, no dark sections |
| Wayfinding | Room name plate (`SGN-001`) at each active door; wayfinding arrows (`SGN-003`) at the corridor ends and near door niches, naming the rooms ahead; the vessel directory (`SGN-002`) sits on the **hub** side of each corridor end |
| Door markings | Department emblem plaques (`DEC-006`); restricted marking (`SGN-006`) on `DR-L9` / `DR-L10`; "RESERVED" plates (`SGN-007`) on `DR-L5` / `DR-L8` |
| Structure | Hull rib trims (`DEC-005`) as a light rhythm along the walls (Asset Registry: corridors) |
| Junctions | `COR-009` corridor-to-hub junctions at all four ends, entering the hub rims through `DOR-009`; never sealed end caps |
| Avoid | Military or spaceship-corridor clichés, dark or horror lighting, decorative or social furniture, plants, benches, extra screens |

## 12. Audio hooks (future only; nothing implemented)

| Future sound | Real trigger it could follow | Note |
|---|---|---|
| Door open / close | A body crossing a listed door **during a real trip** (M1–M14, M16–M17) | Derived from movement that itself follows an event; never from idle doors |
| Footsteps | The same real trips | Quiet; no footsteps without a walk |
| Hand-off pick-up / drop | The drop or pick-up of `PRP-001` / `003` / `005` / `006` (triggers in §7) | One short cue per real transfer |
| Alert repeater cue | A **change** of the derived level to RED (`circuit_breaker.tripped`) or AMBER (`risk.review.requested`) | Single cue, no repeating alarm (HC-15) |
| Corridor ambience | none (constant) | Optional low room tone; carries no information |

---

## 13. Contradictions and owner decisions

| # | Topic | Facts | Resolution |
|---|---|---|---|
| **K1** | Stale corridor purpose (Room Registry `COR-N`: "LAB → L1 / L2 / L3 / L4 → CMD") | Engine order: L2 → L1 (TA-2); L4 data only | **Resolved (CD-1):** Room Registry corridor rows re-worded to the engine order and the full movement list |
| **K2** | Ambient transit vs "real events only" | Seeded ambient to `H-HAB` while idle is approved (Character Registry §3, A13, A14) | **Resolved (CD-2):** kept, and documented **separately** from event-driven operational movement (§9): idle only, never loitering, never shown as work |
| **K3** | Medic `overloaded` and cooldown escort | `agent.overloaded`, `agent.resting` have no producers | **Stands:** **NOT AVAILABLE**; only the `agent.task.failed` visit (M14) |
| **K4** | Alert repeaters PARTIAL | No alert-level producer; on-demand health inputs; no link window defined | **Resolved (CD-4):** derived real state with icon + text when inputs exist, otherwise **NO TELEMETRY**; steady; no flashing; no sound |
| **K5** | L1 → `H-LAB` visitor walk | No event names the triggering task | **Resolved (CD-5):** unused until a real trigger exists; no event invented |
| **K6** | Corridor-level anchors | Hand-offs start and end in rooms | **Stands:** existing room anchors only; no corridor anchor invented |
| **K7** | Supervisor trigger overlap on `RESEARCH_FAILED` | The debate runs inside the research stage | **Resolved (CD-3):** exactly **one** visit: L3 `debate.visitor` if the failing run journaled `debate.started` without a later `debate.completed` (a debate was running), otherwise the L1 entry. L1, L3 and H-CMD sheets aligned |
| **K8** | Width and lanes | Width equal, ≈ 3 tiles proposed, not frozen | **Resolved (CD-6):** keep-right two-lane rule, **provisional** until the width is frozen |
| **K9** | Guide strip direction | Each corridor has a hub at both ends | **Resolved (CD-7):** `LGT-004` guides toward **both** corridor ends; no single hub direction |
| **K10** | Door wording | A2 replaced adjacency auto-doors by the explicit door list | **Stands:** explicit-door interpretation (§5) |
| **K11** | Useful objects that do not exist (passing bays, corridor-name signs) | No such assets | **Stands:** not invented |
| **K12** | `COR-S` row incomplete | Also M7, M12–M14 | **Resolved (CD-1):** Room Registry row re-worded |

## 14. Owner decisions

| # | Decision | Status |
|---|---|---|
| CD-1 | Room Registry corridor rows (K1, K12) | **Closed:** aligned |
| CD-2 | Ambient transit (K2) | **Closed:** kept; idle only; separate from operational movement |
| CD-3 | Supervisor on `RESEARCH_FAILED` (K7) | **Closed:** exactly one visit (L3 if a debate was running, else L1) |
| CD-4 | Alert repeaters (K4) | **Closed:** derived state with icon + text, or NO TELEMETRY; steady; no flashing; no sound |
| CD-5 | L1 → `H-LAB` visit (K5) | **Closed:** unused until a real trigger exists |
| CD-6 | Lanes (K8) | **Closed:** provisional keep-right two-lane rule |
| CD-7 | Guide strip (K9) | **Closed:** toward both corridor ends |
| CD-8 | Repeater positions (§10) | **Closed:** as proposed |
| CD-9 | Exact dimensions | **Open** (after the global tile scale, VB-3 / TP-1) |
| CD-10 | Exact colour values | **Open** (visual production, VB-4) |
| CD-11 | Repeater walls under the frozen Iso · right camera | **Closed (owner):** `DSP-CRN-01` and `DSP-CRS-01` move to the corridors' **south** walls, clear of the door niches, for readability from the frozen camera and so that no important display sits on a cut-away wall. Same IDs, content and function |

## 15. Consistency requirements

- Every corridor movement maps to a row in §6 with a real trigger, or is the approved ambient
  transit; nothing else is animated.
- Only the 14 corridor doors of §5 exist; no new door, junction or passage.
- Carried props appear only between their triggering event and their drop (§7).
- No agent stops, waits or meets in a corridor; door approaches and corridor ends stay clear.
- Repeaters show only the derived level or NO TELEMETRY, with word + icon, never colour alone.
- Nothing is placed on the cut-away walls. Under the frozen **Iso · right** camera these are the corridors' **north** walls; the two repeaters sit on the south walls (CD-11).
- Any future room sheet adding a walk must add its row to §6.
