# Stellar Agents — Layer Design

| | |
|---|---|
| **Status** | v0.4 — approved design, reconciled with the approved Foundation Plan (§8.3). No code yet (Foundation Phase 0). Decisions recorded in §8 |
| **Date** | 2026-09-29 (reconciled 2026-09-30) |
| **Related documents** | `docs/STELLAR_FOUNDATION_PLAN.md` (v0.3, approved) is **canonical** for phases, rosters, contracts and decisions; `docs/STELLAR_MASTER_ROADMAP.md` is the overview. This document holds the architecture and visual-station detail. Phase numbers below are Foundation Plan phases unless marked as a theme (LD-n) |
| **Built on** | Tauric Research TradingAgents v0.5.2 (the "upstream core") |
| **Scope** | An intergalactic trading-station layer on top of TradingAgents: telemetry, hard risk control, an MT5/Vantage **demo** execution layer, and a live visual station |
| **Out of scope** | Live-money trading. No design here authorises orders on a real-money account. |

---

## Contents

1. [Overall architecture](#1-overall-architecture)
2. [Space-station visual concept](#2-space-station-visual-concept)
3. [Agent system](#3-agent-system)
4. [Event model](#4-event-model)
5. [UI and visual states](#5-ui-and-visual-states)
6. [Performance metrics](#6-performance-metrics)
7. [Implementation themes](#7-implementation-themes)
8. [Decisions on the open questions](#8-decisions-on-the-open-questions)
9. [Appendix: upstream surfaces referenced](#appendix-upstream-surfaces-referenced)

---

## 1. Overall architecture

### 1.1 Guiding principles

1. **Upstream is the engine, Stellar is the station built around it.** TradingAgents stays a clean,
   mergeable copy of the Tauric Research repository. Stellar *imports* `tradingagents`;
   `tradingagents` never imports Stellar.
2. **Observe, don't rewrite.** Stellar gets its live picture of the agents from the hooks upstream
   already exposes: LangChain callbacks, `stream_run()`, the returned final state and the memory
   log. It does not patch agent prompts or graph wiring.
3. **An LLM proposes, code decides.** Upstream's output is a *rating* (Buy / Overweight / Hold /
   Underweight / Sell, or the non-tradeable `REVIEW`). Turning a rating into an order goes through
   Stellar's **deterministic** risk gate. No LLM text can size, approve or send an order.
4. **Fail closed.** If telemetry, risk data, account state or the broker bridge are missing or
   ambiguous, nothing trades. The visual station can go dark; the vault door stays shut.
5. **Visuals never lie.** Every animation is derived from a real event. Movement and "life" are
   decoration layered on top of a truthful status badge, never a replacement for it.
6. **Paper first, then demo only.** Stellar Agents V1 is functionally complete with paper
   trading, reached at the Foundation Phase 7 exit; the MT5 / Vantage demo is a separate
   integration and validation gate after a stable paper V1 (Foundation D-15). The execution layer refuses to act unless the connected account
   proves it is a demo account (see §7, theme LD-4 / Foundation Phase 8). No live mode exists.
7. **Model-provider agnostic, tiered by value (§8 Q4).** No Stellar component names a specific LLM
   provider or model. Routine agents use lower-cost, fast models; manager and other high-value
   reasoning roles use stronger models. This extends upstream's existing quick/deep split. The
   exact models and the daily budget stay in configuration until call volume and cost are
   benchmarked.
8. **Market data is separate from execution (§8 Q3).** Stellar owns a market-data abstraction.
   The broker interface never serves analysis data, and the data layer never places orders, even
   when MT5 later backs both.

### 1.2 Layered view

```
+--------------------------------------------------------------------------------+
|  STATION UI  (browser)                                                         |
|  2D station map · agent avatars · room panels · metrics · event log · replay   |
+-------------------------------------^------------------------------------------+
                                      |  WebSocket (live events) + REST (snapshots, history)
+-------------------------------------+------------------------------------------+
|  STELLAR LAYER  (new, separate package: stellar/)                              |
|                                                                                |
|  runner        Stellar graph + supervisor; schedules runs; sets market focus   |
|  research      collectors · validators · research store · macro · specialists |
|  telemetry     event schema · bus · LangChain handler · state observer · store |
|  agents        roster: agent ids, groups, home rooms, visual metadata          |
|  risk          risk engine: proposal rules · sizing · exposure · breaker      |
|  execution     broker interface · paper broker · MT5 bridge client             |
|  metrics       global · per-agent · contribution · risk · wellbeing            |
|  station       rooms · state→visual mapping · movement rules                   |
|  api           FastAPI (or similar) server for the UI                          |
+------+---------------------+-------------------------+--------------------------+
       | imports / calls      | reads                   | talks to (network, narrow API)
       v                      v                         v
+------------------------+  +---------------------+  +--------------------------------+
|  TRADINGAGENTS (core)  |  | memory log, reports |  | MT5 BRIDGE (Windows host)      |
|  UNTOUCHED UPSTREAM    |  | results_dir (files) |  | MetaTrader 5 terminal logged   |
|  graph · agents ·      |  +---------------------+  | into a Vantage DEMO account    |
|  dataflows · llm ·     |                           +--------------------------------+
|  memory · backtest     |
+------------------------+
```

### 1.3 What stays untouched

Nothing under these paths is modified by Stellar. They are upstream-owned and merged from
`TauricResearch/TradingAgents`.

| Path | Why it stays untouched |
|---|---|
| `tradingagents/` (all of it) | The engine: graph, agents, prompts, dataflows, LLM clients, memory, backtest |
| `cli/` | Upstream's terminal app; still usable as-is for plain TradingAgents runs |
| `tests/` | Upstream's test suite (1139 tests at v0.5.2); must keep passing after every upstream merge |
| `main.py`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` | Upstream packaging and runtime |
| `.github/workflows/ci.yml` | Upstream CI (tests, clean install, ruff) |

**Rule:** if a Stellar feature appears to need an upstream change, it is first solved in the Stellar
layer (wrapping, observing, composing). Only if that is impossible do we prepare a small, generic
patch suitable for contributing **upstream** as a pull request, rather than carrying a private fork
diff.

### 1.4 What gets added

All new material lives in new paths, so upstream merges never conflict:

```
stellar/                         # separate installable project (own pyproject.toml)
  pyproject.toml                 # depends on the local tradingagents package
  src/stellar/
    runner.py                    # StellarRun: wraps TradingAgentsGraph, emits events
    pipeline.py                  # Stellar graph for the first four markets (§1.6)
    agents/analysts/             # Stellar-owned market/technical analysts (§1.6)
    config.py                    # Stellar config (risk limits, schedule, broker, UI)
    agents/roster.py             # agent registry: ids, groups, rooms, visual metadata
    telemetry/                   # events.py, bus.py, store.py,
                                 # langchain_handler.py, state_observer.py
    marketdata/                  # source.py (interface), symbols.py (Stellar ↔ provider ↔ broker
                                 # symbol map), one module per provider; mt5.py later (§8 Q3)
    research/                    # collectors, validators, research store (Foundation §4.29)
    analysis/                    # structure, indicators, price action, setups, entry timing,
                                 # macro and market-specialist assessments (Foundation §4.9–4.12)
    risk/                        # risk engine: proposal rules, sizing, exposure, breaker (§3.7)
    execution/                   # broker.py (interface), paper.py, mt5_client.py
                                 # (never imports marketdata providers directly; gets quotes
                                 #  through the marketdata interface)
    metrics/                     # global_.py, per_agent.py, contribution.py, wellbeing.py
    station/                     # rooms.py, visual_states.py (shared JSON with the UI)
    api/                         # server.py (REST + WebSocket)
  tests/                         # Stellar's own tests, including upstream contract tests
stellar_ui/                      # browser front end (Foundation Phase 9+)
mt5_bridge/                      # small service run on the Windows host (Foundation Phase 8)
docs/STELLAR_LAYER_DESIGN.md     # this document
docs/STELLAR_FOUNDATION_PLAN.md  # canonical build plan (module paths in its §11)
docs/STELLAR_MASTER_ROADMAP.md   # overview
.github/workflows/stellar.yml    # Stellar CI (new file; upstream ci.yml untouched)
```

Keeping Stellar as a **separate project with its own `pyproject.toml`** means the root
`pyproject.toml` (upstream-owned) never needs editing to add a package. Install is
`pip install -e . -e ./stellar`.

> Note: upstream's CI runs `ruff check .` over the whole repository, so Stellar code must stay clean
> under upstream's ruff rules too. That is a feature, not a cost.

### 1.5 Where Stellar connects to TradingAgents

These are the **only** integration points. Each is a public (or de-facto public) surface of
upstream. The Stellar test suite pins each one with a contract test so that an upstream merge that
changes it fails loudly in Stellar CI instead of silently breaking the station.

| # | Upstream surface | Stellar uses it for | Stability risk |
|---|---|---|---|
| C1 | `TradingAgentsGraph(selected_analysts, debug, config, callbacks)` | Building a run; injecting the Stellar LangChain callback handler | Low |
| C2 | `callbacks=[...]` → LangChain `on_chat_model_start / on_llm_end / on_tool_start / on_tool_end / on_*_error` | LLM and tool telemetry: tokens, latency, errors, which agent is "thinking" | Low (LangChain API); **the node name in callback metadata must be verified** (see C2 note) |
| C3 | `create_run_state()`, `stream_run()`, `record_decision()`, `clear_checkpoint_on_success()`, `begin/end_checkpoint()` | The same run path `cli/run.py` uses, so Stellar gets per-step state while keeping memory logging and checkpoints | Medium: upstream refactors this area often |
| C4 | `propagate(ticker, date, asset_type, portfolio)` → `(final_state, rating)` | Simple non-streaming runs (batch jobs, tests) | Low |
| C5 | `AgentState` field names (`market_report`, `investment_debate_state`, `risk_debate_state`, `trader_investment_plan`, `final_rating`, …) | The state observer diffs successive states to derive events | Medium |
| C6 | Graph node names (`"Market Analyst"`, `"Bull Researcher"`, `"Portfolio Manager"`, …) and the debate speaker conventions (`current_response` starting with "Bull"/"Bear", `latest_speaker`) | Mapping upstream nodes to Stellar agent ids | Medium: these strings are hard-coded in `graph/setup.py` and `conditional_logic.py` |
| C7 | `agents/rating.py`: `RATINGS_5_TIER`, `RATING_REVIEW`, `is_review()` | Reading the final rating as the approval strength of a setup (R-1); blocking `REVIEW` | Low |
| C8 | `portfolio.PortfolioContext` / `Position` | Passing the demo account's real positions and cash into a run, so agents size against the actual book | Low |
| C9 | `memory.TradingMemoryLog.load_entries()` (rating, raw return, alpha, holding days) | Decision-quality and contribution metrics | Low–medium (markdown format) |
| C10 | `DEFAULT_CONFIG` keys (`llm_provider`, `data_vendors`, `max_debate_rounds`, `results_dir`, …) | Configuring runs per market | Low |
| C11 | `backtest.run_backtest / summarize` | Offline evaluation and ablation studies for contribution metrics | Low |
| C12 | Public agent factories in `tradingagents.agents` (`create_bull_researcher`, `create_bear_researcher`, `create_research_manager`, `create_trader`, the three risk debaters, `create_portfolio_manager`), `AgentState` / `InvestDebateState` / `RiskDebateState`, and `ConditionalLogic` | Building the Stellar market pipeline (§1.6): upstream's downstream agents run unchanged after Stellar-owned analysts | Medium: prompts read specific state keys (e.g. the Trader reads `market_report`) |

**C2 note.** LangGraph normally attaches the running node's name (`langgraph_node`) to the metadata
that callbacks receive. Upstream binds the callbacks to the LLM objects in their constructors rather
than per invocation. A Foundation Phase 6 spike must confirm the node name still arrives in that setup. If it
does not, the state observer (C3/C5) is the fallback source of "who is working". It is coarser but
always available.

### 1.6 Stellar market pipeline for the first four markets (§8 D1)

For **XAU/USD, EUR/USD, USD/JPY and NAS100**, Stellar does **not** patch, extend or modify
upstream's data-provider code (`tradingagents/dataflows/`), and does not change upstream's
analysts. Instead:

1. **Stellar-owned market-data adapters** (`stellar/marketdata/`, §1.4) supply quotes, OHLCV bars
   and symbol metadata for these instruments.
2. **Stellar-owned research and technical chain** (Foundation §4.29, §5.1): research roles,
   source validators, the Causal/Macro Analyst and the market specialists, plus deterministic
   technical agents and the LLM Technical Analyst, using only Stellar data. They write the **same
   report keys** upstream's downstream agents read: `market_report` ← Technical Analyst;
   `news_report` ← Causal/Macro and market-specialist assessments; `sentiment_report` empty in
   V1; `fundamentals_report` empty (later optionally the NAS100 earnings summary). Empty reports
   are already treated by upstream's agents as "no report".
3. **Stellar assembles its own LangGraph graph** for these markets (`stellar/pipeline.py`). It
   uses upstream's `AgentState` and **imports upstream's downstream agents unchanged**: Bull/Bear
   researchers, Research Manager, Trader, the three risk debaters and the Portfolio Manager
   (C12). It reuses upstream's orchestration pattern (analysts in parallel → investment debate →
   trader → risk debate → final rating) and upstream's `ConditionalLogic` for turn-taking.
4. **The Stellar Journal is the system of record** (Foundation §4.24). Upstream's
   `TradingMemoryLog` (C9) is optional and limited to profiles with at most one decision per
   instrument per day (open decision D-10; default: not used). Outcomes are settled from Stellar's
   own trades, not from upstream's settlement.
5. **"Where compatible" is checked, not assumed.** Each reused upstream component is pinned by a
   Stellar contract test that runs it inside the Stellar pipeline with fake LLMs. If an upstream
   release breaks compatibility, Stellar replaces that one component with a Stellar-owned version
   rather than patching upstream.

```
Stellar marketdata adapters ──> technical agents (setup) ──────────┐   (Stellar-owned)
research → validation → Causal/Macro → market specialist ──────────┤
                                                                   v
           upstream Bull ⇄ Bear → Research Manager → Trader →          (upstream code,
           Aggressive → Conservative → Neutral → Portfolio Manager      imported unchanged)
                                                                   v
   final_rating → Trade Proposal Builder (setup-first) → risk engine → execution   (Stellar-owned)
```

Consequences:
- For these markets, telemetry hooks the **Stellar pipeline** directly (callbacks and its own
  stream), so C3/C4 (`TradingAgentsGraph` run methods) apply only to plain upstream runs, such as
  stocks through the unmodified engine.
- Upstream's News and Sentiment Analysts are not in V1. They may be evaluated after V1 as
  additional research inputs that pass through the same validation (Foundation §5.3).
- Upstream's `TradingAgentsGraph` remains fully usable for the markets it already supports.

### 1.7 Run lifecycle through the layers

For the four markets (canonical agent codes from Foundation §5.1; event names per §4.3):

```
Supervisor (O1) picks focus (e.g. EURUSD) on a setup-timeframe close
  -> Data Validator (T1) builds a MarketSnapshot           -> snapshot.created
  -> technical agents T2–T6 assess; Pullback/Setup (T6)   -> analysis.created, setup.state.changed
  -> no candidate Setup: stop here (no LLM chain this cycle)
  -> research snapshot (validated items from R*/V*)       -> research.snapshot.created
  -> Causal/Macro (M1), focus specialist (S*), Technical Analyst (T8) -> analysis.created
  -> Stellar graph: upstream Bull/Bear, Research Manager, Trader, Risk Debaters, Portfolio Manager
        | callbacks   -> agent.llm_call.*, agent.tool_call.*          (C2)
        | state diffs -> debate.*, decision.*                          (C5/C6)
  -> final_rating --(C7)--> Trade Proposal Builder (P1, setup-first)  -> trade.proposed
  -> Contradiction Checker (P2) -> Risk Engine (P3)                    -> risk.approved | risk.rejected
        | approved: order intent; Entry Timing (T7) triggers on the entry timeframe
        |           -> Execution Checker (P4) -> Paper Execution (E1)  -> order.* / trade.closed
        |           (MT5 Execution E2 only after the demo gate, Foundation Phase 8)
        | rejected: shadow-tracked as a paper proposal for counterfactual metrics
  -> Post-Trade Reviewer (L1), Attribution (L2)                        -> memory.*
  -> all events -> bus -> event store + journal -> WebSocket -> Station UI
```

Plain upstream runs (e.g. a stock through the unmodified engine) still follow
`TradingAgentsGraph.create_run_state()` → `stream_run()` → `record_decision()` (C3).

---

## 2. Space-station visual concept

> **Topology superseded (visual layer only).** The station map, rooms, lifts, vault and airlock described in this section belong to the earlier stacked-deck concept. The owner-approved physical topology is `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C** (a flat vessel with 3 hubs, L1–L10, R1–R6 and 21 explicit doors), detailed in the Visual Foundation v2 registries (`STELLAR_STATION_TOPOLOGY.md`, `STELLAR_ROOM_REGISTRY.md`, `STELLAR_CHARACTER_REGISTRY.md`, `STELLAR_SCREEN_REGISTRY.md`, `STELLAR_ASSET_REGISTRY.md`). Risk isolation is now a logical access rule (Risk Control Room L10, Execution Bay L9), not a vault, lift or airlock. The engine's rules (risk gate before execution; the UI never writes) are unchanged.

### 2.1 Design idea: the floor plan is the control flow

The station layout mirrors the real pipeline, so someone watching can understand the system by
watching where agents walk:

- Reports flow **inward** from the analysis wings to the Debate Chamber, then **up** to the Command
  Deck.
- A decision leaves the Command Deck **down** a central lift into the **Risk Control Vault**.
- The **only agent door into the Execution Bay is the one-way airlock from the Vault.** Nothing
  reaches the launch tubes without passing the vault, which is how the real system works.
- The **Data Core** is the station's reactor and spine. Every data fetch is drawn as a beam from a
  room down to the core.
- The **Habitat Ring** (Wellbeing, Lounge/Café/Billiards) is where agents go when they are not on
  duty, overloaded or cooling down.

**Art direction (§8 Q7).** The interior of a futuristic spaceship / trading station in a
**semi-realistic, stylized sci-fi** look. **Not pixel art.** Large wall-sized screens, command
rooms, lit corridors, analysis stations, the risk-control vault, the execution bay, and a habitat
area with the lounge, café, billiard room and wellbeing spaces.

### 2.2 Station map

```
                    +-----------------------------------+
                    | MAIN COMMAND DECK                 |
                    | Portfolio Mgr (captain's chair)   |
                    | Research Mgr · Trader · Proposal  |
                    | Builder · Supervisor · alerts     |
                    +-----------------+-----------------+
                                      | central lift
+---------------------+   +-----------+-----------+   +---------------------+
| MARKET ANALYSIS     |   | DEBATE CHAMBER        |   | MACRO & NEWS        |
| WING                |===| inner ring: bull vs   |===| OBSERVATORY         |
| structure, momentum |   | bear (investment)     |   | research roles ·    |
| price action, setup |   | outer ring: risk      |   | causal / macro      |
| entry timing; desks |   | debaters (3 seats)    |   | analyst             |
| XAU EUR JPY NAS100  |   |                       |   |                     |
+----------+----------+   +-----------+-----------+   +----------+----------+
           |                          | central lift             :
+----------+----------+   +-----------+-----------+   +----------+----------+
| MEMORY ARCHIVE      |   | RISK CONTROL VAULT    |   | EXECUTION BAY       |
| post-trade review · |   | contradiction check · |##>| execution checker · |
| attribution ·       |   | risk engine · breaker |   | paper execution;    |
| journal             |   | (vault door)          |   | MT5 demo relay      |
|                     |   |                       |   | after V1            |
+----------+----------+   +-----------+-----------+   +----------+----------+
           |                          |                          :
+----------+--------------------------+--------------------------+----------+
|                                 DATA CORE                                 |
|         data validator · research validators · market-data caches         |
|                   telemetry bus · event store · journal                   |
+-------------------------------------+-------------------------------------+
                                      |
        ========================== HABITAT RING ==========================
        |   WELLBEING ROOM (wellbeing  |   LOUNGE  ·  CAFÉ  ·  BILLIARD     |
        |   monitor, rest pods)        |   ROOM (off-duty agents)           |
        +------------------------------+------------------------------------+

 ===  open corridor        |  corridor / lift
 ##>  one-way airlock (the only agent entrance to the Execution Bay)
  :   data conduit only (market ticks, fills); agents cannot pass
```

### 2.3 Rooms

| Room | Purpose (real system) | Who is there | Key visual elements |
|---|---|---|---|
| **Main Command Deck** | Final decisions, proposals and orchestration | Portfolio Manager (U8), Research Manager (U3), Trader (U4), Trade Proposal Builder (P1), Supervisor (O1) | Captain's chair; main viewscreen with the focus instrument's chart, the current Setup and the rating; **station alert lights** (§5.4); run queue; the global metrics strip |
| **Market Analysis Wing** | Deterministic technical analysis; instrument desks | Market Session (T2), Market Structure (T3), Technical Indicator (T4), Candle / Price Action (T5), Pullback / Setup (T6), Entry Timing (T7), Technical Analyst (T8); market specialists S1–S4 at the XAU/USD, EUR/USD, USD/JPY and NAS100 desks | Holo chart tables that draw structure levels, indicators and candle features as they are computed; a session world clock; one desk per instrument |
| **Macro & News Observatory** | Research and macro/causal analysis | Research roles R1–R6 (as active), Causal / Macro Analyst (M1) | Telescope toward a "news nebula"; incoming research items as stars, dimmed when rejected by validation; a driver board for the macro assessment with its coverage |
| **Debate Chamber** | Investment debate and risk debate | Bull & Bear Researchers (inner ring), Aggressive / Conservative / Neutral Risk Debaters (outer ring) | Podiums around a central evidence stage (inner pair, outer arc; open and level); neutral podium lights with side icon + text; a round counter (`round n / max`); no score, balance bar or winner (L3 sheet D5) |
| **Risk Control Vault** | Deterministic risk gate | Contradiction Checker (P2), Risk Engine (P3) with its Vault personas (proposal checks, sizing, exposure, breaker) | The vault door (closed by default); a rule checklist that lights each check pass/fail; exposure bars against limits; the kill-switch lever (glows red when engaged) |
| **Execution Bay** | Order routing | Execution Checker (P4), Paper Execution Agent (E1); MT5 Execution Agent (E2) only after the demo gate | Launch tubes (orders as shuttles); a docking board of open positions with live P&L; a "PAPER" or "DEMO" hull marking always visible; bridge link status once MT5 exists |
| **Data Core** | Market data, research validation, telemetry | Data Validator (T1), research validators V1–V4 | Reactor column that brightens with request volume; one conduit per market-data and research source, coloured by health; the telemetry bus and journal |
| **Memory Archive** | Journal, post-trade review, attribution | Post-Trade Reviewer (L1), Performance / Attribution (L2) | Crystal shelves, one crystal per trade, which light up green or red once settled; the review scriptorium |
| **Wellbeing Room** | Operational health: cooldown, retries, rest | Operational Wellbeing Monitor (O2), shown as the Station Medic and Quartermaster personas; any agent that is resting or overloaded | Rest pods; a vitals board (load, error rate, budget); recharge animation |
| **Lounge / Café / Billiard Room** | Off-duty space; pure ambience | Café Host (cosmetic); agents not needed in the current cycle | Café counter; billiard table; windows onto the galaxy; the "hall of fame" (best-calibrated agents, with sample sizes) |

---

## 3. Agent system

The canonical rosters (architectural, minimum executable V1, deferred) are in the Foundation
Plan §5 (R-4). This section gives each role's room, metrics, states and visuals for the station.
Codes (R1, T5, P3, …) are the Foundation Plan's.

### 3.1 Agent groups at a glance

| Group | Agents | Nature | Source |
|---|---|---|---|
| Research | R1 Central Bank, R2 Economic Data, R3 Market News, R4 Geopolitical, R5 Rates/Bonds, R6 Corporate/Earnings | Deterministic retrieval + LLM extraction | Stellar |
| Research validation | V1 Source Validator, V2 Freshness Checker, V3 Duplicate Detector, V4 Fact vs Reaction vs Interpretation Classifier | Deterministic (V4: LLM + deterministic checks) | Stellar |
| Macro analysis | M1 Causal / Macro Analyst | LLM (deep tier) | Stellar |
| Market specialists | S1 XAU/USD, S2 EUR/USD, S3 USD/JPY, S4 NAS100 | LLM | Stellar |
| Technical | T1 Data Validator, T2 Market Session, T3 Market Structure, T4 Technical Indicator, T5 Candle / Price Action, T6 Pullback / Setup, T7 Entry Timing, T8 Technical Analyst | Deterministic (T8: LLM) | Stellar |
| Debate | U1 Bull, U2 Bear, U5–U7 Aggressive / Conservative / Neutral Risk Debaters | LLM | upstream, unchanged |
| Decision | U3 Research Manager, U4 Trader, U8 Portfolio Manager; P1 Trade Proposal Builder | LLM (P1: deterministic) | upstream (U*), Stellar (P1) |
| Validation and risk | P2 Contradiction Checker, P3 Risk Engine (Risk Auditor) | **Deterministic code** | Stellar |
| Execution | P4 Execution Checker, E1 Paper Execution Agent, E2 MT5 Execution Agent | Deterministic code | Stellar |
| Review | L1 Post-Trade Reviewer, L2 Performance / Attribution | Deterministic (L1 LLM narrative later) | Stellar (may reuse upstream Reflector) |
| Supervision and wellbeing | O1 Supervisor, O2 Operational Wellbeing Monitor | Deterministic | Stellar |
| Station personas (visual only) | Station Medic, Quartermaster (personas of O2); Vault personas of P3; Café Host (cosmetic) | No decisions | Stellar UI |

**Decision: execution is its own group.** Putting order-sending agents in any other group would
blur the line the whole design rests on: execution is downstream of, and separate from, risk
approval.

**Decision: the upstream "risk analysts" are debaters.** Upstream's Aggressive, Conservative and
Neutral agents are LLMs arguing positions. They live in the Debate Chamber and are called **Risk
Debaters** in Stellar. The **Risk Control Vault** holds only deterministic code. An LLM debate is
not risk control.

**Mapping from the v0.3 roster of this document (R-4):** FX Session Analyst → T2 Market Session;
Crypto Analyst → out of scope (crypto is not a first market); upstream Market Analyst → T2–T8 for
the four markets; upstream News / Sentiment Analysts → not in V1 (optional research inputs later);
upstream Fundamentals Analyst → not used; Signal Validator → P1 schema + P2; Risk Officer, Exposure
Controller, Circuit Breaker → components of P3, kept as Vault personas; Execution Pilot → E1 / E2;
Position Monitor → P4 + E1 / E2; Station Controller → O1; Data Core Keeper → T1 + O2 (source
health); Memory Archivist → L1 + L2; Station Medic, Quartermaster → personas of O2; Café Host →
cosmetic.

### 3.2 Common agent state machine

Every agent, LLM or code, uses the same state set so the UI can render any agent the same way.

| State | Meaning | Typical trigger |
|---|---|---|
| `OFFLINE` | Not part of the station roster right now (disabled or deferred in config) | config |
| `OFF_DUTY` | On the roster but not needed now (e.g. a research role between its schedules, or a specialist for an instrument not in focus) | `run.started`, schedules |
| `IDLE` | Available, waiting for work in its home room | its part finished / no run |
| `ASSIGNED` | Has work queued; walking to its work position | `agent.task.started`, dependency satisfied |
| `THINKING` | An LLM call is in flight | `on_chat_model_start` |
| `FETCHING` | A data or research retrieval is in flight | `on_tool_start`, collector start |
| `SPEAKING` | Delivering a debate turn | debate turn in progress |
| `LISTENING` | In a debate, not the current speaker | another participant speaking |
| `WAITING` | Blocked on another agent (e.g. Bull waits for all reports) | graph dependency |
| `REPORTING` | Just produced its output; carrying it to the next room | `analysis.created`, `agent.task.completed` |
| `CHECKING` | (code agents) evaluating rules | `risk.check.started`, validation start |
| `DEGRADED` | Working, but retrying / rate-limited / on a fallback path | `agent.degraded` |
| `OVERLOADED` | Load score above threshold | `agent.overloaded` |
| `RESTING` | Cooling down in the Wellbeing Room; takes no new work | `agent.resting` |
| `ERROR` | Last action failed | `agent.task.failed` |

```
OFF_DUTY <-> IDLE -> ASSIGNED -> {THINKING <-> FETCHING | CHECKING} -> REPORTING -> IDLE
                              \-> WAITING -> ...
            (debate agents)   ASSIGNED -> LISTENING <-> SPEAKING -> REPORTING
  any working state -> DEGRADED -> (recovers) | ERROR | OVERLOADED -> RESTING -> IDLE
```

### 3.3 Research, validation and macro agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **R1–R6 research roles** (`research_central_bank`, `research_economic_data`, `research_market_news`, `research_geopolitical`, `research_rates_bonds`, `research_corporate_earnings`) | Collect `ResearchItem`s for their own domain from allowlisted sources (Foundation §4.29.1) | Macro & News Observatory, one console each | items collected; acceptance rate after validation; latency; source errors | `FETCHING` while retrieving; `OFF_DUTY` between schedules; R3–R6 `OFFLINE` until a source is approved | Telescope sweeps; new items arrive as stars |
| **V1 Source Validator** | Allowlist, trust tier, provenance | Data Core, verification bench | accepted / rejected by reason | `CHECKING` | Items pass through a scanner gate; rejected ones dim |
| **V2 Freshness Checker** | No look-ahead; freshness window | Data Core | stale / future counts | `CHECKING` | Timestamp ring around each item |
| **V3 Duplicate Detector** | Exact and near duplicates; keep the primary source | Data Core | duplicate clusters | `CHECKING` | Duplicates merge into one star |
| **V4 Fact vs Reaction vs Interpretation Classifier** | Labels each claim; numeric FACT cross-check against the calendar | Data Core | label distribution; cross-check failures | `THINKING` then `CHECKING` | Claims tagged F / R / I with distinct icons and colours |
| **M1 Causal / Macro Analyst** | `MacroAssessment` from validated research only; every driver cites claim ids | Macro & News Observatory, driver board | drivers per assessment; uncited-claim flags; coverage | Reused while the research snapshot is unchanged | Driver board with arrows per asset and a coverage bar |

### 3.4 Market specialists and technical agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **S1–S4 Market Specialists** (XAU/USD, EUR/USD, USD/JPY, NAS100) | `MarketAssessment`: pressure on the instrument, event-risk windows, invalidation conditions, coverage | Market Analysis Wing, instrument desk | latency; coverage; contradiction flags | Only the focus instrument's specialist runs; others `OFF_DUTY` | Desk screen with the instrument's pressure gauge and event windows |
| **T1 Data Validator** | Builds and validates the `MarketSnapshot` | Data Core | snapshots created / rejected; data gaps | `CHECKING` | Reactor pulse per snapshot; red flash on rejection |
| **T2 Market Session** | Session, overlaps, time to close, per-instrument calendars | Market Analysis Wing, session clock | — | runs every cycle and entry bar | World clock with the active session highlighted |
| **T3 Market Structure** (includes higher-timeframe bias) | Trend state and key levels per timeframe | Market Analysis Wing, chart table | levels per timeframe | deterministic | Structure levels drawn on the holo chart |
| **T4 Technical Indicator** (includes momentum) | Indicator features and momentum assessment | Market Analysis Wing, chart table | features computed; warm-up gaps | deterministic | Indicator lines drawn as computed |
| **T5 Candle / Price Action** | Candle and price-action features tied to structure levels | Market Analysis Wing, chart table | features detected per timeframe | deterministic; part of the first technical foundation | Candle highlights at levels |
| **T6 Pullback / Setup** | Detects and manages Setups | Market Analysis Wing | setups by lifecycle state | emits `setup.state.changed` | Setup card: `WATCHING → ARMED → PROPOSED …` |
| **T7 Entry Timing** | Deterministic entry trigger while a Setup is armed | Market Analysis Wing | triggers; expiries | fastest cadence; no LLM | Countdown on the armed setup; flash on trigger |
| **T8 Technical Analyst** | Writes `market_report` from typed assessments; cites only snapshot values | Market Analysis Wing | latency; tokens; uncited-number flags | `THINKING` | A report crystal assembled at the chart table |

### 3.5 Debate agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Bull Researcher** (U1, `bull_researcher`) | Argues for the setup | Debate Chamber, inner ring, left podium | turns; words per turn; "won" rate (Research Manager sided with it); conditional correctness (§6.3) | `WAITING` until every report is filed; then `SPEAKING` / `LISTENING` | Neutral spotlight with bull icon + label; the excerpt appears on the bull wall (no speech bubble) |
| **Bear Researcher** (U2, `bear_researcher`) | Argues against | Debate Chamber, inner ring, right podium | same as Bull | same | Neutral spotlight with bear icon + label; the excerpt appears on the bear wall |
| **Aggressive Risk Debater** (U5, `risk_aggressive`) | Argues for the high-reward view of the Trader's plan | Debate Chamber, outer ring | turns; agreement with the final rating | Round-robin: Aggressive → Conservative → Neutral | Orange podium light; "upside" arrows |
| **Conservative Risk Debater** (U6, `risk_conservative`) | Argues for caution | Debate Chamber, outer ring | same | same | Blue podium light; shield icon |
| **Neutral Risk Debater** (U7, `risk_neutral`) | Balances the two | Debate Chamber, outer ring | same | same | White podium light; balance-scale icon |

### 3.6 Decision agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Research Manager** (U3, `research_manager`; deep tier) | Judges the bull/bear debate; writes the investment plan | Command Deck, strategy table | recommendation distribution; agreement with the PM; structured-output misses; latency | Walks to the Chamber's judge seat for the debate close, then back | A gavel moment; the recommendation badge appears on the main screen |
| **Trader** (U4, `trader`) | Transaction view on the setup; its entry and stop are **advisory** | Command Deck, trading console | share of plans with numeric levels; disagreement with P1's deterministic levels | emits `decision.trader_plan.created` | A trade ticket filled in field by field, drawn as dashed "advisory" lines |
| **Portfolio Manager** (U8, `portfolio_manager`; deep tier) | Final typed rating = **approval strength for the setup** (setup-first, R-1) | Command Deck, captain's chair | rating distribution; `REVIEW` rate; calibration per tier | `REVIEW` puts it into `DEGRADED` with a "needs owner" flag | The rating stamped on the viewscreen; `REVIEW` flashes amber and nothing proceeds |
| **Trade Proposal Builder** (P1, `trade_proposal_builder`) | Setup + rating → typed `TradeProposal` with deterministic levels | Command Deck | proposals built; proposals not built (Hold / Underweight / Sell / REVIEW) | `CHECKING`; emits `trade.proposed` | A proposal card carried down the lift to the Vault |

### 3.7 Validation and risk agents (deterministic)

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Contradiction Checker** (P2, `contradiction_checker`) | Uncited numbers, Trader levels vs P1 levels, rating vs setup direction, stale plans | Risk Vault, intake desk | contradictions by type | `CHECKING` | The intake checklist lighting each line ✓/✗ |
| **Risk Engine** (P3, `risk_engine`; "Risk Auditor") | Every hard rule (Foundation §8): proposal rules, **sizing by formula**, portfolio exposure, cooldowns, news restriction, breaker | Risk Vault | approvals and rejections by rule; average risk per trade; headroom to each limit; breaker trips | `CHECKING`; breaker `ARMED` / `TRIPPED`. Any rule or agent may trip the breaker; **only the owner resets it, with the local owner command**; the UI shows state only (R-5, Q6) | Vault personas: intake officer, sizing console with a "% of equity at risk" gauge, exposure wall with limit lines, and the kill-switch lever that drops and turns the station RED |

### 3.8 Execution agents (deterministic)

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Execution Checker** (P4, `execution_checker`) | Pre-flight (mode, market open, spread, quote age, idempotency) and reconciliation | Execution Bay, launch console | pre-flight failures by reason; reconciliation mismatches | `PREFLIGHT`, `RECONCILING` | Launch checklist; mismatch alarm |
| **Paper Execution Agent** (E1, `paper_execution`) | Submits order intents to the Paper Broker; tracks fills and closes | Execution Bay | orders; fills; slippage; open positions | `LAUNCHING`, `AWAITING_FILL` | Shuttles launched toward the "Paper Range"; docking board of positions with live P&L |
| **MT5 Execution Agent** (E2, `mt5_execution`) | Same, through the MT5 bridge, demo accounts only | Execution Bay | as E1 plus ack latency and broker rejects | exists only from the demo gate (Foundation Phase 8) | Shuttles toward the "Vantage Demo Relay" |

### 3.9 Review, supervision and wellbeing agents

**Decision: "wellbeing" is operational health made visible, not an emotional simulation.** Every
wellbeing signal maps to something real: latency, retries, rate limits, error rates, token and cost
budgets, and forced wrap-ups. Wellbeing can **pause or slow work** (real cooldowns). It can **never
change a trading decision**.

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Post-Trade Reviewer** (L1, `post_trade_reviewer`) | Typed `TradeReview` per closed trade; LLM narrative mode later | Memory Archive | reviews written | deterministic in V1 | A crystal shelved per trade |
| **Performance / Attribution** (L2, `attribution`) | Settlement, metrics, attribution (§6) | Memory Archive | settled trades; sample sizes | statistical attribution after minimum samples | Crystals light green or red when settled |
| **Supervisor** (O1, `supervisor`) | Scheduling, market focus, run lifecycle; pauses on budget or breaker | Command Deck, ops console | queue depth; runs per day; skipped runs | `SCHEDULING` | Run queue; focus selector; alert lights |
| **Operational Wellbeing Monitor** (O2, `wellbeing_monitor`) | Load score (§6.5), errors, rate limits, budgets; pauses runs; prescribes rests | Wellbeing Room | load per agent; rests; spend vs budget | Visualised as two personas: **Station Medic** (walks to agents in `ERROR` / `OVERLOADED`) and **Quartermaster** (budget gauges) | Med-bot over the patient; vitals board; fuel-cell gauges per provider |
| **Café Host** (`cafe_host`) | **Cosmetic only.** No metrics and no influence on anything | Lounge / Café | none | none | Ambient life; greets agents coming off duty |

---

## 4. Event model

### 4.1 Principles

- **Append-only, ordered, replayable.** Every event is stored. The UI can rebuild any moment by
  replaying events from a snapshot.
- **One envelope, many types.** Consumers (UI, metrics, audit) filter by `type`.
- **Derived, not invented.** Each event type documents its source (§4.4).
- **Safe by construction.** Follow upstream's `run_settings()` allowlist approach: events never
  contain API keys, `backend_url`, account passwords or file-system paths. Long text such as reports
  is truncated to an excerpt plus a content hash; the full text stays in upstream's report files.
- **Versioned.** `schema_version` on every event; additive changes only within a major version.

### 4.2 Envelope

```json
{
  "event_id": "01J8Z6Q3T6V4Y1M2N3P4Q5R6S7",
  "schema_version": "1.0",
  "type": "agent.state.changed",
  "ts": "2026-09-29T14:03:12.481Z",
  "seq": 1842,
  "run_id": "run_2026-09-29_EURUSD_a1b2c3",
  "station_id": "stellar-01",
  "source": "upstream.callback | upstream.state | stellar.risk | stellar.execution | mt5.bridge | stellar.system",
  "agent_id": "market_analyst",
  "room": "market_wing",
  "instrument": "EURUSD",
  "correlation_id": "prop_7f3a",
  "payload": { }
}
```

| Field | Notes |
|---|---|
| `event_id` | A time-sortable unique id (ULID); used for de-duplication |
| `seq` | Monotonic per station; the UI detects gaps and asks for a resync |
| `run_id` | One decision-cycle run; `null` for station-level events |
| `correlation_id` | Threads a proposal through risk, order, fill and close (`prop_*`, then `ord_*`, `trade_*`; Foundation §9.2) |
| `agent_id` / `room` | Optional; present when the event concerns an agent or room |

### 4.3 Event catalogue

**Naming convention (canonical, R-3):** `<domain>.<entity>.<past-tense verb>`, or
`<domain>.<past-tense verb>` when the entity is the domain itself (e.g. `risk.approved`). The
Foundation Plan §10.1 set is the V1 minimum; the rest of this catalogue follows the same
convention and is implemented when needed. Payload fields are unchanged from v0.3 of this document,
except that `symbol` is now `instrument` and `signal_id` is now `proposal_id` (setup-first, R-1).
The old → new name mapping is in §4.6.

#### Station, system and run

| Type | Payload (key fields) |
|---|---|
| `station.heartbeat.emitted` | `alert_level`, `active_runs`, `queue_depth` |
| `station.alert_level.changed` | `from`, `to`, `reason` |
| `system.paused` / `system.resumed` | `reason` |
| `budget.warning` | `scope` (provider / day / run), `used`, `budget` |
| `run.started` | `instrument`, `profile`, `setup_id`, `llm_tiers`, `max_debate_rounds`, `max_risk_rounds` |
| `run.resumed` | `from_checkpoint_step` |
| `run.completed` | `duration_ms`, `final_rating`, `llm_calls`, `tool_calls`, `tokens_in`, `tokens_out` |
| `run.failed` | `error_class`, `message_excerpt`, `last_agent_id` |

#### Agent state and activity

| Type | Payload |
|---|---|
| `agent.task.started` / `agent.task.completed` | task kind, input / output ids, duration, tokens (LLM) |
| `agent.task.failed` | `error_class`, `message_excerpt` |
| `agent.state.changed` | `from`, `to`, `reason` (e.g. `llm_call`, `tool_call`, `dependency_wait`) |
| `agent.moved` | `from_room`, `to_room`, `reason` (emitted by the station layer from state changes; see §5) |
| `agent.llm_call.started` | `model`, `call_id` |
| `agent.llm_call.completed` | `call_id`, `latency_ms`, `tokens_in`, `tokens_out`, `structured` (true/false), `retries` |
| `agent.tool_call.started` | `tool`, `args_excerpt`, `call_id` |
| `agent.tool_call.completed` | `call_id`, `tool`, `source`, `ok`, `latency_ms`, `error_class` |
| `agent.wrap_up.forced` | `tool_rounds_used`, `max_tool_rounds` |

#### Market data, research and analysis

| Type | Payload |
|---|---|
| `market.focus.changed` | `instrument`, `profile`, `reason` (`schedule`, `manual`, `setup_followup`) |
| `market.session.changed` | `session`, `overlaps[]` |
| `market.quote.received` | `bid`, `ask`, `spread` (**throttled**, e.g. at most 1/sec per instrument) |
| `market.data.stale_detected` | `instrument`, `source`, `age_s` |
| `snapshot.created` / `snapshot.rejected` | snapshot id, quality flags / reason |
| `research.item.collected` | item id, role, source id, `published_at` |
| `research.item.accepted` / `research.item.rejected` | item id, validator, reason, claim labels |
| `research.snapshot.created` | research snapshot id, item count, coverage |
| `analysis.created` | analysis id, kind (macro, market, structure, momentum, price action, session, report), `chars`, `excerpt`, `sha256`, coverage |
| `setup.state.changed` | setup id, `from`, `to`, rule |

#### Debate and decision

| Type | Payload |
|---|---|
| `debate.started` | `debate` (`investment` / `risk`), `participants[]`, `max_rounds` |
| `debate.turn.completed` | `debate`, `speaker`, `round`, `turn_index`, `excerpt` |
| `debate.completed` | `debate`, `rounds`, `turns`, `verdict` (Research Manager's recommendation / Portfolio Manager's rating) |
| `decision.research_plan.created` | `recommendation` (5-tier) |
| `decision.trader_plan.created` | `action`, advisory `entry`, advisory `stop_loss`, `sizing_text` (parsed from the Trader's text; advisory only) |
| `decision.final.created` | `rating`, `is_review`, `price_target`, `time_horizon` |
| `trade.proposed` | `proposal_id`, `setup_id`, `instrument`, `direction`, `source_rating`, `size_factor`, levels, `contradictions[]` (replaces v0.3's `signal.intent_created`; setup-first, R-1) |

#### Risk and circuit breaker

| Type | Payload |
|---|---|
| `risk.check.started` | `proposal_id`, `checks[]` |
| `risk.check.completed` | `proposal_id`, `rule`, `passed`, `value`, `limit` |
| `risk.approved` | `proposal_id`, `decision_id`, `order_intent` {`instrument`, `side`, `volume_lots`, `sl`, `tp`}, `risk_pct_equity` |
| `risk.rejected` | `proposal_id`, `decision_id`, `reasons[]` (rule ids), `shadow_tracked: true` |
| `risk.limit.approached` | `rule`, `value`, `limit`, `headroom_pct` |
| `circuit_breaker.tripped` | `rule`, `value`, `limit` |
| `circuit_breaker.reset` | `by` (always the owner, via the local owner command), `reason` |
| `circuit_breaker.reset_refused` | `source`, `reason` (any reset attempt not made through the owner command) |

#### Orders, trades and account

| Type | Payload |
|---|---|
| `order.created` | `order_id`, `intent_id`, `idempotency_key`, `instrument`, `side`, `volume`, `sl`, `tp`, `mode` (`PAPER` / `DEMO`) |
| `order.preflight.failed` | `order_id`, `reason` (`not_demo`, `market_closed`, `spread_too_wide`, `stale_quote`, `bridge_down`) |
| `order.sent` | `order_id`, `sent_at` |
| `order.acknowledged` | `order_id`, `broker_ticket` (MT5 only) |
| `order.rejected` | `order_id`, `broker_retcode`, `reason` |
| `order.filled` | `order_id`, `fill_price`, `filled_volume`, `slippage` |
| `order.partially_filled` | `order_id`, `filled_volume`, `remaining` |
| `position.opened` | `position_id`, `instrument`, `side`, `volume`, `open_price` |
| `position.updated` | `position_id`, `unrealized_pnl`, `price` (**throttled**) |
| `trade.closed` | `trade_id`, `position_id`, `close_price`, `realized_pnl`, `r_multiple`, `reason` (`stop_loss`, `take_profit`, `signal_exit`, `time_exit`, `breaker`, `manual`) |
| `account.snapshot.created` | `balance`, `equity`, `margin_level`, `open_positions`, `mode` (periodic) |

#### Review and memory

| Type | Payload |
|---|---|
| `memory.review.created` | `trade_id`, `review_id`, `r_multiple`, `exit_reason`, coverage |
| `memory.outcome.settled` | `trade_id`, `settlement_id`, `realized_pnl`, `r_multiple`, `holding_time` |
| `memory.decision.stored` | `instrument`, `trade_date`, `rating` (only if the optional upstream memory log is used, D-10) |
| `memory.reflection.written` | `trade_id`, `excerpt` (LLM narrative mode, later) |

#### Wellbeing and workload

| Type | Payload |
|---|---|
| `wellbeing.load.updated` | `agent_id`, `load` (0–1), `components` {latency, retries, errors, token_rate, wrap_ups} |
| `agent.overloaded` | `agent_id`, `load`, `cause` |
| `agent.resting` | `agent_id`, `cooldown_s`, `reason` |
| `agent.rest.ended` | `agent_id` |
| `agent.degraded` | `agent_id` or `provider`, `cause` (`rate_limited`, `retrying`, `freetext_fallback`) |

### 4.4 Where events come from

| Event(s) | Derived from | Upstream surface |
|---|---|---|
| `agent.llm_call.*`, `agent.state.changed → THINKING` | LangChain `on_chat_model_start` / `on_llm_end` (+ `langgraph_node` metadata) | C2 |
| `agent.tool_call.*`, `→ FETCHING` | `on_tool_start` / `on_tool_end` / `on_tool_error` | C2 |
| `snapshot.*`, `research.*`, `analysis.created`, `setup.state.changed` | Stellar data, research and analysis modules | Stellar only |
| `debate.*` (investment) | Diff of `investment_debate_state.count` and `current_response` prefix; completed when `investment_plan` appears | C5, C6 |
| `debate.*` (risk) | Diff of `risk_debate_state.count` / `latest_speaker`; completed when `final_trade_decision` appears | C5, C6 |
| `decision.research_plan.created` | `investment_plan` appears | C5 |
| `decision.trader_plan.created` | `trader_investment_plan` appears | C5 (see note) |
| `decision.final.created` | `final_rating` and `final_trade_decision` | C5, C7 |
| `trade.proposed` | Trade Proposal Builder (P1) | Stellar only |
| `risk.*`, `circuit_breaker.*`, `order.*`, `position.*`, `trade.closed`, `account.*` | Stellar risk and execution modules; MT5 bridge after the demo gate | Stellar only |
| `memory.*` | Post-Trade Reviewer, Attribution, Stellar Journal (upstream memory log only if D-10 allows) | Stellar (C9 optional) |
| `wellbeing.*`, `agent.overloaded`, `agent.resting`, `agent.degraded`, `budget.warning` | Operational Wellbeing Monitor over the events above | Stellar only |

**Note on the Trader's levels.** Upstream keeps the Trader's output as **rendered markdown** in
state; the typed `TraderProposal` object is not kept. Stellar parses the known rendered layout
(Action / Entry Price / Stop Loss / Position Sizing) into **advisory** values only. Order levels
come from the deterministic Trade Proposal Builder; the Contradiction Checker flags disagreement.
If parsing fails, the advisory values are `null`, which cannot cause a trade (fail closed).

### 4.5 Transport and storage

```
producers (callback handler, state observer, research, analysis, risk, execution, bridge client, metrics)
   -> in-process EventBus (thread-safe; upstream runs analysts in parallel)
   -> EventStore: append-only (SQLite, with the Stellar Journal) + periodic state snapshots
   -> WebSocket broadcaster -> Station UI
   -> Metrics aggregator (rolling windows) -> REST /metrics
```

- **Backpressure.** High-rate types (`market.quote.received`, `position.updated`, `wellbeing.load.updated`)
  are throttled and coalesced. Decision, risk and order events are **never** dropped.
- **Resync.** The UI connects, fetches `GET /snapshot` (current station state plus last `seq`), then
  subscribes from `seq+1`. On a gap it refetches the snapshot.
- **Replay.** `GET /runs/{run_id}/events` feeds the UI's replay mode (Foundation Phase 9).
- **Telemetry must not break trading.** Exceptions inside producers are caught and logged. A
  telemetry failure must never fail a run or an order. The reverse is not true: if the **risk** or
  **execution** events cannot be persisted, execution halts (audit trail is mandatory for orders).

### 4.6 Event names: v0.3 → canonical (R-3)

| v0.3 name | Canonical name |
|---|---|
| `station.heartbeat` | `station.heartbeat.emitted` |
| `station.alert_level_changed` | `station.alert_level.changed` |
| `agent.state_changed` | `agent.state.changed` |
| `agent.llm_call.finished` / `agent.tool_call.finished` | `agent.llm_call.completed` / `agent.tool_call.completed` |
| `agent.report_filed` | `analysis.created` (kind `report`) |
| `agent.wrap_up_forced` | `agent.wrap_up.forced` |
| `agent.error` | `agent.task.failed` |
| `market.focus_changed` / `market.session_changed` | `market.focus.changed` / `market.session.changed` |
| `market.quote` | `market.quote.received` |
| `market.data_stale` | `market.data.stale_detected` |
| `debate.turn` / `debate.ended` | `debate.turn.completed` / `debate.completed` |
| `decision.research_plan` | `decision.research_plan.created` |
| `signal.proposed` (Trader draft) | `decision.trader_plan.created` (advisory) |
| `decision.final` | `decision.final.created` |
| `signal.intent_created` | superseded by `trade.proposed` (R-1) |
| `risk.check_started` / `risk.check_result` | `risk.check.started` / `risk.check.completed` |
| `risk.limit_warning` | `risk.limit.approached` |
| `risk.breaker_tripped` / `risk.breaker_reset` / `risk.breaker_reset_refused` | `circuit_breaker.tripped` / `circuit_breaker.reset` / `circuit_breaker.reset_refused` |
| `order.preflight_failed` | `order.preflight.failed` |
| `position.closed` | `trade.closed` |
| `account.snapshot` | `account.snapshot.created` |
| `memory.decision_stored` / `memory.outcome_settled` / `memory.reflection_written` | `memory.decision.stored` / `memory.outcome.settled` / `memory.reflection.written` |
| `wellbeing.load_updated` | `wellbeing.load.updated` |
| `wellbeing.overload` / `wellbeing.rest_started` / `wellbeing.rest_ended` | `agent.overloaded` / `agent.resting` / `agent.rest.ended` |
| `wellbeing.degraded` / `wellbeing.budget_warning` | `agent.degraded` / `budget.warning` |
| (new in the Foundation Plan) | `agent.task.started`, `agent.task.completed`, `system.paused`, `system.resumed`, `snapshot.created`, `snapshot.rejected`, `research.item.*`, `research.snapshot.created`, `setup.state.changed`, `trade.proposed`, `memory.review.created` |

Unchanged: `run.*`, `agent.moved`, `agent.llm_call.started`, `agent.tool_call.started`,
`debate.started`, `risk.approved`, `risk.rejected`, `order.created`, `order.sent`,
`order.acknowledged`, `order.rejected`, `order.filled`, `order.partially_filled`,
`position.opened`, `position.updated`.

---

## 5. UI and visual states

### 5.1 Home rooms and work positions

> **Topology superseded (visual layer only).** The station map, rooms, lifts, vault and airlock described in this section belong to the earlier stacked-deck concept. The owner-approved physical topology is `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C** (a flat vessel with 3 hubs, L1–L10, R1–R6 and 21 explicit doors), detailed in the Visual Foundation v2 registries (`STELLAR_STATION_TOPOLOGY.md`, `STELLAR_ROOM_REGISTRY.md`, `STELLAR_CHARACTER_REGISTRY.md`, `STELLAR_SCREEN_REGISTRY.md`, `STELLAR_ASSET_REGISTRY.md`). Risk isolation is now a logical access rule (Risk Control Room L10, Execution Bay L9), not a vault, lift or airlock. The engine's rules (risk gate before execution; the UI never writes) are unchanged.

Each agent has a **home room** (where it idles) and one or more **work positions** (where it goes
when active). Most analysts work in their home room; decision and debate agents travel.

| Agent | Home | Work positions |
|---|---|---|
| Research roles R1–R6 | Macro & News Observatory | own console; a beam to the Data Core while `FETCHING` |
| Research validators V1–V4 | Data Core | verification bench |
| Causal / Macro Analyst M1 | Macro & News Observatory | driver board |
| Market specialists S1–S4 | Market Analysis Wing | own instrument desk |
| Technical agents T2–T8 | Market Analysis Wing | chart table, session clock; a beam to the Data Core while fetching |
| Data Validator T1 | Data Core | reactor console |
| Bull / Bear | Debate Chamber (inner ring) | podiums |
| Risk Debaters | Debate Chamber (outer ring) | podiums |
| Research Manager | Command Deck | Chamber judge seat (investment debate close) |
| Trader | Command Deck | trading console |
| Portfolio Manager | Command Deck | captain's chair; Chamber judge seat (risk debate close) |
| Trade Proposal Builder | Command Deck | proposal console; the lift to the Vault |
| Contradiction Checker, Risk Engine (and its personas) | Risk Control Vault | intake desk, sizing console, exposure wall, lever |
| Execution Checker, Paper / MT5 Execution Agents | Execution Bay | launch console, docking board |
| Supervisor | Command Deck | ops console |
| Post-Trade Reviewer, Attribution | Memory Archive | shelves; Execution Bay to collect a closed trade |
| Operational Wellbeing Monitor (Medic / Quartermaster personas) | Wellbeing Room | anywhere an agent is in `ERROR` / `OVERLOADED` |
| Café Host | Lounge | lounge only |

### 5.2 Status → visual mapping

The **status badge** above each avatar updates the instant the event arrives. The walk animation
follows and may take a second or two; truth never waits for animation.

| State | Location | Animation / pose | Badge (icon + colour; never colour alone) |
|---|---|---|---|
| `OFFLINE` | not rendered (roster panel shows it greyed) | — | ⏻ grey |
| `OFF_DUTY` | Lounge / Café / Billiards | ambient: sipping, playing billiards, looking out of the window | ☕ muted |
| `IDLE` | home room | small idle loop at its desk | ● neutral |
| `ASSIGNED` | walking to work position | walk; a dotted path line | ➜ white |
| `THINKING` | work position | pulsing halo; live token counter | ✦ cyan, pulsing |
| `FETCHING` | work position | a beam from the desk down to the Data Core conduit of the vendor used; tool label | ⇣ cyan + tool name |
| `SPEAKING` | debate podium | neutral spotlight; the excerpt on the side's wall (no speech bubble); gestures | 🗨 bright, side icon + label |
| `LISTENING` | debate seat | seated, head turned to the speaker | 👂 dim |
| `WAITING` | work position or the waiting bench | seated; hourglass | ⌛ grey |
| `REPORTING` | walking to the next room | carries a glowing data crystal (the report) and hands it over | ◆ gold |
| `CHECKING` | vault stations and validation benches | scanner sweep over the proposal or item | ⌕ violet |
| `DEGRADED` | stays at work | hologram flicker; slower animation | ⚠ amber |
| `OVERLOADED` | stays, then escorted by the Medic persona (O2) to the Wellbeing Room | steam / sparks; then walks | ♨ orange |
| `RESTING` | Wellbeing Room rest pod | lying in a pod; recharge bar | ☾ soft blue + countdown |
| `ERROR` | stays in place | red beacon; the Medic persona (O2) walks over | ✖ red |

### 5.3 Movement rules

1. Movement is **derived from state changes** by the station layer (`agent.moved` events), so every
   client and every replay shows the same thing.
2. Pathfinding runs on a room graph (the corridors in §2.2), not free space. The Execution Bay node
   is reachable **only** from the Vault node.
3. **Teleport when late.** If an avatar is still walking when its next state arrives, it snaps to
   the new position so the view never shows stale activity.
4. **Parallel work is visible as parallel.** Agents that run concurrently (e.g. research roles,
   technical agents) are shown working at the same time.
5. **Deterministic life.** Idle behaviour in the Lounge (who plays billiards with whom, café
   visits) uses a seeded random generator keyed on `run_id` and time, so replays look identical.
6. **Reduced-motion mode** replaces walking with fades and keeps all badges.

### 5.4 Station-wide alert levels

| Level | Condition | Visual |
|---|---|---|
| **GREEN** | No run active; all systems healthy | Soft ambient lighting |
| **BLUE** | A run is active | Blue accent lights; Command Deck viewscreen live |
| **AMBER** | Any data, research or LLM source degraded; a risk limit above 80%; a `REVIEW` decision; the bridge reconnecting | Amber strips; affected room outlined |
| **RED** | Circuit breaker tripped; demo check failed; reconciliation mismatch | Red lighting; vault door sealed; Execution Bay locked; a banner stating that only the owner can reset the breaker, with the local owner command (the UI cannot reset it; R-5) |

### 5.5 Key UI panels (beyond the map)

- **Top strip:** alert level, execution mode (`PAPER`, later `DEMO`), equity, day P&L, open
  positions, today's runs and LLM spend.
- **Room panel** (click a room): its agents, their states and room-specific displays (§2.3).
- **Agent card** (click an avatar): role, current state, recent events, key metrics (§6.2) and
  contribution (§6.3), each with a sample size.
- **Proposal timeline:** one row per `proposal_id`: setup → proposed → approved/rejected → sent →
  filled → closed → reviewed, with timestamps.
- **Event log:** a filterable raw stream.
- **Replay scrubber:** jump anywhere in a past run.

---

## 6. Performance metrics

All metrics are computed from the event store and the Stellar Journal, over rolling windows
(today, 7 days, 30 days, all time). For the four markets, outcomes come from Stellar's own settled
trades and reviews, not from upstream's memory-log alpha against SPY, which is not meaningful for
these instruments (Foundation L10, U17); "alpha" below means the return measure chosen for
settlement. **Every displayed metric carries its sample size**, and
rankings are hidden below a minimum sample size (default N ≥ 30 settled decisions), because small
samples produce confident-looking noise.

### 6.1 Global metrics

| Metric | Definition | Source |
|---|---|---|
| Runs completed / failed | Count per window | `run.*` |
| Run duration p50 / p95 | `run.completed.duration_ms` | events |
| Rating distribution | Share of Buy / Overweight / Hold / Underweight / Sell / REVIEW | `decision.final.created` |
| REVIEW rate | REVIEW ÷ runs | `decision.final.created` |
| Setup hit rate by approval tier | Share of taken setups with positive realized result, per PM rating tier (setup-first, R-1) | journal |
| Mean outcome by approval tier | Average R multiple per tier (should be monotonic: Buy > Overweight > …) | journal |
| Equity, balance, day P&L (paper; demo after the demo gate) | Latest `account.snapshot.created` | Paper Broker / bridge |
| Realized P&L, win rate, profit factor, average R multiple, expectancy | Over closed trades | `trade.closed` |
| Max drawdown (equity, peak-to-trough) | From the equity series | `account.snapshot.created` |
| Sharpe / Sortino (daily) | From daily equity returns; shown only with ≥ 60 trading days | derived |
| Setup-to-trade funnel | setups → proposed → approved → filled | setup / risk / order events |
| LLM calls, tokens, estimated cost | Per day and per run | callback events |
| Vendor error rate | Failed ÷ total tool calls per vendor | tool events |
| Uptime | Heartbeat coverage | `station.heartbeat.emitted` |

### 6.2 Per-agent metrics

| Metric | Applies to |
|---|---|
| Runs participated in; time in each state | all |
| LLM calls, tokens in/out, estimated cost, p50/p95 latency | LLM agents |
| Structured-output fallback rate (free text used instead of the typed schema) | Research Manager, Trader, Portfolio Manager; Stellar LLM agents (a structured miss is a failed step for them) |
| Tool calls, tool failures, source mix | research and technical agents |
| Tool rounds used vs `max_tool_rounds`; forced wrap-ups | LLM agents with tools |
| Report length; empty or "no data" reports; coverage | analysis and research agents |
| Debate turns, words per turn | debaters |
| Checks run, rejections by rule | Contradiction Checker, Risk Engine, research validators |
| Orders sent, rejects, ack latency, slippage | Paper / MT5 Execution Agents |
| Pre-flight failures, reconciliation mismatches | Execution Checker |
| Errors, retries, rests prescribed | all |

### 6.3 Contribution metrics

Attributing the outcome of a multi-agent decision to individual agents is hard. Stellar uses
several **complementary, clearly labelled** measures and never a single "agent score".

| Metric | For | How it is computed | Caveat |
|---|---|---|---|
| **Stance accuracy** | macro, specialist and technical agents | Each typed assessment's directional stance versus the settled outcome. Typed assessments (Foundation §4.29, §9) carry direction; free-text reports would need a **stance extractor**, validated against a hand-labelled sample first | Direction in a typed field is still a model output; judged only with sample sizes |
| **Agreement with final** | all LLM agents | Share of runs where the agent's stance matched the final rating's direction | Agreement is not correctness; shown next to accuracy, never alone |
| **Debate win rate** | Bull / Bear | Share of runs where the Research Manager's recommendation took their side | Measures persuasiveness, not truth |
| **Conditional correctness** | Bull / Bear, risk debaters | When their side won, how often the outcome agreed | Needs many samples |
| **Rating calibration** | Research Manager, Portfolio Manager | Mean outcome per rating tier (setup approval strength); a monotonicity check; Brier-style score on direction | The core decision-quality measure |
| **Trader advisory quality** | Trader | How its advisory entry and stop compared with P1's deterministic levels and with the realized path (MAE / MFE) | Depends on market regime |
| **Risk value added** | Risk Engine, Contradiction Checker | Rejected proposals are **shadow-tracked** as paper trades. Avoided loss = losses of rejected proposals; missed gain = gains of rejected proposals. Net = avoided − missed | Counterfactual; fills are idealised |
| **Ablation delta** | research and analysis agents | Periodic runs of the Stellar simulator (Foundation §4.17) on a fixed grid with one role removed; compare calibration and hit rate | Expensive; run monthly, offline |

### 6.4 Risk metrics

**No final risk numbers are hard-coded (§8 Q5).** Every threshold below is a configuration value.
The rules are deterministic, but their values are set and validated through backtests and demo
trading before any are considered final. The config key names are illustrative.

| Metric | Limit it is checked against |
|---|---|
| Risk per trade (% of equity at the stop) | `risk.max_risk_per_trade_pct` |
| Total open risk (sum over positions) | `risk.max_total_open_risk_pct` |
| Open positions | `risk.max_open_positions` |
| Exposure per symbol and per currency (notional ÷ equity) | `risk.max_exposure_per_symbol`, `risk.max_exposure_per_currency` |
| Correlated-cluster exposure (e.g. USD-leg pairs such as EUR/USD, USD/JPY, XAU/USD) | `risk.max_cluster_exposure` |
| Daily realized + unrealized loss | `risk.daily_loss_limit_pct` → breaker trips |
| Drawdown from equity peak | `risk.max_drawdown_pct` → breaker trips |
| Consecutive losing trades | `risk.max_consecutive_losses` → breaker trips |
| Margin level | `risk.min_margin_level_pct` |
| Stop-loss coverage | structural rule, not a threshold: 100% of open positions |
| Spread at send; slippage at fill | per-symbol ceilings, `risk.symbols.<symbol>.max_spread` / `max_slippage` |
| Rejections by rule; breaker trips; time since last trip | — |

A missing or invalid limit value is treated as a failed check, so trading stays off until every
limit is configured.

### 6.5 Wellbeing / workload metrics

| Metric | Definition |
|---|---|
| **Load score** (0–1) per agent | A weighted blend of: latency relative to its own baseline, retry rate, error rate, token rate relative to its budget, and forced wrap-ups. Initial weights 0.30 / 0.25 / 0.20 / 0.15 / 0.10, tuned in Foundation Phase 6 |
| Overload threshold | load ≥ 0.8 for two consecutive calls → `agent.overloaded` |
| Rest (cooldown) | Real effect: new runs needing that agent or provider are delayed with backoff (e.g. 60 s → 5 min); visual effect: rest pod |
| Fatigue (cosmetic smoothing) | An exponentially decaying sum of recent working time; drives only animation such as slower walking. **Never** gates work |
| Rate-limit hits (429) per provider | from errors and retries |
| Budget usage | tokens and estimated cost vs daily budget per provider |
| Utilisation | share of time in working states per agent |
| Queue depth / wait time | for the Supervisor |

---

## 7. Implementation themes

**Canonical phase numbers, entry and exit criteria are in the Foundation Plan §11 (R-2).** This
section keeps the design content of this document's original six phases as **themes** (LD-1 to
LD-6). Each theme and bullet names the Foundation phase that implements it. Where a gate here and a
Foundation gate differ, the Foundation gate governs.

| Theme | Foundation phase(s) |
|---|---|
| LD-1 Documentation and design | Phase 0 |
| LD-2 Telemetry layer | Phase 1 (core: envelope, bus, journal, registry, contract tests); Phase 6 (LLM callback telemetry); Phase 7 (metrics) |
| LD-3 Risk hardening | Phase 3 (risk engine), Phase 4 (paper broker), Phase 5 (deterministic technical foundation); market data in Phase 2; Stellar pipeline in Phase 6 |
| LD-4 MT5 / Vantage demo | Phase 8 — a separate integration and validation gate **after** paper V1 (D-15) |
| LD-5 Visual station v1 | Phase 9 |
| LD-6 Visual station v2 | Phase 10 |

### Theme LD-1 — Documentation and design *(Foundation Phase 0)*

- Map the upstream repository (done).
- Write this design and the Foundation Plan; resolve the open questions (§8, done) and reconcile
  the two documents (§8.3, done).
- Set up the upstream sync workflow: an `upstream` remote pointing at `TauricResearch/TradingAgents`;
  merge (not rebase) upstream releases; after each merge, run upstream's tests and Stellar's
  contract tests.

The final Windows host for MT5 is deliberately **not** chosen here (§8 Q1, Foundation D-17); it is
chosen at the start of Foundation Phase 8.

### Theme LD-2 — Telemetry layer *(Foundation Phases 1, 6, 7)*

- *(Phase 1)* Create `stellar/` as a separate project; add `.github/workflows/stellar.yml`.
- *(Phase 1)* Implement the event envelope and catalogue (pydantic models), the bus and the SQLite
  store with the journal.
- *(Phase 1)* Contract tests pinning the upstream surfaces Stellar uses (Foundation Phase 1 list:
  node names, state keys, rating constants and the other reused surfaces).
- *(Phase 6)* **Spike:** confirm `langgraph_node` reaches callbacks bound in the LLM constructors
  (§1.5 C2).
- *(Phase 6)* `StellarTelemetryHandler` (LangChain callbacks) and a state observer that diffs the
  Stellar graph's stream.
- *(Phase 1 onward)* A text "station log" CLI (`stellar watch`) that prints events live, to
  validate before any graphics exist.
- *(Phase 7)* Metrics: global and per-agent operational metrics; wellbeing load score.
- Tests use fake LLMs and fake tools in the style of upstream's end-to-end tests. No network.

**Gate (summary):** a full run produces a complete, ordered event stream; replaying it rebuilds the
same final state summary; upstream's tests still pass untouched; telemetry failure injected in
tests does not fail the run.

### Theme LD-3 — Risk hardening *(Foundation Phases 2–6)*

- *(Phase 6)* **Rating → action mapping: setup-first (canonical, R-1).** Deterministic technical
  agents produce a directional Setup; the research chain, debate and Portfolio Manager judge that
  setup, and the PM's typed rating is its **approval strength**:

  | Final rating | Action on the Setup |
  |---|---|
  | Buy | Take the setup (Trade Proposal Builder builds a `TradeProposal`) |
  | Overweight | Take with the size factor of Foundation decision D-9 (safe default until decided: **no trade**) |
  | Hold | Do not take |
  | Underweight | Reject the setup |
  | Sell | Reject the setup |
  | **REVIEW** | **No trade; owner flag** |

  Direction always comes from the deterministic Setup, never from reading "Sell" as "open a short"
  (upstream's prompts define Sell as exiting or avoiding a position; Foundation L8). This
  replaces the v0.3 flat-book / long / short table.
- *(Phases 3, 5, 6)* **Proposal checks:** schema validation of the `TradeProposal` (P1) and the
  Contradiction Checker (P2): stop present and on the correct side; entry within a tolerance of the
  live price; plan not stale; Trader's advisory levels compared with P1's deterministic levels.
- *(Phase 3)* **Risk Engine sizing:** by formula only. The Trader's free-text `position_sizing` is
  displayed, never used. Round down to the broker's lot step; reject below the minimum lot.
- *(Phase 3)* **Exposure limits and the circuit breaker** in the Risk Engine, with the limits in
  §6.4. All limits are configuration; none is hard-coded or treated as final (§8 Q5). Threshold
  values are proposed from simulation evidence (Foundation Phase 7) and confirmed on the demo account
  at the demo gate.
- *(Phase 3)* **Breaker reset belongs to the owner only (§8 Q6, R-5).** Any agent or rule may trip
  the breaker. No agent, scheduler, retry path, API call or UI element can reset it or re-enable
  trading. In V1 the reset is a **local owner command** on the Mac with typed confirmation and a
  reason, recorded as `circuit_breaker.reset`; the station UI shows breaker state only. A UI reset
  may be designed later, only together with authentication. Tests prove that every non-owner reset
  path is refused.
- *(Phase 2)* **Stellar market-data abstraction (§8 Q3):** a `MarketDataSource` interface (quotes,
  OHLCV bars, symbol metadata) and a Stellar-owned symbol map for XAU/USD, EUR/USD, USD/JPY and
  NAS100 (§8 Q2). A file importer for owner-supplied data first, and a historical provider once one
  is chosen (Foundation D-1); shaped so MT5 can implement it later without changes elsewhere. It
  lives in `stellar/marketdata/`, apart from `stellar/execution/`.
- *(Phases 5–6)* **Stellar market pipeline (§1.6, §8 D1):** Stellar-owned technical agents
  (Phase 5) and research chain (Phase 6) using only Stellar data, assembled into a Stellar-owned
  graph that imports upstream's debate, research-manager, trader and manager agents unchanged.
  Upstream's data-provider code is not patched, extended or registered into. Contract tests pin each
  reused upstream component. Upstream's News and Sentiment Analysts are not in V1.
- *(Phase 4)* A **Paper Broker** that implements the same broker interface as MT5 and simulates
  fills from quotes supplied by the market-data abstraction. All work before the demo gate runs
  against it.
- *(Phase 7)* Shadow tracking of rejected proposals (for §6.3 "risk value added").
- *(Phase 3)* Property-based and table tests: every rule can reject; the gate fails closed on
  missing data; no path exists from `decision.final.created` to `order.created` that skips the
  Risk Engine.

**Gate (summary):** 100% rule coverage in tests; a fault-injection suite (missing quote, missing
stop, broker down, NaN equity, REVIEW) yields zero orders; paper operation with no unexplained
orders. Foundation Phases 3–7 hold the canonical gates.

### Theme LD-4 — MT5 / Vantage demo *(Foundation Phase 8: a separate gate after paper V1)*

**Scope (Foundation D-15):** Stellar Agents V1 is functionally complete with paper trading. This
theme is a separate integration and validation gate that starts only after the paper V1 foundation
is stable. Neither V1 nor this gate implies profitability.

- **Host (§8 Q1).** In V1 the Stellar core runs on the owner's **Mac**. The official
  `MetaTrader5` Python package runs only on Windows and talks to a locally running MT5 terminal.
  So `mt5_bridge/` is a dedicated bridge service on a **separate Windows machine or Windows VPS**,
  where the terminal is logged into a **Vantage demo account**. The final Windows host is chosen at
  the start of this phase, not before. The Mac talks to the bridge over an authenticated, private
  channel (for example a VPN or SSH tunnel plus a token). The bridge is never exposed to the public
  internet.
- **Bridge API (narrow):** `account()`, `symbols()`, `quote(symbol)`, `positions()`,
  `send_order(intent, idempotency_key)`, `close(position_id)`, plus an event stream of fills and
  closes. No generic "execute anything" endpoint.
- **Demo guard, checked in the bridge and again in Stellar before every order:** the account's
  trade mode must report *demo*; the login must be on a configured allowlist; the server name must
  match the configured demo server. Any mismatch → `order.preflight.failed` (`not_demo`) and the
  breaker trips.
- **Symbol mapping:** Stellar's symbol map (Foundation Phase 2) gains the broker column for XAU/USD,
  EUR/USD, USD/JPY and NAS100 (§8 Q2). Vantage may use suffixes or its own index name for NAS100;
  confirm this against the demo server's symbol list. Contract size, lot step, minimum volume and
  digits come from the broker, never hard-coded.
- **MT5 as a data source (§8 Q3):** MT5 may be added as an implementation of the
  `MarketDataSource` interface (bars and quotes). It is a separate component from the MT5
  Execution Agent (E2), even though both talk to the same bridge. The analysis chain for these
  markets is the Foundation roster (research chain, market specialists, technical agents);
  fundamentals and SEC data do not apply.
- **Cadence:** set by the configured timeframe profile (Foundation §7). The LLM chain runs at most
  at the profile's setup cadence, and only when a Setup exists; faster entry timing is
  deterministic. No profile is chosen yet (Foundation D-7); the owner's D1/H4 → H1/M15 → M5/M1
  interest is a hypothesis to test.
- **Reconciliation:** the Execution Checker (P4) compares the broker's positions with Stellar's
  ledger on a timer; any mismatch trips the breaker.
- **Secrets:** broker credentials live only on the bridge host (the terminal's own login); Stellar
  holds a bridge token in its environment, never in config files, events or logs.

**Gate:** two or more weeks on the demo account with complete reconciliation, zero demo-guard
bypasses, and every order traceable from `decision.final.created` to `trade.closed` in the event
store.

### Theme LD-5 — Visual station v1 *(Foundation Phase 9)*

- Front end in `stellar_ui/`: a station view in the §2 art direction (§8 Q7), a **semi-realistic,
  stylized sci-fi interior, not pixel art**, plus HTML panels. The rendering technology (for example
  a WebGL renderer with pre-rendered or 3D-modelled rooms) is chosen at the start of this phase to
  fit that look. The back end is in `stellar/api/` (REST + WebSocket).
- **Single-user, local and read-only (§8 Q8, R-5).** The API and UI bind to `localhost` on the
  owner's Mac. There are no user accounts, no multi-user authentication and no remote or public
  access in V1. The UI only consumes the event stream and snapshots; it has **no write actions**,
  including no breaker reset. Remote viewing is not built, and nothing here prevents adding it
  later.
- All ten rooms from §2 as static art; agents as avatars with **status badges** (§5.2).
- Agents **fade/teleport** between rooms (no pathfinding yet).
- Room panels, agent cards, the proposal timeline, the event log and the top metrics strip.
- **Replay mode** for past runs.
- Alert levels (§5.4) driving station lighting.
- Accessibility: icons plus colour, reduced motion, keyboard navigation, readable at laptop width.

**Gate:** someone watching a live run can say, at any moment, which agents are working, what the
decision is and whether anything is blocked; this matches the event log exactly.

### Theme LD-6 — Visual station v2: movement and life *(Foundation Phase 10)*

- Pathfinding along corridors; walk animations; data-crystal hand-offs; debate staging with
  neutral podium lights and the central evidence stage (no tug-of-war bar or score).
- Shuttle launches from the Execution Bay; the docking board of positions.
- Habitat life: lounge and café routines, billiards between off-duty agents, the Café Host; the
  Station Medic and Quartermaster personas of the Operational Wellbeing Monitor; the Vault
  personas of the Risk Engine. All seeded and deterministic (§5.3 rule 5).
- Day/night lighting tied to FX sessions; optional ambient sound.
- Time-lapse replay of a whole day; the "hall of fame" (calibration leaders, with sample sizes).
- Performance budget: 60 fps with the full roster on a mid-range laptop; animation never delays
  badge updates.

**Gate:** the visual layer adds no extra load on the trading path (it only consumes events), and
disabling the UI entirely does not change trading behaviour.

---

## 8. Decisions on the open questions

### 8.1 Owner answers to the open questions

The owner answered the LD-1 (Foundation Phase 0) open questions on 2026-09-29. Each decision is applied in the
sections listed.

| # | Question | Decision | Applied in |
|---|---|---|---|
| Q1 | Where does the MT5 terminal run? | Stellar runs on the owner's **Mac** for now. MT5 execution will later run on a **separate Windows machine or Windows VPS** through a dedicated bridge service. **The final Windows host is not chosen yet.** | §7 LD-1, LD-4 (Host) |
| Q2 | Which markets first? | **XAU/USD, EUR/USD, USD/JPY, NAS100.** | §3.4, §6.4, §7 LD-3 and LD-4 (Symbol mapping) |
| Q3 | Where does FX analysis data come from? | A **Stellar-owned market-data abstraction**, not a direct dependency on upstream's stock-oriented providers. It is designed so **MT5 can become a future live/demo data source**. The **data layer stays separate from the execution layer.** | §1.1 principle 8, §1.4, §1.6, §7 LD-3 and LD-4 |
| Q4 | LLM provider, models and daily budget? | **Model-provider agnostic.** Lower-cost, fast models for routine agents; stronger models reserved for higher-value reasoning and manager roles. **Exact models and the daily budget stay configurable** until call volume and cost are benchmarked. | §1.1 principle 7 |
| Q5 | Initial risk limits? | **No final risk numbers are hard-coded.** Build configurable, deterministic risk controls; validate thresholds in backtests and demo first. | §6.4, §7 LD-3 |
| Q6 | Who can reset the circuit breaker? | **Only the human owner.** Agents may trigger a stop but can **never reactivate trading** themselves. | §3.7, §4.3 (Risk and circuit breaker), §5.4, §7 LD-3 |
| Q7 | Art direction? | A **futuristic spaceship / trading-station interior. Not pixel art.** A semi-realistic, stylized sci-fi look with large screens, command rooms, corridors, analysis stations, risk control, execution bay, lounge, café, billiard room and wellbeing areas. | §2.1, §7 LD-5 |
| Q8 | Multi-user or remote access? | **V1 is single-user only.** No multi-user authentication and no remote or public access. The design must not prevent a future remote-viewing mode, but it is **not built now**. | §7 LD-5 |

### 8.2 Further architectural decision

The owner approved the design, together with one further architectural decision:

| # | Topic | Decision | Applied in |
|---|---|---|---|
| D1 | Data and analysts for the first four markets | For XAU/USD, EUR/USD, USD/JPY and NAS100, **do not patch or modify upstream TradingAgents data-provider code.** Use **Stellar-owned market-data adapters** and **Stellar-owned market/technical analysts**. **Reuse upstream components downstream where compatible**: debate and research, trader, managers, memory and orchestration concepts. **Upstream repository code stays untouched.** | §1.4, §1.5 (C12), §1.6, §3.4, §7 LD-3 |

### 8.3 Reconciliation with the Foundation Plan (2026-09-30)

The owner approved `docs/STELLAR_FOUNDATION_PLAN.md` v0.3, including its §13.1 reconciliation
decisions as canonical (Foundation D-16) and the V1 scope decision (Foundation D-15). This
document was then updated, documentation only, so the two agree. No new architecture was added
here beyond the approved Foundation Plan.

| Ref | Canonical decision | Applied in this document |
|---|---|---|
| R-1 | **Setup-first rating mapping:** the PM's rating is the approval strength of a deterministic Setup; Buy → take; Overweight → per D-9 (default no trade); Hold / Underweight / Sell → do not take; REVIEW → no trade, owner flag | §1.5 (C7), §1.6, §1.7, §3.6, §4.3 (`trade.proposed`), §6.1, §6.3, §7 LD-3 (replaces the v0.3 flat-book / long / short table) |
| R-2 | **Foundation phase numbering** for implementation; this document's phases become themes LD-1 to LD-6 mapped to Foundation phases | Header, §1.1, §1.4, §1.5 (C2 note), §4.5, §6.5, §7 (all themes), §8.1 |
| R-3 | **Event names** `<domain>.<entity>.<past-tense verb>`; Foundation §10.1 is the V1 minimum | §3.2, §4.2, §4.3, §4.4, §4.5, new §4.6 (old → new map), §5, §6, §7 |
| R-4 | **Foundation rosters;** v0.3 agents mapped to new roles or visual personas | §1.2, §1.4, §1.7, §2.2, §2.3, §3 (rewritten), §5.1, §5.2, §6.2, §7 |
| R-5 | **Breaker reset:** owner only, via a local owner command in V1; the UI shows state only; a UI reset only later with authentication | §3.7, §4.3 (`circuit_breaker.*`), §5.4 (RED), §7 LD-3, LD-5 |
| R-6 | **Research chain** (research → validation → macro/causal → market specialists) | §1.2, §1.4, §1.6, §1.7, §2.2, §2.3, §3.3, §3.4 |
| D-15 | **V1 = paper**; the MT5 / Vantage demo is a separate gate after a stable paper V1; no profitability implied | §1.1 principle 6, §1.7, §3.8, §5.5, §6.1, §7 LD-4 |

Consequential edits, made only where this document contradicted the approved Foundation Plan:
the Stellar Journal as system of record, with the upstream memory log optional (Foundation U16,
D-10; §1.6, §4.3, §4.4); settlement from Stellar's own trades rather than upstream's alpha against
SPY (Foundation U17, L10; §6); ablation on the Stellar simulator rather than upstream's backtest
(Foundation U27; §6.3); cadence set by configurable timeframe profiles with no profile chosen
(Foundation §7, D-7; §7 LD-4); and a file importer first for market data (Foundation D-1; §7 LD-3).

---

## Appendix: upstream surfaces referenced

| Upstream file | What this design relies on |
|---|---|
| `tradingagents/graph/trading_graph.py` | `TradingAgentsGraph`, `propagate`, `create_run_state`, `stream_run`, `record_decision`, `settle_pending`, checkpoint methods, `run_settings` allowlist |
| `tradingagents/graph/setup.py` | Node names; parallel analyst sub-graphs; `max_tool_rounds` wrap-up |
| `tradingagents/graph/conditional_logic.py` | Debate turn-taking conventions (`Bull…`, `Aggressive…`, `Conservative…` prefixes; counts) |
| `tradingagents/graph/analyst_execution.py` | Analyst keys (`market`, `social`, `news`, `fundamentals`) ↔ node names ↔ report keys |
| `tradingagents/agents/state.py` | `AgentState`, `InvestDebateState`, `RiskDebateState` |
| `tradingagents/agents/schemas.py` | `PortfolioRating`, `TraderAction`, `TraderProposal`, `PortfolioDecision`, `SentimentReport` |
| `tradingagents/agents/rating.py` | `RATINGS_5_TIER`, `RATING_REVIEW`, `is_review`, `run_rating` |
| `tradingagents/agents/trader/trader.py`, `managers/portfolio_manager.py` | What is stored in state (rendered text vs typed rating) |
| `tradingagents/portfolio.py` | `PortfolioContext` and `Position` for passing real holdings |
| `tradingagents/memory/log.py`, `memory/settlement.py` | Decision records and outcome (raw and alpha return) |
| `tradingagents/backtest.py` | Grid evaluation for ablation and calibration |
| `tradingagents/dataflows/router.py`, `symbols.py` | Vendor chains; symbol normalisation (maps FX/CFD symbols to Yahoo proxies; not used for the four markets, Foundation L2) |
| `tradingagents/default_config.py` | Config keys and `TRADINGAGENTS_*` overrides |
| `cli/run.py`, `cli/display.py`, `cli/stats_handler.py` | Reference implementation of a streaming run, per-agent status and token counting |
| `tests/test_layering.py` | Precedent for enforcing layering rules with a test |
