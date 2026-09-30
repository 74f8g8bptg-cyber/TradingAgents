# Stellar Room Design Sheet — L6 Memory Archive (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; DM-1…DM-9 decided, DM-10 / DM-11 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L6` — Memory Archive · ACTIVE · public (Room Registry v2 §3.8) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Figures: `STELLAR_CHARACTER_REGISTRY.md` §3–§4, `STELLAR_CHARACTER_BIBLE_V1.md`. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Background: `STELLAR_LAYER_DESIGN.md`. Engine facts: `stellar/src/stellar/journal/store.py`, `runtime/ledger.py`, `runtime/orchestrator.py`, `execution/paper.py`, `execution/models.py`, `agents/roster.py`, `telemetry/catalogue.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | The archive only **shows** what the engine journaled. It has **no memory of its own**: no learning, no recall, no summaries, no embeddings, no search. The visual layer never writes, edits, ranks or interprets a record |

---

## 1. StarNet concept review (memory, history, provenance, resumable work)

**Method.** I read the audit (S10, S11, S41–S43, S46) and the local StarNet checkout at pinned
revision `fbddbf99` **read-only**:
- `sidecar/memory-store.js`: durable per-agent memory (notebook, todo, declined and pending
  proposals) and embedding vectors for a hybrid recall lane;
- `sidecar/run-journal.js`: an append-only, hash-chained active-run journal; "an intent without a
  durable result is never replayed";
- `sidecar/transcript-history.js`: immutable history segments with a manifest and term indexes;
- `sidecar/deliverable-provenance.js`: who made a deliverable, **derived from the run log, never
  authored by a model**;
- `sidecar/idempotency-ledger.js`: a repeated write is answered from the ledger and **labelled
  plainly as a replay**;
- `frontend/app/glass-comms.js` (per the audit): words live in a transcript, not in the world.

StarNet has real agent memory and recall; **Stellar does not**. Only structural ideas that match
Stellar's journal are taken. **Nothing is copied:** no art, layouts, interfaces, characters,
assets, dialogue or personality systems.

| StarNet concept | How Stellar adapts the structural idea | What Stellar rejects |
|---|---|---|
| **Append-only run journal; conservative recovery** (`run-journal.js`) | Stellar's journal is already append-only with contiguous `seq` and body hashes; a crashed run **resumes** from its journaled checkpoints (`run.resumed`). The replay index shows each run's real stages and marks a resume | Delta checkpoints of chat messages; torn-record forensics (different system) |
| **Provenance derived from the log, never authored** (`deliverable-provenance.js`) | Every archive entry shows its **ids chain** from the engine (trade → position → order → authorised intent → risk decision → proposal), never prose written for the screen | Contributor lists, project folders |
| **Plainly labelled replay** (`idempotency-ledger.js`) | "Replay" in L6 means **reading the recorded events of a past run in order**. It never re-executes anything and is labelled read-only | Re-sending or re-running work |
| **Immutable history, read one piece at a time** (`transcript-history.js`) | History is browsed as a list of real records (runs, closed trades); details open on request (NAV) | Term indexes, full-text search, segment manifests (Stellar has none) |
| **Words in a transcript, not in the world** (COMMS) | Record details are text on panels, never speech or floating text | Speech bubbles |
| **Durable per-agent memory, reflection proposals, embedding recall** (`memory-store.js`) | — | **Rejected: cannot be adapted honestly.** Stellar has no agent memory, reflection, recall or embeddings; drawing them would invent capabilities |
| Idle "sentience" engine, StarNet art | — | **Rejected** (S27, S33, S34) |

**Stellar original design (not from StarNet):** the archive terminal, the record shelf, the work
table, the panel layout, materials and lighting (§3).

---

## 2. Engine truth (what exists today)

### 2.1 What is persisted

- **Only the journal** (`journal/store.py`): one local SQLite file, append-only (UPDATE / DELETE
  refused), contiguous `seq` from 1, a body hash checked on every read. It stores **every event**,
  including:
  - run lifecycle: `run.started`, `run.stage.completed` (each stage checkpoint with its `refs` and
    `outputs`: snapshot, technical analysis, research / decision support, setup, proposal, risk,
    order), `run.resumed`, `run.completed`, `run.failed`;
  - analysis and debate: `analysis.created`, `debate.*`, `decision.research_plan.created`,
    `agent.task.*` (with outputs), `agent.llm_call.*`;
  - trading records: `setup.state.changed`, `trade.proposed`, `risk.*`, `order.*`, `position.*`,
    **`trade.closed`** (a full `TradeRecord`), account events.
- **Findings are persisted** inside their events: P2 contradiction findings in `debate.completed`,
  guard adjustments in `decision.research_plan.created`, risk evaluations in `risk.*`.
- **No retention, pruning, summarising or compaction** exists. Nothing is ever removed.
- The upstream `TradingMemoryLog` is **not read or written** by Stellar (decision D-10).

### 2.2 What can be retrieved (functions, not events)

| Function | Returns | Used by |
|---|---|---|
| `StellarJournal.read(...)` / `replay(since_seq)` | Events in journal order (filtered by type, run, sequence) | The runtime; the future read-only adapter |
| `RunLedger.run_ids()`, `events(run_id)`, `checkpoints(run_id)`, `record(run_id)` | Run ids; a run's events; its latest checkpoint per stage; a `RunRecord` (state, stage, failure, refs, stages, times) | `PaperRuntime.status()` / `runs()`; the future adapter |
| Execution read model (`execution/state.py`) | Orders, positions and closed trades folded from events | The runtime |

These are **reads on demand**. There is **no retrieval event** ("history requested", "record
recalled") in the catalogue.

### 2.3 Who reads history in the engine

| Reader | What it reads | Why |
|---|---|---|
| Runtime | Stage checkpoints | Resume a run; reuse a journaled result with the same fingerprint (idempotency) |
| Research pipeline, trader desk | Their own `agent.task.completed` by fingerprint | Never pay twice for the same LLM step |
| Setup lifecycle | The latest `setup.state.changed` of a setup | Current state |
| Execution state, reconciliation | `order.*`, `position.*`, `trade.closed` | Book state; integrity |

**No agent role reads history to decide anything.** No agent compares with past setups, learns
from past trades or retrieves "lessons".

### 2.4 Memory producers (none today)

| Capability | Event | Producer | Status |
|---|---|---|---|
| Post-trade review (`TradeReview`) | `memory.review.created` | Roster role L1 `post_trade_reviewer`: **no code** | **NOT AVAILABLE** |
| Settlement / attribution | `memory.outcome.settled` | Roster role L2 `attribution`: **no code** | **NOT AVAILABLE** |
| Stored comparable decisions | `memory.decision.stored` | none (upstream memory log not used, D-10) | **NOT AVAILABLE** |
| Reflections | `memory.reflection.written` | none | **NOT AVAILABLE** |
| R multiple of a trade | — | not computed anywhere | **NOT AVAILABLE** |

### 2.5 What a closed-trade record really contains (`trade.closed`)

Instrument, side, volume, stop loss, take profit, entry and exit fills, close reason
(`STOP_LOSS` / `TAKE_PROFIT` / `MANUAL`), slippage breach, opened / closed times, and the realised
P&L: `price_change` (always known) and the money `amount` **only when** its status is `KNOWN`
(otherwise `MISSING_ECONOMICS` / `MISSING_CONVERSION` / `MISSING_PRICE`). Ids: trade, position,
proposal, risk decision, evaluation fingerprint, intent, authorised intent, order, fill.

---

## 3. Room identity, relationships and architecture

### 3.1 Identity

| Aspect | Definition |
|---|---|
| **Purpose** | The station's **record room**: closed paper trades and the index of recorded runs, each traceable to its source events. It shows what happened; it does not remember, learn or advise |
| **It is not** | A trading room, a research room, a live-data room, a command room, or a storage room of servers |
| **Atmosphere** | Calm, precise, archival, trustworthy; information-dense but uncluttered |
| **Visual identity** | One archive terminal, one low **record shelf** that holds a crystal per real closed trade, a small reading table, and two legible panels |
| **Importance** | **Medium-low today** (most memory producers are missing); it becomes richer only when real producers exist |

### 3.2 Relationships

| Room | Relationship (engine-true) |
|---|---|
| **L9 Execution Bay** | **Upstream.** A real `trade.closed` produces the record; a record crystal (`PRP-006`) travels from L9 to L6 (L9 sheet §5, step 6) |
| **L7 Performance Lab** | **Neighbour** across non-walkable hull (no door). Its attribution role has no producer; no visits in V1 |
| **L4 Data Core** | Shares L6's north wall; **no door**. L4 shows the journal's health; L6 shows journal **content** (runs, trades) |
| **`H-CMD`** | The Agent Pipeline and P/L displays live there; L6 holds the history. No walk |
| Analysis rooms (`H-LAB`, L1–L3) | Their results are in the journal and appear in a run's replay details; no visits |

No new door or connection: L6 is reached only through `DR-L6` from `COR-S`.

### 3.3 Shape and entrance (approved; unchanged)

- **Shape:** a short rectangular room (size S; Floor Plan rev C §4: x 489–603, y 697–788, about
  114 × 91 px; **not frozen**). North of `COR-S`. North: **shared wall** with L4 (y ≈ 695), no
  door. East: L7, across **non-walkable hull** (Q4).
- **One door:** `DR-L6`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator, in
  the **south wall**, opening onto `COR-S`. **No other opening.** No lock, no new airlock, no hidden
  passage, no restricted marking (public room).
- **Cutaway:** the camera-facing walls are cut away (`WAL-008`); the door keeps a visible frame,
  threshold and opening (Visual Bible C4). No screens on a cut-away wall.

### 3.4 Schematic (not to scale; door at the bottom)

```
            north wall (shared with L4, no door)
   +---------------------------------------------+
   | DSP-MEM-01 trade history   DSP-MEM-02 run   |
   | (N wall, west)             replay index     |
   |                            (N wall, east)   |
   | CON-019 archive            STO-004 record   |
   | terminal (W wall)          shelf (E wall)   |
   | archive.terminal           archive.shelf    |
   |                                             |
   |        TBL-005 reading table                |
   |        archive.table_1                      |
   |        (DSP-MEM-04 surface, dark)           |
   | DSP-MEM-03 reviews                          |
   | (W wall, south; NOT AVAILABLE)              |
   +------------------[ DR-L6 ]------------------+
                        COR-S
```

- **North wall:** the two **working** displays (trade history, run replay index), readable from
  the door.
- **West:** the archive terminal (`CON-019`), with the reviews panel (NOT AVAILABLE) beside it.
- **East:** the low record shelf (`STO-004`).
- **Centre:** the small reading table (`TBL-005`); its surface is where comparable setups would
  appear (NOT AVAILABLE; §10, M6).

### 3.5 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`) |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium / light metallic trims** |
| Archive equipment | **Graphite** terminal body, shelf frame and table |
| Accent | **Restrained science blue** (SCI department) on the terminal edge and the shelf rails. Static; never a data state |
| Record shelf (`STO-004`) | **One low** shelf unit, waist to shoulder height, with fixed slots. **Not** an endless glowing library: crystals are small, matte, neutral; the shelf never fills the room |
| Record Crystals (`PRP-006`, registry "Review crystal"; DM-1) | Neutral and identical; they hold **no** memory or knowledge of their own (a marker for one journaled closed trade); they **never** light green or red for profit or loss (§10, M8). The outcome is text on `DSP-MEM-01` |

### 3.6 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a soft linear light over the shelf and terminal; not drawn in the cutaway |
| General | Calm, slightly warm neutral white; never dark |
| Work pool | `LGT-002` over the terminal only while a real record is being filed (§5) |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.7 Walkable areas and archive zones

| Zone | Anchor | Rule |
|---|---|---|
| Entry (inside the door) | — | The door approach tile stays empty |
| Terminal zone (west) | `archive.terminal` (Post-Trade Reviewer) | Reserved |
| Shelf zone (east) | `archive.shelf` | The filing point for a real record crystal (§5) |
| Reading zone (centre) | `archive.table_1` | **Unused in V1**: no event gives a reason to sit and read (§10, M10) |

---

## 4. Characters

### 4.1 Permanent occupant

| Aspect | Post-Trade Reviewer — `CHR-033` (L1 `post_trade_reviewer`, SCI) |
|---|---|
| Registry | Home `L6` · `archive.terminal`; visits L7; state `post_trade_review` |
| Engine | **No producer**: the role exists in the roster only; no `TradeReview`, no `memory.*` event |
| Workstation / position | `CON-019` at `archive.terminal`, facing the terminal |
| Work behaviour | **Never shown reviewing.** On a real `trade.closed` it may take the arriving record crystal and file it on the shelf (a filing action for a real record, not a review; DM-2). Otherwise `stand_idle` |
| Movement | Terminal ↔ `archive.shelf` for a real filing; seeded ambient via `COR-S` → `H-CMD` → `H-HAB` only when idle. **No L7 visits** (nothing to review) |

No dedicated "Memory Agent" exists and none is added. No runtime roles are merged.

### 4.2 Visitors

| Figure | When | Where | What it does |
|---|---|---|---|
| **Paper Execution Agent** `CHR-039` (E1) | Only after a real `trade.closed` | `DR-L6` → `archive.shelf` | Carries the record crystal (`PRP-006`) from L9 along `COR-S` and hands it over; returns to L9 (DM-3; `MP-EXEC` clarified in the Character Registry) |
| **Performance / Attribution** `CHR-034` | — | — | **No visit in V1** (no producer; registry lists an L6 visit) |
| **Supervisor** `CHR-003` | — | — | No real L6 event exists; no visit |
| **Medic persona** `CHR-041` | Only for a figure in a real `error` / `overloaded` state | Entry | Attends, leaves |

---

## 5. Engine-supported workflow

| # | Step | Event | Producer | Consumer | Data source | Visual reaction | Status |
|---|---|---|---|---|---|---|---|
| 1 | Result produced elsewhere | any journaled event (for example `trade.closed`, `run.completed`) | Engine components | Journal | Event | Nothing in L6 by itself | Yes |
| 2 | Result persisted | the same event, stored with its `seq` | Journal | — | Journal | Nothing drawn (persistence is not an animation) | Yes |
| 3 | Closed-trade record available | `trade.closed` | Paper Broker (L9) | L6 displays | Event (full `TradeRecord`) | E1 carries one neutral crystal L9 → `COR-S` → L6; `CHR-033` files it on `STO-004`; `DSP-MEM-01` adds the row | Yes (DM-2, DM-3) |
| 4 | Run record available | `run.completed` / `run.failed` / `run.stage.completed` / `run.resumed` | Runtime | `DSP-MEM-02` | RL (`RunLedger`) | The run appears / updates in the replay index (state, stage, failure, resume marker) | Yes |
| 5 | Another agent requests history | — | — | — | — | — | **NOT AVAILABLE** (no retrieval event; no agent reads history to decide) |
| 6 | Record retrieved for viewing | owner NAV on a display | UI (read-only) | Owner | Journal read | The record's details open (fields, ids chain, source events) | Yes, as an owner action (future UI) |
| 7 | Provenance displayed | — (part of the record) | — | Owner | The record's own ids and provenance fields | Ids chain shown as text; each id opens its source event | Yes |
| 8 | Post-trade review / lessons | `memory.review.created`, `memory.reflection.written` | — | — | — | `DSP-MEM-03` **NOT AVAILABLE · reviews** | **NOT AVAILABLE** |
| 9 | Comparable setups | `memory.decision.stored` | — | — | — | `DSP-MEM-04` **NOT AVAILABLE · memory store** | **NOT AVAILABLE** |
| 10 | Settlement / R multiple | `memory.outcome.settled` | — | — | — | R column **NOT AVAILABLE** | **NOT AVAILABLE** |
| 11 | Return to idle | filing display time ends | — | — | — | E1 back to L9; `CHR-033` at the terminal | Yes |

No memory search, recall, learning or "thinking over the past" is ever animated.

---

## 6. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Archive terminal** | `CON-019` | The reviewer's station; the room's working point | West wall | `archive.terminal` (reserved) | **Hero** |
| 2 | **Record shelf** | `STO-004` (registry "Crystal archive shelf") | One neutral crystal per real closed trade | East wall | `archive.shelf` (filing point) | High |
| 3 | **Record Crystal** | `PRP-006` (registry "Review crystal"; DM-1) | A closed-trade record on its way to the shelf | Carried L9 → L6; then on the shelf | Appears only with `trade.closed` | Medium |
| 4 | **Reading table** | `TBL-005` | Carries the (dark) comparable-setups surface | Room centre | `archive.table_1` (unused in V1) | Low |
| 5 | **Trade history panel** | `SCR-002` (`DSP-MEM-01`) | Closed paper trades | North wall, west | Look target; NAV | High |
| 6 | **Run replay index panel** | `SCR-003` (`DSP-MEM-02`) | Recorded runs; read-only replay | North wall, east | Look target; NAV | High |
| 7 | **Reviews panel** | `SCR-003` (`DSP-MEM-03`) | NOT AVAILABLE today | West wall, south | none | Low |
| 8 | **Comparable-setups surface** | `SCR-012` (`DSP-MEM-04`) | NOT AVAILABLE today; flat and dark, never a glowing hologram | On `TBL-005` | none | Low |
| 9 | Work pool light | `LGT-002` | Over the terminal during a real filing | Above the terminal | none | Low |
| 10 | Room plate, emblem | `SGN-001`, `DEC-006` | Name and department emblem | Corridor side of `DR-L6` | none | Low |

**Not used:** the journal archive rack `SRV-002` (listed for "L4, L6"): server racks would read as
fake storage, and the journal's health belongs to L4 (DM-6). **Not added:** no record table,
provenance console or retrieval station exists beyond these (§10, M11).

---

## 7. Screen design (Screen Registry v2 §5.7 is the authority)

| Display | Placement | Purpose | Actual source | Producer | Consumer | States |
|---|---|---|---|---|---|---|
| `DSP-MEM-01` Trade history | North wall, west | Closed paper trades: instrument, side, volume, entry / exit, close reason, price change, money P&L **only when `KNOWN`**, times; NAV opens the ids chain | `trade.closed` | Paper Broker | Owner | **NO CLOSED TRADES** (registry placeholder) until the first; P&L not known → **UNKNOWN** with the engine's reason (`MISSING_ECONOMICS` / `MISSING_CONVERSION` / `MISSING_PRICE`); R → **NOT AVAILABLE** (§10, M3); **LINK DOWN · age** |
| `DSP-MEM-02` Run replay index | North wall, east | Recorded runs: instrument, `as_of`, state, stage reached, failure, resume marker; NAV opens a **read-only** replay (the run's recorded events in order) | RL (`RunLedger`: run ids, records, events) | Runtime | Owner | **AWAITING DATA** until the first run; **LINK DOWN · age** |
| `DSP-MEM-03` Reviews & lessons | West wall, south | — | `memory.review.created`, `memory.reflection.written` | **none** | — | **NOT AVAILABLE · reviews** ("no post-trade reviewer is implemented") |
| `DSP-MEM-04` Comparable setups | Reading-table surface | — | `memory.decision.stored` | **none** | — | **NOT AVAILABLE · memory store** ("no memory store is implemented") |

**Screen rules for this room:**
- **Never invent** historical values, summaries, lessons, ratings, win rates, R multiples,
  similarity scores or "recommended" setups.
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). **LIVE** does not
  apply (history is recorded, not live). **STALE** does not apply (a closed record does not go
  stale). **MODE UNKNOWN** does not apply (no mode display).
- Profit and loss are **text**, never a green / red glow on crystals or shelves.
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- All displays are read-only. "Replay" never re-runs anything.

---

## 8. Agent life

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Carrying a real record | `trade.closed` | E1 (L9 → L6 → L9) | `walk`, `carry` (`PRP-006`) |
| Filing a real record | The crystal arrives | `CHR-033` (DM-2) | `walk` (terminal ↔ shelf), `stand_work` (display time) |
| Returning to the station | Filing done | `CHR-033` | `walk` |
| Idle | No event | `CHR-033` at the terminal; seeded ambient via `COR-S` → `H-CMD` → `H-HAB` | `stand_idle` |

No memory-search animation, no data streams, no "learning" or "reflecting" poses, no fake emotions.

---

## 9. Access (summary)

- **One explicit door** (`DR-L6`, `DOR-001`, south wall onto `COR-S`). No lock, no automatic door
  beyond the approved `DOR-001` behaviour, no new airlock, no hidden passage. No door to L4 or L7.
- Public room; entered only for a real reason (§4). `archive.terminal` is reserved to `CHR-033`.
- **Red** only from real system states.

---

## 10. Contradictions and owner decisions

| # | Topic | Documents | Engine | Resolution |
|---|---|---|---|---|
| **M1** | **Post-Trade Reviewer has no producer** | Character Registry: `CHR-033` ACTIVE, state `post_trade_review`; Visual World Plan §11; Layer Design §3.9: typed `TradeReview` per trade | Role L1 `post_trade_reviewer` exists in the roster only; `memory.review.created` has no producer | **Resolved (DM-2, DM-5):** files a real record crystal only; never shown reviewing, analysing, learning or reflecting. "No producer" note added to the Character Registry |
| **M2** | **Attribution has no producer** | Character Registry: `CHR-034` visits L6; Layer Design: settlement and attribution | Role L2 `attribution` has no code; `memory.outcome.settled` has no producer | **Resolved (DM-5):** no visit in V1; "no producer" note added |
| **M3** | **R multiple** | Screen Registry `DSP-MEM-01` (before): "outcome, R"; Visual World Plan §10.1 post-trade row | Not computed anywhere; `trade.closed` has no R. Even the planned reward:risk measure is undecided in the engine (`reward_risk` stays `None`; risk rule `min_reward_risk` is NOT CONFIGURED) | **Resolved (DM-4):** **NOT AVAILABLE**; never calculated or displayed. Screen Registry `DSP-MEM-01` aligned; the Visual World Plan §10.1 wording is a later task (§12) |
| **M4** | **Room purpose lists reviews and comparable setups** | Room Registry §3.8 purpose; Visual World Plan §10 room screens | No producers | **Resolved (DM-5):** "no producer" note on the Room Registry L6 card; the panels read **NOT AVAILABLE** |
| **M5** | **"Review crystal" naming** | Asset Registry `PRP-006` "Review crystal"; L9 sheet (before): "review crystal" | No review exists; the crystal marks a closed-trade record | **Resolved (DM-1):** presented as a neutral **Record Crystal**; registry name kept internally; it never implies memory or autonomous knowledge. L9 sheet wording aligned |
| **M6** | **Comparable-setups hardware** | Screen Registry: `DSP-MEM-04` on `SCR-012` | Asset Registry lists `SCR-012` for L2, L3 only | **Resolved (DM-7):** flat and dark on `TBL-005`, **NOT AVAILABLE** (no producer, no retrieval system) |
| **M7** | **Who carries the crystal / E1's L6 access** | L9 sheet (before): the crystal "leaves toward L6"; Layer Design §5.1: the reviewer goes "to the Execution Bay to collect a closed trade" | `MP-EXEC` = L9 + public spaces; `MP-FREE` excludes L9 | **Resolved (DM-3):** E1 carries the crystal L9 → L6 `archive.shelf` only after `trade.closed`. Clarified in the Character Registry (`MP-EXEC`, `CHR-039`) and the L9 sheet. No other courier, no memory agent |
| **M8** | **Crystals lit green / red** | Layer Design §2.3 | Red only for real system states; colour never carries data alone (Visual Bible C2, C7) | **Stands:** neutral crystals; outcome as text. Later task (§12) |
| **M9** | **Stale memory wording elsewhere** | Layer Design §3.1 ("Memory Archivist → L1 + L2"), §5.1 ("Execution Bay to collect a closed trade"), §2.3; Visual World Plan §10, §10.1, §11 (`memory.review.created` "crystal glows") | Superseded by the registries, the access model and the producer audit | **Stands:** later alignment task (DM-8, §12) |
| **M10** | **Reading-table anchor** | Room Registry anchor `archive.table_1` | No event gives a reason to sit and read | **Stands:** unused in V1 |
| **M11** | **Useful objects that do not exist** | Request categories: journal display, record table, provenance display, retrieval console | No such assets | **Stands:** not invented; provenance appears inside `DSP-MEM-01` / `-02` details |
| **M12** | **Retrieval events** | Request workflow: "another agent requests history" | No retrieval event; no agent reads history to decide | **Stands:** **NOT AVAILABLE** |
| **M13** | **Journal archive rack** | Asset Registry `SRV-002`: L4, L6 | Not in the L6 room card | **Resolved (DM-6):** unused; no server or storage workflow |

No conflicts with:
- the topology (one door `DR-L6` on `COR-S`; shared wall with L4 without a door; L7 across hull);
- the access model (with the `MP-EXEC` clarification), the door rules and the Visual Bible materials;
- the Character Registry roster (no Memory Agent added; no merge);
- the Screen Registry display list (`DSP-MEM-01`…`04`) and its availability flags (`-03`, `-04` = N);
- the StarNet exclusions (S27, S33, S34).

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| DM-1 | Record Crystal (M5) | **Closed:** neutral Record Crystal; registry name kept internally |
| DM-2 | Reviewer behaviour (M1) | **Closed:** files a real record crystal after `trade.closed`; never reviews, analyses, learns or reflects |
| DM-3 | Carrier and access (M7) | **Closed:** E1 carries L9 → L6; access clarified in the Character Registry |
| DM-4 | R multiple (M3) | **Closed:** **NOT AVAILABLE**; never calculated or displayed |
| DM-5 | "No producer" notes (M1, M2, M4) | **Closed:** added for the reviewer, Attribution, the four `memory.*` events and the unproduced L6 purposes |
| DM-6 | `SRV-002` (M13) | **Closed:** unused |
| DM-7 | Comparable-setups display (M6) | **Closed:** flat on `TBL-005`, **NOT AVAILABLE** |
| DM-8 | Stale memory wording (M8, M9) | **Closed as a later alignment task** (§12) |
| DM-9 | Layout (§3.4) | **Closed:** approved as drawn |
| DM-10 | Exact dimensions | **Open** (after the global tile scale, VB-3) |
| DM-11 | Exact colour values | **Open** (visual production, VB-4) |

---

## 12. Later alignment tasks (recorded, not done here)

- **Layer Design:** §2.3 (Memory Archive row: crystals that "light up green or red"); §3.1
  ("Memory Archivist → L1 + L2"); §3.9 (a typed `TradeReview` per closed trade presented as V1
  behaviour); §5.1 (the reviewer goes "to the Execution Bay to collect a closed trade"); the
  `memory.*` payloads carrying `r_multiple`.
- **Visual World Plan:** §10 (Memory Archive screens: "previous comparable setups", "post-trade
  reviews and lessons"); §10.1 (post-trade row: "Outcome, R multiple"); §11 (`memory.review.created`
  "crystal glows"; `memory.outcome.settled` wall updates).
- **R multiple in planning documents** (planned, never computed today; R stays NOT AVAILABLE on
  every display, DM-4): Foundation Plan §4.22 (post-trade review) and §10.1 (`trade.closed` fields
  listing an R multiple); Master Roadmap §9; Layer Design §6.1 (global metrics); Visual World Plan
  §10 (Performance Lab "R-multiple distribution") and §10.2 (illustrative worked example). The
  Performance Lab items belong to the future L7 sheet.
- These describe **planned** behaviour with no producer today; none of them is implemented.
