# Stellar Room Registry — v2 (flat vessel)

| | |
|---|---|
| **Status** | v2.0, rebuilt on Floor Plan revision C. Documentation only |
| **Geometry** | `STELLAR_STATION_TOPOLOGY.md` v2 (19 room slots, 2 corridors, 21 doors). This file assigns **functions**; it never changes geometry |
| **Replaces** | v1 (18 rooms on five decks, with the exact Command Deck and Risk Vault layouts). **v1 is void**; its room *contents* were reused where they are still valid (§7) |
| **Hard rules** | No function is invented to fill space: unassigned slots stay **RESERVED**. Positions inside rooms are **PROVISIONAL** until the tile scale is frozen (Topology §8). Rooms show only real telemetry (Screen Registry) |

---

## 1. Conventions

**Room status:**

| Status | Meaning |
|---|---|
| `ACTIVE` | Assigned V1 function, rendered |
| `ACTIVE · RESTRICTED` | As `ACTIVE`, but entry is limited by access rules (Topology §9; Character Registry §3) |
| `RESERVED · FUTURE_RESEARCH` / `FUTURE_OPERATIONS` / `FUTURE_AGENT_TEAM` | Kept empty for a later function family |
| `RESERVED · DESIGNATED` | Earmarked by the owner for a specific future room, not built |

**Reserved rooms:**
- Rendered as a closed, unlit shell with a static `SGN-007` "RESERVED" plate by the door.
- No anchors, no screens, and no character entry in V1.

**Size class** (relative to the sketch; the tile scale is open):

| Class | Rooms |
|---|---|
| **S** | Short L rooms (L4–L7) |
| **M** | Tall L rooms, R rooms |
| **L** | `H-LAB`, `H-HAB` |
| **XL** | `H-CMD` |

**Zones** are named sub-areas inside a room, used for containment and ambient behaviour
(adaptation A11). **Anchors** are named interaction points with a facing and a capacity (A9). An
anchor marked **(R)** is **restricted**: it is reserved for its listed role, and everyone else
paths around it (A12).

**Positions:**
- Hubs are described by **clock sector**, with 12 o'clock toward the top of the floor plan.
- Rooms are described relative to their door wall.
- All positions are provisional.

---

## 2. Room index (19 slots)

| Slot | ID | Canonical name | Anchor namespace | Size | Door → space | Status |
|---|---|---|---|---|---|---|
| 1 | `H-LAB` | Lab / Research Hub | `lab` | L | `DR-N-LAB` → `COR-N`; `DR-S-LAB` → `COR-S` | ACTIVE (lab bench zone FUTURE_RESEARCH) |
| 2 | `H-CMD` | Main Command / Central Operations | `command` | XL | `DR-N-CMD`, `DR-S-CMD`, `DR-CMD-HAB` | ACTIVE |
| 3 | `H-HAB` | Habitat (café, relax, games, plants, billiards, rest) | `habitat` | L | `DR-CMD-HAB`; `DR-R1`…`DR-R6` | ACTIVE |
| 4 | `L1` | Market Specialists Room | `specialists` | M | `DR-L1` → `COR-N` | ACTIVE |
| 5 | `L2` | Technical Deck | `technical` | M | `DR-L2` → `COR-N` | ACTIVE |
| 6 | `L3` | Debate Chamber | `debate` | M | `DR-L3` → `COR-N` | ACTIVE |
| 7 | `L4` | Data Core | `datacore` | S | `DR-L4` → `COR-N` | ACTIVE |
| 8 | `L5` | — | — | S | `DR-L5` → `COR-N` | RESERVED · FUTURE_RESEARCH |
| 9 | `L6` | Memory Archive | `archive` | S | `DR-L6` → `COR-S` | ACTIVE |
| 10 | `L7` | Performance Lab | `perflab` | S | `DR-L7` → `COR-S` | ACTIVE |
| 11 | `L8` | — | — | M | `DR-L8` → `COR-S` | RESERVED · FUTURE_OPERATIONS |
| 12 | `L9` | Execution Bay | `execbay` | M | `DR-L9` → `COR-S` | ACTIVE · RESTRICTED |
| 13 | `L10` | Risk Control Room | `risk` | M | `DR-L10` → `COR-S` | ACTIVE · RESTRICTED |
| 14 | `R1` | Performance & Wellbeing / Coaching Room | `coaching` | M | `DR-R1` → `H-HAB` | RESERVED · DESIGNATED (future) |
| 15 | `R2` | — | — | M | `DR-R2` → `H-HAB` | RESERVED · FUTURE_AGENT_TEAM |
| 16 | `R3` | — | — | M | `DR-R3` → `H-HAB` | RESERVED · FUTURE_AGENT_TEAM |
| 17 | `R4` | — | — | M | `DR-R4` → `H-HAB` | RESERVED · FUTURE_AGENT_TEAM |
| 18 | `R5` | — | — | M | `DR-R5` → `H-HAB` | RESERVED · FUTURE_AGENT_TEAM |
| 19 | `R6` | — | — | M | `DR-R6` → `H-HAB` | RESERVED · FUTURE_AGENT_TEAM |

**Totals:**
- **11 active**: 3 hubs + L1, L2, L3, L4, L6, L7, L9, L10. L9 and L10 are restricted.
- **8 reserved**: L5, L8, R1–R6.

### 2.1 Why this placement (the decision chain follows the corridors)

The chain follows the **engine's run order** (`MARKET_DATA` → `TECHNICAL` → `RESEARCH` → `SETUP`
→ `PROPOSAL` → `RISK` → execution; the engine is the source of truth, L2 sheet TA-2): **Market data
→ Technical → Research → Specialists → Debate → Setup → Central Trader → Approval / Portfolio →
deterministic Risk Engine → Execution**. It maps onto the approved geometry as follows:

- **Upper corridor `COR-N`** — analysis (a functional flow, not a walking order west → east):
  - `L4` Data Core (snapshot) → `L2` technical analysis (T3–T5), which runs **before** the
    specialist stage;
  - `H-LAB` (shared research and macro) and the `L2` technical evidence → `L1` specialists (the
    specialist stage **uses** the technical evidence produced in L2);
  - → `L3` debate (also citing technical evidence) → the setup evaluation back in `L2` (T6, which
    uses the debate verdict) → `H-CMD`.
- **`H-CMD`** — the Central Trader, Portfolio Manager approval, and the proposal builder.
- **Lower corridor `COR-S`** — decision and aftermath, near the `H-CMD` end:
  - `DR-S-CMD` → `L10` risk → `L9` execution;
  - `L6` memory and `L7` performance in the middle.
- **`H-HAB`** — life support and ambient life, behind `H-CMD`.
- **Reserved** — the rooms that no V1 function needs.

This is a **functional** assignment on fixed geometry. Moving a function between slots later
changes this file only.

---

## 3. Room cards

### 3.1 `H-LAB` — Lab / Research Hub · ACTIVE

| Field | Value |
|---|---|
| Purpose | The **shared upstream research team**: source collection, validation, fact / reaction / interpretation separation, and macro / context synthesis. It feeds all three market specialists. It is **one team for all market families**, never duplicated per family |
| Size / shape | L, circular; doors on the east rim (about 2 and 4 o'clock) |
| Entrances / exits | `DR-N-LAB` (`COR-N`), `DR-S-LAB` (`COR-S`) |
| Zones | `lab.feeds` (west arc, feed consoles R1–R6) · `lab.validation` (south arc, 4-station bench) · `lab.macro` (north arc, driver board) · `lab.core` (centre, hero) · `lab.experiment_bench` (south-west, **FUTURE_RESEARCH**, not rendered) · `lab.walkway` (east arc, between the two doors) |
| Mandatory furniture | `CON-006` × 6 (feed consoles; the R3–R6 consoles are **dormant** because those roles are deferred in the engine), `CON-007` validation bench, `CON-008` driver-board station, `EQP-005` lab dome ring (hero), `DEC-007` holo globe (decorative, carries no data), `LGT-009` dome light |
| Mandatory screens | `DSP-LAB-01`…`DSP-LAB-08`; `DSP-LAB-10`…`14` PLANNED (Research Lab) |
| Anchors | `lab.feed_r1`…`lab.feed_r6` · `lab.bench_1`…`lab.bench_4` · `lab.driver_board` · `lab.handoff_n` (by `DR-N-LAB`, item hand-off toward L1) · `lab.visitor_1`, `lab.visitor_2` |
| Usual agents | `CHR-012`–`CHR-017` (R1–R6), `CHR-018`–`CHR-021` (V1–V4), `CHR-011` (M1 macro). Future: `CHR-044`, `CHR-045` (not rendered) |
| Lighting / accent | Cool white dome light; science blue accent |
| State indicators | Feed consoles: active / dormant (grey) / stale · bench pass / fail marks · driver board: coverage partial · all from real events only |

### 3.2 `H-CMD` — Main Command / Central Operations · ACTIVE

| Field | Value |
|---|---|
| Purpose | Central command: the **Central Trader** (all concurrent opportunities), Portfolio Manager approval, the Research Manager, the Supervisor's run lifecycle, the trade proposal builder, and the global status wall |
| Size / shape | XL, circular; doors at about 10 o'clock (`DR-N-CMD`), 8 o'clock (`DR-S-CMD`) and 3 o'clock (`DR-CMD-HAB`) |
| Entrances / exits | `DR-N-CMD` (`COR-N`), `DR-S-CMD` (`COR-S`), `DR-CMD-HAB` (`H-HAB`) |
| Zones | `command.center` (raised dais: command table and chair) · `command.trader` (north-east arc) · `command.proposal` (south-west, beside `DR-S-CMD`, P1's route to the Risk room) · `command.ops` (north-west arc) · `command.walkway` (**through-walkway**: an open ring linking all three doors around the dais; kept clear because all west ↔ Habitat traffic crosses `H-CMD`, Topology §6) |
| Mandatory furniture | `TBL-001` command table, `SEA-001` command chair on `FLR-002` dais, `CON-004` Central Trader console, `CON-005` proposal console, `CON-003` operations console, `CON-022` budget console, `SEA-002` console chairs, `SEA-005` waiting bench, `DEC-007` holo globe (decorative) |
| Mandatory screens | `DSP-CMD-01`…`DSP-CMD-12` |
| Anchors | `command.chair` (R: `portfolio_manager`) · `command.table_head` (Research Manager) · `command.table_n1`, `table_n2`, `table_s1`, `table_s2` · `command.console_trader` (R: `trader`) · `command.console_proposal` (R: `trade_proposal_builder`) · `command.console_ops` (Supervisor) · `command.console_budget` (Quartermaster persona) · `command.bench_1`, `bench_2` · `command.visitor_1`, `visitor_2` |
| Usual agents | `CHR-001` PM, `CHR-002` RM, `CHR-003` Supervisor, `CHR-004` Central Trader, `CHR-005` Proposal Builder, `CHR-042` Quartermaster persona |
| Lighting / accent | Soft cove light around the rim; pools over the consoles; the main viewscreen is the brightest surface; command red accent |
| State indicators | Alert band (derived level) · mode plaque · Central Trader opportunity count · decision-chain stage lit only when its event exists |

### 3.3 `H-HAB` — Habitat · ACTIVE

| Field | Value |
|---|---|
| Purpose | Café, relax, games, plants, billiards and rest (the owner's label). It also holds the **recovery bay** for **real** cooldowns (`agent.resting`), which is visibly different from the cosmetic rest area |
| Size / shape | L, circular; `DR-CMD-HAB` at 9 o'clock; R1–R6 doors on the rim at about 11, 12, 2, 3, 5 and 7 o'clock |
| Entrances / exits | `DR-CMD-HAB` (`H-CMD`), plus the doors of R1–R6 (reserved rooms: closed to entry in V1) |
| Zones | `habitat.plants` (centre planter, hero) · `habitat.cafe` (north arc, counter) · `habitat.lounge` (south arc) · `habitat.games` (east arc, billiards) · `habitat.rest` (south-west, cosmetic pods) · `habitat.recovery` (north-west, real-cooldown pods and vitals) · `habitat.ring` (circulation linking all seven doors; kept clear) |
| Mandatory furniture | `PLT-005` central planter, `LEI-002` café counter, `LEI-003` dispenser, `TBL-003` café tables, `SEA-007` café chairs, `SEA-006` sofas, `TBL-004` coffee table, `LEI-004` rug, `LEI-001` billiard table, `STO-003` cue rack, `LEI-005` cosmetic rest pods, `EQP-004` recovery pods (real cooldown), `CON-021` vitals console, `SEA-009` window bench, `LGT-006` warm pendants |
| Mandatory screens | `DSP-HAB-01`…`DSP-HAB-04` |
| Anchors | `habitat.counter` (Bix) · `habitat.cafe_seat_1`…`_6` · `habitat.sofa_1`…`_4` · `habitat.billiards_1`, `_2` · `habitat.rest_pod_1`…`_3` (cosmetic) · `habitat.recovery_pod_1`…`_3` (real cooldown only) · `habitat.vitals` (Medic persona) · `habitat.window_1`, `_2` |
| Usual agents | `CHR-043` Bix (host), `CHR-041` Medic persona; idle crew (ambient); agents in a real cooldown |
| Lighting / accent | Warm pendants and planter light; synthetic cyan on the host drone |
| State indicators | Recovery pods show a countdown **only** from `agent.resting`; cosmetic pods never show vitals |

### 3.4 `L1` — Market Specialists Room · ACTIVE

| Field | Value |
|---|---|
| Purpose | The **three V1 market specialists**, one desk per **market family** (not per instrument): **Metals** (gold XAU, silver XAG), **FX** (majors and minors, multi-pair scanning, not tied to one pair), and **Indices** (NAS100 first, extensible). All three **report to the Central Trader** in `H-CMD` |
| Size / shape | M, tall; door in the south wall (`COR-N`) |
| Zones | `specialists.metals`, `specialists.fx`, `specialists.indices` (three desk bays behind `WAL-005` glass partitions), `specialists.entry` (by the door) |
| Mandatory furniture | `CON-009` family desk × 3, `SEA-002` × 3, `WAL-005` partitions, `PLT-003` desk plants |
| Mandatory screens | `DSP-SPC-01` Metals, `-02` FX, `-03` Indices, `-04` macro-context repeater |
| Anchors | `specialists.desk_metals`, `specialists.desk_fx`, `specialists.desk_indices` (each reserved to its specialist) · `specialists.visitor` |
| Usual agents | `CHR-022` Metals desk, `CHR-023` FX desk, `CHR-025` Indices desk (family desk representations; runtime agents S1–S4) |
| Engine note — **INTERIM ADAPTER** | The engine roster still has **four** per-instrument specialists (S1–S4). Until it migrates, the three desks are **family desk visual representations**: Metals ← S1; **FX ← S2 + S3 (two runtime agents)**; Indices ← S4. Each desk shows **one task row and one state chip per underlying runtime agent**, and never a single merged state (Character Registry §5.2). Instruments that are not configured (XAG, FX minors, other indices) show `NOT CONFIGURED`, never invented data |
| Lighting / accent | Science blue; each desk shows a family shape tag (not colour alone) |

### 3.5 `L2` — Technical Deck · ACTIVE

| Field | Value |
|---|---|
| Purpose | Charts, market structure, indicators, candles, pullback / setup detection, entry timing, market sessions (T2–T8) |
| Size / shape | M, tall; door in the south wall (`COR-N`) |
| Zones | `technical.table` (centre), `technical.stations` (along the walls), `technical.entry` |
| Mandatory furniture | `TBL-002` holo chart table, `CON-002` standing consoles × 6, `CON-010` session-clock pedestal |
| Mandatory screens | `DSP-TEC-01`…`DSP-TEC-07` |
| Anchors | `technical.station_t3`…`station_t8` · `technical.session_clock` (T2) · `technical.table_1`, `table_2` |
| Usual agents | `CHR-026`–`CHR-032`. T2 (`CHR-026`), T7 (`CHR-031`) and T8 (`CHR-032`) have **no producer** today: shown `idle` |
| Lighting / accent | Science blue; chart-table glow |

### 3.6 `L3` — Debate Chamber · ACTIVE

| Field | Value |
|---|---|
| Purpose | The investment debate (bull / bear, judged by the Research Manager) and the advisory risk debate, with visible evidence exchange |
| Size / shape | M, tall; door in the south wall (`COR-N`), about 1 corridor length from `H-CMD` |
| Zones | `debate.floor` (podiums facing the evidence stage), `debate.bench` (judge end, opposite the door), `debate.entry` |
| Mandatory furniture | `CON-011` podium × 5, `TBL-007` evidence stage, `CON-023` judge lectern, `SEA-003` judge seat, `LGT-007` podium spotlights |
| Mandatory screens | `DSP-DEB-01`…`DSP-DEB-06` |
| Anchors | `debate.podium_bull`, `debate.podium_bear`, `debate.podium_risk_1`…`_3` (each reserved to its debater) · `debate.judge_seat` (Research Manager; the PM when judging) · `debate.visitor` |
| Usual agents | `CHR-006`–`CHR-010`; visits by `CHR-002` and `CHR-001` |
| Lighting / accent | Neutral podium spotlights; the side is shown by icon + text, never by colour (L3 sheet DC-3) |

### 3.7 `L4` — Data Core · ACTIVE

| Field | Value |
|---|---|
| Purpose | Market-data snapshots and validation (T1), plus system health: journal and event-stream health, runtime health, reconciliation |
| Size / shape | S, short; door in the north wall (`COR-N`), opposite L1 / L2 |
| Mandatory furniture | `EQP-001` reactor column (hero; pulses **only** per `snapshot.created`), `CON-018` reactor console, `SRV-001` / `SRV-002` racks, `CON-027` reconciliation console (look-only; carries `DSP-DCR-05`; read from `datacore.visitor`, no work anchor; L4 sheet DK-4) |
| Mandatory screens | `DSP-DCR-01`…`DSP-DCR-06` |
| Anchors | `datacore.reactor_console` (R: `data_validator`) · `datacore.rack_check` · `datacore.visitor` |
| Usual agents | `CHR-035` Data Validator |
| Lighting / accent | Engineering gold; conduit glow dims to hatched grey when stale |

### 3.8 `L6` — Memory Archive · ACTIVE

| Field | Value |
|---|---|
| Purpose | Closed trades, the run replay index (read-only), post-trade reviews, comparable setups. **No producer today** for post-trade reviews (`memory.review.created`), settlement (`memory.outcome.settled`), comparable setups (`memory.decision.stored`) or reflections (`memory.reflection.written`): those panels read NOT AVAILABLE (L6 sheet DM-5) |
| Size / shape | S, short; door in the south wall (`COR-S`) |
| Mandatory furniture | `CON-019` archive terminal, `STO-004` crystal archive shelf, `TBL-005` work table |
| Mandatory screens | `DSP-MEM-01`…`DSP-MEM-04` |
| Anchors | `archive.terminal` (Post-Trade Reviewer) · `archive.shelf` · `archive.table_1` |
| Usual agents | `CHR-033` (no producer: files real Record Crystals only) |

### 3.9 `L7` — Performance Lab · ACTIVE

| Field | Value |
|---|---|
| Purpose | Runtime metrics, execution metrics, attribution, workload and review metrics, with sample-size honesty |
| Size / shape | S, short; door in the south wall (`COR-S`) |
| Mandatory furniture | `CON-020` metrics terminal, `TBL-005` work table |
| Mandatory screens | `DSP-PRF-01`…`DSP-PRF-05` |
| Anchors | `perflab.terminal` (Attribution) · `perflab.table_1` |
| Usual agents | `CHR-034` |

### 3.10 `L9` — Execution Bay · ACTIVE · RESTRICTED

| Field | Value |
|---|---|
| Purpose | Paper order routing. **Paper Broker only**: no MT5, Vantage, DEMO or LIVE path exists or is shown |
| Size / shape | M, tall; door in the north wall (`COR-S`) |
| Access | Restricted (Topology §9): `MP-EXEC` crew; the Supervisor to the entry zone only. Static `SGN-006` marking on `DOR-008` |
| Zones | `execbay.entry` (inside the door), `execbay.floor` (restricted) |
| Mandatory furniture | `CON-016` pre-flight console, `CON-017` launch console, `EQP-002` launch tube, `EQP-003` docking board, `FLR-008` launch-deck marking |
| Mandatory screens | `DSP-EXB-01`…`DSP-EXB-05` |
| Anchors | `execbay.preflight` (R: `execution_checker`) · `execbay.launch` (R: `paper_execution`) · `execbay.entry` |
| Usual agents | `CHR-038`, `CHR-039`. `CHR-040` (MT5) is deferred and not rendered |
| Lighting / accent | Engineering gold; a large **PAPER** marking driven by telemetry (`DSP-EXB-05`) |

### 3.11 `L10` — Risk Control Room · ACTIVE · RESTRICTED

| Field | Value |
|---|---|
| Purpose | The deterministic risk layer: proposal intake, contradiction check (P2), rule checks, sizing, exposure, the circuit breaker, and the hand-off of approved orders |
| Size / shape | M, tall; door in the north wall (`COR-S`); the nearest room to `H-CMD` along `COR-S` |
| Access model | **Logical, not geometric** (owner decision Q10; no secure lift and no airlock). Three zones: `risk.intake` (inside the door: the courier drops the proposal here), `risk.core` (P2 / P3 only), `risk.outbox` (by the door: the Paper Execution Agent collects an **approved** order here). Restricted anchors hold the consoles. The door carries `DOR-008` with a static `SGN-006` marking, plus the telemetry-driven door panel `DSP-RSK-09` |
| Workflow rules (visual) | A proposal card appears only after `trade.proposed`. An order capsule appears in `risk.outbox` only after `risk.approved` **and** `order.created`. While the breaker is `TRIPPED`, the outbox stays dark and the door panel says **BREAKER TRIPPED**. The UI can never trigger any of these |
| Mandatory furniture | `CON-012` intake counter, `CON-029` outbox counter, `CON-013` rule-checklist console, `CON-014` sizing console, `CON-015` breaker panel, `CON-001` contradiction desk, `FLR-003` grating floor, `LGT-005` cold panel light |
| Mandatory screens | `DSP-RSK-01`…`DSP-RSK-09` |
| Anchors | `risk.intake_drop` (courier) · `risk.intake_desk` (R: `contradiction_checker`) · `risk.rule_console` (R: `risk_engine`) · `risk.sizing_console` (R: `risk_engine`) · `risk.breaker_panel` (R: `risk_engine`) · `risk.outbox_pickup` (R: `paper_execution`) · `risk.entry_wait` (Supervisor / Medic approach point) |
| Usual agents | `CHR-036` P2, `CHR-037` P3; visits: `CHR-005` (intake only), `CHR-039` (outbox only), `CHR-003`, `CHR-041` (entry only) |
| Lighting / accent | Cold panel light; engineering gold on charcoal |

### 3.12 Reserved rooms

| Room | Reservation | Note |
|---|---|---|
| `L5` | FUTURE_RESEARCH | Expansion for the Research Lab (experiment runtime is not built) |
| `L8` | FUTURE_OPERATIONS | Operations expansion; no function assigned |
| `R1` | DESIGNATED: **Performance & Wellbeing / Coaching Room** | §4 |
| `R2`–`R6` | FUTURE_AGENT_TEAM | Future agent teams around the Habitat |

---

## 4. `R1` — Performance & Wellbeing / Coaching Room (designated, future)

| Field | Value |
|---|---|
| Status | RESERVED · DESIGNATED. Not rendered, no anchors are active, and no screens are live (`DSP-CCH-01`…`04` are PLANNED) |
| Future purpose | Team debrief; review of repeated errors; workload balancing; conflict resolution between agents' outputs; performance coaching; review after difficult runs; rest / recovery **recommendations** |
| Future persona | `CHR-046` **Performance & Wellbeing Coach** (Character Registry) |
| Signals it may use | **Measurable system signals only:** retries, workload (task counts and durations), repeated errors (`agent.task.failed` patterns), failed reviews, conflict frequency (for example contradiction flags and debate reversals), long-running tasks, real cooldowns |
| Never | No human emotion, mood, stress or psychiatric language or diagnosis. No authority over trading, Risk or runs: its outputs are recommendations shown on screens |
| Planned furniture | `TBL-008` debrief table, `SEA-002` chairs, `CON-028` coaching console |
| Planned anchors | `coaching.console` (future Coach) · `coaching.table_1`…`coaching.table_4` (debrief seats). Not active in V1 |

---

## 5. Corridors (non-room spaces)

| Space | Function | Furniture | Screens | Rule |
|---|---|---|---|---|
| `COR-N` | Transit for the analysis chain (LAB → L1 / L2 / L3 / L4 → CMD) | `COR-008` segments, `COR-009` hub junctions × 2, `COR-007` door niches, `SGN-001` name plates, `SGN-003` wayfinding | `DSP-CRN-01` alert repeater | Transit only: no ambient loitering, no furniture in the path, and the corridor ends (hub doors) stay clear |
| `COR-S` | Transit for the decision chain (CMD → L10 → L9; L6 / L7) | as `COR-N` | `DSP-CRS-01` alert repeater | as `COR-N`. The courier and the order hand-off use this corridor |

---

## 6. Physical integrity rules for every room

- No room adds a door, window-door or hatch. The only openings are the 21 approved doors.
- No furniture or screen sits on a door tile or on the 1-tile approach in front of it.
- Hub walkways (`command.walkway`, `habitat.ring`, `lab.walkway`) stay clear of furniture.
- Reserved rooms stay empty; nothing is stored in them.
- Room positions and zone shapes are PROVISIONAL until the grid is generated. The grid acceptance
  checks (Topology §8) must pass first.

---

## 7. Changes from v1

- **Merged into hubs:**
  - the Research Observatory and the Macro & News Observatory → `H-LAB`;
  - the Café, Lounge, Billiard Room, Rest Area, Observation Deck and the Wellbeing Room's pods → `H-HAB` zones;
  - the Command Deck → `H-CMD`.
- **Re-homed on the corridors:**
  - the Market Analysis Wing → `L1` (three families instead of four instrument desks);
  - the Technical Deck → `L2`, the Debate Chamber → `L3`, the Data Core → `L4`;
  - the Memory Archive → `L6`, the Performance Lab → `L7`;
  - the Execution Bay → `L9`;
  - the Risk Control Vault → `L10` Risk Control Room, **logical access instead of a secure lift, antechamber and blast door**.
- **Moved to reserved:** the Quant Lab (reserved v1 room) → the `H-LAB` future zone plus `L5`.
- **New:** reservations for the Coaching Room (`R1`) and the future teams (`R2`–`R6`, `L8`).
- **Removed:** the exact v1 layouts of the Command Deck (30 × 28) and the Risk Vault (16 × 16).
  Exact layouts will be drawn again on the new grid once the scale is frozen.
