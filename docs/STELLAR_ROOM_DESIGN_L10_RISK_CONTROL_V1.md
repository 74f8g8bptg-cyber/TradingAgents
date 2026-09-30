# Stellar Room Design Sheet — L10 Risk Control Room (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; RC-1…RC-5 decided (§9, §10). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L10` — Risk Control Room · ACTIVE · RESTRICTED (Room Registry v2 §3.11) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors, access: `STELLAR_ROOM_REGISTRY.md` v2 + `STELLAR_CHARACTER_REGISTRY.md` §3. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list, and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | The Risk Engine runs in the engine. This room only **shows** its real work. The visual layer never approves, rejects, sizes, resets the breaker, changes RiskPolicy, or bypasses Risk (Visual World Plan §17; adaptation A27) |

---

## 1. StarNet control-concept review

**Method.** I reviewed the audit (S12, S13 room seal, S26, S42, S43, S46) and read the local StarNet
checkout at pinned revision `fbddbf99` **read-only**:
- `worldmodel.js`: the airlock room seal, and the intake line limits (`maxUsdPerDay` /
  `maxUsdPerMessage`);
- `world.js`: approval walk-and-wait on `permission.prompt`, link-down honesty, render-fault overlay;
- the sidecar's station authority (a server-side validation that never trusts renderer-posted
  state).

**Only structural ideas are extracted. Nothing is copied:** no art, assets, characters, layouts,
interfaces or security aesthetics.

| StarNet concept (what exists) | Structural idea (why / how) | Stellar adaptation | Rejected |
|---|---|---|---|
| **Room seal** (a room holding a sealing airlock loses its boundary doors, so no path crosses) | A control room can be isolated by **state**, not decoration | L10 isolation is **logical**: role permissions, restricted anchors, and the `SGN-006` marking. The door is **never** locked or sealed by the visual layer ("no invented locks"). The room-seal mechanism stays **deferred** (A3) | Physical sealing in V1; a seal set by the UI |
| **Approval walk-and-wait** (an agent walks to a spot and waits while a permission prompt is pending) | Pending decisions are **visible** as a waiting state, not hidden | Proposals waiting for a risk decision appear in the **Approval Queue** (`DSP-RSK-06`). `REVIEW_REQUIRED` items are flagged there (amber + icon + text). The courier drops the card and **leaves**; nobody performs a waiting scene without a real event | Waiting theatre with no event; any UI "approve" affordance |
| **Hard limits at the intake** (a line budget stamped on the entry: max per day / per message) | Checks sit **at the point of entry**, before work proceeds | The **intake counter** is the first step. Limits are shown as **value vs limit** per rule (`DSP-RSK-03`), always from the engine's real check. Limits are **never** set or edited in the UI | UI-editable limits; budgets as build-mode props |
| **Station authority** (the server never trusts renderer-posted state) | The renderer is **not** an authority | The same law: the visual world consumes state and never produces trading authority (A27) | — |
| **Link honesty and the render-fault overlay** | A control display must never look healthy when it is not | Risk screens **freeze and grey** with **LINK DOWN · age**; a renderer fault shows **DISPLAY FAULT**; the breaker is never shown "ARMED" by default (A18, A23) | — |
| **Responsible roles** (work tied to a specific role and station) | One role per check; separation of duties | **P2** (contradiction check) at the intake desk; **P3** (rules, sizing, exposure, breaker) in the core; **E1** only at the outbox; **P1** only at the intake. Each is a separate figure | Merged "security officer" figures |
| **Security aesthetics** (alarms, CRT phosphor, flashing) | — | — | Rejected: StarNet look (S33, S34), flashing alarms, fake danger |
| **Authority theatre / emotions** (for example complaint or "gripe" behaviours) | — | — | Rejected: fake authority, artificial emotions (A30) |

**Stellar original decisions (not from StarNet):**
- The three-zone room (intake → core → outbox).
- The order capsule appears **only after** `risk.approved` **and** `order.created`.
- Door panel **BREAKER TRIPPED** from telemetry.
- Red only from real system states; restricted marking as icon + marking + optional amber
  (Visual Bible C2 / C3).
- The approved nine-screen set.
- All materials and lighting.

---

## 2. Room identity

| Aspect | Definition |
|---|---|
| **Purpose** | The deterministic **risk layer**: proposal intake, contradiction check, rule checks, sizing, exposure, the circuit breaker (display only), and the hand-off of **approved** orders to execution. Risk is evaluated **before** execution. **Not** a trading, execution or command room |
| **Atmosphere** | Caution, precision, verification, protection, responsibility: calm and controlled, never alarmed without cause |
| **Visual identity** | A darker, focused room with a clear **three-step flow**: an **intake counter** by the door → a **verification core** with rule, sizing and breaker stations → an **outbox counter** by the door. A restricted marking on the door. Deliberate, orderly lines |
| **Importance level** | **High.** It is the safety gate of the whole vessel. Its state (the breaker) is at the top of the visual hierarchy (Visual World Plan §14.8) |
| **Relationship with L1 Market Specialists** | **Indirect.** Specialists never visit L10. Their analysis reaches Risk only through the chain (L1 → … → `H-CMD` → proposal). Route if ever needed: `COR-N` → `H-CMD` → `COR-S` → L10 |
| **Relationship with L9 Execution** | **Next door on `COR-S`** (the L9 door is west of the L10 door; the rooms are separated by non-walkable hull). The **Paper Execution Agent** (E1) comes from L9 to L10's **outbox only**, to collect an approved order capsule, and returns to L9. No other link |
| **Relationship with H-CMD** | **Upstream and adjacent.** The Trade Proposal Builder (P1) carries the proposal from `H-CMD` → `DR-S-CMD` → `COR-S` → `DR-L10` (the nearest room to `H-CMD` on `COR-S`). The Supervisor may visit the **entry** only. L10's north-east corner touches the `H-CMD` rim (a closed wall contact, no opening) |

---

## 3. Architecture

### 3.1 Shape and entrance (approved; unchanged)

- **Shape:** tall rectangle south of `COR-S` (sketch about 115 × 179 px; about 7 × 11 tiles at the
  working scale, which is **not frozen**).
- **One door:** `DR-L10` in the **north wall**, onto `COR-S`. It is an ordinary 2-tile door with
  the **restricted variant** `DOR-008`:
  - the `SGN-006` restricted marking: **icon + marking + optional amber light**;
  - the corridor-side door panel `DSP-RSK-09`.

  **It does not lock physically** (no invented locks, no automatic door). Access is a navigation
  permission (Character Registry §3).
- **Closed contact:** the north-east corner touches the `H-CMD` rim. It is solid, with no opening.
- **Cutaway:** the camera-facing walls are cut away. The door keeps a visible frame, threshold and
  opening (Visual Bible C4).

### 3.2 Schematic (not to scale; door at the top)

```
                          COR-S
   +-------------------[ DR-L10 ]------------------+   <- DSP-RSK-09 door panel (corridor side)
   | risk.intake     risk.entry_wait    risk.outbox |
   | CON-012 intake       (entry)       CON-029     |
   |  + DSP-RSK-01                      outbox      |
   | risk.intake_drop                   + DSP-RSK-07|
   | CON-001 contradiction              risk.outbox_|
   | desk (P2) + DSP-RSK-02             pickup (E1) |
   | DSP-RSK-06 approval queue (west wall)          |
   |------------ low divider: start of risk.core ---|
   | CON-015 breaker     |  aisle  |  CON-014 sizing|
   | panel (west wall)   |         |  console (east)|
   | + DSP-RSK-05 band   |         |  DSP-RSK-04    |
   |                     |         |  exposure      |
   |        CON-013 rule-checklist console          |
   |        + DSP-RSK-03 risk rules (south wall)    |
   |        DSP-RSK-08 paper P&L (south-east)       |
   +------------------------------------------------+
```

### 3.3 Materials

| Surface | Material |
|---|---|
| Floor | **The approved grating floor (`FLR-003`) is the Risk room's identity** (owner decision RC-1), laid throughout the room in graphite / deep tones. The depth comes from materials and lighting, **not** from making the room dark |
| Walls | **A combination** (owner decision RC-2): **gunmetal structural elements** (frames, columns, hull ribs `DEC-005`), **warm off-white panels** (`WAL-001`) between them, and **graphite technical accents**, with titanium trims. **Not** a black military bunker |
| Technical elements | **Graphite** console bodies, counters and screen bezels |
| Department accent | **Engineering gold on charcoal** (static). **Owner decision RC-3:** gold = the Risk / Operations **department identity**; amber / red = **real system status only**. Colour never communicates state without an icon and text |
| Core rail | A waist-height titanium-framed rail marking the start of `risk.core`. **Kept** (owner decision RC-4) as a **visual organisation element only**: **not** a barrier, lock or access control. It blocks no path; access is navigation permission |

### 3.4 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a recessed cold panel light (`LGT-005`) over the core; only its edge is suggested in the cutaway |
| General | **Darker and more focused than `H-CMD`:** a lower ambient level, with light concentrated on the consoles and counters (`LGT-002` pools while their agent works) |
| Amber / red accents | **Only from real system states**, and **never colour alone**: <ul><li>**amber** + icon + text on `REVIEW_REQUIRED` (`risk.review.requested`) or on a limit approach (only when the event has a producer);</li><li>**red** + icon + text when the breaker is `TRIPPED` (`circuit_breaker.tripped`), on `DSP-RSK-05` and the door panel `DSP-RSK-09`.</li></ul>No decorative red |
| Alert | The station alert tint on `LGT-001`, with a word and icon (Visual Bible C7) |

### 3.5 Walkable areas and zones (Room Registry §3.11)

| Zone | Who may enter | Rule |
|---|---|---|
| `risk.intake` (inside the door, west) | P2; **P1 courier** (drop only) | The courier drops at `risk.intake_drop` and leaves |
| `risk.entry_wait` (centre, by the door) | Supervisor, Medic (entry only) | Approach point; they go no further |
| `risk.outbox` (inside the door, east) | P3; **E1** (pickup only) | E1 collects at `risk.outbox_pickup` only after `risk.approved` + `order.created` |
| `risk.core` (south, beyond the divider) | **P2, P3 only** | Restricted anchors: rule, sizing and breaker consoles |
| Door approach | Everyone passing | Always empty |

---

## 4. Risk roles and character placement

| Figure | Role | Workstation (anchor) | Usual position | Movement pattern | Interaction |
|---|---|---|---|---|---|
| **Risk Agent** `CHR-037` (P3 `risk_engine`, OPS) | Rules, sizing, exposure, breaker | `CON-013` · `risk.rule_console` (R); also `risk.sizing_console` (R), `risk.breaker_panel` (R) | Standing at the rule console in the core | Moves between its three core consoles as its real checks run; to the outbox counter when an order is approved; rests in the Habitat recovery pods on a real cooldown (`MP-RISK`) | **L1:** none. **H-CMD:** receives proposals via the intake (P1). **L9:** hands approved orders to the outbox for E1 |
| **Contradiction Checker** `CHR-036` (P2, OPS) | Contradiction check at intake | `CON-001` · `risk.intake_desk` (R) | Seated at the intake desk | Mostly stationary; checks each proposal as `trade.proposed` arrives | Receives cards from P1; passes to P3 (the check result on `DSP-RSK-02`) |
| Trade Proposal Builder `CHR-005` (P1, CMD) — visitor | Courier | `risk.intake_drop` | — | `H-CMD` → `COR-S` → drop → back, **only** after `trade.proposed` (`MP-COURIER`) | Drop only; never enters the core |
| Paper Execution Agent `CHR-039` (E1, OPS) — visitor | Order pickup | `risk.outbox_pickup` (R) | — | L9 → `COR-S` → outbox → L9, **only** after `risk.approved` + `order.created` (`MP-EXEC`) | Pickup only |
| Supervisor `CHR-003` — visitor | Monitoring | `risk.entry_wait` | — | Only on a real `run.failed` with `RISK_FAILED` or `ORDER_AUTHORISATION_FAILED` (`MP-SUPERVISOR`; H-CMD HC-16), entry only | Observes; touches no console |
| Medic `CHR-041` — visitor | Operational wellbeing | `risk.entry_wait` | — | Only on a real `error` / `overloaded` of P2 or P3; entry only | Attends from the entry |

**Monitoring in the vessel's sense** (screens, breaker state) happens **in this room on displays**.
There is no separate "monitoring agent" in L10. The **Execution Checker** (`CHR-038`, P4) does
pre-flight validation in **L9**, not here.

Figures follow the Character Bible: the Risk Agent is the widest shoulder line in a gold vest with
a badge and scanner; P2 is a separate figure. There is no emotional simulation. Stamp and lever
gestures play **only** on real events.

---

## 5. Access and restriction (summary)

- **One explicit door** (`DR-L10`, `DOR-008`); no automatic door; **no lock**.
- **Restricted indication** (Visual Bible C3): an **icon + marking** (`SGN-006`) + an **optional
  amber** light; readable without colour.
- **Red** only from real system states (Visual Bible C2). Today only `circuit_breaker.tripped` has a
  producer. Security-event and access-denial events do not exist yet, so they cannot turn the door
  red.
- Access is a **navigation permission**: characters without permission are never routed in.
- The visual layer never "opens" or "closes" the room.

---

## 6. Main objects

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Rule-checklist console** | `CON-013` + `DSP-RSK-03` | Every risk rule, value vs limit, pass / fail | South wall of the core, facing the door | `risk.rule_console` (R: P3) | **Hero** |
| 2 | **Breaker panel** (display only) | `CON-015` + `DSP-RSK-05` | Breaker state, reason, history; the lever moves **only** on a real `circuit_breaker.*` | West wall of the core | `risk.breaker_panel` (R: P3) | **Hero** (top of the visual hierarchy) |
| 3 | **Intake counter** (validation station) | `CON-012` + `DSP-RSK-01` | Where proposals enter | West of the door, in the intake zone | `risk.intake_drop` (P1) | High |
| 4 | **Contradiction desk** (review desk) | `CON-001` + `DSP-RSK-02` | P2's contradiction check | Behind the intake counter | `risk.intake_desk` (R: P2) | High |
| 5 | **Sizing console** | `CON-014` | Sizing by formula (engine) | East wall of the core | `risk.sizing_console` (R: P3) | High |
| 6 | **Outbox counter** | `CON-029` + `DSP-RSK-07` nearby | Approved order hand-off to execution | East of the door, in the outbox zone | `risk.outbox_pickup` (R: E1) | High |
| 7 | **Audit surfaces** (walls) | `SCR-002` / `SCR-003` | Exposure, the approval queue, paper P&L | Walls (§7) | Look targets | Medium |
| 8 | Core rail (kept, RC-4) | *(architectural rail)* | Visual organisation of the core; **not a barrier, lock or access control** | Across the room between the entry zones and the core, with open gaps so no path is blocked | none | Low |
| 9 | Grating floor, cold light, hull ribs | `FLR-003`, `LGT-005`, `DEC-005` | Room character | Core | none | Medium |
| 10 | Lockers | `STO-001` (optional) | Storage | A core wall, clear of consoles | none | Low |

**Alert displays** are the breaker display (`DSP-RSK-05`) and the door panel (`DSP-RSK-09`); there
is no separate alarm device. **No** fake alert beacons or decorative warning lights.

---

## 7. Screen design (Screen Registry v2 §5.10 is the authority)

| Category | Display | Content | Placement | Main placeholders |
|---|---|---|---|---|
| **Risk** | `DSP-RSK-03` Risk Rules | Every rule: value vs limit, pass / fail | South wall above the rule console | Rows **PENDING**; never pre-ticked |
| | `DSP-RSK-04` Exposure | Exposure bars by instrument / currency | East wall of the core | **UNKNOWN**; **STALE** |
| | `DSP-RSK-05` Circuit Breaker | ARMED / TRIPPED, reason, reset history (display only) | Band above the breaker panel, west wall | **UNKNOWN**, never "ARMED" by default |
| | `DSP-RSK-08` Paper P&L | Realised / unrealised paper P&L, drawdown (risk context, not trading) | South-east wall | **UNKNOWN** |
| **Validation** | `DSP-RSK-01` Proposal intake | The proposal under review | On the intake counter | **AWAITING DATA**; **UNKNOWN** for missing economics |
| | `DSP-RSK-02` Contradictions | Contradictions checked at intake | On the contradiction desk | **UNKNOWN**; "NONE REPORTED" only when present and empty |
| | `DSP-RSK-06` Approval Queue | Proposals awaiting a decision; `REVIEW_REQUIRED` items (amber + icon + text) | West wall of the intake zone | **QUEUE EMPTY** only when fresh |
| **Monitoring** | `DSP-RSK-07` Pending / Blocked Orders | Pending orders, pre-flight blocks, rejections with reasons | Beside the outbox counter | **NONE** only when fresh |
| | `DSP-RSK-09` Door status panel | Breaker word + icon, on the corridor side of `DR-L10` | Outside, beside the door | **UNKNOWN** |

**Screen rules for this room:**
- **Never invent** risk values, positions or alerts. Every value comes from the registry's sources,
  with its age.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **MODE UNKNOWN**
  applies only to mode plaques; L10 has none (the mode plaques are in `H-CMD` and L9).
- On link loss, every risk screen **freezes and greys** with **LINK DOWN · age**, and the breaker
  shows its last known state marked stale, never "ARMED".
- `risk.limit.approached` has **no producer** today, so no "approaching limit" warning is shown
  until it does.
- All displays are read-only. The breaker panel has **no** reset affordance in the UI.

---

## 8. Agent life

All activity comes from **real tasks**, **real events** or **normal idle behaviour**. There is **no
emotional simulation**.

| Activity | Trigger | Who / where | Clips |
|---|---|---|---|
| **Receiving** | `trade.proposed` | P1 drops the card at intake; P2 takes it | `walk`, `carry` (`PRP-003`) |
| **Checking information** | Contradiction check on the proposal | P2 at the contradiction desk | `sit_work`, `look_screen` |
| **Validating** | `risk.check.started` → `risk.check.completed` | P3 at the rule console; rows light one by one | `stand_work`, `checklist_sweep` |
| **Reviewing** | Sizing and exposure as part of the real check | P3 at the sizing console / exposure wall | `stand_work`, `look_screen` |
| **Communicating decisions** | `risk.approved` / `risk.rejected` / `risk.review.requested` | P3: `stamp` (display time only). The result appears on the screens. On approval + `order.created`, the capsule appears at the outbox | `stamp` |
| Hand-off out | `risk.approved` **and** `order.created` | E1 arrives from L9, collects `PRP-005`, returns | `walk`, `carry` |
| Breaker | `circuit_breaker.tripped` / `reset` / `reset_refused` | P3 at the breaker panel: `lever`. The door panel updates; the outbox goes dark | `lever` |
| Idle | No task | P2 / P3 at their home anchors; optional seeded ambient to the Habitat | `stand_idle` |

---

## 9. Contradictions and owner decisions (all resolved)

| # | Topic | Owner decision | Aligned |
|---|---|---|---|
| **R1 / RC-1** | Floor | The **approved grating floor `FLR-003`** is the Risk room's identity. Graphite / deep tones come through materials and lighting, not by making the room dark | Sheet §3.3; Room and Asset Registries already list `FLR-003` for L10 |
| **R2 / RC-2** | Walls | A **combination**: gunmetal structural elements + warm off-white panels + graphite technical accents. **No black military bunker** | Sheet §3.3; Visual World Plan §14.2 L10 line updated to match |
| **R3 / RC-3** | Gold vs amber / red | **Gold = Risk / Operations department identity. Amber / red = real system status only.** Colour never communicates state without an icon or text | Sheet §3.3; consistent with Visual Bible C2 / C3 / C7 |
| **RC-4** | Core rail | **Kept** as a visual organisation element only: not a barrier, lock or access control | Sheet §3.3, §6 |
| **RC-5** | Layout | **Approved:** intake → verification core → outbox | Sheet §3.2 |
| R4 | Relationship with L1 | Indirect (through `H-CMD`); documented | — |
| R5 | "Not a trading room" vs the P&L and orders screens | Not a conflict: approved risk context from real data | — |
| R6 | Validation / monitoring roles | P2 here, P4 in L9; monitoring = displays + Supervisor visits | — |

No remaining conflicts with:
- the topology;
- the access model;
- the Visual Bible door and colour rules;
- the Character Bible;
- the Screen Registry;
- the StarNet exclusions.

---

## 10. Decisions

| # | Decision | Status |
|---|---|---|
| RC-1 | Floor | **Closed:** `FLR-003` grating as the room identity |
| RC-2 | Walls | **Closed:** gunmetal structure + warm off-white panels + graphite accents |
| RC-3 | Gold identity vs amber / red status | **Closed:** confirmed |
| RC-4 | Core rail | **Closed:** kept, visual only |
| RC-5 | Layout | **Closed:** intake → core → outbox as drawn |
| RC-6 | Exact dimensions | **Open** (after the tile scale, VB-3) |
| RC-7 | Exact colour values (including the amber and red status tones) | **Open** (visual production, VB-4) |
