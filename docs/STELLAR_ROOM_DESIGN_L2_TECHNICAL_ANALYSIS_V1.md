# Stellar Room Design Sheet — L2 Technical Analysis Room (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; TA-1…TA-8 decided, TA-9 / TA-10 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L2` — registry name **Technical Deck** · ACTIVE · public (Room Registry v2 §3.5). "Technical Analysis Room" is the working title of this sheet; the official name stays **Technical Deck** (TA-1) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Figures: `STELLAR_CHARACTER_REGISTRY.md` §4, `STELLAR_CHARACTER_BIBLE_V1.md`. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Engine facts: `stellar/src/stellar/technical/` (Phase 5 engine and `publish.py`), `setups/lifecycle.py`, `trader/desk.py`, `runtime/orchestrator.py`, `agents/roster.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | Technical analysis runs in the engine (deterministic, Phase 5). This room only **shows** its real outputs. The visual layer never computes or draws an indicator, signal, level, pattern, score, confidence or buy / sell call of its own |

---

## 1. StarNet concept review (analysis stations, visual information, hand-offs)

**Method.** I read the audit (S13, S16, S19, S20, S25, S26, S28, S46) and the local StarNet
checkout at pinned revision `fbddbf99` **read-only**:
- `frontend/app/world.js`: placed workstations (`deskPropFor`, `deskSeat`: one workstation per
  agent, the agent walks to it to work), watchable lead → worker hand-off boxes driven by bus
  events, the "work seizes idle" ladder;
- `frontend/app/linewatch.js`: pure folds of real events into status read-outs with a priority
  order and an honest "not started / unknown";
- `frontend/app/propanchor.js`: approach tile and facing per prop.

StarNet has **no technical analysis and no charts**: its work surfaces show harness runs, not market
data. Only **staging and honesty patterns** are taken. **Nothing is copied:** no art, layouts,
characters, interfaces, assets, dialogue or personality systems.

| StarNet concept | How Stellar adapts it | What Stellar rejects |
|---|---|---|
| **Dedicated workstation per agent** (`deskPropFor` / `deskSeat`: one bound station, the agent walks there to work) | Each technical role has **one reserved station** (`technical.station_t3`…`t8`, `technical.session_clock`), fixed by the Room Registry (§3.2) | Stations placed or reassigned by the user; building mode |
| **Approach tile and facing** (`propanchor.js`) | Every standing console and the chart table have an approach tile and a facing toward their own display (audit S19) | — |
| **Work seizes idle** (a real run pulls the body back to its desk at once; the priority ladder, audit S28) | A real technical result for a role pulls its figure back to its station (adaptation A13) | Social or curiosity beats that compete with work |
| **Watchable hand-off** (boxes fly from lead to worker **only** inside a real dispatch window, from bus events) | A **data crystal** (`PRP-001`) leaves L2 **only** when a real downstream consumer starts (`analysis.created` → the consumer's `agent.task.started`) (§5) | Hand-offs without a consumer; flying boxes; conveyor belts (S16) |
| **Honest status read-outs** (`linewatch.js`: a lamp is WORKING only when the run is confirmed; "a placement whose run never starts is not shown as waiting forever") | Every L2 display shows only engine values; roles with no producer read **NOT AVAILABLE** and their figures stay `idle` (adaptation A19) | Invented progress, timers or "busy" poses without data |
| **Two bodies on one artefact** (the watch beat: stand by a working peer) | When one real technical analysis is published, its structure and momentum figures stand at the chart table's two anchors for its display time (§5, TA-4) | Following or tailing peers; random meetings |
| Idle "sentience" engine, CRT look, station artwork | — | **Rejected** (S27, S33, S34) |

**Stellar original design (not from StarNet):**
- the technical roles and their outputs (Phase 5 engine, setup lifecycle);
- the chart table, the wall displays, the station arrangement, materials and lighting (§3);
- the rule that one technical analysis is **one** crystal to its first real consumer (§5).

---

## 2. Engine truth (what exists today)

### 2.1 Roles, producers and events

| Role | Figure | Kind | Real output | Event | Status |
|---|---|---|---|---|---|
| T1 `data_validator` | `CHR-035` (L4) | deterministic | Verified market snapshot | `snapshot.created` (metadata: ids, timeframe, `as_of`, last bar close, **freshness**; **no bars**) | Upstream of L2 (L4 Data Core) |
| T2 `market_session` | `CHR-026` | deterministic | — | `market.session.changed`: **no producer** | **NOT AVAILABLE** |
| T3 `market_structure` | `CHR-027` | deterministic | Swings, structure state and events, legs, pullback, zones | `analysis.created` kind `structure`, agent `market_structure` | **Available** |
| T4 `technical_indicator` | `CHR-028` | deterministic | Indicators, volatility | `analysis.created` kind `momentum`, agent `technical_indicator` | **Available** |
| T5 `price_action` | `CHR-029` | deterministic | Candle features and labels, sequences, consolidation | `analysis.created` kind `price_action`, agent `price_action` | **Available** |
| T6 `pullback_setup` | `CHR-030` | deterministic | Setup evaluation and lifecycle | `setup.state.changed`, agent `pullback_setup` | **Available** |
| T7 `entry_timing` | `CHR-031` | deterministic | — | **no producer** (no engine code) | **NOT AVAILABLE** |
| T8 `technical_analyst` | `CHR-032` | LLM | — | **no producer**: not in the pipeline's LLM roles, no stage calls it | **NOT AVAILABLE** |

- **No task events for T2–T8.** `agent.task.*` is emitted only by the research pipeline and the
  trader desk. The technical figures therefore have **no "task started"**: the room sees each
  result only when it is published.
- **One technical analysis = three `analysis.created` events** (one per facet, T3 / T4 / T5)
  sharing one `technical_analysis_id` (the event's correlation id).

### 2.2 Where the data actually is

| Data | Carried by | Notes |
|---|---|---|
| Structure state (`UP` / `DOWN` / `RANGE` / `MIXED` / `INSUFFICIENT`), limitations, timeframe, `as_of`, snapshot id, analysis ids, content hash, engine version | `analysis.created` payload | The event carries **no** candles, indicator values, levels or zones |
| Candles (OHLC and features), pivots, swings, structure events, legs, pullback, consolidation, volatility, **indicator values** (SMA, EMA, RSI, MACD, Bollinger, ATR as configured), volume evidence, **zones**, unevaluated items | The run's `run.stage.completed` for stage `TECHNICAL` (its `outputs.analysis`: the full `TechnicalAnalysis`) — source **RL** | Recomputable from the same bars, configuration and engine version |
| Snapshot freshness | `snapshot.created` (`freshness`) | Drives **STALE** |
| Setup: state (`from` → `to`), rule, status, direction, reasons, limitations, invalidation level, validity window, level options, evidence (including the research verdict's final stance and evidence grade) | `setup.state.changed` payload (full `setup`) | Produced in the run's `SETUP` stage, **after** the debate verdict |
| Multi-timeframe alignment | `technical/mtf.py` exists, but the runtime does **not** pass it to the desk | **NOT AVAILABLE** (one timeframe per run) |
| Setup states `APPROVED`, `REJECTED`, `FILLED` | Defined in the lifecycle, but **no code sets them** | **NOT AVAILABLE** on the setup board; risk and fill outcomes live in their own events (L10, L9) |

### 2.3 Where L2 sits in the real run order

`MARKET_DATA` (L4) → **`TECHNICAL` (L2: T3–T5)** → `RESEARCH` (`H-LAB` macro, L1 specialist,
L3 debate and verdict) → **`SETUP` (L2: T6)**, with the Central Trader and the proposal in `H-CMD`
→ `PROPOSAL` → `RISK` (L10) → execution (L9).

The engine's technical stage runs **before** the specialists. Specialists, debaters and the Trader
**consume** technical evidence; **no L2 role consumes a specialist view**. The documented chain is
therefore **L2 Technical → L1 Specialists** (owner decision TA-2; Room Registry §2.1 and the other
documents aligned).

---

## 3. Room identity, relationships and architecture

### 3.1 Identity

| Aspect | Definition |
|---|---|
| **Role** | The technical-analysis stage: deterministic chart reading (structure, momentum, price action) and the setup lifecycle |
| **It is not** | Main Command, the Research Lab, the Market Specialists room, the Debate Chamber, Risk Control or Execution. Nothing is approved, sized, debated or executed here |
| **Atmosphere** | Precise, analytical, technical, clean, focused. A quiet instrument room, **not** a trading-floor spectacle, a dark bunker or a wall of screens |
| **Visual identity** | A central **holographic chart table** showing the run's real candles, slim **standing consoles** along the side walls, a few clean wall panels, and a **session-clock pedestal** by the entry |

### 3.2 Relationships

| Room | Relationship (engine-true) |
|---|---|
| **L4 Data Core** | **Upstream.** The verified snapshot (T1) is the input; no walk (L4 is across `COR-N`, data only) |
| **L1** | **Downstream consumer.** The specialist step receives the technical evidence. A crystal walk L2 → `COR-N` → `DR-L1` happens **only** when the specialist's `agent.task.started` follows the analysis (§5). **Nothing arrives in L2 from L1**: no L2 role consumes a specialist view (§10, T2) |
| **L3** | **Downstream consumer.** Bull and bear cite technical evidence; it appears on the L3 evidence stage **as data** (L3 sheet §2). The L3 verdict (`decision.research_plan.created`) is in turn part of the **setup** evidence T6 evaluates (no walk; data only) |
| **`H-CMD`** | **Downstream.** The Central Trader and the proposal builder use the setup; `DSP-CMD-02` shows setup states and the latest technical assessment. No walk: the setup reaches `H-CMD` as data |
| **`H-LAB`** | **No direct link.** Macro context (M1) goes to L1 and L3, not to L2; the technical engine uses no research input |

No new door or connection: L2 is reached only through `DR-L2` from `COR-N`.

### 3.3 Shape and entrance (approved; unchanged)

- **Shape:** a tall rectangular room (size M; Floor Plan rev C §4: x 550–664, y 343–520, about
  114 × 177 px; **not frozen**). North of `COR-N`, between L1 (west) and L3 (east), both across
  **non-walkable hull** (Q4).
- **One door:** `DR-L2`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator,
  centred in the **south wall**, opening onto `COR-N`. **No other opening.** No lock, no new airlock,
  no hidden passage, no restricted marking (public room).
- **Cutaway:** the camera-facing walls are cut away (`WAL-008`); the door keeps a visible frame,
  threshold and opening (Visual Bible C4).

### 3.4 Schematic (not to scale; door at the bottom)

```
                      north wall (back)
   +-------------------------------------------------+
   |  DSP-TEC-02 indicator      DSP-TEC-03 structure  |
   |  panels (north wall)       & zones (north wall)  |
   |                                                  |
   | CON-002 T3   +------------------------+  CON-002 |
   | structure    |  TBL-002 holo chart    |  T6      |
   | (west)       |  table + DSP-TEC-01    |  setup   |
   |              |  table_1 (W) table_2(E)|  (east)  |
   | CON-002 T4   |                        |  CON-002 |
   | indicators   +------------------------+  T7 entry|
   | (west)                                  timing   |
   |                       DSP-TEC-04 setup  (east)   |
   | CON-002 T5            lifecycle band            |
   | price action          (east wall, over T6 / T7)  |
   | (west)                DSP-TEC-05 pullback,      |
   |                       DSP-TEC-06 entry timing   |
   |                                         CON-002  |
   | CON-010 session-clock pedestal (T2)     T8       |
   | + DSP-TEC-07 clock ring (west wall)     analyst  |
   |            technical.entry                       |
   +--------------------[ DR-L2 ]---------------------+
                          COR-N
```

- **West wall: the analysis line** (T3 structure, T4 indicators, T5 price action), the three roles
  that produce the facets of one analysis, in reading order from the table.
- **East wall: the setup line** (T6 setup, T7 entry timing, T8 analyst report).
- **Centre: the chart table**, with its two anchors on its long sides, facing the north-wall panels.
- **Entry (south):** the session-clock pedestal and ring by the door, so the clock reads from the
  corridor.
- Screens are limited to the **seven approved displays**; no extra monitors.

### 3.5 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`), with a thin titanium inlay framing the chart table (walk-over) |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium / light metallic trims** |
| Technical elements | **Graphite** console bodies, chart-table base, pedestal and screen bezels |
| Accent | **Science blue** lines (SCI department) on console edges and the table rim. Static; never a data state |
| Standing consoles (`CON-002`) | Slim, graphite, a small console-top work surface; each carries its role plate (text + role icon) |
| Chart table (`TBL-002` + `SCR-012`) | A low, long graphite table; the holographic surface is a **flat, restrained projection** just above the table top, showing only real candles and overlays. **No floating "fake hologram" effects** |

### 3.6 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a linear light slot along the table; not drawn in the cutaway (only its edge is suggested) |
| General | Clean neutral white with a light cool-blue tint (Room Registry: science blue; chart-table glow). Bright and even; never dark |
| Work pools | `LGT-002` over a console **only** for its figure's real result display time (§5) |
| Chart-table glow | Soft, **only while** the table shows real data; off (hatched grey) when it reads **AWAITING DATA** / **STALE** |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.7 Walkable areas and zones (Room Registry §3.5)

| Zone | Who | Rule |
|---|---|---|
| `technical.entry` | Everyone entering | The door approach tile stays empty; the pedestal stands beside it, not in front |
| `technical.table` (centre) | T3 / T4 at `technical.table_1` / `table_2` during a real analysis (§5) | The table blocks its footprint; a 1-tile walkway rings it |
| `technical.stations` (along the walls) | T3–T8 at their reserved station anchors; T2 at `technical.session_clock` | Consoles back onto the walls; not walkable behind them |

---

## 4. Characters

### 4.1 Permanent occupants (Character Registry §4: `CHR-026`–`CHR-032`, all SCI)

One figure per runtime role; **no role is merged**.

| Figure | Runtime role | Workstation / anchor | Usual position | Movement | Analysis behaviour | Hand-offs | L1 | L3 | `H-CMD` |
|---|---|---|---|---|---|---|---|---|---|
| **Market Session** `CHR-026` | T2 `market_session` | `CON-010` · `technical.session_clock` | At the pedestal by the entry | Stays; seeded ambient when idle | **None today** (no producer): `idle`; the ring shows UTC only | None | — | — | — |
| **Market Structure** `CHR-027` | T3 `market_structure` | `CON-002` · `technical.station_t3` | West wall, north console | To `technical.table_1` for a real analysis's display time; back | On its `analysis.created` (`structure`): `stand_work`, then `look_screen` at the table; real levels / zones appear on `DSP-TEC-03` | Carries the analysis crystal (`PRP-001`) to the **first real consumer** (TA-3) | Crystal walk to `specialists.visitor` on the specialist's `agent.task.started` | Data only | Data only |
| **Technical Indicator** `CHR-028` | T4 `technical_indicator` | `CON-002` · `technical.station_t4` | West wall, middle | To `technical.table_2` with T3 for the same analysis; back | On its `analysis.created` (`momentum`): `stand_work`; real values on `DSP-TEC-02` | None | — | Data only | Data only |
| **Candle / Price Action** `CHR-029` | T5 `price_action` | `CON-002` · `technical.station_t5` | West wall, south | Stays at its station (the table has two anchors only) | On its `analysis.created` (`price_action`): `stand_work`, `look_screen` toward the table | None | — | Data only | Data only |
| **Pullback / Setup** `CHR-030` | T6 `pullback_setup` | `CON-002` · `technical.station_t6` | East wall, north | Stays | On `setup.state.changed`: `stand_work`; the setup card moves on `DSP-TEC-04`; pullback on `DSP-TEC-05` | None (the setup reaches `H-CMD` as data) | — | Uses the verdict as evidence (data) | Feeds the Trader (data) |
| **Entry Timing** `CHR-031` | T7 `entry_timing` | `CON-002` · `technical.station_t7` | East wall, middle | Stays; seeded ambient when idle | **None today** (no producer): `idle`; `DSP-TEC-06` reads **NOT AVAILABLE · entry timing** | None | — | — | — |
| **Technical Analyst** `CHR-032` | T8 `technical_analyst` | `CON-002` · `technical.station_t8` | East wall, south | Stays; seeded ambient when idle | **None today** (no producer): `idle` | None | — | — | — |

### 4.2 Visitors

| Figure | When | Where | Behaviour |
|---|---|---|---|
| **Supervisor** `CHR-003` | Only on a real `run.failed` whose failure is `TECHNICAL_FAILED` or `SETUP_FAILED` (TA-6) | Inside the entry | Stands, looks at the panels, leaves |
| **Medic persona** `CHR-041` | Only for a figure in a real `error` / `overloaded` state | Entry zone only | Attends, leaves. (No technical role emits task failures today, so this is rare) |
| **Metals / FX / Indices desks** | **Not in L2**: no L2 role consumes their views (TA-2) | — | — |

Nobody else is routed in; L2 is not a transit or loitering room. No permanent occupant is added
beyond the registry's seven.

---

## 5. Engine-supported workflow

| # | Step | Trigger (real event) | What the room shows | Status |
|---|---|---|---|---|
| 0 | No analysis yet | none | Chart table **AWAITING DATA**; panels **AWAITING DATA** / **NO ACTIVE SETUP**; all figures `idle` at their stations | Yes |
| 1 | Input arrives | `snapshot.created` (L4) | The table's freshness line updates (**STALE** if the snapshot says so). No figure moves (no task event exists) | Yes |
| 2 | "Task arrives" / "agent moves to its station" | — | Not shown as a separate step: T3–T5 emit **no task start**. A figure away on ambient returns only when its result arrives (step 3) | **NOT AVAILABLE** (no `agent.task.*` for T2–T8) |
| 3 | Analysis result | `analysis.created` × 3 (`structure`, `momentum`, `price_action`) sharing one `technical_analysis_id` | T3, T4, T5 `stand_work` for a fixed **result display time** (it marks the published result; it does not imitate ongoing work). T3 and T4 step to the table's two anchors for that time (TA-4) | Yes |
| 4 | Technical information displayed | same, with the run's `TECHNICAL` stage checkpoint (RL) | Candles and overlays on the table; indicator values; structure state, levels and zones; limitations and unevaluated items as text | Yes (values from RL, not from the event; §10, T3) |
| 5 | Hand-off to the real consumer | the specialist's `agent.task.started` in the same run | T3 carries **one** crystal (`PRP-001`) `DR-L2` → `COR-N` → `DR-L1` → `specialists.visitor`, then returns. **No walk** to L3 or `H-CMD` (data only there) | Yes, only if the consumer starts |
| 6 | Setup evaluation | `setup.state.changed` (T6, `SETUP` stage, after the L3 verdict) | T6 `stand_work`; the setup card moves on the lifecycle band; `ARMED` shows an icon + text (a glow only together with them) | Yes |
| 6a | Setup proposed | `setup.state.changed` `ARMED` → `PROPOSED` (with `trade.proposed` from `H-CMD`) | The card reads **PROPOSED**; the proposal itself is shown in `H-CMD` / L10, not here | Yes |
| 6b | Setup approved / rejected / filled | — | Not shown on the board | **NOT AVAILABLE** (no producer for these setup states) |
| 7 | Entry timing | — | `DSP-TEC-06` **NOT AVAILABLE · entry timing**; T7 `idle` | **NOT AVAILABLE** |
| 8 | Session state | — | `DSP-TEC-07` **NOT AVAILABLE · session feed**; the ring shows UTC (UI clock) | **NOT AVAILABLE** |
| 9 | Written technical report (T8) | — | T8 `idle` | **NOT AVAILABLE** |
| 10 | Multi-timeframe layers | — | The table shows the run's **one** timeframe | **NOT AVAILABLE** (not wired) |
| 11 | Technical stage failure | `run.failed` with `TECHNICAL_FAILED` | Table and panels keep the last real values with their age; the Supervisor may visit (§4.2) | Yes |
| 12 | Return / idle | display time ends; crystal delivered | Figures at their stations; seeded ambient (`COR-N` → `H-CMD` → `H-HAB`) only when idle | Yes |

Nothing is invented: no signal, score, confidence, "buy / sell", pattern call or chart value that the
engine did not produce.

---

## 6. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Holographic chart table** | `TBL-002` + `SCR-012` (`DSP-TEC-01`) | The run's real candles with structure overlays | Room centre | `technical.table_1`, `table_2` | **Hero** |
| 2 | **Standing consoles** × 6 (analysis workstations) | `CON-002` | One reserved station each for T3–T8 | West wall: T3, T4, T5. East wall: T6, T7, T8 | `technical.station_t3`…`t8` (reserved) | High (T3–T6), Low (T7, T8: idle) |
| 3 | **Session-clock pedestal** | `CON-010` | T2's station | By the entry, west side | `technical.session_clock` | Medium |
| 4 | **Clock ring** | `SCR-010` (`DSP-TEC-07`) | Session clock (UTC only today) | West wall by the entry, above the pedestal | none | Medium |
| 5 | **Indicator panels** | `SCR-002` (`DSP-TEC-02`) | Real indicator values | North wall, west | Look target | High |
| 6 | **Structure & zones panel** | `SCR-002` (`DSP-TEC-03`) | Structure state, levels, zones | North wall, east | Look target | High |
| 7 | **Setup lifecycle band** | `SCR-005` (`DSP-TEC-04`) | Setup cards and states | East wall, over T6 / T7 | Look target; NAV to the setup | High |
| 8 | **Pullback panel** | `SCR-003` (`DSP-TEC-05`) | Pullback on the active setup | East wall, by T6 | Look target | Medium |
| 9 | **Entry-timing panel** | `SCR-003` (`DSP-TEC-06`) | NOT AVAILABLE today | East wall, by T7 | none | Low |
| 10 | **Data crystal** (hand-off) | `PRP-001` | One technical analysis to its first real consumer | T3's hands, L2 → L1 | Appears only with a real consumer | Medium |
| 11 | Work pool lights | `LGT-002` | Over a console during its result display time | Over each console | none | Low |
| 12 | Room plate, emblem | `SGN-001`, `DEC-006` | Name and department emblem | Corridor side of `DR-L2` | none | Low |

**Hand-off area:** none as a separate object. The crystal leaves from T3's station through the door;
the receiving point is L1's `specialists.visitor` (existing anchor). **Not added:** no separate
"hand-off terminal", "chart wall", "timeframe stack" or per-station monitors (§10, T8).

---

## 7. Screen design (Screen Registry v2 §5.4 is the authority)

| Display | Placement | Purpose | Real data source | States / placeholders |
|---|---|---|---|---|
| `DSP-TEC-01` Chart table | Table surface | Candles and overlays (pivots, swings, structure breaks, zones) of the run's one timeframe | Candles and overlays from the `TECHNICAL` checkpoint (RL); freshness from `snapshot.created` (§10, T4) | **AWAITING DATA**, **STALE** (from the snapshot's freshness), **LINK DOWN** |
| `DSP-TEC-02` Indicator panels | North wall, west | Values of the **configured** indicators (SMA, EMA, RSI, MACD, Bollinger, ATR) and volatility | RL (`indicators`, `volatility`); triggered by `analysis.created` (`momentum`) | Not configured → **NOT CONFIGURED**; unevaluated (for example insufficient history) → **NOT AVAILABLE** with the engine's reason text; **AWAITING DATA** |
| `DSP-TEC-03` Structure & zones | North wall, east | Structure state; last swings; structure events; zones (support / resistance / mixed) and their events | State: `analysis.created` (`structure_state`). Levels and zones: RL | **AWAITING DATA**; `INSUFFICIENT` shown as the engine's own state word |
| `DSP-TEC-04` Setup lifecycle | East wall band | One card per setup: state, direction, rule, reasons, invalidation level, validity window | `setup.state.changed` | **NO ACTIVE SETUP**; `APPROVED` / `REJECTED` / `FILLED` never shown (no producer) |
| `DSP-TEC-05` Pullback state | East wall, by T6 | Pullback of the active setup's reference leg: bars, depth, retracement ratios | RL (`pullback`) + `setup.state.changed` (`reference_leg_id`) | **NO ACTIVE SETUP**; missing ratio → **UNKNOWN** |
| `DSP-TEC-06` Entry timing | East wall, by T7 | — | No producer | **NOT AVAILABLE · entry timing** |
| `DSP-TEC-07` Session clock | West wall by the entry | — | `market.session.changed`: no producer | **NOT AVAILABLE · session feed**; the ring shows UTC (UI clock, not market state) |

**Screen rules for this room:**
- **Never fabricate** candles, indicator values, levels, zones, signals, pattern calls, scores,
  confidence or buy / sell labels. A candle label (for example an engine candle classification) is
  shown only as the engine's own label.
- Limitations (for example `insufficient_history`, `tick_volume_only`, `stale_source`) are shown as
  **text** next to the affected values.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). LIVE does not apply
  (no live quotes; snapshot values never pose as live). MODE UNKNOWN does not apply (no mode
  display).
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- Colour never carries a state alone (the `ARMED` glow always has an icon and text).
- All displays are read-only; NAV only opens details.

---

## 8. Agent life

All activity comes from **real events**, **real tasks** or **normal idle behaviour**. There is **no
emotional simulation**, no random conversation and no artificial analysis.

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Showing a published result at the station | Its own `analysis.created` / `setup.state.changed` (fixed display time) | T3, T4, T5, T6 | `stand_work` |
| Reviewing the chart | Same analysis | T3 / T4 at the table anchors; T5 turns toward the table | `look_screen` |
| Moving between stations | Only station ↔ table for T3 / T4 (TA-4) | T3, T4 | `walk` |
| Real hand-off | The specialist's `agent.task.started` after the analysis | T3 | `walk`, `carry` (`PRP-001`) |
| Returning to the station | End of display time; crystal delivered; any new real result (work over idle) | All producing figures | `walk` |
| Idle | No real result | All; T2, T7, T8 always today | `stand_idle`; seeded ambient via `COR-N` → `H-CMD` → `H-HAB` |

No `talk` inside L2; no idle conversations between stations.

---

## 9. Access (summary)

- **One explicit door** (`DR-L2`, `DOR-001`, south wall onto `COR-N`). No lock, no automatic door
  beyond the approved `DOR-001` behaviour, no new airlock, no hidden passage.
- Public room; entered only for a real reason (§4). Station anchors are reserved to their roles.
- **Red** only from real system states.

---

## 10. Contradictions and owner decisions

| # | Topic | Documents (before) | Engine truth | Resolution |
|---|---|---|---|---|
| **T1** | **Room name** | Request: "Technical Analysis Room"; registries: "Technical Deck" | — | **Resolved (TA-1):** the official name stays **Technical Deck**; no registry rename. "Technical Analysis Room" is this sheet's working title only |
| **T2** | **Chain order L1 → L2** | Room Registry §2.1, Visual World Plan §3.1, Character Registry decision chain, Screen Registry `DSP-CMD-04`, H-LAB and H-CMD sheets, L1 sheet (desk walks to "L2") | Run order `TECHNICAL` → `RESEARCH`: the technical stage runs **before** the specialist stage, and the specialists **use** its evidence. No L2 role consumes a specialist view | **Resolved (TA-2):** the engine is the source of truth. The chain is documented as **L2 Technical → L1 Specialists** in all those documents (documentation only; no runtime change) |
| **T3** | **Technical values source** | Screen Registry: `DSP-TEC-02` / `-03` from `analysis.created` | `analysis.created` carries the state and ids only; values, levels and zones are in the `TECHNICAL` checkpoint | **Resolved (TA-5):** Screen Registry sources now name the checkpoint (RL) for values and `analysis.created` for state / ids |
| **T4** | **Chart table source** | Screen Registry: `DSP-TEC-01` from `snapshot.created` | `snapshot.created` carries no bars | **Resolved (TA-5):** candles from the `TECHNICAL` checkpoint; `snapshot.created` for freshness only |
| **T5** | **Indicator list** | Screen Registry: "EMA / RSI / MACD / ATR" | Engine kinds: SMA, EMA, RSI, MACD, Bollinger, ATR | **Resolved (TA-5):** SMA and Bollinger added; no other indicator |
| **T6** | **T2 / T8 producers** | Character Registry: `CHR-026`, `CHR-032` ACTIVE without a note | T2 has no code; T8 is never called | **Resolved (TA-7):** explicit "no producer" notes in the Character Registry, Room Registry §3.5 and Visual World Plan §3.2 |
| **T7** | **Timeframe layers** | Visual World Plan §3.2: "timeframe layers" | `mtf.py` not connected in the runtime | **Resolved:** **NOT AVAILABLE** until connected; the Visual World Plan L2 card says so |
| **T8** | **Useful objects that do not exist** | Request: "hand-off areas"; a multi-timeframe display | No such assets | **Stands:** none invented; the crystal uses L1's existing `specialists.visitor` anchor |
| **T9** | **Setup states after PROPOSED** | `APPROVED` / `REJECTED` / `FILLED` listed | No code sets them | **Stands:** **NOT AVAILABLE** on `DSP-TEC-04` until a real producer exists |
| **T10** | **Task-started movement** | Request workflow step 2; Visual World Plan §7 | No `agent.task.*` for T2–T8 | **Stands:** **NOT AVAILABLE**; figures react only to the published result |

No conflicts with:
- the topology (one door `DR-L2` on `COR-N`; neighbours across hull);
- the access model, the door rules and the Visual Bible materials;
- the Character Registry roster (seven figures, one per runtime role; no merge);
- the Screen Registry display list (`DSP-TEC-01`…`07`) and its availability flags (`DSP-TEC-06`,
  `-07` = N);
- the StarNet exclusions (S16, S27, S33, S34).

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| TA-1 | Room name | **Closed:** "Technical Deck" kept; no rename |
| TA-2 | Chain order | **Closed:** L2 Technical → L1 Specialists, per the engine; documents aligned (§10, T2) |
| TA-3 | Who carries the technical crystal to L1 | **Closed:** T3 (Market Structure), one crystal per analysis, only on a real specialist `agent.task.started` |
| TA-4 | T3 / T4 at the chart table | **Closed:** yes, during their real result's display time |
| TA-5 | Screen Registry sources and indicator list | **Closed:** aligned (§10, T3–T5); all eight screen states respected |
| TA-6 | Supervisor visit trigger | **Closed:** only `run.failed` with `TECHNICAL_FAILED` or `SETUP_FAILED` |
| TA-7 | "No producer" notes for T2 and T8 | **Closed:** added |
| TA-8 | Layout | **Closed:** approved as drawn (§3.4) |
| TA-9 | Exact dimensions | **Open** (after the tile scale, VB-3) |
| TA-10 | Exact colour values | **Open** (visual production, VB-4) |
