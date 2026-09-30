# Stellar Room Design Sheet — L9 Execution Bay (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; EX-1…EX-4 decided, EX-5 / EX-6 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L9` — Execution Bay · ACTIVE · RESTRICTED (Room Registry v2 §3.10) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors, access: `STELLAR_ROOM_REGISTRY.md` v2, `STELLAR_CHARACTER_REGISTRY.md` §3. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures: `STELLAR_CHARACTER_BIBLE_V1.md`. Objects: `STELLAR_ASSET_REGISTRY.md` v2. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list, and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | Execution runs in the engine (the **Paper Broker only**; no MT5, Vantage, DEMO or LIVE path exists or is shown). This room only **shows** real execution events. The visual layer never sends, cancels, modifies or fabricates an order, fill, position or result |

---

## 1. StarNet concept review

**Method.** I reviewed the audit (S13, S16, S19–S20, S25, S26, S28, S46) and read the local StarNet
checkout at pinned revision `fbddbf99` **read-only**:
- `world.js`: `deskPropFor`, `deskSeat`, `setActivityFor`, handoff, work pose, run clocks and work
  glyphs;
- `worldmodel.js`: bay roles and the INBOX ▸ BAY ▸ OUTBOX blueprints;
- `linewatch.js` (per the audit): lamp status priority with an honest "unknown".

**Nothing is copied:** no art, assets, characters, layouts, interfaces or StarNet execution logic.

| StarNet concept | How Stellar adapts it | What Stellar rejects |
|---|---|---|
| **Dedicated work stations** (a desk per agent; `deskPropFor` / `deskSeat`) | Two **reserved** stations with restricted anchors: `execbay.preflight` (Execution Checker) and `execbay.launch` (Execution Agent) | Stations assigned or built by the user |
| **Work before idle / return to the station** (work seizes idle; the agent re-paths to its desk) | A real `order.*` event pulls the relevant figure back to its station (A13) | — |
| **Task hand-offs** (visible handoff between agents) | The **order capsule** (`PRP-005`) is collected by E1 at the L10 outbox **only after** `risk.approved` **and** `order.created`, and carried to L9. The review crystal (`PRP-006`) leaves on `trade.closed` | Hand-offs with no triggering event |
| **Action queues** (INBOX ▸ BAY ▸ OUTBOX conveyor lines) | **Not as belts.** The queue is a **display**: Working Orders (`DSP-EXB-02`) lists real non-final orders | Conveyor belts, pipeline edges, line budgets (S16) |
| **Visible workflow progression** (run clocks and work glyphs on bodies; lamp status with priority) | The **Order Lifecycle** display (`DSP-EXB-01`) shows each real step; steps without a producer are drawn **NOT AVAILABLE**, never skipped as if they happened (the linewatch "honest unknown" principle, A19) | Invented progress, and timers without data |
| **Bay roles** (a bay stamped with its role) | The **PAPER** mode marking (`DSP-EXB-05`, from telemetry) and the station roles give the bay its identity | User-editable bay roles |
| StarNet execution logic (harness runs, tool calls, permission prompts) | — | **Rejected:** Stellar's execution is the engine's Paper Broker; nothing of StarNet's run or execution logic is used |
| Security / launch aesthetics (CRT, phosphor, flashing) | — | Rejected (S33, S34) |

**Stellar original design (not from StarNet):**
- The paper-only rule and the PAPER marking from telemetry.
- The L10 outbox → L9 hand-off with a double trigger (`risk.approved` + `order.created`).
- Separate Execution Agent and Execution Checker figures.
- The dispatch-tube / docking-board metaphor, drawn as clean logistics (§3.3).
- All materials and lighting.

---

## 2. Room identity and relationships

| Aspect | Definition |
|---|---|
| **Purpose** | Where **approved** actions are **executed**: paper order routing to the Paper Broker, pre-flight checks, and the fill or rejection result. **Risk validates; Execution acts.** **Not** a research, specialist analysis, command or risk room |
| **Atmosphere** | Precise, clean, controlled, procedural, traceable, responsible. An operational logistics bay, never a weapons room or an aggressive command set |
| **Visual identity** | A tidy operational bay: a **checker station** by the entry, an **execution console** facing the **Dispatch Tube** and a **docking board**, a **launch-deck floor marking**, and a large **PAPER** marking on the wall |
| **Importance level** | **High.** It is the last step before an order reaches the Paper Broker. Its mode marking must always read |

**Relationships (no new connections or doors):**

| Room | Role | Link to L9 |
|---|---|---|
| `H-CMD` | Decision and coordination | **Indirect.** Decisions reach L9 only through L10. The Supervisor may visit the L9 **entry** from `H-CMD` (`DR-S-CMD` → `COR-S` → `DR-L9`) |
| `L10` Risk | Validation and approval | **Adjacent on `COR-S`** (the L10 door is east of the L9 door; the rooms are separated by non-walkable hull). The **only** hand-off link: E1 walks L9 → `COR-S` → L10 outbox → back |
| `L9` Execution | Executes the approved action | — |
| `L1` Specialists | Upstream analysis | **None directly.** The analysis reaches L9 only as an approved order, after `H-CMD` and L10 |

---

## 3. Architecture

### 3.1 Shape and entrance (approved; unchanged)

- **Shape:** tall rectangle south of `COR-S` (sketch about 115 × 177 px; about 7 × 11 tiles at the
  working scale, which is **not frozen**). West of L10 and east of L8 (reserved), separated from both
  by **non-walkable hull**.
- **One door:** `DR-L9` in the **north wall**, onto `COR-S`. It is an ordinary 2-tile door with the
  restricted variant `DOR-008` and a static `SGN-006` marking: **icon + marking + optional amber
  light**.
  - **No lock, no automatic door, no airlock, no hidden passage.** Access is a navigation
    permission (`MP-EXEC` crew; the Supervisor and Medic to the entry only).
  - The breaker **BREAKER TRIPPED** door panel belongs to L10 (`DSP-RSK-09`); L9 has no door panel
    of its own (§10, E6).
- **Cutaway:** the camera-facing walls are cut away. The door keeps a visible frame, threshold and
  opening (Visual Bible C4).

### 3.2 Schematic (not to scale; door at the top)

```
                          COR-S
   +-------------------[ DR-L9 ]-------------------+
   | execbay.entry (Supervisor / Medic stop here)  |
   | CON-016 pre-flight   |                        |
   | console (P4)         |   DSP-EXB-02 working   |
   | + DSP-EXB-04         |   orders (east wall)   |
   | execbay.preflight    |                        |
   |------ FLR-008 launch-deck marking begins -----|
   |                                               |
   | CON-017 execution console (E1)                |
   | execbay.launch   -> faces the Dispatch Tube   |
   |                                               |
   | EQP-002 Dispatch Tube (west wall)             |
   | EQP-003 docking board (south wall)            |
   |  + DSP-EXB-01 order lifecycle                 |
   | DSP-EXB-03 positions (east wall)              |
   | DSP-EXB-05 PAPER hull marking (south wall,    |
   |            large, above the docking board)    |
   +-----------------------------------------------+
```

### 3.3 Materials and objects' character

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor, with the **launch-deck marking** (`FLR-008`) in a titanium / light line pattern outlining the execution area (walk-over) |
| Walls | **Warm off-white structural panels** where they face the room, **titanium** trims, and **graphite** technical elements around the tube and board |
| Dispatch Tube (`EQP-002`) | Named the **Dispatch Tube** in the visual design (owner decision EX-2; the registry asset name "Launch tube" is unchanged). Drawn as a **clean pneumatic dispatch tube** (logistics), **never** as a weapon, torpedo tube or launch system: rounded, translucent, with titanium bands (§10, E3) |
| Docking board (`EQP-003`) | A clean wall frame where results "dock" as the real events arrive |
| Department accent | Engineering **gold** (Risk / Operations identity; static). Amber / red = **real states only**, with an icon and text |

### 3.4 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a linear light over the execution line; not drawn in the cutaway |
| General | Clean, even, operational white: brighter than L10, more neutral than `H-CMD` |
| Work pools | `LGT-002` over a station only while its figure acts on a real `order.*` event |
| Status accents | **Amber** + icon + text for a real `order.preflight.failed` (BLOCKED) or a real `order.rejected`. **Red** + icon + text only from real system states (for example the station RED alert on a tripped breaker). **Never decorative** |
| Alert | The station alert tint on `LGT-001`, with a word and icon (Visual Bible C7) |

### 3.5 Walkable areas and zones

| Zone | Who | Rule |
|---|---|---|
| `execbay.entry` (inside the door) | Supervisor, Medic (entry only); the E1 / P4 transit | The door approach stays empty |
| `execbay.floor` (restricted) | **P4, E1 only** (`MP-EXEC`) | Stations, tube and board |
| The launch-deck marking | Walk-over | Visual only, not a barrier |

---

## 4. Character placement

| Figure | Role | Workstation (anchor) | Normal position | Movement | Hand-offs | With L10 | With H-CMD |
|---|---|---|---|---|---|---|---|
| **Execution Agent** `CHR-039` (E1 `paper_execution`, OPS) | Submits order intents to the Paper Broker; tracks fills and closes | `CON-017` · `execbay.launch` (R) | At the execution console, facing the tube | On `risk.approved` + `order.created`: L9 → `COR-S` → L10 `risk.outbox_pickup` → back (`MP-EXEC`). Returns to its station on any real `order.*` | Collects `PRP-005` at the L10 outbox; loads it into the Dispatch Tube | Outbox pickup only | None directly |
| **Execution Checker** `CHR-038` (P4 `execution_checker`, OPS) | Pre-flight checks (and reconciliation in the engine) | `CON-016` · `execbay.preflight` (R) | At the pre-flight console by the entry | Mostly stationary; stays in L9 | None | None | None |

**The two figures are separate and never merged** (Character Bible K1): the Execution Agent is
compact, curly-haired and wears a tool belt; the Execution Checker is average build, shaved with a
beard, with a tablet and badge.

**Visitors:**

| Visitor | Behaviour in L9 |
|---|---|
| **Risk Agent** `CHR-037` | **Does not enter L9.** `MP-RISK` does not include L9 (Character Registry §3). The Risk → Execution hand-off happens at the **L10 outbox** (§10, E1) |
| **Proposal Builder** `CHR-005` | **Does not enter L9.** `MP-COURIER` reaches only the L10 intake (§10, E2) |
| **Supervisor** `CHR-003` | Entry zone only (`execbay.entry`), on real events; touches no station |
| **Medic** `CHR-041` | Entry zone only, on a real `error` / `overloaded` of P4 or E1 |
| Any other agent | Not routed into L9 (restricted) |

---

## 5. Execution workflow (what the room shows, event by event)

Each step appears **only** when its event exists. Availability follows the Screen Registry producer
audit (Phase 7).

| # | Step | Visual in L9 | Trigger (event) | Available today |
|---|---|---|---|---|
| 1 | **Approved item arrives** | E1 collects the order capsule at the L10 outbox and carries it into L9 | `risk.approved` **and** `order.created` | **Yes** |
| 2 | **Execution preparation** | The capsule is placed at the execution console; the order appears on Working Orders (`DSP-EXB-02`) as PENDING | `order.created` | **Yes** |
| 3 | **Checker verifies** | P4 at the pre-flight console; `DSP-EXB-04` shows the pre-flight result for the order | `order.preflight.failed` (a **failure** is explicit). There is **no "pre-flight passed" event**: a pass is only implied when the order proceeds | **Partial:** failures shown (BLOCKED, amber + icon + text); a pass is **not** shown as a separate state (§10, E4) |
| 4 | **Execution occurs** (sent / acknowledged) | The tube dispatch moment | `order.sent`, `order.acknowledged` | **No producer.** Drawn as **NOT AVAILABLE** on the lifecycle; the tube does **not** animate a "send" (§10, E5) |
| 5 | **Result recorded** | The result "docks" on the docking board; the lifecycle step lights; the position appears | `order.filled` / `order.rejected` / `order.cancelled` / `order.expired`; `position.opened` / `updated`. `order.partially_filled` has **no producer** (NOT AVAILABLE) | **Yes** (except partial fills) |
| 6 | **Task leaves the bay** | On close, E1 carries a Record Crystal (`PRP-006`) to the Memory Archive (L6 `archive.shelf`), where the Post-Trade Reviewer files it (L6 sheet DM-1–DM-3) | `trade.closed` | **Yes** |

**Reconciliation** is shown in the Data Core (`DSP-DCR-05`, L4), not in L9. **Agent task events**
(`agent.task.*`) are **not** emitted by the execution roles today. Their working poses therefore
follow the **`order.*` events** above, never an assumed task state.

---

## 6. Main objects (registry-supported only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Execution console** | `CON-017` | E1's station: prepares and dispatches the approved order (paper) | Centre of the execution area, facing the tube | `execbay.launch` (R: E1) | **Hero** |
| 2 | **Pre-flight console** (checker station) | `CON-016` + `DSP-EXB-04` | P4's pre-flight checks | West side, by the entry | `execbay.preflight` (R: P4) | High |
| 3 | **Dispatch Tube** (registry name "Launch tube", unchanged) | `EQP-002` | Where the capsule leaves; animates **only on real `order.*`** (no "send" animation while `order.sent` has no producer) | West wall of the execution area | none (visual) | High (a clean logistics look, not a weapon) |
| 4 | **Docking board** | `EQP-003` + `DSP-EXB-01` | Where real results dock; carries the Order Lifecycle | South wall | Look target | High |
| 5 | **Action queue** (display) | `SCR-003` (`DSP-EXB-02`) | Working orders: PENDING / BLOCKED | East wall, near the entry | Look target | Medium |
| 6 | **PAPER hull marking** | `SCR-009` (`DSP-EXB-05`) | Mode from telemetry (**PAPER**, or **MODE UNKNOWN**) | Large, south wall above the board | none | **High** (always readable) |
| 7 | Positions display | `SCR-003` (`DSP-EXB-03`) | Open paper positions and unrealised P&L (real only) | East wall | Look target | Medium |
| 8 | Launch-deck marking | `FLR-008` | Outlines the execution area | Floor | walk-over | Medium |
| 9 | Hand-off point | *(no separate object)*: the capsule arrives in E1's hands at the console | — | — | — | — |

**Not added:** no separate "hand-off terminal" or "paper handling area" asset (none exists). The
paper character of the room comes from the **PAPER marking** and the Paper Broker-only rule (§10,
E7).

---

## 7. Screen design (Screen Registry v2 §5.9 is the authority)

| Category | Display | Content | Placement | Main placeholders |
|---|---|---|---|---|
| **Execution** | `DSP-EXB-01` Order Lifecycle | created → filled / rejected / cancelled / expired → closed. **`sent`, `acknowledged` and `partially filled` are drawn NOT AVAILABLE**, never skipped as if they happened | On the docking board, south wall | **NOT AVAILABLE** per missing step; **AWAITING DATA** |
| **Pending / action** | `DSP-EXB-02` Working Orders | Orders not yet final: PENDING / BLOCKED | East wall, near the entry | **NO WORKING ORDERS** only when fresh |
| **Checker** | `DSP-EXB-04` Pre-flight Results | Pre-flight checks for the latest order (a failure is explicit; there is no pass event) | On the pre-flight console | **AWAITING DATA** |
| **Status** | `DSP-EXB-03` Positions | Open paper positions, unrealised P&L | East wall | **UNKNOWN** for missing economics |
| | `DSP-EXB-05` PAPER marking | Mode from telemetry (`account.opened`) | South wall, large | **MODE UNKNOWN** (amber + icon + text) |

**Screen rules for this room:**
- **Never invent** orders, prices, positions, execution results, latency or success values.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **MODE UNKNOWN**
  applies to the PAPER marking.
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- There is no DEMO, LIVE, MT5 or Vantage indicator anywhere.
- All displays are read-only. No cancel, send or modify affordance.

---

## 8. Agent life

All activity comes from **real events** or **normal idle behaviour**. There is **no emotional
simulation**.

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Collecting an approved action | `risk.approved` + `order.created` | E1: walk to the L10 outbox and back | `walk`, `carry` (`PRP-005`) |
| Preparing | `order.created` | E1 at the execution console | `stand_work` |
| Checking | `order.created` (a check in progress) / `order.preflight.failed` (a failure) | P4 at the pre-flight console; a failure marks BLOCKED | `stand_work`, `checklist_sweep` |
| Executing | *(no producer for `order.sent`)* | **Not animated as a send**. The next visible step is the result | — |
| Recording a real result | `order.filled` / `rejected` / `cancelled` / `expired` | E1 turns to the docking board; the lifecycle step lights | `look_screen` |
| Hand-off out | `trade.closed` | E1 carries a Record Crystal to L6 `archive.shelf` (the Post-Trade Reviewer files it; no review) and returns | `carry` (`PRP-006`) |
| Returning to the station | Any real `order.*` while away | E1 / P4 re-path to their stations (work over idle) | `walk` |
| Idle | No real event | At their stations; optional seeded ambient to the Habitat (`MP-EXEC` allows public spaces) | `stand_idle` |

---

## 9. Access (summary)

- **One explicit door** (`DR-L9`, `DOR-008`). There is no automatic door, no lock, no new airlock
  and no hidden passage.
- The restricted indication is an **icon + marking** (`SGN-006`) + an **optional amber** light;
  readable without colour.
- **Red** only from real system states.
- Only `MP-EXEC` crew (P4, E1) enter the floor; the Supervisor and Medic stop at the entry; nobody
  else is routed in.

---

## 10. Contradictions and owner decisions

| # | Topic | Request | Approved documents | Suggested handling |
|---|---|---|---|---|
| **E1** | **Risk Agent as an L9 visitor** | Define the Risk Agent's visitor behaviour | Character Registry §3: `MP-RISK` = L10 + public spaces; **L9 is not allowed**. The hand-off is at the L10 outbox | **Resolved (EX-1):** the Risk Agent does **not** enter L9; its hand-off ends at the L10 outbox. Access model unchanged |
| **E2** | **Proposal Builder as an L9 visitor** | Define its visitor behaviour | `MP-COURIER` = L10 intake only | **Resolved (EX-1):** the Proposal Builder does **not** enter L9; its hand-off ends at the L10 outbox |
| **E3** | **"Launch tube" vs "not a weapons room"** | No weapons / aggressive look | Asset `EQP-002` "Launch tube"; Visual World Plan §11 uses a "shuttle launches / docks" metaphor | **Resolved (EX-2):** `EQP-002` kept; called the **Dispatch Tube** in the visual design and never presented as a weapon or launch system. The registry asset name stays unchanged |
| **E4** | **"Checker verifies" step** | Requested as a workflow step | The engine emits only `order.preflight.failed`; **no pre-flight pass event**. Execution roles emit no `agent.task.*` | **Resolved (EX-3):** the pass stays **implicit** in V1; failures are shown, no pass event is invented. If the engine later produces one, the design can be updated |
| **E5** | **"Execution occurs" step** | Requested | `order.sent` and `order.acknowledged` have **no producer**; `order.partially_filled` has none either | **Stands (no decision needed):** drawn **NOT AVAILABLE**; no send animation. Future when the producers exist |
| **E6** | **Door status panel for L9** | Status displays requested | The breaker door panel exists only for L10 (`DSP-RSK-09`) | **Stands:** none added to L9 |
| **E7** | **"Paper / order handling area", hand-off terminal** | Possible categories | No such assets exist | **Stands:** not invented; the paper identity comes from the PAPER marking |

No conflicts with:
- the topology (one door `DR-L9` on `COR-S`; neighbours across hull);
- the access model and the Visual Bible door and colour rules;
- the Character Bible (E1 and P4 separate, no emotion);
- the Screen Registry (the five L9 displays and their placeholders);
- the StarNet exclusions.

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| EX-1 | Risk Agent / Proposal Builder never entering L9 (E1, E2) | **Closed:** confirmed; their hand-off ends at the L10 outbox |
| EX-2 | Tube naming and metaphor (E3) | **Closed:** `EQP-002` kept, called the **Dispatch Tube** in the visual design; not a weapon or launch system; registry name unchanged |
| EX-3 | Pre-flight pass (E4) | **Closed:** implicit in V1; no new event invented; revisit if the engine later produces one |
| EX-4 | Layout: pre-flight by the entry (west); execution console centre; Dispatch Tube west; board + PAPER south; queue + positions east | **Closed:** approved as drawn (§3.2) |
| EX-5 | Exact dimensions | **Open** (after the tile scale, VB-3) |
| EX-6 | Exact colour values | **Open** (visual production, VB-4) |
