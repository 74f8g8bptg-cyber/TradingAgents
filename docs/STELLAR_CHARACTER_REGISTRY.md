# Stellar Agents — Character Registry v2

| | |
|---|---|
| **Status** | v2.0, rebuilt on Floor Plan revision C. Original characters; no sprites or portraits exist yet |
| **Builds on** | Visual World Plan §4–§7 (agent model, personas, states, movement); engine roster `stellar/src/stellar/agents/roster.py` (codes and `technical_id`s, read-only); `STELLAR_ROOM_REGISTRY.md` v2; `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Identity rule** | `technical_id` is the only key in events, schemas and the journal. Character IDs, names, uniforms and portraits are **UI-level only** (Visual plan §4) |
| **Replaces** | v1 (rooms, lifts and movement classes of the stacked-deck model). IDs are kept; changed rows are marked; retired IDs are never reused |

---

## 1. Originality rules (unchanged)

- All names are **original** Stellar names. Familiar crew-role archetypes are fine (captain, first
  officer, science officer, chief engineer, medic, archivist); **no** actor likeness, franchise
  name, franchise uniform cut, rank insignia, arrowhead badge, logo or LCARS styling.
- Characters are slightly stylised humanoids (about 6–7 heads tall) with clear silhouettes and
  varied builds, skin tones, hair and ages.
- Nothing is reused from StarNet: no sprites, skins, names or idle "personality" (adaptation A30, A31).

## 2. Departments and uniforms

| Department | Code | Colour family | Shape icon | Who |
|---|---|---|---|---|
| Command / Leadership | `CMD` | **red / burgundy** | hexagon | Portfolio Manager, Research Manager, Supervisor, Central Trader, Trade Proposal Builder |
| Science / Research / Technical | `SCI` | **blue** | circle | shared research team, validators, macro, market specialists, technical agents, debaters, review and attribution, future lab scientists, the future Coach (advisory) |
| Risk / Engineering / Operations | `OPS` | **gold / yellow on charcoal** | square | data validation, contradiction and risk checks, execution, operational wellbeing monitor personas |
| Synthetic / System | `SYN` | **white / cyan / metallic** | diamond | service drones and system characters |

**Colour grammar:** gold is reserved for roles with deterministic engineering, risk or operations
duties. Advisory LLM roles (for example the risk debaters, and the future Coach) wear
blue. A uniform colour never implies an authority the agent does not have. Colour tokens
`uniform.cmd` / `.sci` / `.ops` / `.syn` are set during art production. The shape icon always
accompanies the colour.

**Uniform design (original):**
- a charcoal two-tone base garment;
- department colour on the shoulder yoke and cuffs;
- the shape icon on the chest;
- **no rank insignia** (titles appear only in HUD text);
- synthetic characters wear metallic / white shells with cyan light lines.

---

## 3. Movement and access classes (logical access, owner decision Q10)

The geometry is open: every door is ordinary (Topology §3). Access is enforced as a **per-class
room permission** in navigation and as **restricted anchors**. It is never enforced by walls,
lifts or airlocks.

| Class | May enter | Never |
|---|---|---|
| `MP-FREE` | Corridors, the public zones of all hubs, every **active public** room when a real event gives a reason, and its home room | L9, L10, reserved rooms, restricted anchors of other roles |
| `MP-COURIER` | `MP-FREE` + **L10 `risk.intake` zone** (to drop a proposal after `trade.proposed`) | `risk.core`, `risk.outbox`, L9 |
| `MP-RISK` | L10 (all zones), plus public spaces for real cooldowns and ambient when idle | L9; other roles' anchors |
| `MP-EXEC` | L9 (all zones), plus public spaces. The Paper Execution Agent also enters **L10 `risk.outbox`** to collect an order capsule (only after `risk.approved` + `order.created`) | `risk.intake`, `risk.core` |
| `MP-SUPERVISOR` | `MP-FREE` + the entry zones of L9 and L10 (event-driven visits) | restricted anchors; the inner zones of L9 and L10 |
| `MP-MEDIC` | `MP-FREE` + the entry zone of any active room, including L9 and L10, to attend an agent in `error` / `overloaded` (from a real event) | restricted anchors |
| `MP-HOST` | `H-HAB` only | everything else |
| `MP-NONE` | not rendered | — |

**Rules shared by every class** (Visual plan §1.5–§1.6, §12; adaptation A8, A12, A13, A20):
- **Work over idle:** a real task always pre-empts ambient behaviour, and the agent re-paths to its
  workstation.
- **Operational right of way:** in corridors and on hub walkways, operational agents pass before
  ambient ones. Ties are broken deterministically. A jam gives up after a timeout and falls back
  to a fade.
- **Badges first:** the state badge updates at once; walking is cosmetic and follows the state
  change. If the walk is late, the agent fades out and in at the destination.
- **Ambient** only in `idle`, only inside the agent's allowed zones (the Habitat, or its own room),
  seeded and replayable. There is **no emotion language** (A11, A14).
- **Real cooldowns** (`agent.resting`) go to `habitat.recovery` pods. Nobody is confined to a room
  any more, so the v1 "rest in place" exception is removed.

---

## 4. Character roster

The standard state set of every rendered character is `idle`, `walking`, `waiting`, `paused`,
`error`, `offline`, `overloaded` and `resting` (Visual plan §6.2). "Role states" lists the
additional working states.

| ID | Name | Role (code · technical id) | Dept | Home room · anchor | Other rooms | Role states | Class | Status | v2 change |
|---|---|---|---|---|---|---|---|---|---|
| `CHR-001` | Captain Aurelia Voss | Portfolio Manager (U8 · `portfolio_manager`) | CMD | `H-CMD` · `command.chair` | L3 judge seat; ambient | reviewing | MP-FREE | ACTIVE | room |
| `CHR-002` | Commander Idris Kael | Research Manager (U3 · `research_manager`) | CMD | `H-CMD` · `command.table_head` | L3 `debate.judge_seat` | reviewing, analysing | MP-FREE | ACTIVE | room |
| `CHR-003` | First Officer Mara Solen | Supervisor (O1 · `supervisor`) | CMD | `H-CMD` · `command.console_ops` | every active room (entry zones of L9 / L10) | monitoring | MP-SUPERVISOR | ACTIVE | room, class |
| `CHR-004` | Lt. Cmdr. Rook Halden | **Central Trader** (U4 · `trader`) | CMD | `H-CMD` · `command.console_trader` | ambient | analysing | MP-FREE | ACTIVE | role wording (§6) |
| `CHR-005` | Ensign Tavi Marr | Trade Proposal Builder (P1 · `trade_proposal_builder`) | CMD | `H-CMD` · `command.console_proposal` | L10 `risk.intake_drop` | analysing | MP-COURIER | ACTIVE | route |
| `CHR-006` | Lt. Leo Brask | Bull Researcher (U1 · `bull_researcher`) | SCI | `L3` · `debate.podium_bull` | ambient | debating | MP-FREE | ACTIVE | room |
| `CHR-007` | Lt. Ursa Venn | Bear Researcher (U2 · `bear_researcher`) | SCI | `L3` · `debate.podium_bear` | ambient | debating | MP-FREE | ACTIVE | room |
| `CHR-008` | Ensign Rhea Vantor | Aggressive Risk Debater (U5 · `risk_aggressive`) | SCI | `L3` · `debate.podium_risk_1` | ambient | debating | MP-FREE | ACTIVE | room |
| `CHR-009` | Ensign Hollis Crane | Conservative Risk Debater (U6 · `risk_conservative`) | SCI | `L3` · `debate.podium_risk_2` | ambient | debating | MP-FREE | ACTIVE | room |
| `CHR-010` | Ensign Tamsin Ly | Neutral Risk Debater (U7 · `risk_neutral`) | SCI | `L3` · `debate.podium_risk_3` | ambient | debating | MP-FREE | ACTIVE | room |
| `CHR-011` | Dr. Elara Maren | Causal / Macro Analyst (M1 · `causal_macro_analyst`) | SCI | `H-LAB` · `lab.driver_board` | L1 (hand-off); ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-012` | Lt. Cassian Rho | Central Bank Research (R1 · `research_central_bank`) | SCI | `H-LAB` · `lab.feed_r1` | ambient | researching | MP-FREE | ACTIVE | room |
| `CHR-013` | Ensign Mira Dal | Economic Data Research (R2 · `research_economic_data`) | SCI | `H-LAB` · `lab.feed_r2` | ambient | researching | MP-FREE | ACTIVE | room |
| `CHR-014` | Ensign Poe Varga | Market News Research (R3 · `research_market_news`) | SCI | `H-LAB` · `lab.feed_r3` | ambient | researching | MP-FREE | ACTIVE (console dormant: engine role deferred) | room |
| `CHR-015` | Lt. Imre Castell | Geopolitical Research (R4 · `research_geopolitical`) | SCI | `H-LAB` · `lab.feed_r4` | ambient | researching | MP-FREE | ACTIVE (dormant) | room |
| `CHR-016` | Lt. Selah Ward | Rates / Bonds Research (R5 · `research_rates_bonds`) | SCI | `H-LAB` · `lab.feed_r5` | ambient | researching | MP-FREE | ACTIVE (dormant) | room |
| `CHR-017` | Ensign Theo Brandt | Corporate / Earnings Research (R6 · `research_corporate_earnings`) | SCI | `H-LAB` · `lab.feed_r6` | ambient | researching | MP-FREE | ACTIVE (dormant) | room |
| `CHR-018` | Specialist Ada Kerr | Source Validator (V1 · `source_validator`) | SCI | `H-LAB` · `lab.bench_1` | ambient | validating | MP-FREE | ACTIVE | room |
| `CHR-019` | Specialist Noor Hale | Freshness Checker (V2 · `freshness_checker`) | SCI | `H-LAB` · `lab.bench_2` | ambient | validating | MP-FREE | ACTIVE | room |
| `CHR-020` | Specialist Jem Oris | Duplicate / Consistency Detector (V3 · `duplicate_detector`) | SCI | `H-LAB` · `lab.bench_3` | ambient | validating | MP-FREE | ACTIVE | room |
| `CHR-021` | Specialist Lyra Fenn | Fact / Reaction / Interpretation Classifier (V4 · `claim_classifier`) | SCI | `H-LAB` · `lab.bench_4` | ambient | validating | MP-FREE | ACTIVE | room |
| `CHR-022` | Lt. Auric Reyes | **Metals FAMILY DESK** (visual representation; interim adapter over S1 `specialist_xauusd`) | SCI | `L1` · `specialists.desk_metals` | ambient | analysing | MP-FREE | ACTIVE | **re-scoped** to a family desk (§5) |
| `CHR-023` | Lt. Elise Marchetti | **FX FAMILY DESK** (visual representation; interim adapter over **two** runtime agents: S2 `specialist_eurusd` + S3 `specialist_usdjpy`) | SCI | `L1` · `specialists.desk_fx` | ambient | analysing (per task row) | MP-FREE | ACTIVE | **re-scoped** to a family desk (§5) |
| `CHR-024` | Lt. Ren Takeda | *(was USD/JPY Specialist)* | — | — | — | — | — | **RETIRED** | folded into FX; ID never reused |
| `CHR-025` | Lt. Nash Coleman | **Indices FAMILY DESK** (visual representation; interim adapter over S4 `specialist_nas100`) | SCI | `L1` · `specialists.desk_indices` | ambient | analysing | MP-FREE | ACTIVE | **re-scoped** to a family desk (§5) |
| `CHR-026` | Ensign Sol Meridian | Market Session (T2 · `market_session`) | SCI | `L2` · `technical.session_clock` | ambient | analysing, monitoring | MP-FREE | ACTIVE | room |
| `CHR-027` | Lt. Vega Stone | Market Structure (T3 · `market_structure`) | SCI | `L2` · `technical.station_t3` | ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-028` | Lt. Iris Calder | Technical Indicator (T4 · `technical_indicator`) | SCI | `L2` · `technical.station_t4` | ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-029` | Ensign Wick Arlo | Candle / Price Action (T5 · `price_action`) | SCI | `L2` · `technical.station_t5` | ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-030` | Lt. Tess Harrow | Pullback / Setup (T6 · `pullback_setup`) | SCI | `L2` · `technical.station_t6` | ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-031` | Ensign Kit Sparrow | Entry Timing (T7 · `entry_timing`) | SCI | `L2` · `technical.station_t7` | ambient | analysing, monitoring | MP-FREE | ACTIVE (engine role not built: shown `idle`) | room |
| `CHR-032` | Lt. Cmdr. Rune Halloway | Technical Analyst (T8 · `technical_analyst`) | SCI | `L2` · `technical.station_t8` | ambient | analysing | MP-FREE | ACTIVE | room |
| `CHR-033` | Archivist Quinn Morrow | Post-Trade Reviewer (L1 · `post_trade_reviewer`) | SCI | `L6` · `archive.terminal` | L7; ambient | post_trade_review | MP-FREE | ACTIVE | room |
| `CHR-034` | Dr. Pax Lindqvist | Performance / Attribution (L2 · `attribution`) | SCI | `L7` · `perflab.terminal` | L6; ambient | post_trade_review | MP-FREE | ACTIVE | room |
| `CHR-035` | Chief Engineer Oren Kade | Data Validator (T1 · `data_validator`) | OPS | `L4` · `datacore.reactor_console` | ambient | validating, monitoring | MP-FREE | ACTIVE | room |
| `CHR-036` | Lt. Nyx Aldren | Contradiction Checker (P2 · `contradiction_checker`) | OPS | `L10` · `risk.intake_desk` | public spaces (rest, ambient) | risk_review | MP-RISK | ACTIVE | room, class |
| `CHR-037` | Lt. Cmdr. Sera Quill | Risk Engine / Risk Auditor (P3 · `risk_engine`) | OPS | `L10` · `risk.rule_console` | public spaces (rest, ambient) | risk_review, approved, rejected | MP-RISK | ACTIVE | room, class |
| `CHR-038` | Chief Dane Corso | Execution Checker (P4 · `execution_checker`) | OPS | `L9` · `execbay.preflight` | public spaces | executing, monitoring | MP-EXEC | ACTIVE | room, class |
| `CHR-039` | Lt. Kiri Sato | Paper Execution Agent (E1 · `paper_execution`) | OPS | `L9` · `execbay.launch` | L10 `risk.outbox_pickup`; public spaces | executing, monitoring | MP-EXEC | ACTIVE | room, class, route |
| `CHR-040` | Lt. Bram Oduya | MT5 Execution Agent (E2 · `mt5_execution`) | OPS | — | — | — | MP-NONE | **DEFERRED**: not rendered | — |
| `CHR-041` | Dr. Noa Ferris (Medic persona) | Operational Wellbeing Monitor (O2 · `wellbeing_monitor`) | OPS | `H-HAB` · `habitat.vitals` | entry zone of any active room (attends `error` / `overloaded`) | monitoring | MP-MEDIC | ACTIVE (producers mostly not emitted: mostly `idle`) | room, class |
| `CHR-042` | QM Bex Talon (Quartermaster persona) | Operational Wellbeing Monitor (O2 · `wellbeing_monitor`) | OPS | `H-CMD` · `command.console_budget` | ambient | monitoring | MP-FREE | ACTIVE | room |
| `CHR-043` | Bix | Habitat Host (cosmetic · `habitat_host`) | SYN | `H-HAB` · `habitat.counter` | `H-HAB` only | ambient service only | MP-HOST | ACTIVE (cosmetic; no operational meaning) | room, id text |
| `CHR-044` | Dr. Juno Pell | Lab Explorer (future · `lab_explorer`) | SCI | `H-LAB` · `lab.experiment_bench` (future) | L5 (future) | analysing | MP-NONE until built | **FUTURE** (Research Lab; not rendered) | room |
| `CHR-045` | Dr. Cato Ilves | Lab Validator (future · `lab_validator`) | SCI | `H-LAB` · `lab.experiment_bench` (future) | L5 (future) | validating | MP-NONE until built | **FUTURE** | room |
| `CHR-046` | Coach Talia Brenn | **Performance & Wellbeing Coach** (future · proposed id `performance_coach`) | SCI (advisory; see §7) | `R1` · `coaching.console` (future) | `H-HAB`; L7 | reviewing (debrief), monitoring | MP-NONE until built | **FUTURE** (not rendered) | **new** |

**Two personas, one technical id:** `CHR-041` and `CHR-042` share `wellbeing_monitor`. The adapter
routes an O2 event to the Medic (load, errors, cooldowns) or the Quartermaster (budgets, rate
limits).

**Cosmetic ids:** `habitat_host` is a UI-only id (it was `cafe_host` in v1). It never appears in
engine events.

---

## 5. Market specialist model — INTERIM ADAPTER

**Approved target (future engine):** three runtime specialists, one per family: **Metals** (gold XAU,
silver XAG), **FX** (majors and minors, multi-pair scanning, not tied to one pair) and **Indices**
(NAS100 first, extensible). All three report to the Central Trader.

**Runtime today:** the engine roster still has **four per-instrument specialists**: S1
`specialist_xauusd`, S2 `specialist_eurusd`, S3 `specialist_usdjpy`, S4 `specialist_nas100`. **The
engine migration is not part of this visual pass.**

### 5.1 Family desks, not agents

Until the engine is migrated, `CHR-022`, `CHR-023` and `CHR-025` are **FAMILY DESK visual
representations**, not runtime agents. The visual layer must never imply that one runtime agent
exists where several do.

| Family desk | Underlying runtime agents today | Relationship |
|---|---|---|
| `CHR-022` Metals desk | S1 `specialist_xauusd` | 1 : 1 (XAG is not configured → `NOT CONFIGURED`) |
| `CHR-023` FX desk | **S2 `specialist_eurusd` + S3 `specialist_usdjpy`** | **1 : 2, aggregated** |
| `CHR-025` Indices desk | S4 `specialist_nas100` | 1 : 1 |

### 5.2 Truth rules of the interim adapter

1. **One task row per underlying runtime agent.** Every desk (screen `DSP-SPC-0n` and the
   character's HUD) shows one row per mapped `technical_id`. Each row shows:
   - the instrument, the `technical_id` and the agent's **own** visual state;
   - its current task and age.

   Rows are never merged.
2. **No collapsed state.** A desk that aggregates several agents has **no single state badge**.
   The HUD shows one **state chip per underlying agent**, for example
   `EUR/USD · analysing` + `USD/JPY · idle`. If S2 and S3 differ, **both** states are visible at the
   same time. The adapter must never compute a "highest-priority" or averaged state for the desk.
3. **Markers stay with their own agent.** `error`, `overloaded`, `resting`, `offline` and `paused`
   markers attach to the chip and row of the agent that has them, never to the whole desk.
   Example: S3 in `error` while S2 is `analysing` shows an error chip on the USD/JPY row only.
4. **The body pose is neutral about state.** The desk character's animation only means "this desk
   has activity":
   - it works at its desk while **at least one** underlying agent is in a working state;
   - it is idle when none is.

   It carries no state badge of its own. The per-agent chips are the only state truth. In overview
   zoom, where chips are hidden, the desk shows a **split pip** (one segment per underlying agent),
   never a single pip.
5. **Concurrent tasks are shown as concurrent.** When S2 and S3 run at the same time, the FX desk
   lists both tasks together, with a count ("FX · 2 active").
   - The character does not "switch" between them in a way that suggests sequential work.
   - Hand-off props (`PRP-001`) are per task: each carries its own instrument tag.
6. **Clicking inspects the real agents.** A click on a desk (`NAV`) opens a panel listing each
   underlying `technical_id` with its own recent events.
7. **Labelled as interim.** The desk panel footer reads "Family desk · interim view of N runtime
   agents".
8. **Configuration, not invention.** A desk lists only instruments the engine configures (today
   XAU/USD; EUR/USD and USD/JPY; NAS100). Other family members are `NOT CONFIGURED` or not listed.

### 5.3 After the engine migration (future)

When the engine adopts family specialists (proposed ids `specialist_metals`, `specialist_fx`,
`specialist_indices`, **not implemented**), each desk maps 1 : 1 to one runtime agent. The desk can
then show that agent's single state, and its per-instrument rows become that agent's concurrent
tasks. No character ID changes. The interim adapter is removed.

## 6. Shared research team and the Central Trader

**Shared research team** (one team for all families, home `H-LAB`):

| Function | Characters |
|---|---|
| Central Bank Research | `CHR-012` |
| Economic Data Research | `CHR-013` |
| News Research | `CHR-014` (deferred in the engine: dormant) |
| Geopolitics Research | `CHR-015` (deferred: dormant) |
| Rates / Bonds Research | `CHR-016` (deferred: dormant) |
| Earnings Research | `CHR-017` (deferred: dormant) |
| Source validation | `CHR-018` |
| Freshness | `CHR-019` |
| Duplicate / consistency checking | `CHR-020` |
| Fact / reaction / interpretation separation (with numeric cross-checks) | `CHR-021` |
| Macro / context synthesis | `CHR-011` |
| Contradiction checking | Research-stage consistency is `CHR-020` / `CHR-021`. The proposal-stage **Contradiction Checker** (`CHR-036`, P2) sits in the Risk Control Room, because the engine runs it as the gate before risk |

The research layer **feeds the three specialists**. It is never duplicated per market family.

**Central Trader (`CHR-004`):**
- Handles **multiple simultaneous opportunities**. Its console (`DSP-CMD-09`) lists every active
  trader plan / setup across instruments, each with its instrument, stage and age.
- The HUD shows the count. The character works at one console and is never cloned per instrument.

**Visual decision chain:**

| Step | Who | Where |
|---|---|---|
| Research | `CHR-011`–`021` | `H-LAB` |
| Specialists | `CHR-022`, `023`, `025` | `L1` |
| Technical | `CHR-026`–`032` | `L2` |
| Debate | `CHR-006`–`010`, judged by `CHR-002` | `L3` |
| Central Trader | `CHR-004` | `H-CMD` |
| Approval / Portfolio | `CHR-001` | `H-CMD` |
| Proposal | `CHR-005` | `H-CMD` → courier to `L10` intake |
| Deterministic Risk Engine | `CHR-036`, `CHR-037` | `L10` |
| Execution | `CHR-039` collects from the `L10` outbox; `CHR-038` / `CHR-039` work in `L9` | `L9` |

Each step lights up only when its real event exists (Visual plan §10.1).

## 7. Performance & Wellbeing Coach (future)

- **`CHR-046`, home `R1`.** Not rendered until the room and the role exist.
- **Uses only measurable signals:**
  - retries;
  - workload (task counts and durations);
  - repeated errors;
  - failed reviews;
  - conflict frequency (contradiction flags, debate reversals);
  - long-running tasks;
  - real cooldowns.
- **Never:** emotions, mood, stress, or psychiatric terms or diagnoses. It has **no authority**
  over trading, Risk, runs or other agents; it produces recommendations for screens only.
- **Department:** SCI blue: an advisory, research-adjacent role; not Command, not Risk (owner
  decision, Character Bible V1 K4).

---

## 8. Visual state support

| States | Characters | Animation set |
|---|---|---|
| Standard set | all rendered characters | stand, walk (8 facings), sit, wait, freeze (paused), error beacon, overloaded, rest (recovery pod) |
| `researching` | CHR-012–017 | read streams at a feed console |
| `validating` | CHR-018–021, 035 (045 future) | scan cards / snapshots |
| `analysing` | CHR-002, 004, 005, 011, 022, 023, 025–032 (044 future) | work the room's main display; family desks show one task row per underlying agent (§5.2); the Trader lists concurrent opportunities |
| `monitoring` | CHR-003, 026, 031, 035, 038, 039, 041, 042 | watchful pose, periodic glance |
| `debating` | CHR-006–010 | speak / listen |
| `reviewing` | CHR-001, 002 (046 future) | judge seat or command chair |
| `risk_review`, `approved`, `rejected` | CHR-036, 037 | checks light one by one; stamp |
| `executing` | CHR-038, 039 | pre-flight, launch |
| `post_trade_review` | CHR-033, 034 | shelve crystals, update walls |

Rules from the Visual plan:
- a character shows work **only** while telemetry says so;
- badges update before movement;
- transient `approved` / `rejected` last their display time only;
- ambient never implies an emotion or a decision.

## 9. Changes from v1

- **Re-homed:** every character, to the v2 rooms.
- **Movement classes replaced:** `MP-COURIER`, `MP-VAULT`, `MP-BAY` and the lift rights are
  replaced by the logical classes `MP-COURIER` (L10 intake), `MP-RISK`, `MP-EXEC` and the entry-zone
  rights for the Supervisor and Medic.
- **Specialists:**
  - `CHR-022`, `CHR-023`, `CHR-025` re-scoped to Metals, FX and Indices **family desks**;
  - `CHR-024` retired;
  - an **interim adapter** added (§5) that never collapses S2 and S3 into one state.
- **Renamed:** `CHR-004` to Central Trader (multi-opportunity); `CHR-043` to Habitat Host.
- **New:** `CHR-046` Performance & Wellbeing Coach (future).
- **Removed:** resident "rest in place"; real cooldowns now go to `habitat.recovery`.

## 10. Open decisions

| # | Decision | Default |
|---|---|---|
| CR-1 | Engine migration to the three family specialists (a roster change outside this visual pass) | The interim adapter of §5 |
| CR-2 | ~~The Coach's department colour~~ | **Closed**: advisory SCI blue (Character Bible V1 K4) |
| CR-3 | Exact uniform colour tokens under the four alert tints | Set during art production |
