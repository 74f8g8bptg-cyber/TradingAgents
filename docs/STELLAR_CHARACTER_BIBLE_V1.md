# Stellar Character Bible V1

**Visual identity guide for Stellar agents in the 2.5D world**

| | |
|---|---|
| **Status** | V1, direction **approved by the owner**, with decisions K1–K6 and the CB rules applied (§10, §11). Visual design specification only: no code, no images, no assets, no runtime change |
| **Goal** | Easy recognition at medium zoom: distinct silhouettes, clear department identity, and a role you can read from the workstation. These are **not** movie characters: no backstories, no unnecessary personal detail |
| **References** | `STELLAR_VISUAL_BIBLE_V1.md` (§7 colours, §11 character rules); `STELLAR_CHARACTER_REGISTRY.md` v2 (IDs, departments, rooms, movement, the interim specialist adapter); `STELLAR_ROOM_REGISTRY.md` v2 (workstations and anchors); `STELLAR_VISUAL_WORLD_PLAN.md` (§6 states, §14.6 agents, §14.7 animation) |
| **Precedence** | The Character Registry remains the source of truth for **who exists**, their `technical_id`, room, anchor, movement class and status. This Bible defines only **how they look and move**. Differences are listed in §10 and not silently changed |

---

## 1. General character rules

**Recognition comes from six layers**, in this order of importance at medium zoom:

| # | Layer | Read at |
|---|---|---|
| 1 | **Workstation** (where the agent stands or sits) | overview |
| 2 | **Department colour** (shoulder yoke and cuffs) + **shape icon** | overview |
| 3 | **Silhouette** (garment cut + body base + height) | medium zoom |
| 4 | **Hairstyle** | medium zoom |
| 5 | **Role accessory** | medium zoom / room focus |
| 6 | **Clothing detail** (collar, belt, panels) | room focus |

**Scale and style:**

| Rule | Value |
|---|---|
| Height | About **80–90 % of the door-opening height**; the door height itself is open (§11, CB-1) |
| Proportions | Stylised, about **6–7 heads tall** (Visual World Plan §14.6). Realistic proportions, simplified for clarity |
| Faces | **Simple, and not to be made more detailed** (owner decision): readable eyes and brows, at most a simple mouth line; no pores, wrinkles or realistic skin detail. Faces are **not** a recognition layer at medium zoom |

**Avoid:**
- identical clones: no two rendered characters share the same body + hair + accessory combination (§7);
- overly realistic humans;
- unnecessary biological detail;
- personal backstories;
- expressions that imply emotion (Character Registry §3: no emotion language).

**Uniforms** (Character Registry §2.2, unchanged):
- a charcoal two-tone base garment;
- department colour on the shoulder yoke and cuffs;
- the department **shape icon** on the chest;
- **no rank insignia** (titles appear only in HUD text).

A **badge** accessory is an ID or access badge, never a rank mark. Badge designs are left to visual production (owner decision).

**Originality:** nothing is copied from Star Trek (no uniforms, delta or arrowhead badges, insignia
or interfaces) or from StarNet (no characters, sprites, skins, uniforms or visual identity). Only
StarNet's *ideas* are kept: readable agents, roles tied to spaces, believable movement and work
behaviour (adaptation A20, A13).

---

## 2. Department visual identity

| Department | Colour | Shape icon | Garment cut (silhouette cue) | Style | Main characters |
|---|---|---|---|---|---|
| **Command** | deep red, burgundy | hexagon | **Long tunic-coat** with a knee-length hem and a structured, squared shoulder line. The hem is the Command silhouette at medium zoom | leadership, coordination, professional | Supervisor, Central Trader, Portfolio Manager, Research Manager (+ Trade Proposal Builder) |
| **Research / Science** | blue, cyan | circle | **Fitted jacket** at hip length with a high collar; slim trousers. A visible data device in hand is common | analytical, scientific, technical | Metals, FX and Indices desks; research, validation, macro and technical agents; debaters; review; future Coach (advisory; owner decision K4) |
| **Risk / Operations** | gold, amber, charcoal | square | **Utility cut:** a structured vest over the base garment, with shoulder panels and a belt carrying tools. Broader and squarer than Research | control, precision, security | Risk Agent, Execution Agent (+ Contradiction Checker, Execution Checker, Data Validator, O2 personas) |
| **Synthetic / System** | white, cyan, metallic | diamond | **No uniform:** a smooth shell body with cyan light lines, and no hair | AI infrastructure, system technology | Habitat Host (Bix) |

**Habitat is a location style, not a department.** Agents in `H-HAB` keep their uniform. The
Habitat changes only the lighting and the furniture around them (Visual Bible §7, C5).

---

## 3. Reusable library (no hundreds of unique models)

Every rendered character is **one combination** from these small sets. The Character Registry ID
maps to a code such as `B2-H3-A4`.

### 3.1 Body bases (4) × height steps (3)

| Code | Body base | Silhouette note |
|---|---|---|
| **B1** | Slim, narrow shoulders | Reads tall and light |
| **B2** | Average | Neutral reference body |
| **B3** | Broad shoulders, solid torso | Reads strong and square; pairs well with the Operations vest |
| **B4** | Compact, shorter limbs | Reads small and quick |

The three height steps are **S** (short), **M** (medium) and **T** (tall), within the 80–90 % door
band. The same body base at two heights gives two distinct silhouettes.

### 3.2 Hairstyles (7)

| Code | Hairstyle |
|---|---|
| **H1** | Short crop |
| **H2** | Long hair, tied back (low ponytail) |
| **H3** | Curly, medium volume |
| **H4** | High bun / top knot |
| **H5** | Shaved / very short |
| **H6** | Medium swept (side part) |
| **H7** | Short hair **with beard** (beard as a modifier: `H1b` / `H5b` / `H6b`) |

Hair colours and skin tones come from token palettes (natural range, varied across the crew). They
are never used as a recognition layer on their own.

### 3.3 Accessories (role signals)

| Code | Accessory | Signals |
|---|---|---|
| **A1** | Tablet / data slate | analysis, research |
| **A2** | ID / access badge (clip-on) | access roles (Risk, Execution) |
| **A3** | Glasses | study, review |
| **A4** | Headset with a boom microphone | coordination, communication |
| **A5** | Technical tool belt / handheld scanner | engineering, checks |
| **A6** | Data device (glowing handheld cube or crystal) | data hand-offs (the prop `PRP-001` is separate and event-driven) |
| **A7** | Shoulder-mounted holo projector (small) | desk with several concurrent tasks |
| **A8** | Clipboard-style debrief pad | coaching, review |

**At most two accessories per character.** Accessories never carry live data: a device's screen
glow is decorative unless the Screen Registry binds a display to it.

---

## 4. Main characters

For each character: role, look, silhouette, clothing, hair, accessories, workstation, and main
animations (clips from §6).

### 4.1 Supervisor — `CHR-003` (O1 `supervisor`) · Command

| Field | Definition |
|---|---|
| Role | Run lifecycle, scheduling, pauses; event-driven room visits |
| Visual appearance | Upright, alert stance; the most "mobile" command figure |
| Silhouette | **B2 · T** + long tunic-coat. The tallest command figure |
| Clothing | Command tunic-coat, burgundy yoke; a slim belt |
| Hairstyle | **H4** high bun (adds height to the silhouette) |
| Accessories | **A4** headset, **A1** tablet |
| Workstation | `H-CMD` `command.console_ops` (`CON-003` wide operations console) |
| Main animations | stand-work at a wide console, look at screens, walk (visits), talk, meeting pose at the command table |

### 4.2 Central Trader — `CHR-004` (U4 `trader`) · Command

| Field | Definition |
|---|---|
| Role | Handles **all concurrent opportunities**; there is one Trader, never one per instrument |
| Visual appearance | Focused and seated; leans toward a triple display |
| Silhouette | **B3 · M** + tunic-coat worn open (the open front distinguishes it from the other command figures) |
| Clothing | Command tunic-coat, open; red yoke |
| Hairstyle | **H6b** medium swept with a short beard |
| Accessories | **A7** shoulder holo projector (reads as "juggling several items") |
| Workstation | `H-CMD` `command.console_trader` (`CON-004` triple-display console) |
| Main animations | sit-work at a console, **switch-card gesture** between concurrent opportunity cards (from real `DSP-CMD-09` items only), look at screens, talk |

### 4.3 Portfolio Manager — `CHR-001` (U8 `portfolio_manager`) · Command

| Field | Definition |
|---|---|
| Role | Approval strength (the typed rating); closes the risk debate |
| Visual appearance | Calm, still, central; the command-chair figure |
| Silhouette | **B1 · T** + the longest tunic-coat hem (ankle-length variant, the only one). Reads clearly even when seated |
| Clothing | Command tunic-coat, deep red yoke, high collar |
| Hairstyle | **H2** long hair, tied back |
| Accessories | **A2** badge; no hand device (hands free for the stamp gesture) |
| Workstation | `H-CMD` `command.chair` (`SEA-001` on the dais); visits `L3` `debate.judge_seat` |
| Main animations | sit in the command chair, **stamp gesture** (the rating, only on `decision.final.created`), look at the main viewscreen, walk, meeting pose |

### 4.4 Research Manager — `CHR-002` (U3 `research_manager`) · Command

| Field | Definition |
|---|---|
| Role | Judges the investment debate; writes the investment plan |
| Visual appearance | Studious command figure; often seen at the table or the judge seat |
| Silhouette | **B2 · M** + tunic-coat with a shorter (mid-thigh) hem, which distinguishes it from the PM |
| Clothing | Command tunic-coat, burgundy yoke |
| Hairstyle | **H3** curly |
| Accessories | **A3** glasses, **A1** tablet |
| Workstation | `H-CMD` `command.table_head` (`TBL-001`); `L3` `debate.judge_seat` during debates |
| Main animations | sit at a table, look at screens, listen / talk, meeting pose, walk (to L3), stamp (verdict, only on the real event) |

### 4.5 Metals Specialist desk — `CHR-022` · Research / Science

| Field | Definition |
|---|---|
| Role | **Metals family desk**: gold (XAU), silver (XAG). **Interim adapter** over one runtime agent today (S1 `specialist_xauusd`); XAG is `NOT CONFIGURED` |
| Visual appearance | Measured, precise analyst |
| Silhouette | **B3 · S** + Research jacket (short and broad: distinct from the slim research roles) |
| Clothing | Science jacket, blue yoke; a small **family tag** on the sleeve (a metals shape tag, not colour alone) |
| Hairstyle | **H5b** shaved with a beard |
| Accessories | **A1** tablet |
| Workstation | `L1` `specialists.desk_metals` (`CON-009` family desk) |
| Main animations | sit-work, look at screens, walk (hand-off to `H-CMD`, only on a real consumed `analysis.created`), talk |

### 4.6 FX Desk — `CHR-023` · Research / Science · **INTERIM ADAPTER**

| Field | Definition |
|---|---|
| Role | **FX family desk** representing **multiple runtime agents**: today S2 `specialist_eurusd` **and** S3 `specialist_usdjpy`. It is **not** one agent |
| Visual appearance | One desk figure working among **several floating task panels**, one panel per underlying runtime agent |
| Silhouette | **B1 · M** + Research jacket |
| Clothing | Science jacket, cyan yoke; FX family tag on the sleeve |
| Hairstyle | **H2** long hair, tied back |
| Accessories | **A7** shoulder holo projector (it drives the per-agent task panels) |
| Workstation | `L1` `specialists.desk_fx` (`CON-009`), with `DSP-SPC-02` above it |
| Main animations | sit-work, look at a panel; **no single "state" animation** (rules below) |

**Interim-adapter visual rules** (Character Registry §5.2; these are binding):
1. **One task panel and one state chip per underlying runtime agent.** EUR/USD (S2) and USD/JPY
   (S3) each show their **own task, own status and own activity**, side by side.
2. **Never merged.** The FX figure has **no single state badge**. There is no "highest-priority" or
   averaged state.
3. **Markers stay with their agent.** Error, overloaded, resting, paused and offline markers attach
   to that agent's panel and chip only, never to the figure.
4. **The body pose is neutral.** The figure works at the desk while **at least one** underlying
   agent is working, and is idle otherwise. The pose means "desk has activity", nothing more. It
   never plays the error beacon, overloaded or rest animation for the desk as a whole.
5. **Concurrent tasks.** When S2 and S3 work at the same time, both panels are active together, with
   a count ("FX · 2 active"). The figure does not "switch" between them in a way that suggests
   sequential work.
6. **Overview zoom.** A **split pip** (one segment per underlying agent), never one pip.
7. **Footer.** "Family desk · interim view of N runtime agents".

### 4.7 Indices Specialist desk — `CHR-025` · Research / Science

| Field | Definition |
|---|---|
| Role | **Indices family desk**: NAS100 first, extensible. **Interim adapter** over one runtime agent today (S4 `specialist_nas100`) |
| Visual appearance | Quick, energetic analyst |
| Silhouette | **B4 · S** + Research jacket (the smallest research figure) |
| Clothing | Science jacket, blue yoke; indices family tag on the sleeve |
| Hairstyle | **H1** short crop |
| Accessories | **A3** glasses, **A6** data device |
| Workstation | `L1` `specialists.desk_indices` (`CON-009`) |
| Main animations | sit-work, look at screens, walk (hand-off, event-driven), talk |

The interim rules of §4.6 apply to the Metals and Indices desks too; with one underlying agent each
today, they show one panel.

### 4.8 Risk Agent — `CHR-037` (P3 `risk_engine`) · Risk / Operations

| Field | Definition |
|---|---|
| Role | The deterministic Risk Engine / Risk Auditor: rule checks, sizing, exposure, and the breaker (display only) |
| Visual appearance | Precise and deliberate; the most "controlled" posture in the vessel |
| Silhouette | **B3 · T** + Operations vest with **extended shoulder panels** (the widest shoulder line in the crew) |
| Clothing | Operations vest over charcoal, gold yoke, amber piping |
| Hairstyle | **H1** short crop |
| Accessories | **A2** access badge, **A5** handheld scanner |
| Workstation | `L10` `risk.rule_console` (`CON-013`); also `risk.sizing_console`, `risk.breaker_panel` (restricted anchors) |
| Main animations | stand-work at a console, **checklist sweep** (lines light one by one, only on `risk.check.*`), stamp (approved / rejected, display time only), lever pose (only on a real `circuit_breaker.*`), walk |

**Separate character:** the Contradiction Checker `CHR-036` (P2) also works in L10. It is a
**different** runtime agent and figure (§7 table), never merged into the Risk Agent.

### 4.9 Execution Agent — `CHR-039` (E1 `paper_execution`) · Risk / Operations

| Field | Definition |
|---|---|
| Role | Paper order submission only (the Paper Broker; there is no DEMO or LIVE path) |
| Visual appearance | Hands-on operator |
| Silhouette | **B4 · M** + Operations vest with a **tool belt** (compact, busy outline) |
| Clothing | Operations vest, gold yoke; gloves |
| Hairstyle | **H3** curly (tied back when working) |
| Accessories | **A5** tool belt, **A2** access badge |
| Workstation | `L9` `execbay.launch` (`CON-017`); collects orders at `L10` `risk.outbox_pickup` |
| Main animations | stand-work at a console, **carry** (order capsule `PRP-005`, only after `risk.approved` + `order.created`), launch gesture (only on real `order.*`), walk |

**Separate character:** the Execution Checker `CHR-038` (P4) also works in L9. It is a different
runtime agent and figure.

### 4.10 Performance & Wellbeing Coach — `CHR-046` (future) · Research / Science (advisory)

| Field | Definition |
|---|---|
| Role | **Future** (not rendered until R1 and the role exist). Debrief, repeated-error review, workload balance, recovery recommendations, using **measurable system signals only** |
| Visual appearance | Approachable and calm; reads as a facilitator, not an authority |
| Silhouette | **B2 · S** + Research jacket in a **softer cut** (rounded shoulders, no high collar) |
| Clothing | Science jacket, lighter blue yoke. **Advisory, blue / research-adjacent; not Command, not Risk** (owner decision K4) |
| Hairstyle | **H6** medium swept |
| Accessories | **A8** debrief pad |
| Workstation | `R1` `coaching.console` (future); `coaching.table_1`…`4` for debriefs |
| Main animations | sit at a table, talk / listen, meeting pose, look at screens, walk |
| Never | Emotion, mood or psychiatric cues in pose, expression or props; no authority gestures (no stamp, no lever) |

---

## 5. Remaining cast (library assignment)

Each other rendered character gets one library code, so no two figures share body + hair +
accessory. Uniform department follows the Character Registry.

| ID | Role | Dept | Code | Accessory / cue |
|---|---|---|---|---|
| `CHR-005` | Trade Proposal Builder | CMD | B4·S-H6 | A6 data device (carries the proposal card when the event exists) |
| `CHR-006` | Bull Researcher | SCI | B2·M-H6 | A1 |
| `CHR-007` | Bear Researcher | SCI | B1·T-H5 | A1 |
| `CHR-008` | Aggressive Risk Debater | SCI | B4·M-H5 | A6 |
| `CHR-009` | Conservative Risk Debater | SCI | B2·T-H1b | A3 |
| `CHR-010` | Neutral Risk Debater | SCI | B1·S-H4 | A1 |
| `CHR-011` | Causal / Macro Analyst | SCI | B2·T-H2 | A3 + A1 |
| `CHR-012` | Central Bank Research | SCI | B1·M-H1 | A4 |
| `CHR-013` | Economic Data Research | SCI | B4·M-H4 | A1 |
| `CHR-014` | Market News Research | SCI | B2·S-H3 | A4 |
| `CHR-015` | Geopolitical Research | SCI | B3·M-H1b | A1 |
| `CHR-016` | Rates / Bonds Research | SCI | B1·T-H3 | A3 |
| `CHR-017` | Earnings Research | SCI | B2·M-H5 | A6 |
| `CHR-018` | Source Validator | SCI | B3·S-H1 | A5 scanner |
| `CHR-019` | Freshness Checker | SCI | B1·S-H3 | A5 |
| `CHR-020` | Duplicate / Consistency Detector | SCI | B2·T-H6 | A1 |
| `CHR-021` | Fact / Reaction / Interpretation Classifier | SCI | B4·T-H2 | A3 |
| `CHR-026` | Market Session | SCI | B3·M-H5 | A4 |
| `CHR-027` | Market Structure | SCI | B2·M-H1b | A1 |
| `CHR-028` | Technical Indicator | SCI | B1·M-H6 | A3 |
| `CHR-029` | Candle / Price Action | SCI | B4·S-H5 | A6 |
| `CHR-030` | Pullback / Setup | SCI | B2·S-H2 | A1 |
| `CHR-031` | Entry Timing | SCI | B1·S-H1 | A4 |
| `CHR-032` | Technical Analyst | SCI | B3·T-H3 | A3 + A1 |
| `CHR-033` | Post-Trade Reviewer | SCI | B2·T-H5b | A8 |
| `CHR-034` | Performance / Attribution | SCI | B1·M-H3 | A3 |
| `CHR-035` | Data Validator | OPS | B3·M-H4 | A5 |
| `CHR-036` | Contradiction Checker | OPS | B1·T-H4 | A5 scanner + A2 |
| `CHR-038` | Execution Checker | OPS | B2·M-H5b | A1 + A2 |
| `CHR-041` | Medic persona (O2) | OPS | B2·S-H5b | A5 (medical-style scanner) |
| `CHR-042` | Quartermaster persona (O2) | OPS | B4·T-H1 | A1 |
| `CHR-043` | Habitat Host (Bix) | SYN | synthetic shell | a floating tray (no hair, no uniform) |
| `CHR-044`, `CHR-045` | Lab Explorer / Validator (future) | SCI | B3·S-H2 / B4·M-H6 | A1 / A5 (not rendered) |
| `CHR-040` | MT5 Execution (deferred) | OPS | — | not rendered (no figure designed until the owner lifts the deferral) |
| `CHR-024` | — | — | — | RETIRED |

---

## 6. Animation library (simple and reusable)

**Budget rule (owner decision):** the animation set stays **lightweight and reusable**: one shared
clip set for every figure, few frames per clip, no per-character bespoke animation. Exact frame
counts are measured in the renderer spike (VB-11).

All characters share **one clip set**, in **8 facings**. The state catalogue (Visual World Plan
§6.2) picks the clip; a clip never implies a state that telemetry did not report.

| Clip | Used for | Notes |
|---|---|---|
| `walk` | movement between rooms (after the badge updates) | Eased; corner arcs (A7); fades out and in when late |
| `stand_idle` | `idle` at the workstation | Minimal breathing only; no fidgeting that looks like work |
| `sit_work` / `stand_work` | analysing, researching, validating, monitoring | Loops calmly at the console |
| `look_screen` | reading a room display | A head and torso turn toward the bound screen |
| `talk` / `listen` | debate turns, operational meetings, ambient conversation while idle | **Only from real events, real tasks or idle behaviour** (owner decision K6); neutral gestures; **no emotional simulation** |
| `meeting` | standing at the command table (`run.started` gathering), debriefs | **Only from real events or tasks** (owner decision K6) |
| `wait` | `waiting` | Seated or standing, with the hourglass badge |
| `carry` | event-driven hand-offs (`PRP-001` / `003` / `005`) | Only when the triggering event exists |
| `stamp` | PM rating, RM verdict, Risk approved / rejected | Display time only |
| `checklist_sweep` | Risk and validation checks | Lines light one by one |
| `lever` | breaker display (Risk Agent) | Only on a real `circuit_breaker.*` |
| Overlays: `error_beacon`, `overloaded`, `paused_freeze`, `rest_pod` | state overlays | Attached to the agent (for family desks, to the agent's **panel**, §4.6) |

Ambient clips (café sit, billiards, window bench) reuse `sit_work`, `stand_idle` and `talk` with
Habitat props. They are seeded and deterministic (A14), and never shown while a real task is
active (work over idle, A13).

---

## 7. Uniqueness and readability checks (for the art pass)

1. **No two rendered characters share the same body · height + hairstyle** (and therefore no
   identical body + hair + accessory set), checked against §4 and §5.
2. In each room, neighbours at the same workstation type differ in **at least two** of: body base,
   height, hairstyle.
3. **Department readable in greyscale:** the garment cut (coat / jacket / vest / shell) and the
   shape icon identify the department without colour (Visual Bible, "state never colour alone").
4. **Readable at medium zoom:** workstation, department and silhouette are identifiable at hub
   view; the accessory at room focus.
5. **Under all four alert tints** (GREEN, BLUE, AMBER, RED), the department colours stay
   distinguishable.

---

## 8. What StarNet contributes (ideas only)

| Kept (as ideas) | Not copied |
|---|---|
| Readable agents at small scale; roles tied to places; believable walking (eased gait, corner arcs); work pre-empting idle; seat and anchor use | StarNet art, sprites, skins, characters, uniforms, recolouring recipes, the idle "sentience" behaviours (mourning, chase, mimic), visual identity (adaptation A30, A31) |

---

## 9. Human variation rules (summary)

- **Silhouette variety:** 4 body bases × 3 heights.
- **Hair variety:** short, long tied, curly, bun, shaved, swept; beard as a modifier.
- **Skin and hair colours:** natural token palettes, spread across the crew. Never assigned by
  department or role.
- **Accessories:** one or two role accessories per character, from §3.3.
- **Age:** varied through hair colour and posture only; no age-detail textures.
- **Library size:** 4 bodies × 3 heights, 7 hairstyles (+ beard) and 8 accessories cover the
  **41 rendered V1 characters** (40 human figures + the synthetic Habitat Host) and the 3 future
  figures, each with a unique body · height + hairstyle.

---

## 10. Contradictions and owner decisions (all resolved)

| # | Topic | Owner decision | Applied in |
|---|---|---|---|
| **K1** | Risk Agent / Execution Agent vs two runtime agents per room | **Keep** the Risk Agent (`CHR-037`, P3) and the Execution Agent (`CHR-039`, E1) as the main visual figures. **Do not merge** the other runtime agents: the Contradiction Checker (`CHR-036`) and the Execution Checker (`CHR-038`) stay separate figures | §4.8, §4.9, §5 |
| **K2** | Family desks | Keep the family-desk model: **Metals Desk, FX Desk, Indices Desk**. **FX remains the special interim adapter** because it represents several runtime agents; their states are **never merged** | §4.5–§4.7 |
| **K3** | Trade Proposal Builder | Remains **Command** | §5 (`CHR-005`) |
| **K4** | Performance Coach | **Advisory** role; **blue / research-adjacent** colour; **not Command, not Risk** | §4.10; Character Registry §7 and CR-2 aligned |
| **K5** | Door height | **Remains open** | §11 CB-1 |
| **K6** | Talk and meetings | Allowed **only from real events, tasks or idle behaviour**. **No emotional simulation** | §6 |

**Additional owner rules:**
- simple faces and readable silhouettes;
- no increase in facial detail;
- a lightweight, reusable animation budget;
- exact colours and badge designs are left to visual production.

---

## 11. Open decisions

| # | Decision | Status |
|---|---|---|
| CB-1 | Door-opening height (needed for the 80–90 % rule), together with the tile scale | **Open** (K5; VB-3) |
| CB-2 | Risk Agent / Execution Agent mapping | **Closed** (K1) |
| CB-3 | Coach department colour | **Closed**: advisory blue (K4) |
| CB-4 | Exact colour tokens (uniforms, skin palette, hair palette) | **Open**: visual production (VB-4) |
| CB-5 | Family-desk sleeve tags and badge designs | **Open**: visual production |
| CB-6 | Face detail | **Closed**: simple faces (eyes, brows, at most a simple mouth line); detail is not increased |
| CB-7 | Animation budget | **Closed as a rule**: lightweight, reusable, one shared clip set. Exact frame counts are measured in the renderer spike (VB-11) |
| CB-8 | Habitat Host form (current synthetic shell vs a simpler drone) | **Open** (not decided) |
