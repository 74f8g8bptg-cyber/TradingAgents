# Stellar Room Design Sheet — L3 Debate Chamber (V1)

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**; DC-1…DC-10 decided, DC-11 / DC-12 open (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Room** | `L3` — Debate Chamber · ACTIVE · public (Room Registry v2 §3.6) |
| **Source of truth** | Geometry: `STELLAR_MASTER_FLOOR_PLAN_V1.md` rev C, `STELLAR_STATION_TOPOLOGY.md` v2. Function, zones, anchors: `STELLAR_ROOM_REGISTRY.md` v2. Figures and access: `STELLAR_CHARACTER_REGISTRY.md` §3–§4, `STELLAR_CHARACTER_BIBLE_V1.md`. Screens and the producer audit: `STELLAR_SCREEN_REGISTRY.md` v2. Objects: `STELLAR_ASSET_REGISTRY.md` v2. Look: `STELLAR_VISUAL_BIBLE_V1.md`. Engine facts: `stellar/src/stellar/pipeline/orchestrator.py` (the research-and-debate pipeline, Phase 6), `stellar/src/stellar/agents/roster.py`. StarNet: `STARNET_REUSE_AUDIT.md`, `STELLAR_STARNET_VISUAL_ADAPTATION.md` |
| **Not changed here** | Room position, shape, door, topology, the access model, zones, anchors, the screen list and data rules. Placements are **provisional** (the tile scale is open) and are given relative to the door wall |
| **Hard boundary** | Debates run in the engine. This room only **shows** real debate events. The visual layer never writes an argument, a vote, a score, an opinion, a verdict or a market value, and never starts or ends a debate |

---

## 1. StarNet concept review (meetings, gatherings, shared information)

**Method.** I read the audit (S19, S25–S28, S33, S34) and the local StarNet checkout at pinned
revision `fbddbf99` **read-only**:
- `frontend/app/world.js`: the social encounter system (`huddle` / `border` conversations, the
  silent `watch` / `follow` beats, turn-taking `talkTurn`, the sightline rule for meeting tiles) and
  the "Tier E" station gathering (a formation plus one speaker);
- `frontend/app/verdictfollowup.js`: the verdict follow-up after a review.

StarNet has **no decision system like Stellar's**: its meetings are ambient beats, not debates, and
nothing in StarNet produces an argument or a verdict. Only **staging ideas** are taken.
**Nothing is copied:** no art, assets, characters, layouts, interfaces, dialogue or personality
systems.

| StarNet concept | What is useful | How Stellar adapts it | What Stellar rejects |
|---|---|---|---|
| **Conversation beat** (`huddle`: 2–3 bodies on adjacent tiles, face each other, take turns) | Turn-taking reads as "talking" **without any dialogue**; StarNet keeps words in a transcript, not in bubbles | One speaker at a time: the side whose **real** task is running uses `talk`; the others `listen` facing the evidence stage. Words appear only on the argument walls and in the Inspect transcript, from real outputs | Randomly started huddles, trio chances, social cooldown lanes, speech bubbles, mouth-flap "chatter" |
| **Sightline rule** (meeting tiles must see each other; no conversation through a wall) | Participants of one exchange must visibly share a space | Every podium and the judge seat have a clear line to the **evidence stage**; no podium is hidden behind furniture (§3.2) | — |
| **Gathering formation** (Tier E: one speaker, an audience in a formation, slots resolved deterministically) | A fixed formation with named slots is legible and cheap | The chamber's **fixed anchors** are the formation: podiums, the judge seat, the visitor spot. Figures go only to their own reserved anchor (audit S19, S25) | The random quiet-station trigger, the "scatter and pretend nothing happened" gag, the overseer persona, suspending movement limits |
| **Truthful telemetry of meetings** (StarNet never claims a meeting happened: no event, no log for its gathering) | A meeting shown on screen must be a meeting that really happened | The chamber is active **only** between `debate.started` and the debate's end; nothing is staged without those events | Any ambient "meeting" in L3 |
| **Silent watch beat** (stand near a working peer without talking) | A participant can be present and attentive without speaking | The non-speaking side and the judge **listen** (`listen`, `look_screen`) while a real turn is running | Following or tailing other figures |
| **Verdict follow-up** (a verdict is recorded, then acted on) | A review ends in a **recorded outcome** | The Verdict display (`DSP-DEB-06`) shows only the real `decision.research_plan.created` | User rating chips, XP, praise or feedback loops |
| Idle "sentience" engine (needs, curiosity, quirks, emotion language, `Math.random`) | — | — | **Rejected** (audit S27): no emotional simulation, no artificial arguments, no fake personality |
| Station artwork, CRT look | — | — | **Rejected** (S33, S34) |

**Stellar original design (not from StarNet):**
- the debate structure itself (bull / bear rounds, a judge, a recorded research plan) comes from the
  Stellar engine;
- the evidence stage with cited evidence ids, the argument walls, the round counter and the verdict;
- the podium / judge-seat layout, materials and lighting (§3).

---

## 2. Room identity and relationships

| Aspect | Definition |
|---|---|
| **Role** | The structured discussion and review space: participants examine cited evidence, exchange cases in rounds, and the judge records a documented outcome (the research plan) |
| **It is not** | Main Command (`H-CMD`), the Research Lab (`H-LAB`), the Market Specialists room (L1), the Risk Control Room (L10) or the Execution Bay (L9). Nothing is approved, sized or executed here |
| **Atmosphere** | Intelligent, focused, collaborative, calm. Disagreement is handled **structurally** (two columns, rounds, cited evidence), never theatrically. **Not** a parliament, a courtroom or a military briefing room |
| **Visual identity** | A central **evidence stage** with a holographic surface, slim **standing podiums** around it in an open arc, argument walls on the side walls, and a low **review desk** at the far end for the judge |

| Room | Relationship |
|---|---|
| **`H-LAB`** | **Upstream: research and evidence.** Accepted research items and the macro assessment are the evidence the cases cite. They appear on the evidence stage as **cited ids resolved from their own real events**; researchers do not visit L3 |
| **L1** | **Upstream: specialist analysis.** The specialist market view is part of the debate input and can be **cited**; shown as data on the evidence stage, not as a visit (L1 sheet §2). Specialists do not debate |
| **L2** | Technical evidence is cited the same way (no visit) |
| **`H-CMD`** | **Downstream: receives the result.** The Research Manager comes from `H-CMD` to judge and returns there after the real `decision.research_plan.created`. The result appears in `H-CMD` on the Agent Pipeline (`DSP-CMD-04`), lit only by the event. Route: `DR-L3` → `COR-N` → `DR-N-CMD` |
| **L10** | **Context only.** The Contradiction Checker (P2) belongs to L10 (`MP-RISK`) and does **not** visit L3. Its findings may be shown here as a **remote feed** (`DSP-DEB-05` from `debate.completed`; Visual World Plan §3.2; VW-6 decided by DC-10). The deterministic Risk Engine is downstream and never reviewed in L3 in V1 |
| **L9** | **Downstream, no link.** Execution never happens here and is not shown here |

No new door or connection: L3 is reached only through `DR-L3` from `COR-N`.

---

## 3. Architecture

### 3.1 Shape and entrance (approved; unchanged)

- **Shape:** a tall rectangular room (size M; Floor Plan rev C §4: x 689–803, y 341–518, about
  114 × 177 px; **not frozen**). North of `COR-N`, the last small room before `H-CMD`. Its
  neighbours (L2 to the west, the `H-CMD` rim to the east) are across **non-walkable hull** (Q4).
- **One door:** `DR-L3`, an ordinary 2-tile sliding door (`DOR-001`) with the normal indicator,
  centred in the **south wall**, opening onto `COR-N`. **No other opening.** No lock, no new
  airlock, no hidden passage, no restricted marking (L3 is a public room).
- **Cutaway:** the camera-facing walls are cut away (`WAL-008`). The door keeps a visible frame,
  threshold and opening (Visual Bible C4).

### 3.2 Schematic (not to scale; door at the bottom)

```
                     north wall (back)
   +----------------------------------------------+
   |  DSP-DEB-04 round    DSP-DEB-06 verdict      |
   |  counter             (north wall, centre)    |
   |        CON-023 review desk + SEA-003 seat    |
   |        debate.judge_seat  (faces south)      |
   |                                              |
   | DSP-DEB-01           +-----------+ DSP-DEB-02|
   | bull wall  CON-011   |  TBL-007  | CON-011   |
   | (west)     podium    | evidence  | podium    |
   |            BULL  ->  |  stage +  | <-  BEAR  |
   |            (inner)   | DSP-DEB-03| (inner)   |
   |                      +-----------+ bear wall |
   |                                   (east)     |
   |     CON-011    CON-011    CON-011            |
   |     risk_1     risk_2     risk_3  (outer arc,|
   |     (unlit in V1: no risk debate producer)   |
   |                                              |
   | DSP-DEB-05 contradiction   debate.visitor    |
   | feed (west wall, entry)    debate.entry      |
   +------------------[ DR-L3 ]-------------------+
                        COR-N
```

- The **evidence stage** is the centre of the room; every podium and the judge seat face it.
- The two inner podiums face each other **across** the stage (bull west, bear east, as in the
  Visual World Plan §5.3), so an exchange reads left ↔ right in the 2.5D view.
- The three risk podiums stand in a shallow **open arc** south of the stage, facing north. The arc
  is open: no enclosing rows, no tiers, no raised bench.
- The judge end is **opposite the door** (Room Registry §3.6: `debate.bench`).

### 3.3 Materials

| Surface | Material |
|---|---|
| Floor | **Deep navy** working floor (`FLR-001`), with a thin titanium inlay ring around the evidence stage (walk-over, not a barrier) |
| Walls | **Warm off-white structural panels** (`WAL-001`) with **titanium / light metallic trims** |
| Technical elements | **Graphite** podium bodies, review desk, stage base and screen bezels |
| Accent | **Science blue** lines (SCI department: the debaters are SCI) on podium edges and the stage rim. Static; never a data state |
| Podiums (`CON-011`) | Drawn as **slim standing consoles** (graphite body, off-white top, small side-icon plate), **not** speaker lecterns, parliament desks or witness boxes |
| Review desk (`CON-023` + `SEA-003`) | Drawn as a **low graphite review desk with a single chair** at floor level (DC-2), **not** a courtroom lectern or raised bench; no gavel, no rail, no dock, no hierarchy of heights. The registry names "Judge lectern" / "Judge seat" are kept internally (§10, D8) |

### 3.4 Ceiling and lighting

| Layer | Treatment |
|---|---|
| Ceiling | A flat ceiling with a soft round light panel over the evidence stage; not drawn in the cutaway (only its edge is suggested) |
| General | Clean neutral white with a light cool tint; calm and even. Never dark |
| Podium spotlights (`LGT-007`) | A soft pool on a podium **only while its debater takes part in a real debate** (`debate.started` → the debate's end). **Neutral light** (DC-3): no side colour, no red for the bear side. The side is shown by an **icon** (bull ▲ / bear ▼; risk icons for the future debate) **and a text label**. Any other state indication appears only for a real system state, with icon + text |
| Stage light | The stage surface glows softly **only while** cited evidence is shown |
| Alert | The station alert tint on `LGT-001`, with a word and icon. Lighting alone never carries data (Visual Bible C7) |

### 3.5 Walkable areas and zones (Room Registry §3.6)

| Zone | Who | Rule |
|---|---|---|
| `debate.entry` (inside the door) | Everyone entering | The door approach tile stays empty |
| `debate.floor` | Debaters at their reserved podium anchors; walkways around the stage | The stage and podiums block their footprint; a 1-tile walkway rings the stage |
| `debate.bench` (north) | The judge at `debate.judge_seat` | Reserved while a judge is seated |
| `debate.visitor` (south-east, near the entry) | A visitor with a real reason (§4.3) | Standing spot; no seat |
| Behind the review desk, behind the wall screens | Not walkable | — |

---

## 4. Characters

### 4.1 Occupants and visitors (Character Registry §4)

| Figure | Runtime role | Home / anchor | Normal position | Movement | Role in the chamber |
|---|---|---|---|---|---|
| **Bull Researcher** `CHR-006` (SCI) | U1 `bull_researcher` | `L3` · `debate.podium_bull` (reserved) | Inner west podium, facing the stage | Stays in L3. Ambient only when no debate is running; returns on `debate.started` (work over idle) | Argues the case **for** the setup, one real turn per round |
| **Bear Researcher** `CHR-007` (SCI) | U2 `bear_researcher` | `L3` · `debate.podium_bear` (reserved) | Inner east podium, facing the stage | As above | Argues the case **against** the setup |
| **Aggressive / Conservative / Neutral Risk Debaters** `CHR-008`–`010` (SCI) | U5–U7 (advisory) | `L3` · `debate.podium_risk_1`…`_3` (reserved) | Outer arc, facing north | Stay in L3; ambient when idle | **No producer today** (§5, §10 D1): shown `idle` at unlit podiums; they never speak, never listen to a debate they are not part of, and never appear in a verdict |
| **Research Manager** `CHR-002` (CMD) | U3 `research_manager` | `H-CMD` · `command.table_head`; visits `debate.judge_seat` | Seated at the review desk, facing the stage | `H-CMD` → `DR-N-CMD` → `COR-N` → `DR-L3` on `debate.started`; back to `H-CMD` after the real verdict or the run's end | **Leads the review:** listens to the rounds, then writes the research plan; `stamp` only on `decision.research_plan.created` |
| **Portfolio Manager** `CHR-001` (CMD) | U8 `portfolio_manager` | `H-CMD` · `command.chair`; registry visit `debate.judge_seat` | — | **Does not visit L3 in V1.** The PM's registered L3 visit closes the **risk** debate, which has no producer (§10, D1) | Future |
| **Supervisor** `CHR-003` (CMD) | O1 `supervisor` | `H-CMD` · `command.console_ops` (`MP-SUPERVISOR`) | `debate.visitor` only | Only on `run.failed` (`RESEARCH_FAILED`) of a run whose debate was running (`debate.started` without `debate.completed`); exactly one visit, never also to L1 (DC-7; Corridor CD-3); stands, looks at the screens, leaves | Oversight, no participation |
| **Medic persona** `CHR-041` (OPS) | O2 (`MP-MEDIC`) | `H-HAB` | `debate.entry` only | Only to attend a figure in a real `error` / `overloaded` state | None |

**Not in the chamber:** researchers (`H-LAB`), specialists (L1), technical agents (L2), the
Contradiction Checker P2 and the Risk Engine P3 (L10, `MP-RISK`), the Central Trader and the
Proposal Builder (`H-CMD`), the execution crew (L9). Their work reaches L3 **only as cited data**.
No runtime agents are merged into one figure, and no permanent occupant is added beyond the
registry's five debaters.

### 4.2 Participant positions and interaction with the shared evidence

- **Standing participants:** the debaters stand at their podiums (`CON-011` work anchors). There are
  **no participant chairs**; the only seat is the judge's (`SEA-003`). The optional tier bench
  (`SEA-004`) is **not used** (§10, D10).
- **Shared evidence:** all participants face the **evidence stage**. The speaker's cited evidence
  appears on the stage surface (`DSP-DEB-03`) and as an **evidence card** (`PRP-004`) placed on the
  stage from the speaker's side. Listeners turn to the stage (`look_screen`).
- **Arguments:** each side's real points appear on its **own side wall** (bull west, bear east),
  behind its podium, so the camera reads the two cases side by side.
- **The judge** faces the stage and both walls from the north end, and records the outcome on the
  Verdict display above the review desk.

### 4.3 Who can enter

- Public room (`MP-FREE` rules): an active public room is entered **only when a real event gives a
  reason**.
- Reasons in V1: the five debaters (home room); the Research Manager (a real debate); the Supervisor
  (a real run event, visitor spot only); the Medic (entry zone only, for a real `error` /
  `overloaded`).
- Nobody else is routed in. L3 is **not** a transit or ambient loitering room.

---

## 5. Debate workflow (what the room shows, event by event)

Engine facts (`pipeline/orchestrator.py`):
- `debate.started` carries the number of rounds;
- each round runs U1 then U2; each successful case emits `agent.task.completed` (the case, with its
  cited evidence ids) and then `debate.turn.completed` (round, side, role);
- a failed case emits `agent.task.failed`; a **skipped** case (LLM disabled, failed dependency)
  emits **nothing**;
- after the rounds, P2 runs deterministically and `debate.completed` carries the turn counts and the
  contradiction findings;
- U3 then writes the synthesis: `decision.research_plan.created` (model stance, final stance, guard
  adjustments, evidence grade).

| # | Step | Trigger (real event) | What the room shows | Status |
|---|---|---|---|---|
| 0 | No debate | none | Podium spotlights off; walls read **NO DEBATE IN PROGRESS**; the stage reads **NO EVIDENCE CITED**; the Verdict shows the latest real verdict with its time, or **PENDING** if none | Yes |
| 1 | Debate starts | `debate.started` | Bull and bear spotlights on; the round counter shows round 0 of N (N from the event) | Yes |
| 2 | Participants arrive | `debate.started` | Bull and bear return to their podiums if away (work over idle); the Research Manager walks from `H-CMD` to the judge seat | Yes (derived from the event) |
| 3 | A side prepares its case | `agent.task.started` (`bull_researcher` / `bear_researcher`) | That debater `talk`s at its podium; the others `listen` / `look_screen` | Yes |
| 4 | Evidence is shown | `agent.task.completed` of that role (its cited evidence ids) + `debate.turn.completed` | The cited ids appear on the evidence stage, resolved against their own research / analysis events (an id that cannot be resolved reads **UNKNOWN**); an evidence card is placed on the stage | Yes (paired sources; the turn event itself carries no evidence ids, §10 D3) |
| 5 | Arguments / rebuttals recorded | same | The side's real points, its named weaknesses and rebuttals appear on its wall; the round counter advances | Yes (paired sources, D3) |
| 5a | A case fails / is skipped | `agent.task.failed` / no event | Failure: the debater's error overlay; no argument is written. Skipped: nothing appears, and the column keeps its real count | Yes; a skipped case is simply absent |
| 6 | Contradictions checked | `debate.completed` (P2 findings) | The real findings appear on the contradiction feed (§10, D4); P2 never appears in person | Yes |
| 7 | Debate ends | `debate.completed` | Spotlights off; the round counter shows the real turn counts | Yes |
| 8 | Review | `agent.task.started` (`research_manager`) | The judge `reviewing` at the review desk; the Verdict reads **PENDING** | Yes |
| 9 | Result recorded | `decision.research_plan.created` | `stamp`; the Verdict shows the **final stance**, and the model stance plus guard adjustments when they differ; the evidence grade; a link to the plan (NAV) | Yes |
| 9a | No result | `agent.task.failed` (`research_manager`) or no event | No verdict; **PENDING** stays; the judge's error overlay on failure | Yes |
| 10 | Participants leave | after step 9 or 9a, or the run's end (`run.completed` / `run.failed`) | The Research Manager returns to `H-CMD`; the debaters stay at home (idle) | Yes |
| — | Risk debate (U5–U7) and its PM close | — | Risk podiums unlit; debaters `idle`; the PM does not come | **NOT AVAILABLE** (no producer; future) |

Nothing is invented: there is no vote, no score, no winner, no confidence meter and no competitive
bar on any screen (§10, D5).

---

## 6. Main objects (registry assets only)

| # | Object | Asset | Purpose | Placement | Interaction role | Importance |
|---|---|---|---|---|---|---|
| 1 | **Evidence stage** (the shared table) | `TBL-007` + `SCR-012` surface (`DSP-DEB-03`) | The shared evidence surface every participant faces | Room centre | Look target; evidence cards land here | **Hero** |
| 2 | **Podiums** × 5 (participant positions) | `CON-011` | One reserved standing station per debater | Bull W / bear E (inner, facing each other across the stage); risk × 3 in the south arc | `debate.podium_bull`, `_bear`, `_risk_1`…`_3` (reserved) | High (inner), Medium (risk, unlit in V1) |
| 3 | **Review desk + seat** (the judge's station) | `CON-023` + `SEA-003` | Where the judge listens and records the outcome | North end, facing south | `debate.judge_seat` (RM; PM in the future) | High |
| 4 | **Podium spotlights** | `LGT-007` | Mark who takes part in a real debate (icon + label) | Over each podium | none | Medium |
| 5 | **Argument walls** | `SCR-002` (`DSP-DEB-01`, `-02`) | Each side's real case | West / east walls, behind their podiums | Look target | High |
| 6 | **Verdict** (review surface) | `SCR-005` (`DSP-DEB-06`) | The recorded outcome | North wall above the review desk | Look target; NAV to the plan | High |
| 7 | **Round counter** | `SCR-003` (`DSP-DEB-04`) | Round n of N | North wall, west of the verdict | none | Medium |
| 8 | **Contradiction feed** | `SCR-003` (`DSP-DEB-05`) | Remote feed of P2 findings | West wall by the entry | Look target | Medium |
| 9 | **Evidence card** | `PRP-004` | A cited piece of evidence placed on the **shared central stage** | Speaker's side → stage; never passed between podiums | Appears only on a real turn whose case cites evidence | Medium |
| 10 | Room plate, emblem | `SGN-001`, `DEC-006` | Name and department emblem by the door | Corridor side of `DR-L3` | none | Low |

**Not used:** the optional tier bench `SEA-004` and tier steps `FLR-006` (they read as a parliament;
§10, D10); the chamber stays open and level. **Not added:** no separate "debate table", participant chairs or presentation screen;
the evidence stage, the podiums and the six approved displays cover these roles (§10, D9).

---

## 7. Screen design (Screen Registry v2 §5.5 is the authority)

| Category | Display | Content (real fields only) | Placement | Placeholders |
|---|---|---|---|---|
| **Evidence** | `DSP-DEB-03` Evidence projector | From the speaking role's `agent.task.completed` (paired with `debate.turn.completed`): the evidence ids cited in the current turn, each resolved to its research item or analysis (source, kind, time); NAV opens the item | Evidence stage surface | **NO EVIDENCE CITED**; unresolved id → **UNKNOWN** |
| **Research / arguments** | `DSP-DEB-01` Bull wall · `DSP-DEB-02` Bear wall | From each side's `agent.task.completed` (paired with `debate.turn.completed` for round and side): the side's points with their basis, named weaknesses, rebuttals | West / east walls | **NO DEBATE IN PROGRESS** |
| **Proposal / review** | `DSP-DEB-06` Verdict | Final stance; model stance and guard adjustments when different; evidence grade; research snapshot id; time | North wall | **PENDING** |
| | `DSP-DEB-05` Contradiction feed | P2 contradiction findings from `debate.completed` (remote data feed; no P2 figure) | West wall, entry | **AWAITING DATA** |
| **System context** | `DSP-DEB-04` Round counter | Round n of N; the debate type as derived from the turns' roles (§10, D2) | North wall | **NO DEBATE IN PROGRESS** |

**Screen rules for this room:**
- **Never invent** debate scores, votes, opinions, sentiment, winners, confidence values, market
  values or decisions. The model's self-reported confidence is **not shown** (DC-9).
- States follow the registry: **LIVE, AWAITING DATA, STALE, LINK DOWN, MODE UNKNOWN,
  NOT AVAILABLE, NOT CONFIGURED, UNKNOWN** (plus PLANNED and DISPLAY FAULT). MODE UNKNOWN does not
  apply in L3 (no mode display).
- On link loss, every screen **freezes and greys** with **LINK DOWN · age**.
- Argument text and evidence are shown as **data** (quoted, attributed to the role and round), never
  as speech bubbles.
- All displays are read-only; NAV only opens details (Inspect debate: the transcript of turns, the
  verdict and the evidence links; Visual World Plan §17).

---

## 8. Agent life

All activity comes from **real events**, **real tasks** or **normal idle behaviour**. There is **no
emotional simulation**, no random conversation and no artificial argument.

| Activity | Trigger | Who | Clips |
|---|---|---|---|
| Entering for a real debate | `debate.started` | RM walks in; bull / bear return to their podiums | `walk` |
| Speaking (preparing a case) | `agent.task.started` of the side's role | The speaking debater | `talk` (neutral gestures) |
| Listening | A real turn of another participant | The other debater, the RM | `listen`, `look_screen` |
| Reviewing evidence | A turn's cited evidence appears | Listeners turn to the stage | `look_screen` |
| Recording the review | `agent.task.started` → `decision.research_plan.created` (`research_manager`) | RM at the review desk | `sit_work`, `stamp` (display time only) |
| Leaving after completion | Verdict, RM failure, or the run's end | RM returns to `H-CMD` | `walk` |
| Idle | No debate | Debaters at their podiums or seeded ambient via `COR-N` → `H-CMD` → `H-HAB`; risk debaters idle | `stand_idle` |
| Error | `agent.task.failed` | The failing figure | `error_beacon` overlay |

No `talk` between debaters outside a real debate; no idle conversations inside L3.

---

## 9. Access (summary)

- **One explicit door** (`DR-L3`, `DOR-001`, south wall onto `COR-N`). No lock, no automatic door
  beyond the approved `DOR-001` behaviour, no new airlock, no hidden passage.
- Public room; entered only for a real reason (§4.3). Reserved anchors (podiums, judge seat) belong
  to their roles.
- **Red** only from real system states.

---

## 10. Contradictions and owner decisions

| # | Topic | Documents | Engine / facts | Resolution |
|---|---|---|---|---|
| **D1** | **Risk debate and the PM's close** | Room Registry §3.6: "the advisory risk debate"; Visual World Plan §3.2 and §5.3; Character Bible and H-CMD sheet: the PM walks to L3 to close it; `CHR-008`–`010` ACTIVE | U5–U7 exist in the roster, but **no pipeline stage runs them** (not in `LLM_ROLES`); no event is emitted. The PM's approval enters as `decision.final.created` from the run request, not from a debate | **Resolved (DC-5):** all five podiums kept; the three risk podiums stay **unlit / inactive**, the risk debaters `idle`, no activity simulated, no PM visit. **NOT AVAILABLE / future** until a producer exists |
| **D2** | **Debate type** on `DSP-DEB-04` | Screen Registry: "Round n of N; debate type" | `debate.started` carries only `rounds` | **Stands:** the type is derived from the turns' real `role` field (only the investment debate exists) |
| **D3** | **Argument and evidence source** | Screen Registry (before): `DSP-DEB-01`–`03` from `debate.turn.completed` only; Asset Registry: `PRP-004` on a turn "citing evidence" | `debate.turn.completed` carries **only** round, side and role. The case (points, evidence ids, rebuttals) is in the **`agent.task.completed`** output of the same role and run | **Resolved (DC-6):** the displays pair `agent.task.completed` (content) with `debate.turn.completed` (round, side). The turn event is never described as carrying arguments or evidence. Screen Registry §5.5 and Asset Registry `PRP-004` aligned |
| **D4** | **Contradiction feed source** | Screen Registry (before): `DSP-DEB-05` from `trade.proposed` (P) | P2's findings arrive in `debate.completed` | **Resolved (DC-6):** `DSP-DEB-05` now reads the P2 findings from **`debate.completed`**; `trade.proposed` is not its source. Screen Registry §5.5 aligned (now available, `A`) |
| **D5** | **Tug-of-war bar** | Visual World Plan §11 (before): "Tug-of-war bar moves" on each turn | It would be a **debate score** | **Resolved:** removed completely. No winner, score, vote, confidence meter or competitive bar anywhere. Visual World Plan §11 and Layer Design (Debate Chamber row, U1 / U2 rows, `SPEAKING`, LD-6) aligned |
| **D6** | **Spotlight colours** | Visual World Plan §5.3 (before): bull green, **bear red**, risk orange / blue / white | Red only for real system states; lighting never carries data (Visual Bible C2, C7) | **Resolved (DC-3):** podium lighting is **neutral**; the side is shown by **icon + text**. Another state indication appears only for a real system state, with icon + text. Visual World Plan §5.3 / §6.2, Room Registry §3.6 and `LGT-007` aligned |
| **D7** | **Evidence card path** | Visual World Plan §8 (before): "evidence card passed between podiums" | Cards support one side; they are not handed to the opponent | **Resolved:** the card is placed on the **shared central stage**; never passed between podiums. Visual World Plan §8 / §11 aligned |
| **D8** | **Courtroom asset names** | "Not a courtroom" | `CON-023` "Judge lectern", `SEA-003` "Judge seat" | **Resolved (DC-2):** registry names kept internally; drawn as a **low review desk and chair**: no raised bench, gavel, courtroom hierarchy or parliament look |
| **D9** | **Debate table / participant seats / presentation area** | Requested object categories | No such assets; the debaters stand at podiums | **Resolved:** none invented. `TBL-007` + `CON-011` + the approved displays |
| **D10** | **Tier bench / tier steps** | "Not a parliament" | `SEA-004`, `FLR-006` are optional L3 assets | **Resolved (DC-4):** not used; the chamber stays **open and level** |
| **D11** | **Specialists joining a debate** | The request: "relevant specialists or agents when a real debate requires them" | The engine's debate is U1 / U2 judged by U3; no other role takes part | **Resolved:** specialists and researchers are **cited evidence only**; physical participation only if the engine later supports it |

No conflicts with:
- the topology (one door `DR-L3` on `COR-N`; neighbours across hull);
- the access model, the door rules and the Visual Bible materials;
- the Character Registry (five debaters at home; the RM as visitor; no merged agents);
- the Screen Registry display list (`DSP-DEB-01`…`06`);
- the StarNet exclusions (S27, S33, S34).

---

## 11. Decisions

| # | Decision | Status |
|---|---|---|
| DC-1 | Layout: judge end north; evidence stage centre; bull W / bear E inner podiums; risk arc south; entry south | **Closed:** approved as drawn (§3.2) |
| DC-2 | Review chamber, not a courtroom (D8) | **Closed:** low review desk and chair, slim podiums; no raised bench, gavel, hierarchy or parliament look |
| DC-3 | Podium lighting (D6) | **Closed:** neutral; status only as icon + text; no red to identify the bear side |
| DC-4 | Tier seating / steps (D10) | **Closed:** not used; open and level |
| DC-5 | Risk podiums and the PM visit (D1) | **Closed:** five podiums kept; risk podiums unlit / inactive; no simulated activity; no PM visit |
| DC-6 | Display sources (D3, D4) | **Closed:** pair `agent.task.completed` with `debate.turn.completed`; Contradiction Feed from `debate.completed` |
| DC-7 | Supervisor's reason to visit L3 | **Closed:** only `run.failed` of the debating run; visitor spot |
| DC-8 | Research Manager's arrival | **Closed:** at `debate.started` |
| DC-9 | Self-reported confidence | **Closed:** not shown |
| DC-10 | Contradiction Checker representation (Visual World Plan VW-6) | **Closed:** remote / data feed only; no holographic character |
| DC-11 | Exact dimensions | **Open** (after the tile scale, VB-3) |
| DC-12 | Exact colour values | **Open** (visual production, VB-4) |
