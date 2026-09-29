# Stellar Agents — Layer Design

| | |
|---|---|
| **Status** | v0.3 — design approved by the owner; no code yet (Phase 1). Decisions recorded in §8 |
| **Date** | 2026-09-29 |
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
7. [Implementation phases](#7-implementation-phases)
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
6. **Demo only.** The execution layer refuses to act unless the connected account proves it is a
   demo account (see §7, Phase 4).
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
|  runner        wraps TradingAgentsGraph; schedules runs; sets market focus     |
|  telemetry     event schema · bus · LangChain handler · state observer · store |
|  agents        roster: agent ids, groups, home rooms, visual metadata          |
|  risk          signal validator · risk officer · exposure · circuit breaker    |
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
    risk/                        # validator.py, officer.py, exposure.py, breaker.py, sizing.py
    execution/                   # broker.py (interface), paper.py, mt5_client.py
                                 # (never imports marketdata providers directly; gets quotes
                                 #  through the marketdata interface)
    metrics/                     # global_.py, per_agent.py, contribution.py, wellbeing.py
    station/                     # rooms.py, visual_states.py (shared JSON with the UI)
    api/                         # server.py (REST + WebSocket)
  tests/                         # Stellar's own tests, including upstream contract tests
stellar_ui/                      # browser front end (Phase 5+)
mt5_bridge/                      # small service run on the Windows host (Phase 4)
docs/STELLAR_LAYER_DESIGN.md     # this document
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
| C7 | `agents/rating.py`: `RATINGS_5_TIER`, `RATING_REVIEW`, `is_review()` | Turning the final rating into a signal; blocking `REVIEW` | Low |
| C8 | `portfolio.PortfolioContext` / `Position` | Passing the demo account's real positions and cash into a run, so agents size against the actual book | Low |
| C9 | `memory.TradingMemoryLog.load_entries()` (rating, raw return, alpha, holding days) | Decision-quality and contribution metrics | Low–medium (markdown format) |
| C10 | `DEFAULT_CONFIG` keys (`llm_provider`, `data_vendors`, `max_debate_rounds`, `results_dir`, …) | Configuring runs per market | Low |
| C11 | `backtest.run_backtest / summarize` | Offline evaluation and ablation studies for contribution metrics | Low |
| C12 | Public agent factories in `tradingagents.agents` (`create_bull_researcher`, `create_bear_researcher`, `create_research_manager`, `create_trader`, the three risk debaters, `create_portfolio_manager`), `AgentState` / `InvestDebateState` / `RiskDebateState`, and `ConditionalLogic` | Building the Stellar market pipeline (§1.6): upstream's downstream agents run unchanged after Stellar-owned analysts | Medium: prompts read specific state keys (e.g. the Trader reads `market_report`) |

**C2 note.** LangGraph normally attaches the running node's name (`langgraph_node`) to the metadata
that callbacks receive. Upstream binds the callbacks to the LLM objects in their constructors rather
than per invocation. A Phase 2 spike must confirm the node name still arrives in that setup. If it
does not, the state observer (C3/C5) is the fallback source of "who is working". It is coarser but
always available.

### 1.6 Stellar market pipeline for the first four markets (§8 D1)

For **XAU/USD, EUR/USD, USD/JPY and NAS100**, Stellar does **not** patch, extend or modify
upstream's data-provider code (`tradingagents/dataflows/`), and does not change upstream's
analysts. Instead:

1. **Stellar-owned market-data adapters** (`stellar/marketdata/`, §1.4) supply quotes, OHLCV bars
   and symbol metadata for these instruments.
2. **Stellar-owned market / technical analysts** (`stellar/agents/analysts/`) call only
   Stellar tools backed by those adapters. They write the **same report keys** upstream's
   downstream agents read (`market_report`, and where applicable `news_report`,
   `sentiment_report`), with `fundamentals_report` left empty, which upstream's agents already
   treat as "no report".
3. **Stellar assembles its own LangGraph graph** for these markets (`stellar/pipeline.py`). It
   uses upstream's `AgentState` and **imports upstream's downstream agents unchanged**: Bull/Bear
   researchers, Research Manager, Trader, the three risk debaters and the Portfolio Manager
   (C12). It reuses upstream's orchestration pattern (analysts in parallel → investment debate →
   trader → risk debate → final rating) and upstream's `ConditionalLogic` for turn-taking.
4. **Memory is reused** through `TradingMemoryLog` (C9): the pipeline records decisions and
   writes outcomes through its public methods. Outcomes for these instruments are priced from
   Stellar's market data, because upstream's settlement fetches prices from its own providers.
5. **"Where compatible" is checked, not assumed.** Each reused upstream component is pinned by a
   Stellar contract test that runs it inside the Stellar pipeline with fake LLMs. If an upstream
   release breaks compatibility, Stellar replaces that one component with a Stellar-owned version
   rather than patching upstream.

```
Stellar marketdata adapters ──> Stellar market/technical analysts ─┐   (Stellar-owned)
(optional) upstream-compatible news/sentiment analysts ────────────┤
                                                                   v
           upstream Bull ⇄ Bear → Research Manager → Trader →          (upstream code,
           Aggressive → Conservative → Neutral → Portfolio Manager      imported unchanged)
                                                                   v
                     final_rating → Stellar risk gate → execution        (Stellar-owned)
```

Consequences:
- For these markets, telemetry hooks the **Stellar pipeline** directly (callbacks and its own
  stream), so C3/C4 (`TradingAgentsGraph` run methods) apply only to plain upstream runs, such as
  stocks through the unmodified engine.
- Whether upstream's News and Sentiment Analysts give useful output for these symbols is
  evaluated in Phase 3. If not, Stellar-owned news and macro analysts take their place under the
  same rule.
- Upstream's `TradingAgentsGraph` remains fully usable for the markets it already supports.

### 1.7 Run lifecycle through the layers

```
Station Controller picks focus (e.g. EURUSD, stock NVDA)
  -> StellarRun builds config + PortfolioContext (from broker positions)
  -> TradingAgentsGraph(callbacks=[StellarTelemetryHandler])
  -> create_run_state()  ... stream_run()  ... record_decision()
        | callbacks  -> agent.llm_call.*, agent.tool_call.*        (C2)
        | state diffs -> agent.report_filed, debate.*, signal.*    (C3/C5)
  -> final_rating  --(C7)--> SignalValidator -> RiskOfficer -> ExposureController -> CircuitBreaker
        | risk.approved  -> ExecutionPilot -> MT5 bridge -> order.sent / order.filled
        | risk.rejected  -> shadow-tracked as a paper signal for counterfactual metrics
  -> all events -> bus -> event store -> WebSocket -> Station UI
```

---

## 2. Space-station visual concept

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
                    |         MAIN COMMAND DECK         |
                    |  Portfolio Mgr (captain's chair)  |
                    |  Research Mgr · Trader · Station  |
                    |  Controller · alert-level lights  |
                    +-----------------+-----------------+
                                      | central lift
+---------------------+   +-----------+-----------+   +---------------------+
| MARKET ANALYSIS     |   |    DEBATE CHAMBER     |   | MACRO & NEWS        |
| WING                |===|  inner ring: bull vs  |===| OBSERVATORY         |
| market · fundament. |   |  bear (investment)    |   | news · sentiment ·  |
| FX desk · crypto    |   |  outer ring: risk     |   | macro · prediction  |
| desk                |   |  debaters (3 seats)   |   | markets             |
+----------+----------+   +-----------+-----------+   +----------+----------+
           |                          | central lift             :
+----------+----------+   +-----------+-----------+   +----------+----------+
| MEMORY ARCHIVE      |   |  RISK CONTROL VAULT   |##>|  EXECUTION BAY      |
| memory log ·        |   |  validator · officer  |   |  launch tubes ->    |
| reflections ·       |   |  exposure · breaker   |   |  "Vantage Demo      |
| checkpoints         |   |  (vault door)         |   |   Relay"            |
+----------+----------+   +-----------+-----------+   +----------+----------+
           |                          |                          :
+----------+--------------------------+--------------------------+----------+
|                                DATA CORE                                   |
|   vendor router · price/indicator caches · telemetry bus · event store     |
+-------------------------------------+--------------------------------------+
                                      |
        ========================== HABITAT RING ==========================
        |   WELLBEING ROOM (med-bay,   |   LOUNGE  ·  CAFÉ  ·  BILLIARD     |
        |   rest pods, recharge)       |   ROOM (off-duty agents)           |
        +------------------------------+------------------------------------+

 ===  open corridor        |  corridor / lift
 ##>  one-way airlock (the only agent entrance to the Execution Bay)
  :   data conduit only (market ticks, fills); agents cannot pass
```

### 2.3 Rooms

| Room | Purpose (real system) | Who is there | Key visual elements |
|---|---|---|---|
| **Main Command Deck** | Final decisions and orchestration | Portfolio Manager, Research Manager, Trader, Station Controller | Captain's chair; main viewscreen with the focus symbol's chart and the current rating; **station alert lights** (§5.4); run queue; the global metrics strip |
| **Market Analysis Wing** | Price, technicals, fundamentals, market-specific desks | Market Analyst, Fundamentals Analyst, FX Session Analyst, Crypto Analyst | Holo chart tables that draw each indicator as it is fetched; the fundamentals "filing wall"; the FX desk with a world clock of trading sessions |
| **Macro & News Observatory** | News, macro, sentiment, prediction markets | News Analyst, Sentiment Analyst | Telescope toward a "news nebula"; scrolling headlines; macro gauges (rates, CPI from FRED); a sentiment dial (band, score, confidence); Polymarket odds panel |
| **Debate Chamber** | Investment debate and risk debate | Bull & Bear Researchers (inner ring), Aggressive / Conservative / Neutral Risk Debaters (outer ring) | Two concentric rings of podiums; a spotlight on the current speaker; a round counter (`round n / max`); a tug-of-war balance bar that shifts as arguments land |
| **Risk Control Vault** | Deterministic risk gate | Signal Validator, Risk Officer, Exposure Controller, Circuit Breaker | The vault door (closed by default); a rule checklist that lights each check pass/fail; exposure bars against limits; the kill-switch lever (glows red when engaged) |
| **Execution Bay** | Order routing to the demo broker | Execution Pilot, Position Monitor | Launch tubes (orders as shuttles); a docking board of open positions with live P&L; a "DEMO" hull marking always visible; bridge link status |
| **Data Core** | Data vendors, caches, telemetry | Data Core Keeper | Reactor column that brightens with request volume; one conduit per vendor (yfinance, Alpha Vantage, SEC EDGAR, FRED, Polymarket, MT5 feed), coloured by health; cache-hit sparkle |
| **Memory Archive** | Memory log, settlement, reflection, checkpoints | Memory Archivist | Crystal shelves, one crystal per past decision, which light up green or red once settled against the benchmark; the reflection scriptorium |
| **Wellbeing Room** | Operational health: cooldown, retries, rest | Station Medic, Quartermaster; any agent that is resting or overloaded | Rest pods; a vitals board (load, error rate, budget); recharge animation |
| **Lounge / Café / Billiard Room** | Off-duty space; pure ambience | Café Host (cosmetic); agents not needed for the current run or with nothing to do | Café counter; billiard table; windows onto the galaxy; the "hall of fame" (best-calibrated agents this month) |

---

## 3. Agent system

### 3.1 Agent groups at a glance

| Group | Agents | Nature | Source |
|---|---|---|---|
| Analysis | Market, Fundamentals, News, Sentiment, *FX Session*, *Crypto* | LLM | 4 upstream, 2 future Stellar |
| Strategy / debate | Bull, Bear, Aggressive, Conservative, Neutral | LLM | upstream |
| Decision | Research Manager, Trader, Portfolio Manager | LLM | upstream |
| Risk / validation | Signal Validator, Risk Officer, Exposure Controller, Circuit Breaker | **Deterministic code** | Stellar |
| Execution *(added group)* | Execution Pilot, Position Monitor | Deterministic code | Stellar |
| System / memory | Station Controller, Data Core Keeper, Memory Archivist | Code (Archivist wraps upstream's LLM Reflector) | Stellar wrapping upstream |
| Wellbeing | Station Medic, Quartermaster, Café Host | Code; Café Host is cosmetic | Stellar |

**Decision: execution is its own group.** The brief listed six groups. Execution gets a seventh
because putting order-sending agents in any other group would blur the line the whole design rests
on: execution is downstream of, and separate from, risk approval.

**Decision: the upstream "risk analysts" are debaters.** Upstream's Aggressive, Conservative and
Neutral agents are LLMs arguing positions. They live in the Debate Chamber and are called **Risk
Debaters** in Stellar. The **Risk Control Vault** holds only deterministic code. An LLM debate is
not risk control.

### 3.2 Common agent state machine

Every agent, LLM or code, uses the same state set so the UI can render any agent the same way.

| State | Meaning | Typical trigger |
|---|---|---|
| `OFFLINE` | Not part of the station roster right now (disabled in config) | config |
| `OFF_DUTY` | On the roster but not selected for the current run (e.g. Fundamentals on an FX run) | `run.started` with analyst selection |
| `IDLE` | Available, waiting for work in its home room | run finished its part / no run |
| `ASSIGNED` | Has work queued; walking to its work position | `run.started`, dependency satisfied |
| `THINKING` | An LLM call is in flight | `on_chat_model_start` |
| `FETCHING` | A data tool call is in flight | `on_tool_start` |
| `SPEAKING` | Delivering a debate turn | debate turn in progress |
| `LISTENING` | In a debate, not the current speaker | another participant speaking |
| `WAITING` | Blocked on another agent (e.g. Bull waits for all analysts) | graph dependency |
| `REPORTING` | Just filed its output; carrying it to the next room | `agent.report_filed` |
| `CHECKING` | (code agents) evaluating rules | `risk.check_started` |
| `DEGRADED` | Working, but retrying / rate-limited / on a fallback path | retries, 429, structured-output fallback |
| `OVERLOADED` | Load score above threshold | `wellbeing.overload` |
| `RESTING` | Cooling down in the Wellbeing Room; takes no new work | `wellbeing.rest_started` |
| `ERROR` | Last action failed | `on_*_error`, vendor error |

```
OFF_DUTY <-> IDLE -> ASSIGNED -> {THINKING <-> FETCHING} -> REPORTING -> IDLE
                              \-> WAITING -> ...
            (debate agents)   ASSIGNED -> LISTENING <-> SPEAKING -> REPORTING
  any working state -> DEGRADED -> (recovers) | ERROR | OVERLOADED -> RESTING -> IDLE
```

### 3.3 Analysis agents

| Agent (`id`) | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Market Analyst** (`market_analyst`; upstream `Market Analyst`) | Price action, technical indicators, verified market snapshot | Market Analysis Wing, chart table | tool calls per run; indicators fetched; tool rounds used vs `max_tool_rounds`; forced wrap-ups; report latency; tokens | `FETCHING` shows the tool name (`get_indicators: rsi`) | A holo chart of the focus symbol; each fetched indicator is drawn onto the chart as it arrives; a rounds meter `7/20` |
| **Fundamentals Analyst** (`fundamentals_analyst`) | Statements, overview, insider activity | Market Analysis Wing, filing wall | statements fetched; vendor used (SEC EDGAR vs Yahoo); latency; no-data rate | `OFF_DUTY` for FX/crypto runs | Floating balance-sheet, cash-flow and income sheets that fill in; an insider-trade ticker |
| **News Analyst** (`news_analyst`) | Company and global news, FRED macro, prediction markets | Macro & News Observatory, telescope | articles read; macro series fetched; prediction markets queried; latency | Telescope turns when a new query is issued | A headline stream; macro gauges; a prediction-odds board |
| **Sentiment Analyst** (`sentiment_analyst`; upstream key `social`) | News, StockTwits and Reddit sentiment (optionally screened by TypeSafe Jev) | Macro & News Observatory, signal deck | posts ingested per source; posts screened out; sentiment band, score and confidence | Has no tools: goes straight `ASSIGNED → THINKING` | A sentiment dial (band from very bearish to very bullish), a confidence ring and a trickle of post "stars" |
| ***FX Session Analyst*** (`fx_session_analyst`, future) | FX-specific context: trading session, spread regime, rate differentials, economic calendar | Market Analysis Wing, FX desk | spread at analysis time; session; calendar events in window | Only on FX runs; new Stellar agent (§8 Q2) | A world clock with the active session highlighted; a spread gauge; upcoming-events strip |
| ***Crypto Analyst*** (`crypto_analyst`, future) | Crypto-specific context (upstream already has a crypto asset mode; this adds depth such as funding and on-chain data) | Market Analysis Wing, crypto desk | data sources hit; latency | Only on crypto runs. **Deferred:** crypto is not in the first market set (§8 Q2) | An orbiting-coin display; a funding-rate gauge |

**First markets (§8 Q2): XAU/USD, EUR/USD, USD/JPY and NAS100.** These are FX pairs, a metal and
an equity index, not single stocks. Upstream's Fundamentals Analyst and SEC data do not apply to
them, so it is `OFF_DUTY` on these runs. **For these instruments the market / technical analysis
is done by Stellar-owned analysts** backed by Stellar's market-data adapters, not by upstream's
Market Analyst (§1.6, §8 D1). They occupy the same chart tables in the Market Analysis Wing and
use the same states and visuals as the Market Analyst row above. How market-specific context for
gold and NAS100 is covered (by the FX Session Analyst or by dedicated desks) is decided in Phase 3.

### 3.4 Strategy / debate agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Bull Researcher** (`bull_researcher`) | Argues the investment case | Debate Chamber, inner ring, left podium | turns; words per turn; "won" rate (Research Manager sided bullish); conditional correctness (§6.3) | `WAITING` until every analyst has filed; then `SPEAKING` / `LISTENING` | Green spotlight when speaking; speech bubble with an excerpt; tug-of-war bar moves left |
| **Bear Researcher** (`bear_researcher`) | Argues against | Debate Chamber, inner ring, right podium | same as Bull | same | Red spotlight; bar moves right |
| **Aggressive Risk Debater** (`risk_aggressive`) | Argues for the high-reward view of the Trader's plan | Debate Chamber, outer ring | turns; agreement with the final rating | Round-robin: Aggressive → Conservative → Neutral | Orange podium light; "upside" arrows |
| **Conservative Risk Debater** (`risk_conservative`) | Argues for caution | Debate Chamber, outer ring | same | same | Blue podium light; shield icon |
| **Neutral Risk Debater** (`risk_neutral`) | Balances the two | Debate Chamber, outer ring | same | same | White podium light; balance-scale icon |

### 3.5 Decision agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Research Manager** (`research_manager`; deep model) | Judges the bull/bear debate; writes the investment plan with a 5-tier recommendation | Command Deck, strategy table | recommendation distribution; agreement with the PM; structured-output fallback rate; latency | Walks from the Command Deck to the Chamber's judge seat for the debate close, then back | A gavel moment; the recommendation badge appears on the main screen |
| **Trader** (`trader`) | Turns the plan into a proposal: Buy/Hold/Sell with entry, stop-loss and sizing text | Command Deck, trading console | action distribution; share of proposals with a numeric entry and stop; stop hit rate; entry-to-fill drift | Emits `signal.proposed` (draft) | A trade ticket being filled in field by field; the stop and entry drawn on the main chart |
| **Portfolio Manager** (`portfolio_manager`; deep model) | Weighs the risk debate; issues the **final rating** | Command Deck, captain's chair | rating distribution; `REVIEW` rate; calibration (average alpha per rating tier); latency | `REVIEW` puts it into `DEGRADED` with a "needs human" flag | The final rating stamped on the viewscreen; a `REVIEW` outcome flashes amber and nothing proceeds to the vault |

### 3.6 Risk / validation agents (deterministic)

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Signal Validator** (`signal_validator`) | Structural sanity: rating is not `REVIEW`; Hold produces no order; stop-loss present and on the correct side; entry within X% of the live price (stale-plan guard); the proposal parses | Risk Vault, intake desk | signals checked; rejection reasons histogram | `CHECKING` | The rule checklist lighting each line ✓/✗ |
| **Risk Officer** (`risk_officer`) | Per-trade limits and **position sizing by formula** (risk % of equity ÷ stop distance) in lots, respecting the broker's minimum lot and step | Risk Vault, main console | approvals and rejections; average risk per trade; sizing clipped by limits | `CHECKING` | A risk gauge "% of equity at risk"; the stamp APPROVED / REJECTED |
| **Exposure Controller** (`exposure_controller`) | Portfolio-level limits: open positions, per-symbol and per-currency exposure, correlated clusters (e.g. several USD pairs), margin level | Risk Vault, exposure wall | exposure versus limits; correlation-cluster load | `CHECKING` | Stacked exposure bars with limit lines |
| **Circuit Breaker** (`circuit_breaker`) | Station-wide stops: daily loss limit, max drawdown, consecutive-loss limit, bridge or feed failures, manual kill | Risk Vault, kill-switch lever | trips; time tripped; current headroom to each limit | `ARMED` (normal) / `TRIPPED` (all execution blocked until the **human owner** resets it; any agent may trip it, no agent can reset it — §8 Q6) | A lever that drops and turns the station to RED alert; vault door sealed |

### 3.7 Execution agents (deterministic)

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Execution Pilot** (`execution_pilot`) | Takes an approved order intent; runs pre-flight (demo check, market open, spread limit, idempotency key); sends to the broker bridge; records acknowledgement or rejection | Execution Bay, launch console | orders sent; broker rejections; ack latency; slippage | `PREFLIGHT`, `LAUNCHING`, `AWAITING_ACK` | A shuttle loaded into a launch tube and launched toward the Vantage Demo Relay |
| **Position Monitor** (`position_monitor`) | Tracks open positions; stop-loss/take-profit hits; closes on a new opposite signal or at the holding-period end; reconciles with the broker | Execution Bay, docking board | open positions; unrealized P&L; reconciliation mismatches | `RECONCILING` | The docking board: each position a docked ship with a live P&L halo |

### 3.8 System / memory agents

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Station Controller** (`station_controller`) | Schedules runs; picks the market focus; enforces run concurrency and budgets; owns the station alert level | Command Deck, ops console | queue depth; runs per day; run duration; skipped runs (budget or breaker) | `SCHEDULING` | The run queue; the focus-symbol selector; alert lights |
| **Data Core Keeper** (`data_core_keeper`) | Watches data vendors, caches and the telemetry bus | Data Core | requests per vendor; error rate (`VendorUnavailableError`, no-data); latency; cache hits | `DEGRADED` when any vendor is failing | Reactor brightness equals request rate; conduits coloured by vendor health |
| **Memory Archivist** (`memory_archivist`) | Settles pending decisions (upstream `settle_pending`), records outcomes and reflections, manages checkpoints | Memory Archive | pending vs settled decisions; settlement lag; reflections written | Uses upstream's Reflector (an LLM), so it can be `THINKING` | A new crystal shelved per decision; it lights green or red when settled |

### 3.9 Wellbeing agents

**Decision: "wellbeing" is operational health made visible, not an emotional simulation.** Every
wellbeing signal maps to something real: latency, retries, rate limits, error rates, token and cost
budgets, and forced wrap-ups. Wellbeing can **pause or slow work** (real cooldowns). It can **never
change a trading decision**.

| Agent | Role | Room | Key metrics | Specific states / notes | Displays visually |
|---|---|---|---|---|---|
| **Station Medic** (`station_medic`) | Computes each agent's load score (§6.5); sends overloaded agents to rest (real effect: a provider/agent cooldown and backoff before the next run); clears them when healthy | Wellbeing Room | load per agent; rests prescribed; mean time to recover | Walks to an agent in `ERROR` or `OVERLOADED` | A med-bot hovering over the patient; the vitals board |
| **Quartermaster** (`quartermaster`) | Token, cost and API-quota budgets per day and per run; warns and rations | Wellbeing Room, supply desk | spend vs budget; tokens by model; quota headroom per vendor | `RATIONING` when above 80% of budget | Fuel-cell gauges per provider |
| **Café Host** (`cafe_host`) | **Cosmetic only.** Serves drinks and moves around the lounge. No metrics and no influence on anything | Lounge / Café | none | none | Ambient life; greets agents coming off duty |

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
  "type": "agent.state_changed",
  "ts": "2026-09-29T14:03:12.481Z",
  "seq": 1842,
  "run_id": "run_2026-09-29_EURUSD_a1b2c3",
  "station_id": "stellar-01",
  "source": "upstream.callback | upstream.state | stellar.risk | stellar.execution | mt5.bridge | stellar.system",
  "agent_id": "market_analyst",
  "room": "market_wing",
  "symbol": "EURUSD",
  "correlation_id": "sig_7f3a",
  "payload": { }
}
```

| Field | Notes |
|---|---|
| `event_id` | A time-sortable unique id (ULID); used for de-duplication |
| `seq` | Monotonic per station; the UI detects gaps and asks for a resync |
| `run_id` | One TradingAgents run; `null` for station-level events |
| `correlation_id` | Threads a signal through risk, order, fill and close (`sig_*`, then `ord_*`, `pos_*`) |
| `agent_id` / `room` | Optional; present when the event concerns an agent or room |

### 4.3 Event catalogue

#### Station and run

| Type | Payload (key fields) |
|---|---|
| `station.heartbeat` | `alert_level`, `active_runs`, `queue_depth` |
| `station.alert_level_changed` | `from`, `to`, `reason` |
| `run.started` | `symbol`, `asset_type`, `trade_date`, `analysts[]`, `llm_provider`, `deep_model`, `quick_model`, `max_debate_rounds`, `max_risk_rounds` |
| `run.resumed` | `from_checkpoint_step` |
| `run.completed` | `duration_ms`, `final_rating`, `llm_calls`, `tool_calls`, `tokens_in`, `tokens_out` |
| `run.failed` | `error_class`, `message_excerpt`, `last_agent_id` |

#### Agent state and activity

| Type | Payload |
|---|---|
| `agent.state_changed` | `from`, `to`, `reason` (e.g. `llm_call`, `tool_call`, `dependency_wait`) |
| `agent.moved` | `from_room`, `to_room`, `reason` (emitted by the station layer from state changes; see §5) |
| `agent.llm_call.started` | `model`, `call_id` |
| `agent.llm_call.finished` | `call_id`, `latency_ms`, `tokens_in`, `tokens_out`, `structured` (true/false), `retries` |
| `agent.tool_call.started` | `tool`, `args_excerpt`, `call_id` |
| `agent.tool_call.finished` | `call_id`, `tool`, `vendor`, `ok`, `latency_ms`, `error_class` |
| `agent.report_filed` | `report_key`, `chars`, `excerpt`, `sha256` |
| `agent.wrap_up_forced` | `tool_rounds_used`, `max_tool_rounds` |
| `agent.error` | `error_class`, `message_excerpt` |

#### Market focus

| Type | Payload |
|---|---|
| `market.focus_changed` | `symbol`, `asset_type`, `reason` (`schedule`, `manual`, `signal_followup`) |
| `market.session_changed` | `session` (Sydney / Tokyo / London / New York), `overlaps[]` (FX) |
| `market.quote` | `bid`, `ask`, `spread` (**throttled**, e.g. at most 1/sec per symbol, from the MT5 bridge) |
| `market.data_stale` | `symbol`, `vendor`, `age_s` |

#### Debate

| Type | Payload |
|---|---|
| `debate.started` | `debate` (`investment` / `risk`), `participants[]`, `max_rounds` |
| `debate.turn` | `debate`, `speaker`, `round`, `turn_index`, `excerpt` |
| `debate.ended` | `debate`, `rounds`, `turns`, `verdict` (Research Manager's recommendation / Portfolio Manager's rating) |

#### Signal and decision

| Type | Payload |
|---|---|
| `decision.research_plan` | `recommendation` (5-tier) |
| `signal.proposed` | `signal_id`, `symbol`, `trader_action`, `entry`, `stop_loss`, `sizing_text`, `source` (`trader`) |
| `decision.final` | `signal_id`, `rating`, `is_review`, `price_target`, `time_horizon` |
| `signal.intent_created` | `signal_id`, `direction` (long / short / reduce / close / none), `size_factor` (from the rating mapping, §7 Phase 3) |

#### Risk

| Type | Payload |
|---|---|
| `risk.check_started` | `signal_id`, `checks[]` |
| `risk.check_result` | `signal_id`, `rule`, `passed`, `value`, `limit` |
| `risk.approved` | `signal_id`, `order_intent` {`symbol`, `side`, `volume_lots`, `sl`, `tp`}, `risk_pct_equity` |
| `risk.rejected` | `signal_id`, `reasons[]` (rule ids), `shadow_tracked: true` |
| `risk.limit_warning` | `rule`, `value`, `limit`, `headroom_pct` |
| `risk.breaker_tripped` | `rule`, `value`, `limit` |
| `risk.breaker_reset` | `by` (always the human owner; a reset from any other source is refused and logged as `risk.breaker_reset_refused`) |

#### Orders and positions

| Type | Payload |
|---|---|
| `order.created` | `order_id`, `signal_id`, `idempotency_key`, `symbol`, `side`, `volume`, `sl`, `tp` |
| `order.preflight_failed` | `order_id`, `reason` (`not_demo`, `market_closed`, `spread_too_wide`, `bridge_down`) |
| `order.sent` | `order_id`, `sent_at` |
| `order.acknowledged` | `order_id`, `broker_ticket` |
| `order.rejected` | `order_id`, `broker_retcode`, `reason` |
| `order.filled` | `order_id`, `fill_price`, `filled_volume`, `slippage_pips` |
| `order.partially_filled` | `order_id`, `filled_volume`, `remaining` |
| `position.opened` | `position_id`, `symbol`, `side`, `volume`, `open_price` |
| `position.updated` | `position_id`, `unrealized_pnl`, `price` (**throttled**) |
| `position.closed` | `position_id`, `close_price`, `realized_pnl`, `r_multiple`, `reason` (`stop_loss`, `take_profit`, `signal_exit`, `time_exit`, `breaker`, `manual`) |
| `account.snapshot` | `balance`, `equity`, `margin_level`, `open_positions`, `is_demo` (periodic) |

#### Memory

| Type | Payload |
|---|---|
| `memory.decision_stored` | `symbol`, `trade_date`, `rating` |
| `memory.outcome_settled` | `symbol`, `trade_date`, `rating`, `raw_return`, `alpha_return`, `holding_days` |
| `memory.reflection_written` | `symbol`, `trade_date`, `excerpt` |

#### Wellbeing and workload

| Type | Payload |
|---|---|
| `wellbeing.load_updated` | `agent_id`, `load` (0–1), `components` {latency, retries, errors, token_rate, wrap_ups} |
| `wellbeing.overload` | `agent_id`, `load`, `cause` |
| `wellbeing.rest_started` | `agent_id`, `cooldown_s`, `reason` |
| `wellbeing.rest_ended` | `agent_id` |
| `wellbeing.degraded` | `agent_id` or `provider`, `cause` (`rate_limited`, `retrying`, `freetext_fallback`) |
| `wellbeing.budget_warning` | `scope` (provider / day / run), `used`, `budget` |

### 4.4 Where events come from

| Event(s) | Derived from | Upstream surface |
|---|---|---|
| `agent.llm_call.*`, `agent.state_changed → THINKING` | LangChain `on_chat_model_start` / `on_llm_end` (+ `langgraph_node` metadata) | C2 |
| `agent.tool_call.*`, `→ FETCHING` | `on_tool_start` / `on_tool_end` / `on_tool_error` | C2 |
| `agent.report_filed` | `stream_run()` yields an analyst's report dict when its sub-graph finishes | C3 |
| `debate.started/turn/ended` (investment) | Diff of `investment_debate_state.count` and `current_response` prefix; end when `investment_plan` appears | C3, C5, C6 |
| `debate.*` (risk) | Diff of `risk_debate_state.count` / `latest_speaker`; end when `final_trade_decision` appears | C3, C5, C6 |
| `signal.proposed` | `trader_investment_plan` appears | C5 (see note) |
| `decision.final` | `final_rating` and `final_trade_decision` | C5, C7 |
| `risk.*`, `order.*`, `position.*`, `account.*` | Stellar risk and execution modules; MT5 bridge | Stellar only |
| `memory.*` | Wrapping `record_decision()` and `settle_pending()`; reading `TradingMemoryLog` | C3, C9 |
| `wellbeing.*` | Stellar metrics over the events above | Stellar only |

**Note on `signal.proposed`.** Upstream keeps the Trader's output as **rendered markdown** in state;
the typed `TraderProposal` object is not kept. Stellar parses the known rendered layout (Action /
Entry Price / Stop Loss / Position Sizing). If parsing fails, the numeric fields are `null` and the
Signal Validator rejects on "missing stop". This keeps it fail-closed. It is also a candidate for a
small, generic upstream contribution (keeping the structured proposal in state).

### 4.5 Transport and storage

```
producers (callback handler, state observer, risk, execution, bridge client, metrics)
   -> in-process EventBus (thread-safe; upstream runs analysts in parallel)
   -> EventStore: append-only (SQLite table, or JSONL per day) + periodic state snapshots
   -> WebSocket broadcaster -> Station UI
   -> Metrics aggregator (rolling windows) -> REST /metrics
```

- **Backpressure.** High-rate types (`market.quote`, `position.updated`, `wellbeing.load_updated`)
  are throttled and coalesced. Decision, risk and order events are **never** dropped.
- **Resync.** The UI connects, fetches `GET /snapshot` (current station state plus last `seq`), then
  subscribes from `seq+1`. On a gap it refetches the snapshot.
- **Replay.** `GET /runs/{run_id}/events` feeds the UI's replay mode (Phase 5).
- **Telemetry must not break trading.** Exceptions inside producers are caught and logged. A
  telemetry failure must never fail a run or an order. The reverse is not true: if the **risk** or
  **execution** events cannot be persisted, execution halts (audit trail is mandatory for orders).

---

## 5. UI and visual states

### 5.1 Home rooms and work positions

Each agent has a **home room** (where it idles) and one or more **work positions** (where it goes
when active). Most analysts work in their home room; decision and debate agents travel.

| Agent | Home | Work positions |
|---|---|---|
| Analysts | their wing / observatory | own desk; a beam to the Data Core while `FETCHING` |
| Bull / Bear | Debate Chamber (inner ring) | podiums |
| Risk Debaters | Debate Chamber (outer ring) | podiums |
| Research Manager | Command Deck | Chamber judge seat (investment debate close) |
| Trader | Command Deck | trading console |
| Portfolio Manager | Command Deck | captain's chair; Chamber judge seat (risk debate close) |
| Vault agents | Risk Control Vault | intake desk, console, exposure wall, lever |
| Execution agents | Execution Bay | launch console, docking board |
| Station Controller | Command Deck | ops console |
| Data Core Keeper | Data Core | reactor console |
| Memory Archivist | Memory Archive | shelves; Command Deck to collect a finished decision |
| Medic / Quartermaster | Wellbeing Room | anywhere an agent is in `ERROR` / `OVERLOADED` |
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
| `SPEAKING` | debate podium | spotlight; speech bubble with an excerpt; gestures | 🗨 bright, the side's colour |
| `LISTENING` | debate seat | seated, head turned to the speaker | 👂 dim |
| `WAITING` | work position or the waiting bench | seated; hourglass | ⌛ grey |
| `REPORTING` | walking to the next room | carries a glowing data crystal (the report) and hands it over | ◆ gold |
| `CHECKING` | vault stations | scanner sweep over the signal | ⌕ violet |
| `DEGRADED` | stays at work | hologram flicker; slower animation | ⚠ amber |
| `OVERLOADED` | stays, then escorted by the Medic to the Wellbeing Room | steam / sparks; then walks | ♨ orange |
| `RESTING` | Wellbeing Room rest pod | lying in a pod; recharge bar | ☾ soft blue + countdown |
| `ERROR` | stays in place | red beacon; the Medic walks over | ✖ red |

### 5.3 Movement rules

1. Movement is **derived from state changes** by the station layer (`agent.moved` events), so every
   client and every replay shows the same thing.
2. Pathfinding runs on a room graph (the corridors in §2.2), not free space. The Execution Bay node
   is reachable **only** from the Vault node.
3. **Teleport when late.** If an avatar is still walking when its next state arrives, it snaps to
   the new position so the view never shows stale activity.
4. **Parallel analysts are visible as parallel.** Upstream runs analysts concurrently; all four are
   shown working at the same time.
5. **Deterministic life.** Idle behaviour in the Lounge (who plays billiards with whom, café
   visits) uses a seeded random generator keyed on `run_id` and time, so replays look identical.
6. **Reduced-motion mode** replaces walking with fades and keeps all badges.

### 5.4 Station-wide alert levels

| Level | Condition | Visual |
|---|---|---|
| **GREEN** | No run active; all systems healthy | Soft ambient lighting |
| **BLUE** | A run is active | Blue accent lights; Command Deck viewscreen live |
| **AMBER** | Any vendor or provider degraded; a risk limit above 80%; a `REVIEW` decision; the bridge reconnecting | Amber strips; affected room outlined |
| **RED** | Circuit breaker tripped; demo check failed; broker reconciliation mismatch | Red lighting; vault door sealed; Execution Bay locked; a banner requiring the owner's reset |

### 5.5 Key UI panels (beyond the map)

- **Top strip:** alert level, demo equity, day P&L, open positions, today's runs and LLM spend.
- **Room panel** (click a room): its agents, their states and room-specific displays (§2.3).
- **Agent card** (click an avatar): role, current state, recent events, key metrics (§6.2) and
  contribution (§6.3), each with a sample size.
- **Signal timeline:** one row per `signal_id`: proposed → validated → approved/rejected → sent →
  filled → closed, with timestamps.
- **Event log:** a filterable raw stream.
- **Replay scrubber:** jump anywhere in a past run.

---

## 6. Performance metrics

All metrics are computed from the event store and upstream's memory log, over rolling windows
(today, 7 days, 30 days, all time). **Every displayed metric carries its sample size**, and
rankings are hidden below a minimum sample size (default N ≥ 30 settled decisions), because small
samples produce confident-looking noise.

### 6.1 Global metrics

| Metric | Definition | Source |
|---|---|---|
| Runs completed / failed | Count per window | `run.*` |
| Run duration p50 / p95 | `run.completed.duration_ms` | events |
| Rating distribution | Share of Buy / Overweight / Hold / Underweight / Sell / REVIEW | `decision.final` |
| REVIEW rate | REVIEW ÷ runs | `decision.final` |
| Directional hit rate | Share of settled Buy/Overweight with raw return > 0, and Sell/Underweight with raw return < 0 | memory log |
| Mean alpha by rating | Average alpha vs benchmark per tier (should be monotonic: Buy > Overweight > Hold > …) | memory log |
| Demo equity, balance, day P&L | Latest `account.snapshot` | bridge |
| Realized P&L, win rate, profit factor, average R multiple, expectancy | Over closed positions | `position.closed` |
| Max drawdown (equity, peak-to-trough) | From the equity series | `account.snapshot` |
| Sharpe / Sortino (daily) | From daily equity returns; shown only with ≥ 60 trading days | derived |
| Signal-to-trade funnel | proposed → approved → filled | risk / order events |
| LLM calls, tokens, estimated cost | Per day and per run | callback events |
| Vendor error rate | Failed ÷ total tool calls per vendor | tool events |
| Uptime | Heartbeat coverage | `station.heartbeat` |

### 6.2 Per-agent metrics

| Metric | Applies to |
|---|---|
| Runs participated in; time in each state | all |
| LLM calls, tokens in/out, estimated cost, p50/p95 latency | LLM agents |
| Structured-output fallback rate (free text used instead of the typed schema) | Research Manager, Trader, Portfolio Manager, Sentiment Analyst |
| Tool calls, tool failures, vendor mix | analysts |
| Tool rounds used vs `max_tool_rounds`; forced wrap-ups | analysts with tools |
| Report length; empty or "no data" reports | analysts |
| Debate turns, words per turn | debaters |
| Checks run, rejections by rule | vault agents |
| Orders sent, broker rejects, ack latency, slippage | Execution Pilot |
| Reconciliation mismatches | Position Monitor |
| Errors, retries, rests prescribed | all |

### 6.3 Contribution metrics

Attributing the outcome of a multi-agent decision to individual agents is hard. Stellar uses
several **complementary, clearly labelled** measures and never a single "agent score".

| Metric | For | How it is computed | Caveat |
|---|---|---|---|
| **Stance accuracy** | analysts | Each report's directional stance (bullish / neutral / bearish), versus the settled raw return. The Sentiment Analyst already emits a typed band. Other analysts need a cheap Stellar-side **stance extractor** (a small LLM call or a rules pass over the report) | The extractor is itself a model; it is validated against a hand-labelled sample first |
| **Agreement with final** | all LLM agents | Share of runs where the agent's stance matched the final rating's direction | Agreement is not correctness; shown next to accuracy, never alone |
| **Debate win rate** | Bull / Bear | Share of runs where the Research Manager's recommendation took their side | Measures persuasiveness, not truth |
| **Conditional correctness** | Bull / Bear, risk debaters | When their side won, how often the outcome agreed | Needs many samples |
| **Rating calibration** | Research Manager, Portfolio Manager | Mean alpha per rating tier; a monotonicity check; Brier-style score on direction | The core decision-quality measure |
| **Trader execution quality** | Trader | Stop-hit rate; entry-to-fill drift; maximum adverse / favourable excursion vs the proposed stop | Depends on market regime |
| **Risk value added** | vault agents | Rejected signals are **shadow-tracked** as paper trades. Avoided loss = losses of rejected signals; missed gain = gains of rejected signals. Net = avoided − missed | Counterfactual; fills are idealised |
| **Ablation delta** | analysts | Periodic `run_backtest` on a fixed grid with one analyst removed; compare calibration and hit rate | Expensive; run monthly, offline |

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
| **Load score** (0–1) per agent | A weighted blend of: latency relative to its own baseline, retry rate, error rate, token rate relative to its budget, and forced wrap-ups. Initial weights 0.30 / 0.25 / 0.20 / 0.15 / 0.10, tuned in Phase 2 |
| Overload threshold | load ≥ 0.8 for two consecutive calls → `wellbeing.overload` |
| Rest (cooldown) | Real effect: new runs needing that agent or provider are delayed with backoff (e.g. 60 s → 5 min); visual effect: rest pod |
| Fatigue (cosmetic smoothing) | An exponentially decaying sum of recent working time; drives only animation such as slower walking. **Never** gates work |
| Rate-limit hits (429) per provider | from errors and retries |
| Budget usage | tokens and estimated cost vs daily budget per provider |
| Utilisation | share of time in working states per agent |
| Queue depth / wait time | for the Station Controller |

---

## 7. Implementation phases

Each phase ends with a **gate**: its exit criteria must hold before the next phase starts. Phases 2
and 3 can overlap; **Phase 4 must not start before Phase 3's gate passes**.

### Phase 1 — Documentation and design *(this document)*

- Map the upstream repository (done).
- Write this design; review and resolve the open questions (§8).
- Set up the upstream sync workflow: an `upstream` remote pointing at `TauricResearch/TradingAgents`;
  merge (not rebase) upstream releases; after each merge, run upstream's tests and Stellar's
  contract tests.

**Gate:** design approved; open questions resolved (§8, done). The final Windows host for MT5 is
deliberately **not** chosen in this phase (§8 Q1); it is chosen at the start of Phase 4.

### Phase 2 — Telemetry layer

- Create `stellar/` as a separate project; add `.github/workflows/stellar.yml`.
- Implement the event envelope and catalogue (pydantic models), the bus and the SQLite/JSONL store.
- **Spike:** confirm `langgraph_node` reaches callbacks bound in the LLM constructors (§1.5 C2).
- `StellarTelemetryHandler` (LangChain callbacks) and `StateObserver` (diffs `stream_run()` output).
- `StellarRun`: mirrors `cli/run.py`'s path (`create_run_state` → `stream_run` → `record_decision`
  → checkpoint handling) and emits events.
- Contract tests pinning C1–C11 (node names, state keys, rating constants, `stream_run` shape).
- A text "station log" CLI (`stellar watch`) that prints events live, to validate before any
  graphics exist.
- Metrics v0: global and per-agent operational metrics; wellbeing load score.
- Tests use fake LLMs and fake tools in the style of upstream's end-to-end tests. No network.

**Gate:** a full run produces a complete, ordered event stream; replaying it rebuilds the same
final state summary; upstream's tests still pass untouched; telemetry failure injected in tests does
not fail the run.

### Phase 3 — Risk hardening

- **Rating → intent mapping** (deterministic, configurable):

  | Final rating | Flat book | Existing long | Existing short |
  |---|---|---|---|
  | Buy | open long, size ×1.0 | hold / top up to target | close short; optional long |
  | Overweight | open long, size ×0.5 | hold | reduce short |
  | Hold | no order | no change | no change |
  | Underweight | open short ×0.5 (FX) / no order (long-only markets) | reduce long | hold |
  | Sell | open short ×1.0 (FX) / no order (long-only markets) | close long | hold / top up |
  | **REVIEW** | **no order; human flag** | no change | no change |

- **Signal Validator:** schema and sanity rules (stop present and on the correct side; entry
  within a tolerance of the live price; plan not older than N hours; duplicate-signal cooldown).
- **Risk Officer:** sizing by formula only. The Trader's free-text `position_sizing` is displayed,
  never used. Round down to the broker's lot step; reject below the minimum lot.
- **Exposure Controller** and **Circuit Breaker** with the limits in §6.4. All limits are
  configuration; none is hard-coded or treated as final (§8 Q5). Threshold values are calibrated
  with backtests and paper trading here, and confirmed on the demo account in Phase 4.
- **Breaker reset belongs to the human owner only (§8 Q6).** Any agent or rule may trip the breaker.
  No agent, scheduler, retry path or API call made by the system can reset it or re-enable
  trading. Reset is a separate, owner-only action with confirmation, and it is recorded as an
  event. Tests prove that every non-owner reset path is refused.
- **Stellar market-data abstraction (§8 Q3):** a `MarketDataSource` interface (quotes, OHLCV
  bars, symbol metadata) and a Stellar-owned symbol map for XAU/USD, EUR/USD, USD/JPY and NAS100
  (§8 Q2). It has one initial implementation backed by an existing provider (chosen here) and is
  shaped so MT5 can implement it later without changes elsewhere. It lives in
  `stellar/marketdata/`, apart from `stellar/execution/`.
- **Stellar market pipeline (§1.6, §8 D1):** Stellar-owned market / technical analysts that
  use only the Stellar market-data adapters, assembled into a Stellar-owned graph that imports
  upstream's debate, research, trader and manager agents unchanged. Upstream's data-provider code
  is not patched, extended or registered into. Contract tests pin each reused upstream component.
  Phase 3 also decides whether upstream's News and Sentiment Analysts are useful for these symbols,
  or whether Stellar-owned replacements are needed.
- A **paper broker** that implements the same broker interface as MT5 and simulates fills from
  quotes supplied by the market-data abstraction. All of Phase 3 runs against it.
- Shadow tracking of rejected signals (for §6.3 "risk value added").
- Property-based and table tests: every rule can reject; the gate fails closed on missing data;
  no path exists from `decision.final` to `order.created` that skips the gate.

**Gate:** 100% rule coverage in tests; a fault-injection suite (missing quote, missing stop,
bridge down, NaN equity, REVIEW) yields zero orders; a multi-week paper-trading soak with no
unexplained orders.

### Phase 4 — MT5 / Vantage demo layer

- **Host (§8 Q1).** In v1 the Stellar core runs on the owner's **Mac**. The official
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
  match the configured demo server. Any mismatch → `order.preflight_failed(not_demo)` and the
  breaker trips.
- **Symbol mapping:** Stellar's symbol map (Phase 3) gains the broker column for XAU/USD,
  EUR/USD, USD/JPY and NAS100 (§8 Q2). Vantage may use suffixes or its own index name for NAS100;
  confirm this against the demo server's symbol list. Contract size, lot step, minimum volume and
  digits come from the broker, never hard-coded.
- **MT5 as a data source (§8 Q3):** MT5 may be added as an implementation of the
  `MarketDataSource` interface (bars and quotes). It is a separate component from the execution
  client, even though both talk to the same bridge. Analysts for these markets are `market` +
  `news` (+ the future FX Session Analyst); fundamentals and SEC data do not apply.
- **Cadence:** TradingAgents is a daily, date-based system (one `trade_date`, a 5-day holding
  period by default), and a full run costs many LLM calls and minutes of time. Stellar therefore
  trades at a **daily or multi-day cadence** (for example one run per symbol per day, after a
  chosen session close), not intraday.
- **Reconciliation:** the Position Monitor compares the broker's positions with Stellar's ledger on
  a timer; any mismatch trips the breaker.
- **Secrets:** broker credentials live only on the bridge host (the terminal's own login); Stellar
  holds a bridge token in its environment, never in config files, events or logs.

**Gate:** two or more weeks on the demo account with complete reconciliation, zero demo-guard
bypasses, and every order traceable from `decision.final` to `position.closed` in the event store.

### Phase 5 — Visual station v1

- Front end in `stellar_ui/`: a station view in the §2 art direction (§8 Q7), a **semi-realistic,
  stylized sci-fi interior, not pixel art**, plus HTML panels. The rendering technology (for example
  a WebGL renderer with pre-rendered or 3D-modelled rooms) is chosen at the start of this phase to
  fit that look. The back end is in `stellar/api/` (REST + WebSocket).
- **Single-user and local only (§8 Q8).** The API and UI bind to `localhost` on the owner's Mac.
  There are no user accounts, no multi-user authentication and no remote or public access in v1.
  To avoid ruling out a future remote-viewing mode, the UI only consumes the event stream and
  snapshots, and the API keeps read-only viewing endpoints separate from owner actions such as a
  breaker reset. Remote viewing itself is not built.
- All ten rooms from §2 as static art; agents as avatars with **status badges** (§5.2).
- Agents **fade/teleport** between rooms (no pathfinding yet).
- Room panels, agent cards, the signal timeline, the event log and the top metrics strip.
- **Replay mode** for past runs.
- Alert levels (§5.4) driving station lighting.
- Accessibility: icons plus colour, reduced motion, keyboard navigation, readable at laptop width.

**Gate:** someone watching a live run can say, at any moment, which agents are working, what the
decision is and whether anything is blocked; this matches the event log exactly.

### Phase 6 — Visual station v2 (movement and life)

- Pathfinding along corridors; walk animations; data-crystal hand-offs; debate staging with
  spotlights and the tug-of-war bar.
- Shuttle launches from the Execution Bay; the docking board of positions.
- Habitat life: lounge and café routines, billiards between off-duty agents, the Café Host.
  All seeded and deterministic (§5.3 rule 5).
- Day/night lighting tied to FX sessions; optional ambient sound.
- Time-lapse replay of a whole day; the "hall of fame" (calibration leaders, with sample sizes).
- Performance budget: 60 fps with the full roster on a mid-range laptop; animation never delays
  badge updates.

**Gate:** the visual layer adds no extra load on the trading path (it only consumes events), and
disabling the UI entirely does not change trading behaviour.

---

## 8. Decisions on the open questions

The owner answered the Phase 1 open questions on 2026-09-29. Each decision is applied in the
sections listed.

| # | Question | Decision | Applied in |
|---|---|---|---|
| Q1 | Where does the MT5 terminal run? | Stellar runs on the owner's **Mac** for now. MT5 execution will later run on a **separate Windows machine or Windows VPS** through a dedicated bridge service. **The final Windows host is not chosen yet.** | §7 Phase 1 gate, Phase 4 (Host) |
| Q2 | Which markets first? | **XAU/USD, EUR/USD, USD/JPY, NAS100.** | §3.3, §6.4, §7 Phase 3 and Phase 4 (Symbol mapping) |
| Q3 | Where does FX analysis data come from? | A **Stellar-owned market-data abstraction**, not a direct dependency on upstream's stock-oriented providers. It is designed so **MT5 can become a future live/demo data source**. The **data layer stays separate from the execution layer.** | §1.1 principle 8, §1.4, §3.3, §7 Phase 3 and Phase 4 |
| Q4 | LLM provider, models and daily budget? | **Model-provider agnostic.** Lower-cost, fast models for routine agents; stronger models reserved for higher-value reasoning and manager roles. **Exact models and the daily budget stay configurable** until call volume and cost are benchmarked. | §1.1 principle 7 |
| Q5 | Initial risk limits? | **No final risk numbers are hard-coded.** Build configurable, deterministic risk controls; validate thresholds in backtests and demo first. | §6.4, §7 Phase 3 |
| Q6 | Who can reset the circuit breaker? | **Only the human owner.** Agents may trigger a stop but can **never reactivate trading** themselves. | §3.6, §4.3 (Risk), §5.4, §7 Phase 3 |
| Q7 | Art direction? | A **futuristic spaceship / trading-station interior. Not pixel art.** A semi-realistic, stylized sci-fi look with large screens, command rooms, corridors, analysis stations, risk control, execution bay, lounge, café, billiard room and wellbeing areas. | §2.1, §7 Phase 5 |
| Q8 | Multi-user or remote access? | **V1 is single-user only.** No multi-user authentication and no remote or public access. The design must not prevent a future remote-viewing mode, but it is **not built now**. | §7 Phase 5 |

The owner approved the design, together with one further architectural decision:

| # | Topic | Decision | Applied in |
|---|---|---|---|
| D1 | Data and analysts for the first four markets | For XAU/USD, EUR/USD, USD/JPY and NAS100, **do not patch or modify upstream TradingAgents data-provider code.** Use **Stellar-owned market-data adapters** and **Stellar-owned market/technical analysts**. **Reuse upstream components downstream where compatible**: debate and research, trader, managers, memory and orchestration concepts. **Upstream repository code stays untouched.** | §1.4, §1.5 (C12), §1.6, §3.3, §7 Phase 3 |

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
| `tradingagents/dataflows/router.py`, `symbols.py` | Vendor chains; symbol normalisation (stocks and crypto; FX to be assessed) |
| `tradingagents/default_config.py` | Config keys and `TRADINGAGENTS_*` overrides |
| `cli/run.py`, `cli/display.py`, `cli/stats_handler.py` | Reference implementation of a streaming run, per-agent status and token counting |
| `tests/test_layering.py` | Precedent for enforcing layering rules with a test |
