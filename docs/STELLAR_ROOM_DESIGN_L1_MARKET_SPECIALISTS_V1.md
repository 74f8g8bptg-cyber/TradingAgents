# Stellar Room Design Sheet — L1 Market Specialists Room (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; SP-1…SP-5 decided (§9, §10). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L1` — Market Specialists Room (Room Registry v2 §3.4) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Screens: `STELLAR_SCREEN_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Figures and the interim adapter: `STELLAR_CHARACTER_BIBLE_V1.md`, `STELLAR_CHARACTER_REGISTRY.md` §5. Objects: `STELLAR_ASSET_REGISTRY.md` v2. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the room assignment, anchors, the screen list, and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |

---

## 1. StarNet concept review

**Method.** I reviewed the StarNet audit (S13, S16, S19–S20, S25–S28, S38, S48) and read the local
StarNet checkout at pinned revision `fbddbf99` **read-only**:
- `worldmodel.js`: `BAY_ROLES`, `CAP_PROP_MAP`, the INBOX ▸ BAY ▸ OUTBOX workflow blueprints;
- `world.js`: `deskPropFor`, `deskSeat`, `setActivityFor`, handoff.

**Nothing was copied:** no art, assets, characters, layouts, interfaces or code.

| StarNet concept (what exists) | What is useful | Adapted for Stellar | Rejected |
|---|---|---|---|
| **Role-stamped work bays** (`BAY_ROLES`): a dock or bay carries a role, so a workstation says what its agent does | A workstation's identity tells the viewer the agent's job at a glance | **Family desks** (`CON-009`) with a **family shape tag** (Metals / FX / Indices) and a desk screen. The role comes from the **Room Registry**, never from user building | User-built, editable bays; bay roles as a build-mode feature (S16, S40) |
| **Desk per agent** (`deskPropFor`, `deskSeat`) with **work seizes idle** (a task re-paths the agent to its desk) | Agents visibly return to their own station when real work starts | **Reserved desk anchors** (`specialists.desk_*`, restricted per desk) + the **work over idle** priority (A12, A13). If the desk is unreachable, fall back through the waiting ladder (A10) | StarNet's complaint / "gripe" behaviour when no desk is available (emotion-adjacent) |
| **Visible handoff** (`setActivityFor`, handoff): work passes from one agent to another in view | Makes the analysis flow readable | A **data-crystal hand-off** (`PRP-001`) walked to the **next real consumer**, only when that consumer's task starts (Visual World Plan §8) | Hand-offs with no triggering event |
| **INBOX ▸ BAY ▸ OUTBOX pipelines** (conveyor belts carrying work items between stations) | Shows a workflow as a physical line | **Not as belts.** Stellar shows the flow through **walking hand-offs** and the **Agent Pipeline** display in `H-CMD` (`DSP-CMD-04`) | Belts, conveyors, pipeline edges and budgets on doors (S16: station-building semantics) |
| **Capability → prop mapping** (`CAP_PROP_MAP`) | — | — | Rejected (S16): Stellar desks are bound to registry roles, not capabilities |
| **Frontend-owned crew roster, skins and personas** | — | — | Rejected (S48, S38): the engine roster and the Character Registry own identity; there are no StarNet skins |
| **Zones** confining idle roaming | Keeps specialists in plausible places when idle | `specialists.*` zones; idle ambient only via `COR-N` → `H-CMD` → `H-HAB` (A11) | — |
| **Team clustering** (agents of one line working near each other) | Readable team identity | The three family desks share **one room** with glass-partitioned bays (not three rooms) | — |

**Stellar original decisions (not from StarNet):**
- Family desks per **market family** (Metals / FX / Indices), never one desk per instrument.
- The **interim adapter** truth rules (one row, chip and panel per runtime agent; never merged).
- Configuration-driven instrument lists (`NOT CONFIGURED` for unconfigured members).
- The glass-bay room layout.
- All materials, lighting and look.

---

## 2. Room identity

| Aspect | Definition |
|---|---|
| **Purpose** | **Specialised market analysis** by family: Metals, FX and Indices. It turns the shared research and macro context from `H-LAB` into **market-specific views** (pressure, drivers, counter-evidence, event risk, coverage) for the Central Trader. **Not** a trading or execution room (no orders, positions, prices or P&L), **not** a command room, **not** a general research lab |
| **Atmosphere** | Analytical, clean, focused: a quiet specialist studio |
| **Visual identity** | Three **glass-partitioned desk bays**, one per market family, each with a family shape tag and a desk screen. It sits between the Lab's blue and Command's neutral white |
| **Importance level** | **Medium-high.** It is a key working room on the analysis chain; its desks read at hub-view zoom |
| **Relationship with H-LAB** | **Upstream.** L1 is the **first room** on `COR-N` after `H-LAB` (`DR-N-LAB` → `COR-N` → `DR-L1`, 2 door crossings). Macro context arrives from M1 (a `PRP-001` walk into L1) and is repeated on `DSP-SPC-04` |
| **Relationship with H-CMD** | **Downstream.** The specialists report to the **Central Trader**. A hand-off walks `DR-L1` → `COR-N` → `DR-N-CMD` **only** when a real downstream consumer uses the specialist's `analysis.created`. Market Overview in `H-CMD` (`DSP-CMD-01`) shows the families' latest views |
| **Relationship with L3 Debate Chamber** | **Indirect.** L3 is at the east end of `COR-N` (`DR-L1` → `COR-N` → `DR-L3`). Specialists **do not debate**. Their assessments may be **cited** as evidence cards in L3 (`DSP-DEB-03`), shown there as data, not as a visit |

---

## 3. Architecture

### 3.1 Shape and entrance (approved; unchanged)

- **Shape:** tall rectangle (sketch 114 × 177 px; about 7 × 11 tiles at the working scale, which is
  **not frozen**). North of `COR-N`, the first small room east of `H-LAB`. Its neighbour to the
  east is L2 (Technical Deck), across **non-walkable hull** (Q4).
- **One door:** `DR-L1`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator,
  centred in the **south wall**, opening onto `COR-N`. **No other opening.**
- **Cutaway:** the camera-facing walls are cut away. The door keeps a visible frame, threshold and
  opening (Visual Bible C4).

### 3.2 Schematic (not to scale; door at the bottom)

```
            north wall (back)
   +------------------------------------+
   |        FX BAY  (specialists.fx)    |
   |   CON-009 FX desk  + DSP-SPC-02    |   <- widest bay: several task rows
   |   [task panel S2 | task panel S3]  |
   |------ WAL-005 glass partition -----|
   | METALS BAY    |  aisle  |  INDICES |
   | (west wall)   |         |   BAY    |
   | CON-009 +     |         | (east    |
   | DSP-SPC-01    |         |  wall)   |
   |               |         | CON-009 +|
   |               |         | DSP-SPC-03
   |---------------+         +----------|
   | DSP-SPC-04 macro repeater (west    |
   | wall, entry zone)  specialists.entry|
   |           specialists.visitor      |
   +---------------[ DR-L1 ]------------+
                       COR-N
```

### 3.3 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`); a thin titanium inlay marks the central aisle (walk-over) |
| Walls | **Warm off-white structural panels** (`WAL-001`), titanium trims |
| Bay partitions | **Low glass partitions** (`WAL-005`) with titanium frames. Waist-to-shoulder height, so every figure stays visible in the 2.5D view |
| Technical elements | **Graphite** desk bodies, screen bezels and cable spines |
| Accent | **Science blue** lines on the desks. Each bay carries a **family shape tag** (Metals / FX / Indices; exact shapes are CB-5, open). The family is never shown by colour alone |

### 3.4 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a linear light slot along the aisle; not drawn in the cutaway (only its edge is suggested) |
| General | **Between H-LAB and H-CMD:** clean neutral white with a light cool-blue tint; analytical and focused, less saturated than H-LAB |
| Work pools | `LGT-002` over a desk **only while one of its underlying runtime agents works** (telemetry) |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.5 Walkable areas

| Area | Rule |
|---|---|
| `specialists.entry` | Clear floor inside the door; the door's approach tile stays empty |
| Central aisle | Links the entry to all three bays; no furniture |
| Bays | The desks block their footprint. The desk anchors are **restricted** to their own desk figure; visitors stop at `specialists.visitor` |
| Behind the desks | Not walkable (the desks sit against the walls) |

---

## 4. Specialist desks

All three desks are **FAMILY DESK visual representations** under the **interim adapter**
(Character Registry §5; Character Bible K2). Each desk shows **one row, one chip and one task panel
per underlying runtime agent**. States are **never merged**.

### 4.1 Metals Desk — `CHR-022` (runtime today: S1 `specialist_xauusd`)

| Aspect | Definition |
|---|---|
| Responsible for | **Gold (XAU)** and **silver (XAG)**. XAG is **`NOT CONFIGURED`** in the engine today, so only gold shows a live row |
| Workstation | West bay: `CON-009` family desk at `specialists.desk_metals` (restricted) |
| Screens | `DSP-SPC-01`: one row per underlying agent (today S1 / XAU/USD). Each row: state, task, pressure, drivers, counter-evidence, event risk, coverage, age. A silver slot, if shown, reads **NOT CONFIGURED** |
| Visual identity | Metals family tag; the Metals figure (Character Bible §4.5: short, broad, shaved with a beard, tablet) |
| Behaviour | `sit_work` while S1 analyses; `look_screen` at the desk screen; idle at the desk otherwise |
| Interaction | Receives macro context from `H-LAB` (M1's hand-off walk). Sends its view downstream (a `PRP-001` walk) **only** when a real consumer uses it |

### 4.2 FX Desk — `CHR-023` · **INTERIM ADAPTER** (runtime today: S2 `specialist_eurusd` + S3 `specialist_usdjpy`)

| Aspect | Definition |
|---|---|
| Represents | **Several runtime agents**, today S2 (EUR/USD) and S3 (USD/JPY). Future FX agents add rows |
| Workstation | North bay (the widest): `CON-009` family desk at `specialists.desk_fx` (restricted) |
| Visual representation | **One desk figure** (Character Bible §4.6) working among **floating task panels, one per underlying runtime agent**, each labelled with its instrument and `technical_id`. **A split pip** at overview (one segment per agent). **No single state badge.** The footer reads "Family desk · interim view of N runtime agents" |
| Screens | `DSP-SPC-02`: **one row per underlying agent, side by side** (S2 / EUR/USD and S3 / USD/JPY), each with its **own** state chip, task, latest view and age, plus a count ("FX · 2 active") |
| Interaction rules | <ul><li>**Never merge** the EUR/USD state, the USD/JPY state, or any future FX agent's state; no "highest-priority" or averaged state.</li><li>Error, overloaded, resting, paused and offline markers attach **only** to that agent's panel and row.</li><li>The body pose is **neutral**: the figure works while **at least one** underlying agent works, and is idle otherwise.</li><li>Concurrent tasks are shown **side by side**, never as sequential switching.</li><li>Any hand-off walk is tied to **one** underlying agent's real output and carries that instrument's tag.</li><li>Clicking the desk (NAV) lists each real underlying agent and its events.</li></ul> |

### 4.3 Indices Desk — `CHR-025` (runtime today: S4 `specialist_nas100`)

| Aspect | Definition |
|---|---|
| Responsible for | **Index research**: NAS100 first; extensible to more indices (not configured today) |
| Workstation | East bay: `CON-009` family desk at `specialists.desk_indices` (restricted) |
| Screens | `DSP-SPC-03`: one row per underlying agent (today S4 / NAS100), with its own state, task, view and age |
| Role | Translates macro drivers into index pressure and event risk (engine S4 responsibility) |
| Interaction | As Metals: macro in from `H-LAB`; hand-off out only on real consumption |

---

## 5. Character placement

| Figure | Works at | Movement pattern | Collaboration behaviour |
|---|---|---|---|
| Metals desk `CHR-022` (SCI) | West bay | Mostly seated. Hand-off walks: `DR-L1` → `COR-N` → the real consumer's room (`L2`, `L3` or `H-CMD`), then back. Idle ambient: `COR-N` → `H-CMD` → `H-HAB` only when **all** its underlying agents are idle | Receives M1 at `specialists.visitor`. No desk-to-desk "meetings" without a real shared task |
| FX desk `CHR-023` (SCI) | North bay | As Metals; **each walk is tied to one underlying agent's output**. The figure never walks "on behalf of the FX desk" as a whole | As above; panels, not the figure, carry the per-agent status |
| Indices desk `CHR-025` (SCI) | East bay | As Metals | As above |
| Visitor: Causal / Macro Analyst `CHR-011` (from `H-LAB`) | `specialists.visitor` | Enters with a `PRP-001` when macro output is consumed here, then returns to `H-LAB` | Hand-off only |
| Visitor: Supervisor `CHR-003` | `specialists.entry` / `visitor` | Event-driven visits (`MP-SUPERVISOR`) | Observes; touches no desk anchor |
| Visitor: Medic `CHR-041` | `specialists.entry` | Only on a real `error` / `overloaded` of an underlying agent. The Medic attends **that agent's panel position** at the desk | No authority gestures |

**Departments:** all three desks are **Science / Research (blue)**, distinguished by silhouette and
family tag (Character Bible §4.5–§4.7). There is **no emotional simulation**.

---

## 6. Main objects

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **FX family desk** | `CON-009` + `SCR-004` + task panels | Multi-agent FX analysis | North bay (back wall) | `specialists.desk_fx` (R) | **Hero** (widest desk; the interim adapter is most visible here) |
| 2 | **Metals family desk** | `CON-009` + `SCR-004` | Metals analysis | West bay | `specialists.desk_metals` (R) | High |
| 3 | **Indices family desk** | `CON-009` + `SCR-004` | Index analysis | East bay | `specialists.desk_indices` (R) | High |
| 4 | Glass bay partitions | `WAL-005` | Separate the families while keeping them visible | Between the bays and the aisle | none (solid) | Medium |
| 5 | **Macro context repeater** | `SCR-003` (`DSP-SPC-04`) | Macro context from `H-LAB` for all three desks | West wall, entry zone (clear of the door approach) | Look target | Medium |
| 6 | Visitor / hand-off point | anchor `specialists.visitor` | Where hand-offs arrive (M1) and visitors stop | Entry zone | Hand-off anchor | Medium |
| 7 | Console chairs, desk plants | `SEA-002` × 3, `PLT-003` | Seating; softening | At the desks | Seats | Low |

**Not added** (owner decisions SP-1…SP-4): no specialist overview screen, no hand-off terminal, no
comparison display, and no collaboration table or area. The room is organised around the
**specialist work bays**.

---

## 7. Screen design (Screen Registry v2 §5.3 is the authority)

| Request category | Display | Content (from the registry) | Placement | Main placeholders |
|---|---|---|---|---|
| **Metals screens** | `DSP-SPC-01` | One row per underlying agent: state, task, pressure, drivers, counter-evidence, event risk, coverage, age | On the Metals desk | XAG **NOT CONFIGURED**; no view **AWAITING DATA** |
| **FX screens** | `DSP-SPC-02` | One row per underlying agent (S2 and S3 **side by side**), each with its own state chip; the active count | On the FX desk + the floating task panels | per row **AWAITING DATA**; unconfigured pairs not listed |
| **Index screens** | `DSP-SPC-03` | One row per underlying agent (S4) | On the Indices desk | **AWAITING DATA** |
| Macro context | `DSP-SPC-04` | Same as `DSP-LAB-06` | West wall, entry zone | **AWAITING DATA** |
| **Specialist overview** | **None in L1** (owner decision SP-1). Cross-family views stay in `H-LAB` (`DSP-LAB-07`) and `H-CMD` (`DSP-CMD-01`) only | — | — | — |
| **Hand-off screens** | **None** (owner decision SP-2). Hand-offs happen through **real agent movement and events** (`PRP-001` walks); the chain is shown on the Agent Pipeline in `H-CMD` (`DSP-CMD-04`) | — | — | — |
| Comparison displays | **None in L1** (owner decision SP-3). Comparisons stay outside the specialist desks | — | — | — |

Every specialist desk has the footer **"Family desk · interim view of N runtime agents"**.

**Screen rules for this room:**
- **Never invent** market values, prices, positions or profits. The desk rows show **analysis only**
  (pressure, drivers, counter-evidence, event risk, coverage, age), with no prices.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **MODE UNKNOWN** is
  not used here: there is no mode plaque, since this is not an execution room.
- On link loss, the desk screens **freeze and grey** with **LINK DOWN · age**.
- No screen sits over the door or its approach.
- All displays are read-only or navigation-only.

---

## 8. Agent life

All activity comes from **real tasks**, **real events** or **normal idle behaviour**. There is **no
emotional simulation**.

| Activity | Trigger | Who / where | Clips |
|---|---|---|---|
| **Analysing** | `agent.task.started` … `completed` for the desk's underlying agent (S1–S4) | The desk figure at its desk. For the FX desk, the **matching panel** lights, not a merged state | `sit_work` |
| **Comparing information** | An underlying agent's task updates while the macro repeater also updates (real data on both) | The desk figure turns between its desk screen and `DSP-SPC-04` | `look_screen` |
| **Reviewing reports** | A new macro assessment arrives (`analysis.created` macro) | Desk figures glance at `DSP-SPC-04` | `look_screen` |
| **Preparing hand-offs** | A specialist's `analysis.created` is about to be consumed downstream | The figure picks up `PRP-001` (tagged with the instrument) | `carry`, `walk` |
| **Receiving hand-offs** | M1's macro output consumed in L1 | M1 at `specialists.visitor` | `carry`, `talk` / `listen` (neutral) |
| **Collaboration** | Only when two desks have real tasks on related inputs at the same time (for example the same macro assessment) | Each figure at its **own** bay, facing the macro repeater. There is no collaboration table or area in V1 (SP-4), and no invented meetings | `look_screen` |
| Idle | All underlying agents of a desk idle | At the desk; optional seeded ambient to `H-HAB` via `H-CMD` | `stand_idle` |

---

## 9. Contradictions and owner decisions (all resolved)

| # | Topic | Owner decision |
|---|---|---|
| **X1 / SP-1** | Specialist overview screen in L1 | **None in L1.** Cross-family views stay in `H-LAB` (`DSP-LAB-07`) and `H-CMD` (`DSP-CMD-01`) only |
| **X2 / SP-2** | Hand-off terminal / hand-off screens | **None.** Hand-offs happen through **real agent movement and events** |
| **X3 / SP-3** | Comparison display in L1 | **None.** Comparisons stay outside the specialist desks |
| **X4 / SP-4** | Collaboration table / area | **None in V1.** The room is organised around the specialist work bays |
| **SP-5** | Bay layout | **Approved:** FX north / back bay as the centrepiece; Metals west bay; Indices east bay |
| **X5** | Desk naming | Consistent (all three are family desks under the interim adapter); no change |

No remaining conflicts with:
- the topology;
- the Visual Bible;
- the Character Bible (the FX never-merged rules);
- the Screen Registry (L1 keeps exactly `DSP-SPC-01`…`04`);
- the Room Registry (three bays + entry; the desk and visitor anchors);
- the StarNet exclusions.

---

## 10. Decisions

| # | Decision | Status |
|---|---|---|
| SP-1 | L1 specialist overview display | **Closed:** none |
| SP-2 | Hand-off terminal / screen | **Closed:** none; real movement and events |
| SP-3 | Comparison display | **Closed:** none in L1 |
| SP-4 | Collaboration table / area | **Closed:** none in V1 |
| SP-5 | Bay layout | **Closed:** FX north (centrepiece), Metals west, Indices east |
| SP-6 | Family tag shapes (Character Bible CB-5) | **Open** |
| SP-7 | Exact dimensions and partition height | **Open** (after the tile scale, VB-3) |
| SP-8 | Exact colour values | **Open** (visual production, VB-4) |
