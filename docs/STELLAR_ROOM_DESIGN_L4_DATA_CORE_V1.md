# Stellar Room Design Sheet — L4 Data Core (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; DK-1…DK-9 decided, DK-10 / DK-11 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L4` — Data Core · ACTIVE · public (Room Registry v2 §3.7) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Figures: `STELLAR_CHARACTER_REGISTRY.md` §4, `STELLAR_CHARACTER_BIBLE_V1.md`. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Background: `STELLAR_LAYER_DESIGN.md`. Engine facts: `stellar/src/stellar/marketdata/snapshot.py`, `runtime/orchestrator.py`, `runtime/health.py`, `runtime/metrics.py`, `runtime/reconcile.py`, `runtime/ledger.py`, `journal/store.py`, `telemetry/catalogue.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | The Data Core room only **shows** what the engine recorded. The visual layer never fetches data, builds or rejects a snapshot, runs a health check on its own schedule, repairs anything, or shows a metric the engine does not produce |

---

## 1. StarNet concept review (storage, snapshots, status, event-driven updates)

**Method.** I read the audit (S9–S11, S41–S43, S46) and the local StarNet checkout at pinned
revision `fbddbf99` **read-only**:
- `frontend/app/world.js` (per the audit S10–S11): `linkDown` / `linkState` link-health honesty;
  `normalizeSnapshot` / `reconcileFromSnapshot` (an authoritative state snapshot reconciles the
  live view after a gap) and the TTL sweep of stale states;
- `frontend/app/floorstats.js`, `linewatch.js`: pure folds of real events into read-outs; a metric
  with no samples reports "unknown" and the HUD shows "—";
- `frontend/app/widgets.js` (S43): "—" until data, provenance, "no signal";
- `sidecar/checkpoint-store.js`: content-addressed snapshots whose id **is** the content hash,
  fail-open, no clock or randomness;
- `frontend/app/diagnostics.js`: a report assembled from real state only, never a placeholder.

StarNet stores agent workspaces and harness runs; it has **no market data, no journal of trading
events and no health model like Stellar's**. Only **structural ideas** are taken. **Nothing is
copied:** no art, layouts, characters, interfaces, assets, dialogue or personality systems.

| StarNet concept | How Stellar adapts the structural idea | What Stellar rejects |
|---|---|---|
| **Link-health honesty** (`linkDown`, S10) | `DSP-DCR-03` shows the UI's own link state and, on loss, **LINK DOWN · age**; every L4 screen freezes and greys | Link state presented as engine health |
| **Authoritative snapshot reconcile after a gap** (S11) | After a link gap, the room redraws from the journal / read-only snapshot, never from guesses | StarNet's `/api/state/snapshot` contents (Stellar's equivalent is open: audit Q8) |
| **Content-addressed snapshots** (id = content hash; `checkpoint-store.js`) | Stellar already does this: a snapshot carries its `series_hash`; run checkpoints carry fingerprints. The column labels a snapshot by its **id and hash**, never by an invented name | Git-backed workspace snapshots, rollback, restore (Stellar has no restore) |
| **Truthful read-outs** (`floorstats.js`, `widgets.js`: "—" until a real sample) | Each L4 display shows only engine values; displays without a producer read **NOT AVAILABLE · …** (adaptation A19) | Throughput, "yield", cache or queue gauges (no such Stellar metrics) |
| **Event-driven updates** (the view changes only on a real event) | The column pulses **only** on `snapshot.created`; nothing else animates it | Idle blinking, "activity" loops, data streams |
| **Report from real state only** (`diagnostics.js`) | Health and reconciliation panels show the engine's own `HealthReport` / `ReconciliationReport` fields, with their `checked_at` time | Fabricated support text or placeholder values |
| Save envelopes, station stores (S41, S42) | — | **Not used in the room:** UI preferences are not world data; the UI never posts state |
| Idle "sentience" engine, CRT look, StarNet station art | — | **Rejected** (S27, S33, S34) |

**Stellar original design (not from StarNet):** the snapshot column, the validator console, the
journal and reconciliation panels, the equipment arrangement, materials and lighting (§3).

---

## 2. Engine truth (what exists today)

### 2.1 Producers

| Capability | Producer (code) | Event / access | Status |
|---|---|---|---|
| **Verified market snapshot** | `build_verified_snapshot` (`marketdata/snapshot.py`); provenance `produced_by = data_validator` (T1). Built in the run's `MARKET_DATA` stage from a validated market-data response (and an optional quote) | `snapshot.created` (payload: `snapshot_id`, `timeframe`, `as_of`, `series_hash`, `last_bar_close_time`, **`freshness`**, `has_quote`; event `agent_id` = **`market_data`**, not `data_validator`) | **Available** (one per run and snapshot id; idempotent) |
| **Snapshot content** | Same | The run's `run.stage.completed` for `MARKET_DATA` (`outputs.snapshot`, `outputs.quote`): latest bar, quote, bar count, first / last bar times, source, mapping, quality, freshness, provenance | **Available** (RL) |
| **Market-data failure** | Runtime | `run.stage.completed` `MARKET_DATA` `FAILED` (`MARKET_DATA_FAILED` + detail) and `run.failed` | **Available** |
| **Snapshot rejected** | — | `snapshot.rejected`: **no producer** | **NOT AVAILABLE** |
| **Stale-feed detection** | — | `market.data.stale_detected`: **no producer**. Freshness exists only **inside** each snapshot (`FRESH` / `STALE` / `UNKNOWN` = no threshold configured / `NO_DATA`); nothing re-checks it between runs | **NOT AVAILABLE** (as a feed monitor) |
| **Per-source feed health** | — | No producer | **NOT AVAILABLE** |
| **Heartbeat** | — | `station.heartbeat.emitted`: **no producer** | **NOT AVAILABLE** |
| **Journal** | `StellarJournal` (`journal/store.py`): local **SQLite**, append-only (triggers refuse UPDATE / DELETE), contiguous `seq` from 1, a body hash checked on every read; `verify()` checks contiguity and hashes | Every event's `seq` and time | **Available** |
| **Runtime health** | `health(runtime, checked_at=…)` (`runtime/health.py`) → `HealthReport`: `status` (`HEALTHY` / `DEGRADED` / `BLOCKED` / `FAILED`), `reasons`, breaker, runs by state, reconciliation, `checked_at` | **On demand only**: a function call; **no event, no schedule**. For the displays: the future read-only adapter calls it on connection or on an explicit owner request (DK-5) | **Available** when called (HL) |
| **Reconciliation** | `reconcile(journal, …)` (`runtime/reconcile.py`) → `ReconciliationReport`: `ok`, `issues` (code, ref, detail), events / runs / orders / trades checked, unsettled trade ids | **On demand only** (also inside `health()`); same adapter rule (DK-5) | **Available** when called (RC) |
| **Runtime metrics** | `runtime_metrics(journal, runtime)` → runs, by state, completed, no setup, review required, rejected, failed, paper submissions, execution failures, stage timings, LLM totals | **On demand only** | Available (MT) but **not an L4 display** (used by other rooms' displays) |
| **Read-only `/snapshot` endpoint, UI link** | — | No HTTP server exists in the engine today; the UI link (LK) belongs to the future visual layer | **Future** (audit Q8) |

### 2.2 What is persistent

- **Only the journal.** Every event, including each run's stage checkpoints
  (`run.stage.completed` with their `outputs`), is stored once and never changed or deleted.
- **There is no retention or pruning behaviour**, no separate database, no cache service, no
  backup or automatic recovery process. Re-running a run re-uses journaled results by fingerprint;
  that is idempotency, not recovery.

### 2.3 Who consumes Data Core information (engine consumers)

| Consumer | Uses | Room |
|---|---|---|
| Technical engine (T3–T5) | The snapshot's series (same run) | L2 |
| Setup evaluation (T6) and the proposal builder (P1) | The verified snapshot (`TraderInputs.market`) | L2, `H-CMD` |
| Risk Engine (P3) | Snapshot freshness and quote integrity rules | L10 |
| Execution Checker (P4) | Market input / quote recency | L9 |
| `health()` | Reconciliation, breaker, runs, configuration | (owner / UI read) |

These are **in-process data reads within one run**. No agent walks to L4 to "fetch" anything, and
no event says "consumed".

---

## 3. Room identity, relationships and architecture

### 3.1 Identity

| Aspect | Definition |
|---|---|
| **Purpose** | The foundational information layer: the verified market snapshot each run starts from, its freshness, the journal every other room reads from, and the engine's own health and reconciliation reports |
| **It is not** | Main Command, the Research Lab, the Technical Deck, the Market Specialists room, the Debate Chamber, Risk Control or Execution. No analysis, decision or order happens here |
| **Atmosphere** | Quiet, clean, precise, technical, information-focused. **Not** a server-room cliché, cyberpunk, a bunker or a wall of blinking lights |
| **Visual identity** | One calm **snapshot column** at the centre (the registry's "reactor column"), a single validator console facing it, two low racks, and a few legible status panels |
| **Importance** | **Medium.** Small and short, but foundational: every run's first step is recorded here, and its health panels are the owner's view of system integrity |

### 3.2 Relationships

| Room | Relationship (engine-true) |
|---|---|
| **L2 Technical Deck** | **Downstream (first consumer).** The technical stage uses each run's snapshot. Data only; no walk (L2's `DSP-TEC-01` shows freshness from `snapshot.created`) |
| **`H-CMD`** | **Downstream.** The setup and proposal use the snapshot; the Agent Pipeline (`DSP-CMD-04`) lights its first stage from the run's events |
| **L10 Risk Control** | **Downstream.** Risk rules read the snapshot's freshness and quote; data only |
| **L9 Execution Bay** | **Downstream.** Reconciliation of orders and trades is shown **here** (`DSP-DCR-05`), not in L9 (L9 sheet §5) |
| **L6 Memory Archive** | Shares L4's south wall; **no door** between them. Both read the same journal; no hand-off |
| **`H-LAB`** | **No direct link.** Research validation (V1–V4) happens in `H-LAB`, not here (§10, K6) |

No new door or connection: L4 is reached only through `DR-L4` from `COR-N`.

### 3.3 Shape and entrance (approved; unchanged)

- **Shape:** a short rectangular room (size S; Floor Plan rev C §4: x 489–603, y 588–694, about
  114 × 106 px; **not frozen**). South of `COR-N`, opposite L1 / L2. East: L5 (reserved), across
  **non-walkable hull** (Q4). South: **shared wall** with L6 (y ≈ 695), no door.
- **One door:** `DR-L4`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator,
  in the **north wall**, opening onto `COR-N`. **No other opening.** No lock, no new airlock, no
  hidden passage, no restricted marking (public room).
- **Cutaway:** the camera-facing walls are cut away (`WAL-008`); the door keeps a visible frame,
  threshold and opening (Visual Bible C4). No screens are placed on a cut-away wall.

### 3.4 Schematic (not to scale; door at the top)

```
                           COR-N
   +------------------[ DR-L4 ]-------------------+
   | DSP-DCR-02 feed    (entry)          DSP-DCR-06|
   | health (N wall,    datacore.visitor heartbeat |
   | west of the door)                  (N wall,   |
   |                                     east)     |
   | DSP-DCR-03 journal                   SRV-001  |
   | (W wall)          EQP-001 snapshot   server   |
   |                   column + SCR-006   rack     |
   | DSP-DCR-04        (DSP-DCR-01)       (E wall) |
   | runtime health        ^               SRV-002 |
   | (W wall)              |               journal |
   |              CON-018 validator        archive |
   | CON-027 recon. console (faces         rack    |
   | + DSP-DCR-05   north to the column)  (E wall) |
   | (SW corner)  datacore.reactor_console         |
   |                              datacore.rack_check
   +==== shared wall with L6 (cut away, no door) ==+
```

- **Centre: the snapshot column** (`EQP-001`) with its display (`SCR-006`, `DSP-DCR-01`).
- **South of it: the validator console** (`CON-018`), facing north toward the column and the door.
- **East wall: the two racks**, low and orderly, with `datacore.rack_check` in front of them.
- **West wall: the system panels** (journal, runtime health) and, in the south-west corner, the
  reconciliation console (`CON-027`) with its own display.
- **North wall: feed health** (west of the door) and the heartbeat panel (east of the door).

### 3.5 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`); a thin titanium ring inlay around the column (walk-over) |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium / light metallic trims** |
| Technical elements | **Graphite** console bodies, rack fronts and screen bezels |
| Accent | **Engineering gold on charcoal** (OPS department; Room Registry). Static; never a data state |
| Data / Snapshot Column (`EQP-001`, registry "Reactor column"; DK-2) | A slim, matte graphite column with a soft translucent band and titanium rings. Drawn as an **information column**, **not** a power reactor: no glowing core, no energy arcs, no hazard stripes (§10, K8) |
| Racks (`SRV-001`, `SRV-002`) | Two **low**, closed, off-white-and-graphite cabinets. Small, steady status marks only; **no rows of blinking LEDs** |

### 3.6 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a round light panel over the column; not drawn in the cutaway |
| General | Clean neutral white, slightly warm; quiet and even. Never dark |
| Column pulse | One soft pulse **per real `snapshot.created`**, then steady. Between snapshots the band shows the latest snapshot's **age**; when its freshness is `STALE` the band dims to **hatched grey** with the word **STALE** (text + icon, not colour alone) |
| Work pool | `LGT-002` over the validator console only during the display time after a real snapshot (§5) |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.7 Walkable areas and equipment zones

| Zone | Who | Rule |
|---|---|---|
| Entry, with `datacore.visitor` just inside the door | Visitors with a real reason (§4.2) | The door approach tile stays empty |
| Column zone (centre) | Nobody stands on the column's footprint | A 1-tile walkway rings the column |
| Console zone (south) | T1 at `datacore.reactor_console` (reserved) | — |
| Rack zone (east) | `datacore.rack_check` | **Unused in V1** (no real event gives a reason to go there; §10, K9) |
| System panel zone (west, south-west) | Look targets; `CON-027` is read from `datacore.visitor` (DK-4) | Not a workstation (no work anchor) |

---

## 4. Characters

### 4.1 Permanent occupant (Character Registry §4)

L4 has **one** dedicated character. No other occupant is added, and no role is merged.

| Aspect | Data Validator — `CHR-035` (T1 `data_validator`, OPS) |
|---|---|
| Workstation | `CON-018` validator console at `datacore.reactor_console` (reserved) |
| Normal position | Standing at the console, facing north toward the column |
| Movement pattern | Stays in L4. Seeded ambient via `COR-N` → `H-CMD` → `H-HAB` **only when idle**; a real snapshot pulls it back (work over idle, adaptation A13) |
| Work behaviour | **No task events exist for T1.** On a real `snapshot.created`: `stand_work` for a fixed **display time** (it marks the recorded result; it does not imitate an ongoing check), then `look_screen` at the column. Otherwise `stand_idle` |
| Validation failure | On a real `MARKET_DATA_FAILED` (`run.stage.completed` / `run.failed`): the console shows the engine's failure detail as text; no red flash (there is no `snapshot.rejected` producer) |
| Interaction with other rooms | **Data only.** No hand-off walks: consumers read the snapshot in-process (§2.3). No `PRP-*` prop exists for a snapshot hand-off |
| Visiting / leaving | Leaves only for seeded ambient while idle; never "delivers" a snapshot |

### 4.2 Visitors

| Figure | When | Where | Behaviour |
|---|---|---|---|
| **Supervisor** `CHR-003` | Only on a real `run.failed` with `MARKET_DATA_FAILED` (DK-6) | `datacore.visitor` | Stands, reads the panels, leaves |
| **Medic persona** `CHR-041` | Only for a figure in a real `error` / `overloaded` state | Entry | Attends, leaves (T1 emits no task failure, so this is rare) |
| Anyone else | — | — | Not routed in. No health check, reconciliation or journal read is a reason to visit (they are not events) |

---

## 5. Engine-supported workflow

| # | Step | Event | Producer | Consumer | Data source | Visual reaction | Status |
|---|---|---|---|---|---|---|---|
| 0 | No snapshot yet | — | — | — | — | Column steady and unlit band; `DSP-DCR-01` **AWAITING DATA**; T1 `idle` | Yes |
| 1 | Market data requested / fetched | — | (runtime, in-process) | — | — | Nothing drawn: no fetch event exists (no "beams") | **NOT AVAILABLE** |
| 2 | Snapshot recorded | `snapshot.created` | Runtime (`agent_id` `market_data`); snapshot provenance `data_validator` (T1) | L2 (T3–T5), then T6 / P1, P3, P4 in the same run | Event + `MARKET_DATA` checkpoint (RL) | One column pulse; `DSP-DCR-01` lists time, instrument, timeframe, snapshot id, bar close, `has_quote`; T1 `stand_work` for the display time | Yes |
| 3 | Freshness shown | `snapshot.created` (`freshness`) | Same | L2 `DSP-TEC-01`, L10 rules | Event | Band reads the engine word: `FRESH` / **STALE** / **UNKNOWN** (no threshold configured) / `NO_DATA` | Yes (per snapshot only) |
| 3a | Freshness re-checked between runs | — | — | — | — | Only the **age** grows; no new verdict is invented | **NOT AVAILABLE** (no stale detector) |
| 4 | Snapshot rejected | `snapshot.rejected` | — | — | — | — | **NOT AVAILABLE** |
| 4a | Market-data stage failed | `run.stage.completed` `MARKET_DATA` `FAILED`; `run.failed` | Runtime | Owner / Supervisor | Events | No pulse; T1 console shows the failure detail; Supervisor may visit | Yes |
| 5 | Another agent consumes the snapshot | — (in-process read) | — | L2, `H-CMD`, L10, L9 | — | Nothing drawn in L4; the consumer rooms show their own results | **NOT AVAILABLE** as a visible hand-off |
| 6 | Journal advances | every event (`seq`) | Journal | UI | Event stream | `DSP-DCR-03`: latest `seq` and time; link state | Yes (for the UI once it exists) |
| 7 | Health / reconciliation report | — (on-demand call) | `health()`, `reconcile()` | Owner / UI | HL, RC | `DSP-DCR-04` / `-05` show the last report with its `checked_at` and age (no STALE verdict: no threshold exists) | Yes when called (on connection or explicit owner request; DK-5) |
| 8 | Heartbeat | `station.heartbeat.emitted` | — | — | — | — | **NOT AVAILABLE** |
| 9 | Return to normal | display time ends | — | — | — | Column steady; T1 `stand_idle` | Yes |

Nothing is invented: no fetch beams, data streams, request-volume brightness, throughput numbers,
retention, backups or recovery.

---

## 6. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Data / Snapshot Column** (registry "Reactor column") | `EQP-001` | Pulses **only** per `snapshot.created`; shows freshness and age | Room centre | Look target | **Hero** |
| 2 | **Column display** | `SCR-006` (`DSP-DCR-01`) | The snapshot list | Beside the column, one visual unit (DK-3) | Look target | High |
| 3 | **Validator console** (registry "Reactor control console") | `CON-018` | T1's station | South of the column, facing north | `datacore.reactor_console` (R: T1) | High |
| 4 | **Server rack** | `SRV-001` | Quiet equipment presence (no data meaning) | East wall | `datacore.rack_check` (unused in V1) | Low |
| 5 | **Journal archive rack** | `SRV-002` | Visual anchor for the journal (the journal panel carries the data) | East wall | as above | Low |
| 6 | **Reconciliation console** | `CON-027` + `SCR-004` (`DSP-DCR-05`) | Reconciliation report | South-west corner | Look target; read from `datacore.visitor` (DK-4) | Medium |
| 7 | **Feed health panel** | `SCR-002` (`DSP-DCR-02`) | NOT AVAILABLE today | North wall, west of the door | none | Low |
| 8 | **Journal & event-stream panel** | `SCR-003` (`DSP-DCR-03`) | Journal sequence and link | West wall, north | Look target | Medium |
| 9 | **Runtime health panel** | `SCR-003` (`DSP-DCR-04`) | `HealthReport` | West wall, south | Look target | Medium |
| 10 | **Heartbeat panel** | `SCR-011` (`DSP-DCR-06`) | NOT AVAILABLE today | North wall, east of the door | none | Low |
| 11 | Work pool light | `LGT-002` | Over `CON-018` during the display time | Above the console | none | Low |
| 12 | Room plate, emblem | `SGN-001`, `DEC-006` | Name and department emblem | Corridor side of `DR-L4` | none | Low |

**Not used:** the optional crate stack `STO-002` (a storage cliché with no data meaning) and the
optional overhead cable tray `SRV-004` (visual noise in a small room); DK-7. The data conduit
`SRV-003` may appear **only** inside the non-walkable hull gap to the east, never inside the room.
**Not added:** no snapshot hand-off prop, no "data access station", no storage wall (§10, K10).

---

## 7. Screen design (Screen Registry v2 §5.6 is the authority)

| Display | Location | Purpose | Source / producer | States |
|---|---|---|---|---|
| `DSP-DCR-01` Snapshot pulse | Column (`SCR-006`) | Recent snapshots: time, instrument, timeframe, snapshot id, last bar close, quote present or not, freshness word | `snapshot.created` (runtime; provenance T1); detail from the `MARKET_DATA` checkpoint (RL) | **AWAITING DATA** until the first snapshot; the engine's freshness words; **STALE** when the snapshot says so; **UNKNOWN** when no threshold is configured; **LINK DOWN · age** |
| `DSP-DCR-02` Feed health | North wall, west | — | `market.data.stale_detected`, `snapshot.rejected`: **no producers** | **NOT AVAILABLE · feed health** ("no feed monitor exists; freshness is only recorded per snapshot") |
| `DSP-DCR-03` Journal & event-stream health | West wall, north | Latest journal `seq`, last event time, the UI's link state | Event sequence; LK (UI) | **AWAITING DATA** before the first event; **LINK DOWN · age** on link loss |
| `DSP-DCR-04` Runtime health | West wall, south | `status` (`HEALTHY` / `DEGRADED` / `BLOCKED` / `FAILED`) as a word + icon, its `reasons`, breaker status, runs by state, `checked_at` | `health()` (HL, on demand) | **AWAITING DATA** until a report exists; otherwise the report with its `checked_at` and age (no STALE verdict; §12); **LINK DOWN · age** |
| `DSP-DCR-05` Reconciliation | On `CON-027` (`SCR-004`) | `ok` / issues (code, ref, detail), counts checked, unsettled trade ids | `reconcile()` (RC, on demand; also inside HL) | **AWAITING DATA**; otherwise the report with its `checked_at` and age; **LINK DOWN · age** |
| `DSP-DCR-06` Heartbeat | North wall, east | — | `station.heartbeat.emitted`: **no producer** | **NOT AVAILABLE · heartbeat** ("the engine emits no heartbeat") |

**Screen rules for this room:**
- **Never invent** metrics, rates, latencies, disk use, request counts, uptime, feed status or
  health values. Status colours always come with a word and an icon.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **LIVE** does not
  apply (snapshots are per run, never live quotes). **MODE UNKNOWN** does not apply (no mode
  display). **NOT CONFIGURED** applies only to an instrument slot that is not an enabled instrument.
- `HEALTHY` is the engine's word for its own report, shown with the report time; it is never
  shown without a real report.
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- All displays are read-only; no "run check", "repair" or "reconcile now" affordance.

---

## 8. Agent life

All activity comes from **real events** or **normal idle behaviour**. There is **no emotional
simulation**, no fake "busy" animation and no data-processing animation without a real event.

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Checking the console | A real `snapshot.created` (fixed display time) | T1 | `stand_work` |
| Reviewing the column / a panel | Same | T1 | `look_screen` |
| Reading a failure | A real `MARKET_DATA_FAILED` | T1 | `look_screen` |
| Walking to the workstation | Returning from ambient on a real snapshot | T1 | `walk` |
| Real data hand-off | — (none exists) | — | — |
| Idle | No event | T1 at the console, or seeded ambient via `COR-N` → `H-CMD` → `H-HAB` | `stand_idle` |

---

## 9. Access (summary)

- **One explicit door** (`DR-L4`, `DOR-001`, north wall onto `COR-N`). No lock, no automatic door
  beyond the approved `DOR-001` behaviour, no new airlock, no hidden passage. No door to L6.
- Public room; entered only for a real reason (§4). `datacore.reactor_console` is reserved to T1.
- **Red** only from real system states (for example a `FAILED` health report, with word + icon).

---

## 10. Contradictions and owner decisions

| # | Topic | Documents | Engine | Resolution |
|---|---|---|---|---|
| **K1** | **Snapshot event attribution** | Character Registry / Visual World Plan: T1 builds the snapshot | `snapshot.created` carries `agent_id` **`market_data`** (not a roster id); T1 appears as the snapshot's recorded producer (`produced_by = data_validator`) in the `MARKET_DATA` checkpoint | **Resolved (DK-1):** the pulse is credited to `CHR-035` through the recorded producer. The engine truth stays: the event's agent id is `market_data` |
| **K2** | **Rejection flash and stale alerts** | Visual World Plan §11: `snapshot.rejected` "red flash", `market.data.stale_detected` "conduit flicker"; Layer Design §3.4 T1 row: "red flash on rejection" | Neither event has a producer | **Stands:** not drawn; `DSP-DCR-02` **NOT AVAILABLE**. The stale wording elsewhere is a later alignment task (DK-8) |
| **K3** | **Health / reconciliation are not events** | Screen Registry: HL / RC sources, placeholder **STALE** for `DSP-DCR-04` / `-05` | `health()` and `reconcile()` are on-demand calls; no schedule; no age threshold exists | **Resolved (DK-5):** future read-only adapter, called on connection or on an explicit owner request. No polling, heartbeat, automatic check or invented threshold. The displays show the report's `checked_at` and age; **no STALE verdict** is computed for them. The Screen Registry's **STALE** placeholder for these two displays remains a registry wording to revisit (§12) |
| **K4** | **Reconciliation console missing from the room card** | Asset Registry: `CON-027` in L4; Screen Registry: `DSP-DCR-05` on `CON-027` | Room Registry §3.7 furniture did not list it | **Resolved (DK-4):** added to the Room Registry L4 card as look-only furniture, read from the existing `datacore.visitor` anchor (no new anchor, no work anchor) |
| **K5** | **Request-volume reactor and fetch beams** | Layer Design §2.3 Data Core row: "reactor column that brightens with request volume"; §2.1: "every data fetch is drawn as a beam"; the `FETCHING` state | No request-volume measure; no fetch event (`agent.tool_call.*` has no producer) | **Stands:** not drawn. Later alignment task (DK-8) |
| **K6** | **Research validators in the Data Core** | Layer Design: V1–V4 and "a verification bench" in the Data Core; "Data Core Keeper → T1 + O2" | Room / Character Registries: V1–V4 live in `H-LAB`; T1 and O2 are separate figures | **Stands:** not placed in L4; roles not merged. Later alignment task (DK-8) |
| **K7** | **Heartbeat and feed health** | Screen Registry `DSP-DCR-02`, `-06` | No producers (registry already marks `N`) | **Stands:** **NOT AVAILABLE** with an honest line |
| **K8** | **"Reactor" naming** | Asset Registry `EQP-001` "Reactor column", `CON-018` "Reactor control console"; anchor `datacore.reactor_console` | The object shows snapshots, not power | **Resolved (DK-2):** presented as the **Data / Snapshot Column** and the **Validator Console**; registry IDs and names kept internally; never implies a power reactor |
| **K9** | **Rack-check anchor** | Room Registry anchor `datacore.rack_check` | No event gives anyone a reason to check a rack | **Stands:** unused in V1 (no fake maintenance) |
| **K10** | **Useful objects that do not exist** | Request categories: snapshot hand-off / access station, storage | No such assets; consumers read in-process | **Stands:** not invented |
| **K11** | **Two columns in a small room** | `DSP-DCR-01` is on `SCR-006`; `EQP-001` is also a column | Both are registry assets for L4 | **Resolved (DK-3):** `SCR-006` stands beside `EQP-001` as one coherent visual unit |
| **K12** | **Read-only `/snapshot` and the UI link** | Screen Registry SN / LK sources | No HTTP server or UI link exists yet (audit Q8 open) | **Stands:** future; `DSP-DCR-03` link state applies once the visual layer exists |

No conflicts with:
- the topology (one door `DR-L4` on `COR-N`; shared wall with L6 without a door; L5 across hull);
- the access model, the door rules and the Visual Bible materials;
- the Character Registry (one T1 figure; no merge);
- the Screen Registry display list (`DSP-DCR-01`…`06`) and its availability flags (`-02`, `-06` = N);
- the StarNet exclusions (S27, S33, S34, S42).

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| DK-1 | Snapshot attribution (K1) | **Closed:** credited to `CHR-035` via the recorded producer; event agent id stays `market_data` |
| DK-2 | Reactor objects (K8) | **Closed:** Data / Snapshot Column and Validator Console; registry IDs / names kept internally |
| DK-3 | Column display (K11) | **Closed:** beside the column, one visual unit |
| DK-4 | `CON-027` in the Room Registry (K4) | **Closed:** added; look-only, read from `datacore.visitor` |
| DK-5 | Health / reconciliation calls (K3) | **Closed:** future read-only adapter, on connection or explicit owner request; no polling, heartbeat, automatic check or invented threshold |
| DK-6 | Supervisor visit trigger | **Closed:** only a real market-data-related `run.failed` (`MARKET_DATA_FAILED`) |
| DK-7 | `STO-002` crate stack, `SRV-004` cable tray | **Closed:** not used |
| DK-8 | Stale Layer Design / Visual World Plan wording (K2, K5, K6) | **Closed as a later alignment task:** not changed in this sheet's commit |
| DK-9 | Layout (§3.4) | **Closed:** approved as drawn |
| DK-10 | Exact dimensions | **Open** (after the global tile scale, VB-3) |
| DK-11 | Exact colour values | **Open** (visual production, VB-4) |

---

## 12. Later alignment tasks (recorded, not done here)

- Layer Design §2.1, §2.3 and §3.4, and Visual World Plan §11 (Data Core rows): remove the
  request-volume reactor, fetch beams, rejection flash, stale-feed flicker, V1–V4 in the Data Core
  and the "Data Core Keeper" merge (K2, K5, K6).
- Screen Registry §5.6: the **STALE** placeholder for `DSP-DCR-04` / `-05` implies an age threshold
  that the engine does not define (K3).
