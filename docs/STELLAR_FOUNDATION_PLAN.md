# Stellar Agents — Foundation Plan

| | |
|---|---|
| **Status** | v0.3 — **approved by the owner (2026-09-30)**. Owner decisions D-15 (V1 scope) and D-16 (reconciliation) approved 2026-09-29. Design only; no source code, scaffolding or dependencies. |
| **Date** | 2026-09-29 |
| **Companion to** | `docs/STELLAR_LAYER_DESIGN.md` (v0.4, reconciled with this plan on 2026-09-30; see its §8.3). That document is the architecture and visual-station reference; this one is the canonical build plan. §13.1 records the canonical decisions **approved by the owner (D-16)**; if any conflict is found later, this plan governs and the conflict is fixed in a documentation-only change. |
| **Master Roadmap** | `docs/STELLAR_MASTER_ROADMAP.md` (added 2026-09-30, D-19) is the overview and defers to this plan. This plan was reconciled against the requirements the owner stated for it: the multi-stage research chain (§4.29, §9), candle/price action in the first technical foundation (§4.10, §11), separate architectural / minimum-V1 / deferred rosters (§5), and configurable timeframe profiles with the owner's strategy hypothesis (§7). |
| **Upstream baseline** | TradingAgents v0.5.2 (commit `8b22d43`), inspected read-only |
| **Not a claim of** | Profitability. Nothing in this plan assumes or implies that any strategy makes money. |

---

## How to read this document: three sources, never merged

Every capability in this plan is labelled with **exactly one** source.

| Label | Meaning | Trust level |
|---|---|---|
| **UPSTREAM** | Exists today in the TradingAgents repository and was inspected. | Behaviour is **verified** from the code where marked VERIFIED; everything else is interpretation. |
| **ARIA** | A concept from the owner's earlier experimental XAU/USD prototype, ARIA Gold V2, as supplied by the owner. | **Inspiration only.** Not validated. No ARIA formula, threshold or code is carried over as truth. |
| **STELLAR** | New, designed and owned by Stellar Agents. | To be built, tested and validated. |

When a Stellar component is *inspired by* ARIA or *reuses* upstream, it still carries the
STELLAR label, and the inspiration or reuse is named explicitly next to it.

In §1–§2, **VERIFIED** means "confirmed by reading the upstream source at the path given".
**DESIGN INTERPRETATION** means "our reading of what that implies for Stellar"; it may be wrong
and is checked in the phase noted.

---

## Contents

1. [Upstream TradingAgents — reuse map](#1-upstream-tradingagents--reuse-map)
2. [Upstream components we must not trust directly](#2-upstream-components-we-must-not-trust-directly)
3. [ARIA legacy concepts](#3-aria-legacy-concepts)
4. [Stellar Agents — required new foundation](#4-stellar-agents--required-new-foundation)
5. [Stellar agent rosters](#5-stellar-agent-rosters)
6. [First four markets](#6-first-four-markets)
7. [Trading horizons](#7-trading-horizons)
8. [Hard risk foundation](#8-hard-risk-foundation)
9. [Data → decision → execution contract](#9-data--decision--execution-contract)
10. [Telemetry and visual-station foundation](#10-telemetry-and-visual-station-foundation)
11. [Implementation roadmap](#11-implementation-roadmap)
12. [V1 definition of done](#12-v1-definition-of-done)
13. [Reconciliation with the layer design, and open decisions](#13-reconciliation-with-the-layer-design-and-open-decisions)

---

## 1. Upstream TradingAgents — reuse map

### 1.1 Classification key

| Class | Meaning |
|---|---|
| **KEEP** | Import and use unchanged, as is. |
| **WRAP** | Import unchanged, but always call it through a thin Stellar wrapper that adds a contract (inputs set, outputs validated, telemetry). |
| **ADAPT** | Reuse the *idea or pattern*, or subclass without changing upstream, but Stellar owns the working code. |
| **REPLACE** | Stellar builds its own component for the four markets. Upstream's stays in the repository for upstream's own use. |
| **NOT USED** | Not part of Stellar for the four markets. |

In every case the upstream file itself is **never modified** (layer design §8 D1).

### 1.2 Cross-cutting facts that shape the whole reuse map (VERIFIED)

- **The downstream agents are date-agnostic and data-free.** Bull/Bear researchers, the Research
  Manager, the Trader, the three risk debaters and the Portfolio Manager read only graph state:
  report strings, debate state, `instrument_context`, `portfolio_context`, `past_context`. They
  call no data tools and do not read `trade_date`. Only the analysts, `agents/tools.py` and
  `agents/context.py` read `trade_date`. This is what makes downstream reuse possible.
- **Agent factories are public.** `tradingagents/agents/__init__.py` exports
  `create_bull_researcher`, `create_bear_researcher`, `create_research_manager`, `create_trader`,
  `create_aggressive_debator`, `create_conservative_debator`, `create_neutral_debator`,
  `create_portfolio_manager` (plus the four analyst factories). Each takes one LLM object and
  returns a node function `state -> dict`.
- **Output language comes from a process-wide config.** `get_language_instruction()` in
  `agents/context.py` reads `tradingagents.dataflows.config.get_config()`. Any Stellar graph that
  runs upstream agents must set upstream config first (`set_config` / `run_config`).
- **Instrument context is injectable.** `get_instrument_context_from_state()` uses
  `state["instrument_context"]` when it is non-empty and makes **no network call** in that case.
  Stellar can supply its own instrument description and avoid upstream's yfinance identity
  lookup entirely.

### 1.3 Reuse table

Paths are relative to the repository root.

| # | Area | Exact upstream path → symbol | Current responsibility | How Stellar reuses it | Import unchanged? | Adapter / contract Stellar needs | Known limitations | If upstream changes | Class |
|---|---|---|---|---|---|---|---|---|---|
| U1 | Graph state | `tradingagents/agents/state.py` → `AgentState`, `InvestDebateState`, `RiskDebateState` | Typed LangGraph state shared by all nodes | Stellar's graph state **subclasses** `AgentState` to add Stellar fields (snapshot id, profile, setup, analysis timestamp) | Yes (subclassed, not edited) | Contract test: the fields the reused agents read still exist with the same types | `trade_date` is a date string only; no timeframe or timestamp | Copy the last-compatible definition into Stellar and pin it | **ADAPT** |
| U2 | Analyst report fields | `AgentState` keys `market_report`, `sentiment_report`, `news_report`, `fundamentals_report` | Where analysts publish reports for downstream agents | Stellar fills them from its research and technical chain (§4.29): `market_report` ← Technical Analyst; `news_report` ← rendered Causal/Macro and market-specialist assessments; `fundamentals_report` ← empty, or later the NAS100 corporate/earnings summary (deferred); `sentiment_report` ← empty in V1 | Yes | Empty reports are rendered by `agents/context.py` → `report_or_absent()` as "No … report in this run" (VERIFIED), so downstream agents see an explicit absence | Downstream prompts label these as "market", "news", etc.; Stellar content must fit those labels | Contract test on key names | **KEEP** |
| U3 | Graph assembly | `tradingagents/graph/setup.py` → `GraphSetup.setup_graph()`, `_analyst_graph()`; `tradingagents/graph/trading_graph.py` → `TradingAgentsGraph` | Builds and runs upstream's full pipeline including upstream analysts | Not used for the four markets. Stellar builds its own graph (`stellar/pipeline`) following the same shape. The per-analyst sub-graph with a tool-round cap is copied as a *pattern*; the private `_analyst_graph` is not imported | n/a | — | `TradingAgentsGraph` always builds upstream analysts, which Stellar replaces | No dependency, so no impact | **NOT USED** (for the four markets) / pattern **ADAPT** |
| U4 | Turn-taking | `tradingagents/graph/conditional_logic.py` → `ConditionalLogic.should_continue_debate`, `.should_continue_risk_analysis` | Decides next debate speaker from counts and speaker prefixes | Used unchanged in the Stellar graph with the same node names | Yes | Stellar graph must use upstream's node names ("Bull Researcher", "Research Manager", …) and path maps equivalent to `DEBATE_PATH_MAP` / `RISK_ANALYSIS_PATH_MAP` | Depends on hard-coded name prefixes | Contract test; if broken, a Stellar copy of the two functions | **KEEP** |
| U5 | Initial state | `tradingagents/graph/propagation.py` → `Propagator.create_initial_state()` | Builds an empty run state | Called by Stellar to get correctly shaped empty debate states, then Stellar fields are added | Yes | Wrapper adds Stellar fields and a Stellar-supplied `instrument_context` | Takes `trade_date` string only | Stellar copies the dict shape | **WRAP** |
| U6 | Bull / Bear research | `tradingagents/agents/researchers/bull_researcher.py` → `create_bull_researcher(llm)`; `bear_researcher.py` → `create_bear_researcher(llm)` | LLM debate for and against | Imported unchanged as nodes in the Stellar graph | Yes | Stellar reports must be self-contained text; `asset_type` should be a non-`"stock"` value so prompts say "asset" | Prompts mention "unavailable for crypto" for non-stocks (VERIFIED wording); framed as an investment thesis, not a timed trade | Replace with a Stellar researcher behind the same state contract | **KEEP** |
| U7 | Research Manager | `tradingagents/agents/managers/research_manager.py` → `create_research_manager(llm)`; schema `agents/schemas.py` → `ResearchPlan` | Judges the debate; typed 5-tier recommendation, rendered to text in `investment_plan` | Imported unchanged | Yes | Stellar reads only `investment_plan` text for display; it does not drive execution | Recommendation is kept only as rendered text in state | Stellar version behind the same contract | **KEEP** |
| U8 | Trader | `tradingagents/agents/trader/trader.py` → `create_trader(llm)`; `agents/schemas.py` → `TraderProposal`, `render_trader_proposal()` | Buy/Hold/Sell plus optional entry, stop and sizing; **stored only as rendered markdown** in `trader_investment_plan` | Imported unchanged. Its entry and stop are parsed from the rendered text and treated as **advisory**; they are compared with Stellar's deterministic levels (Contradiction Checker), never used as order levels | Yes | Strict parser for the `render_trader_proposal` layout. A free-text fallback output (no layout) → levels "unknown" | Levels are LLM-produced; `position_sizing` is free text such as "5% of portfolio" (VERIFIED schema) | Parser pinned by contract test; if the layout changes, levels are treated as unknown (fail closed) | **WRAP** |
| U9 | Risk debate | `tradingagents/agents/risk_mgmt/aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py` → `create_*_debator(llm)` | LLM argument about the Trader's plan | Imported unchanged. **Advisory only**; it is not risk control (§2) | Yes | Output shown in UI and journal; no execution effect | Opinion, not limits | Stellar version or removal | **KEEP** (advisory) |
| U10 | Portfolio Manager | `tradingagents/agents/managers/portfolio_manager.py` → `create_portfolio_manager(llm)`; `agents/schemas.py` → `PortfolioDecision`, `PortfolioRating` | Final **typed** 5-tier rating in `final_rating`, plus rendered `final_trade_decision`; reads `past_context` lessons | Imported unchanged. `final_rating` is the one LLM output that feeds the Trade Proposal Builder, and only as an approval strength for a Stellar setup (§4.13) | Yes | Wrapper validates `final_rating` ∈ 5 tiers or `REVIEW`; anything else → no trade | Rating semantics are position-oriented: "Sell = exiting or avoiding the position" (VERIFIED, research manager / PM prompts). Sell does **not** mean "open a short" | Contract test on the rating vocabulary | **WRAP** |
| U11 | Rating vocabulary | `tradingagents/agents/rating.py` → `RATINGS_5_TIER`, `RATING_REVIEW`, `is_review()`, `parse_rating()`, `run_rating()` | Canonical rating set; non-tradeable `REVIEW` sentinel | Used unchanged | Yes | — | `parse_rating` reads text heuristically; Stellar prefers the typed `final_rating` | Stellar copy of the constants | **KEEP** |
| U12 | Structured output helpers | `tradingagents/agents/structured.py` → `bind_structured()`, `invoke_structured()`, `invoke_structured_or_freetext()`, `NO_EXTERNAL_TOOLS` | Provider-native structured output with free-text fallback | Stellar's own LLM agents use `bind_structured` + `invoke_structured`. **Not** `invoke_structured_or_freetext` at decision boundaries: a structured miss is a failed step, not free text | Yes | Stellar treats `None` from `invoke_structured` as failure | Fallback path silently changes output shape | Stellar copy (the functions are small) | **WRAP** |
| U13 | Output schemas | `tradingagents/agents/schemas.py` → `PortfolioRating`, `TraderAction`, `TraderProposal`, `SentimentReport`, `_coerce_optional_float()` | Pydantic schemas for decision agents | Rating enums reused. `TraderProposal` is a reference only; Stellar defines its own `TradeProposal` (§4.13) | Yes (enums) | — | Upstream schemas lack instrument, timeframe, take-profit, expiry | Stellar schemas are independent | **KEEP** (enums) / **REPLACE** (proposal) |
| U14 | Instrument context | `tradingagents/agents/context.py` → `build_instrument_context()`, `resolve_instrument_identity()`, `get_instrument_context_from_state()` | Describes the instrument to agents; identity looked up via yfinance | Stellar writes its own `instrument_context` string into state (e.g. "Spot gold quoted in USD; not a company; no fundamentals") | n/a | Stellar sets `state["instrument_context"]` so the upstream lookup is never triggered (VERIFIED behaviour) | Upstream text is company/crypto oriented | No dependency | **REPLACE** (Stellar string, upstream mechanism) |
| U15 | Portfolio context | `tradingagents/portfolio.py` → `PortfolioContext`, `Position`, `load_portfolio()`, `.render()`, `.fingerprint()` | Caller's holdings and cash rendered for agents | Stellar builds a `PortfolioContext` from the Paper Broker (or later MT5) positions and puts `.render()` into `portfolio_context` | Yes | Mapping Stellar positions (lots) → `Position.quantity` (generic units) with a stated unit label | Units generic; no margin, no lot semantics (by design, VERIFIED docstring) | Stellar renderer with the same output text | **WRAP** |
| U16 | Memory log | `tradingagents/memory/log.py` → `TradingMemoryLog.store_decision()`, `.load_entries()`, `.get_pending_entries()`, `.get_past_context()`, `.batch_update_with_outcomes()` | Append-only markdown log; supplies `past_context` lessons to the PM | Optional, **only for profiles that make at most one decision per instrument per day**: Stellar may write decisions here so the PM receives past lessons. The **Stellar Journal** (§4.24) is the system of record | Yes | Stellar writes outcomes itself via `batch_update_with_outcomes()` | **One entry per ticker per date**: `store_decision` silently skips a second entry for the same ticker and date (VERIFIED idempotency guard). Unusable for several decisions a day. Markdown format | Stellar generates `past_context` from its own journal | **WRAP** (limited) |
| U17 | Settlement / scoring | `tradingagents/memory/settlement.py` → `settle_pending()`, `fetch_returns()`, `resolve_benchmark()` | Scores a decision by daily close-to-close return over `holding_period_days` (default 5) vs a benchmark | Not used for the four markets | n/a | — | Uses Yahoo daily closes via `get_closes`; benchmark for suffix-less symbols is **SPY** (VERIFIED `benchmark_map[""]`), so "alpha vs SPY" for EUR/USD is meaningless; scores a rating, not a trade | — | **REPLACE** (Stellar settlement from actual trades) |
| U18 | Reflection | `tradingagents/memory/reflection.py` → `Reflector.reflect_on_final_decision()` | LLM lesson from a decision and its outcome | Deferred Post-Trade Reviewer may call it with Stellar's numbers | Yes | Stellar supplies return and a benchmark label (e.g. "none") | Built around raw/alpha return, not R-multiple | Stellar reviewer prompt | **WRAP** (deferred) |
| U19 | Checkpoint / resume | `tradingagents/graph/checkpointer.py` → `get_checkpointer()`, `thread_id()`, `checkpoint_step()`, `clear_checkpoint()` | Per-ticker SQLite LangGraph checkpoints keyed by ticker + date + signature | Stellar graph may use `get_checkpointer()` and pass a `signature` that includes the analysis timestamp and profile, so intraday runs do not collide | Yes | Signature must be unique per run; checkpoints are an optimisation, never a source of truth | Keyed by date by default; per-ticker DB files | LangGraph's own SQLite saver directly | **WRAP** (optional in V1) |
| U20 | Streaming hooks | `TradingAgentsGraph.stream_run()` | Yields `(messages, state)` pairs from `values` + `tasks` modes with sub-graphs | Pattern reused in the Stellar graph's own streaming; the method itself belongs to upstream's graph and is not usable for Stellar's graph | n/a | — | Tied to `TradingAgentsGraph` | No dependency | **ADAPT** (pattern) |
| U21 | CLI status callbacks | `cli/stats_handler.py` → `StatsCallbackHandler`; `cli/display.py` → `MessageBuffer`, `update_agent_status()` | Token/call counting and terminal status | Not imported; the Stellar core must not depend on the `cli` package. The callback approach (LangChain `BaseCallbackHandler`) is reused in Stellar's telemetry handler | n/a | — | Terminal-specific | No dependency | **ADAPT** (pattern) / **NOT USED** (code) |
| U22 | LLM provider abstraction | `tradingagents/llm_clients/factory.py` → `create_llm_client()`, `build_llm_kwargs()`; `base_client.py` → `BaseLLMClient.get_llm()` | Provider-agnostic chat model creation (OpenAI, Anthropic, Google, Azure, Bedrock, OpenAI-compatible) with retries, token caps, reasoning effort | Used unchanged to build a model per **tier** (e.g. `quick`, `deep`) from Stellar config | Yes | Stellar config maps each agent to a tier; per-tier provider/model/kwargs | Kwargs are keyed on upstream config names | Stellar calls LangChain chat classes directly | **KEEP** |
| U23 | Look-ahead guard | `tradingagents/dataflows/date_window.py` → `as_of()`, `as_of_window()`, `is_historical()` | Stops tools returning data after `trade_date` | Principle adopted; code not used (Stellar needs timestamp-level as-of, not date-level) | n/a | — | Date granularity | — | **ADAPT** (principle) |
| U24 | Upstream data vendors | `tradingagents/dataflows/router.py` → `route_to_vendor()`, `VENDOR_METHODS`; `dataflows/vendors/*`; `agents/tools.py` | Stock-oriented data tools | Not used for the four markets (layer design D1) | n/a | — | See §2 | — | **NOT USED** |
| U25 | Symbol normalisation | `tradingagents/dataflows/symbols.py` → `normalize_symbol()`, `safe_ticker_component()` | Maps broker-style symbols to Yahoo symbols; path-safe tickers | `safe_ticker_component()` pattern (path safety) adopted. `normalize_symbol()` not used (§2) | n/a | — | Maps to Yahoo proxies (§2) | — | **ADAPT** (path-safety pattern) / **NOT USED** |
| U26 | Upstream analysts | `tradingagents/agents/analysts/*` → `create_market_analyst`, `create_news_analyst`, `create_sentiment_analyst`, `create_fundamentals_analyst` | Stock-oriented analysis | Not in V1. News and Sentiment Analysts may be evaluated later (§5) | n/a | — | Depend on upstream data tools | — | **REPLACE** (market) / **NOT USED** (others, V1) |
| U27 | Backtesting | `tradingagents/backtest.py` → `run_backtest()`, `summarize()`, `iter_grid()`, `BacktestSummary` | Runs `TradingAgentsGraph` over a ticker × date grid; scores ratings via the memory log | Not used for the four markets. Adopted principles: an isolated memory log per run; resumable sweeps; "evaluation, not a portfolio simulator" | n/a | — | Daily grid; runs the upstream graph; no fills | — | **REPLACE** (Stellar simulator, §4.17) |
| U28 | Reports on disk | `tradingagents/reporting.py` → `write_report_tree()` | Writes markdown report folders for a finished state | Optional human-readable export of a Stellar run's LLM reports | Yes | Final state must contain the keys it reads | Markdown only | Stellar exporter | **WRAP** (optional) |
| U29 | Upstream config | `tradingagents/default_config.py` → `DEFAULT_CONFIG`, `build_default_config()`; `dataflows/config.py` → `set_config()`, `run_config()` | Engine settings, env overrides | Stellar derives a minimal upstream config (language, LLM tiers, debate rounds) from Stellar config and applies it with `run_config()` | Yes | Stellar owns its own config; upstream config is derived, never hand-edited | Process-wide state | Contract test on the keys used | **WRAP** |
| U30 | Layering test | `tests/test_layering.py` | Enforces "only the data layer imports vendor libraries" | Pattern reused for Stellar's own boundary tests (§8.4) | n/a | — | — | — | **ADAPT** (pattern) |

### 1.4 Summary by class

| Class | Items |
|---|---|
| **KEEP** | U2 report fields, U4 turn-taking, U6 Bull/Bear, U7 Research Manager, U9 risk debate (advisory), U11 rating vocabulary, U13 rating enums, U22 LLM factory |
| **WRAP** | U5 initial state, U8 Trader, U10 Portfolio Manager, U12 structured helpers, U15 portfolio context, U16 memory log (limited), U18 Reflector (deferred), U19 checkpointer (optional), U28 reports, U29 config |
| **ADAPT** | U1 state (subclass), U3 analyst sub-graph pattern, U20 streaming pattern, U21 callback pattern, U23 as-of principle, U25 path safety, U30 layering test |
| **REPLACE** | U13 proposal schema, U14 instrument context text, U17 settlement, U26 market analyst, U27 backtesting |
| **NOT USED** | U3 `TradingAgentsGraph` / `GraphSetup` (for the four markets), U21 CLI code, U24 data vendors, U25 `normalize_symbol`, U26 other upstream analysts in V1 |

---

## 2. Upstream components we must not trust directly

| # | Limitation | VERIFIED (what the code does) | DESIGN INTERPRETATION (what it means for Stellar) |
|---|---|---|---|
| L1 | Stock-oriented market data | Default vendors are Yahoo Finance (`data_vendors` in `default_config.py`). `vendors/yahoo/ohlcv.py` → `load_ohlcv()` downloads **5 years of daily history** through `yf.Ticker(...).history(...)` with no interval argument, cached per symbol | Daily bars only. No intraday data for M5–H4 profiles, no bid/ask, no spread |
| L2 | Proxy symbols for FX/CFD | `dataflows/symbols.py` `_ALIASES`: `XAUUSD` → `GC=F` (COMEX gold **future**), `NAS100` → `^NDX` (Nasdaq-100 **cash index**). Six-letter currency pairs → `EURUSD=X`, `USDJPY=X`. A trailing `+` is stripped | These are *proxies*. Futures trade at a basis to spot; the cash index has no overnight prices, unlike a CFD. Prices from them must never be used as order levels on a broker's spot/CFD instrument |
| L3 | Fundamentals not applicable | Fundamentals tools serve company statements (SEC EDGAR, Yahoo), insider transactions, company profile | Meaningless for XAU/USD, EUR/USD, USD/JPY. For NAS100 only indirectly relevant (constituents' earnings). Upstream's fundamentals tools are not used; `fundamentals_report` stays empty except for an optional, later NAS100 earnings summary from Stellar research (§4.29) |
| L4 | Text-formatted levels | `TraderProposal` (typed) is rendered by `render_trader_proposal()` and only the **markdown** is stored in `trader_investment_plan`. On a structured miss, the Trader falls back to free text via `invoke_structured_or_freetext()` | Entry/stop must be parsed from text; on the fallback path they may be absent or ambiguous. They are advisory only in Stellar |
| L5 | LLM risk debate ≠ risk control | The three risk debaters are LLM prompts arguing positions; no numeric limit is enforced anywhere in upstream | Stellar's hard risk controls (§8) are entirely new and deterministic |
| L6 | No execution | `backtest.py` and `portfolio.py` state explicitly that there is no fill, quantity or execution model | Paper Broker and MT5 bridge are entirely Stellar |
| L7 | Daily / multi-day horizon | `trade_date` must be `YYYY-MM-DD` and not in the future (`trading_graph.py` → `_validate_trade_date`); `holding_period_days` default 5; settlement uses daily closes | Upstream's assumptions fit swing-style horizons. Intraday profiles cannot rely on upstream timing, scoring or memory (L9) |
| L8 | Position-oriented rating semantics | Research Manager prompt: "Sell: … recommend exiting or avoiding the position" | A Sell is not reliably "open a short". Stellar must not map Sell → short by itself (§4.13, "setup-first framing") |
| L9 | One memory entry per ticker per day | `TradingMemoryLog.store_decision()` returns early if any entry exists for the same ticker and date | Multiple intraday decisions would be silently dropped. The Stellar Journal is the record |
| L10 | Benchmark alpha | `settlement.resolve_benchmark()` falls back to `benchmark_map[""] = "SPY"` for symbols without an exchange suffix | "Alpha vs SPY" for EUR/USD, USD/JPY or gold is not a meaningful metric |
| L11 | Nondeterministic decisions | `temperature` defaults to `None` (provider default); the comment on it in `default_config.py` states that no setting makes LLM output bit-identical across runs | The same inputs can yield different ratings. Replay must use **recorded** LLM outputs (§4.25), and attribution needs many samples |
| L12 | Process-wide config | `get_language_instruction()` reads the global `get_config()` | Stellar must set upstream config before running reused agents; concurrent runs with different configs need `run_config()` contexts |
| L13 | API / name drift | Node names ("Bull Researcher", …) are literal strings in `graph/setup.py`; speaker prefixes in `conditional_logic.py`; the Trader's rendered layout; state key names | Any upstream release may change these. Every reused surface is pinned by a Stellar contract test (§11, Phase 1) |
| L14 | Crypto-flavoured "non-stock" wording | Researchers switch to "asset" wording when `asset_type != "stock"` and describe fundamentals as "may be unavailable for crypto" | Minor prompt mismatch for FX/indices. Accepted for V1; revisit if it measurably confuses outputs |

---

## 3. ARIA legacy concepts

ARIA Gold V2 was an experimental XAU/USD application. **Only the concepts listed by the owner are
considered.** No ARIA code, formulas or thresholds are imported.

### 3.1 Classification key

| Class | Meaning |
|---|---|
| **KEEP AS CONCEPT** | The idea is sound as a *capability*. Stellar designs its own implementation with configurable parameters. |
| **RESEARCH / VALIDATE** | Plausible, but its value must be demonstrated on historical data (Phase 6) before it can influence decisions. Off by default. |
| **REDESIGN** | The need is real, but ARIA's form is unsuitable (too simple, ambiguous or unsafe). Stellar solves it differently. |
| **DROP** | Not carried forward. |

### 3.2 Concept table

| Area | ARIA concept | Class | Stellar treatment (STELLAR) |
|---|---|---|---|
| Modes | Scalp M5/M15 | **REDESIGN** | Not a separate "mode": short timeframes appear as the **entry** level of a profile (§7), where timing is deterministic. Running the LLM chain at an M5 cadence is unlikely to be feasible (many LLM calls per run); to be measured (Phase 6) |
| Modes | Day Trade M15/H1 | **KEEP AS CONCEPT** | A candidate profile; no V1 profile is chosen in this plan (§7, §13.2 D-7) |
| Modes | Swing H4/Daily | **KEEP AS CONCEPT** | A candidate profile; closest to upstream's horizon (L7); not chosen as V1 by default |
| Sessions | Asian, London, London/NY overlap, New York, quiet/close | **KEEP AS CONCEPT** | Market Session Agent (§5). Session boundaries are configuration, defined in UTC with DST handling, and **per instrument** (NAS100's cash session differs from FX sessions) |
| Technical | EMA 9 / 21 / 50 / 200 | **KEEP AS CONCEPT** (periods: **RESEARCH / VALIDATE**) | The indicator pipeline supports any EMA set; the specific periods are configuration, not defaults assumed to work |
| Technical | RSI | **KEEP AS CONCEPT** | Standard indicator; period and levels configurable |
| Technical | MACD | **KEEP AS CONCEPT** | Standard indicator; parameters configurable |
| Technical | ATR | **KEEP AS CONCEPT** | Core volatility measure; used by stop distance sanity checks and volatility filters |
| Technical | EMA cross | **RESEARCH / VALIDATE** | Computed as a feature; any signal role must be validated |
| Technical | H1 / M15 / H4 / Daily directional context | **KEEP AS CONCEPT** | Multi-timeframe context is the backbone of §7 |
| Technical | Candle patterns | **REDESIGN** | Deterministic, precisely defined candle and price-action features (body/range ratios, engulfing, pin bars, inside bars, rejection at levels) with unit tests on constructed candles, owned by the Candle / Price Action Agent in the **first technical foundation** (Phase 5). Never LLM "eyeballing". Predictive value of each pattern: RESEARCH |
| Technical | Psychological support/resistance | **RESEARCH / VALIDATE** | Round-number levels as a feature with a per-instrument, configurable step. No step is assumed here |
| Pullback | Oversold RSI | **RESEARCH / VALIDATE** | Feature available to the Pullback Agent; thresholds configurable and validated |
| Pullback | RSI direction | **RESEARCH / VALIDATE** | Feature (slope over N bars) |
| Pullback | RSI crossing a level | **RESEARCH / VALIDATE** | Feature (cross event with bar index) |
| Pullback | Bullish/bearish candle confirmation | **REDESIGN** | Candle / Price Action Agent output consumed by the Pullback / Setup and Entry Timing Agents (Phase 5) |
| Pullback | MACD confirmation | **RESEARCH / VALIDATE** | Feature |
| Pullback | Support/resistance context | **KEEP AS CONCEPT** | Market Structure Agent produces levels with a stated method (swing points, prior highs/lows) |
| Pullback | Market-session quality | **KEEP AS CONCEPT** | Session context attached to every setup; its weighting is RESEARCH |
| Risk | Stop-loss / take-profit | **KEEP AS CONCEPT** | Stop-loss **mandatory** (hard rule §8); take-profit required by default (configurable) |
| Risk | Reward:risk relationship | **KEEP AS CONCEPT** | Minimum R:R is a configurable hard rule; the value is not chosen here |
| Risk | News proximity | **KEEP AS CONCEPT** | Becomes a hard news/event restriction (§8) driven by an economic calendar |
| Risk | Volatility | **KEEP AS CONCEPT** | ATR-based filters; thresholds RESEARCH |
| Risk | Spread | **KEEP AS CONCEPT** | Hard max-spread rule per instrument (§8) |
| Risk | Session quality | **REDESIGN** | Not a hard risk rule in V1 (too subjective); a recorded context feature and optional session allowlist per profile |
| Operational | WAIT / WATCH / TRADE IDEA / NO TRADE | **REDESIGN** | A precise setup lifecycle state machine (§4.12): `NO_SETUP → WATCHING → ARMED → PROPOSED → APPROVED/REJECTED → EXPIRED`. Each transition has a deterministic cause |
| Operational | Macro / technical / risk / rebound scoring | **REDESIGN** | No single additive score that can hide contradictions. Each dimension is a structured assessment (direction, strength, evidence ids); contradictions are surfaced, not averaged away |
| Operational | Confidence display | **REDESIGN** | LLM confidence is uncalibrated. The UI shows the rating plus **measured** calibration of that rating tier with its sample size (§6 of the layer design) |
| Operational | Lot calculator | **REDESIGN** | Becomes Risk Engine position sizing from risk amount ÷ stop distance using **broker-supplied** instrument metadata. Nothing hard-coded |
| Operational | Economic calendar | **KEEP AS CONCEPT** | Input to Economic Data Research and to the news/event risk rule (§4.29, §8); source unresolved (§13.2 D-2) |
| Operational | Analysis journal | **KEEP AS CONCEPT** | Stellar Journal (§4.24): every snapshot, report, proposal, decision, order and outcome, linked by ids |
| Operational | Live chart / dashboard | **KEEP AS CONCEPT** | Station UI (Phase 8); charts render from the event store and snapshots |
| All | ARIA's numeric thresholds, weights and formulas as defaults | **DROP** | Not used as defaults anywhere. Any value is set in config and validated (Phase 6) |

---

## 4. Stellar Agents — required new foundation

All components in this section are **STELLAR**. "Inspired by" and "reuses" notes name any ARIA or
UPSTREAM relationship. Module paths are proposals under `stellar/src/stellar/` (layer design
§1.4); they are not created in this phase.

### 4.1 Market-data abstraction
- **Purpose:** the only way any Stellar component obtains prices.
- **Contract:** a `MarketDataSource` interface with `instruments()`, `candles(instrument,
  timeframe, start, end, as_of)`, `quote(instrument, as_of)`, `metadata(instrument)`. Every call
  takes an explicit `as_of` timestamp; no data after `as_of` is ever returned (UPSTREAM principle
  U23, re-implemented at timestamp level).
- **Implementations:** V1: a local file importer (CSV/Parquet) for owner-supplied data and
  reproducible tests, plus a historical provider once one is chosen (§13.2 D-1); later: MT5 (via
  the bridge), separate from execution.
- **Module:** `marketdata/source.py`, `marketdata/providers/…`.

### 4.2 Symbol normalisation
- **Purpose:** one canonical Stellar symbol per instrument, mapped to each provider and broker.
- **Contract:** `InstrumentId` values `XAUUSD`, `EURUSD`, `USDJPY`, `NAS100`. A mapping table
  per provider and (later) per broker. An unmapped symbol is an error, never a guess.
- **Rule:** every candle and quote records **which provider symbol** produced it. A proxy
  (for example a future for spot gold) is flagged `proxy=true` and may be used for analysis only,
  never for order levels (L2).
- **Module:** `marketdata/symbols.py`.

### 4.3–4.6 Instrument support: XAU/USD, EUR/USD, USD/JPY, NAS100
- Each instrument is a configuration record: canonical id, asset class (`metal`, `fx`, `index_cfd`),
  base/quote currency, session calendar id, provider mappings, analysis-only flags. Price
  precision, contract size and lot rules come from the broker at runtime (§6).
- Per-market detail is in §6.

### 4.7 Timeframe abstraction
- **Purpose:** a closed set of timeframes with exact boundaries.
- **Contract:** `Timeframe` ∈ {M1, M5, M15, M30, H1, H4, D1, W1}; each has a duration and a
  bar-alignment rule in UTC. D1 and W1 bar boundaries are **provider-specific** (for example
  New York close vs UTC midnight); the provider declares its convention and snapshots record it.
- **Module:** `marketdata/timeframes.py`.

### 4.8 OHLC / candle representation
- **Contract (fields):** `instrument`, `timeframe`, `open_time` (UTC), `close_time` (UTC), `open`,
  `high`, `low`, `close`, `volume`, `volume_kind` (`tick` / `real` / `none`), `price_side`
  (`bid` / `ask` / `mid` / `last`), `source`, `provider_symbol`, `is_closed`.
- **Rule:** analysis uses **closed** candles only; the forming candle is excluded unless a rule
  explicitly asks for it.
- **Validation:** high ≥ max(open, close), low ≤ min(open, close), monotonic times, no duplicates,
  gap detection (weekend and session gaps are expected; unexpected gaps are flagged).

### 4.9 Technical indicator pipeline
- **Purpose:** deterministic features computed from candles: EMA(n), RSI(n), MACD(a,b,c),
  ATR(n), crosses, slopes (concepts from ARIA §3; parameters configurable).
- **Contract:** pure functions `features = compute(candles, spec)`; output includes the spec and
  the input candle range so any value is reproducible. Warm-up bars are tracked; a feature
  without enough history is `null`, not a number.
- **Tests:** against hand-computed values on fixed candle fixtures.

### 4.10 Price-action / candle analysis — part of the first technical foundation
- **Why it is foundational:** the first strategy family the owner wants to test is
  *higher-timeframe bias → pullback → candle/price-action analysis → momentum confirmation → entry
  timing*. Candle / price action is a required link in that chain, so it is built in Phase 5,
  **before** any serious paper or demo strategy validation (Phases 7–8). It is not deferred.
- **Purpose:** deterministic candle and price-action features (inspired by ARIA's candle patterns,
  REDESIGNED): body/range ratios, wick ratios, engulfing, pin bar, inside/outside bar, rejection
  or acceptance at a Market Structure level, break-and-retest, with exact definitions documented
  next to each.
- **Output:** a typed `PriceActionAssessment` per timeframe: per-candle features, events tied to
  structure levels, and bar indices. Never a "buy/sell" verdict. Which features predict anything
  is RESEARCH (§3), measured in Phase 7.

### 4.11 Trend / pullback analysis
- **Purpose:** multi-timeframe market structure (swing highs/lows, higher-high/lower-low state,
  support/resistance levels with method) and pullback detection relative to the context trend.
- **Output:** a typed `StructureAssessment` per timeframe (trend state, key levels, evidence) and
  `PullbackAssessment` (depth, location vs levels, confirmation features present/absent).
- **Inspired by:** ARIA pullback/rebound concepts (classified RESEARCH in §3).

### 4.11a Momentum confirmation and entry timing
- **Momentum confirmation:** typed `MomentumAssessment` from the indicator pipeline (e.g. RSI
  level/direction/crosses, MACD state) on the pullback and entry levels of the profile (§7).
  Which conditions count as "confirmed" is strategy configuration, validated in Phase 7.
- **Entry timing:** a deterministic Entry Timing Agent evaluates the entry trigger on the
  profile's entry timeframe while a Setup is `ARMED`, combining price action (§4.10) and momentum.
  It is the only component that runs at the fastest cadence, and it calls no LLM.

### 4.12 Setup lifecycle (inspired by ARIA decision states, REDESIGNED)
- A **Setup** is a deterministic candidate trade idea on the setup timeframe:
  `setup_id`, instrument, profile, direction (`LONG` / `SHORT`), trigger conditions, invalidation
  level, created_at, valid_until, evidence ids.
- States: `NO_SETUP → WATCHING → ARMED → PROPOSED → APPROVED | REJECTED → FILLED | EXPIRED |
  INVALIDATED`. Each transition is caused by a named rule and emits an event.

### 4.13 Structured `TradeProposal` schema
- **Setup-first framing (key decision, approved as canonical in §13.1 R-1 via D-16; DESIGN
  INTERPRETATION of L8, validated in Phase 6):** the LLM pipeline does **not** invent direction
  from scratch. The deterministic layer produces a directional Setup; the research chain, debate
  and Portfolio Manager evaluate **that setup**. The PM's typed rating is read as **approval
  strength for the setup**: Buy → take it; Overweight → size factor per decision D-9 (safe default:
  no trade); Hold → do not take it; Underweight / Sell → reject it; REVIEW → no trade, flagged for
  the owner. This makes "Sell" unambiguous for FX and indices, where "avoid the position" and "go
  short" differ.
- **Built by:** the deterministic Trade Proposal Builder (P1, §5.1), never by an LLM directly.
- **Fields:** `proposal_id`, `run_id`, `snapshot_id`, `setup_id`, `instrument`, `profile`,
  `direction`, `source_rating`, `size_factor`, `entry` {type `market`/`limit`, price or zone},
  `stop_loss` {price, basis}, `take_profits` [{price, basis}], `reward_risk` (computed),
  `valid_until`, `llm_levels_advisory` {entry, stop from the Trader, parsed (U8)},
  `contradictions` [], `report_hashes`, `config_hash`, `created_at`.

### 4.14 Structured `OrderIntent` schema
- **Built by:** the Risk Engine only, and only from an APPROVED `RiskDecision`.
- **Fields:** `intent_id`, `proposal_id`, `decision_id`, `account_mode` (`PAPER` / `DEMO`),
  `broker_symbol`, `side`, `volume` (lots, from Risk Engine sizing), `order_type`, `price`,
  `stop_loss`, `take_profit`, `max_slippage`, `idempotency_key`, `expires_at`.

### 4.15 Paper Broker
- **Purpose:** simulated execution with the same interface as the future MT5 client.
- **Behaviour:** fills from bid/ask quotes supplied by the market-data abstraction; configurable
  spread model when only mid/bid history exists; slippage model; stop-loss and take-profit
  evaluated on subsequent candles with a documented intrabar rule (for example stop-first when
  both are touched in one candle, the conservative assumption); swap/commission as configurable
  costs, off until modelled.
- **Account:** starting balance and account currency are required configuration with no default; the Paper Broker refuses to start without them (§13.2 D-8).

### 4.16 Execution abstraction
- `Broker` interface: `account()`, `positions()`, `quote()`, `submit(OrderIntent)`,
  `close(position_id)`, `events()`; implemented by `PaperBroker` and later `Mt5BridgeClient`.
- Only the Execution service holds a `Broker` object. No LLM agent can reach it (§8.4).

### 4.17 Simulation / backtesting (REPLACES upstream U27)
- Event-driven replay over historical candles: at each setup-timeframe close, run analysis →
  (LLM pipeline, recorded or live) → proposal → risk → paper broker.
- Two modes: **deterministic-only** (no LLM; setups taken by rule, to measure the deterministic
  layer) and **full** (LLM calls recorded for replay). Point-in-time: snapshots are built with
  `as_of` equal to the simulated clock.

### 4.18 Future MT5 bridge
- As in the layer design (§7 Phase 4 there): a Windows-hosted service; narrow API; demo guard;
  data and execution as separate components. Host not chosen (owner decision Q1).

### 4.19 Telemetry / event bus
- Event envelope and bus as in the layer design §4; minimum V1 event set in §10 here. Emitted
  from Phase 1 onward so that replay and metrics exist from the first run.

### 4.20 Agent identity registry
- A static roster: `agent_id`, display name, group, source (UPSTREAM / STELLAR), kind
  (deterministic / LLM), LLM tier, home room, V1 flag. The upstream node-name → `agent_id` map
  lives here and is covered by a contract test.

### 4.21 Per-agent metrics
- Operational metrics (calls, latency, tokens, errors, structured-output misses) from telemetry;
  as defined in the layer design §6.2.

### 4.22 Post-trade review and attribution
- **Post-Trade Review:** every closed trade gets a typed `TradeReview`: outcome, R multiple,
  MAE/MFE, exit reason, which setup, price-action and momentum features were present, which risk
  checks were closest to their limits, and the research coverage at decision time. V1 produces it
  deterministically; an LLM narrative mode (which may reuse upstream `Reflector`, U18) is deferred.
- **Attribution:** links each closed trade to its research items, assessments, proposal, ratings
  and risk checks. V1: records and basic per-agent agreement statistics; statistical attribution
  (layer design §6.3) after enough samples.

### 4.23 Workload / operational-health layer
- V1 minimum: per-provider error and rate-limit counters, token and cost budgets per day and per
  run, automatic pause of new runs when a budget or error threshold is exceeded. Wellbeing visuals
  come later (Phase 9).

### 4.24 Persistence: Stellar Journal
- Single-user local store (SQLite on the owner's Mac, V1) with tables for market snapshots (with
  content hash), research items and their validation results, research snapshots, assessments,
  reports, setups, proposals, risk decisions, order intents, executions, trades, trade reviews,
  settlements and events. Append-only for decision records; every record carries `config_hash`.

### 4.25 Replay
- **Deterministic stages** are recomputed from stored snapshots and must reproduce identical
  outputs (tested).
- **LLM stages** are replayed from **recorded outputs** (a cassette), never re-called, so a replay
  shows exactly what happened (L11).

### 4.26 Configuration system
- Typed, validated configuration (Pydantic models) loaded from a local file; secrets only from the
  environment. Sections: instruments, providers, timeframe profiles, LLM tiers and budgets, risk
  limits, execution mode, sessions, calendar, UI.
- Loaded once at start. Its hash is recorded on every run and record. Invalid or incomplete risk
  configuration → trading disabled (fail closed). Agents cannot change configuration.

### 4.27 Kill switch (circuit breaker)
- Deterministic states `ARMED` / `TRIPPED`. Tripped by risk rules, reconciliation mismatches, data
  failures, budget exhaustion or the owner. Owner-only reset (§8.3). Persisted, so a restart does
  not re-arm it.

### 4.28 Visual-station API
- Read-only in V1: `GET /snapshot`, `GET /events?since=seq`, `GET /runs/{id}`, WebSocket event
  stream; bound to `localhost` (owner decision Q8). No endpoint changes risk state or places orders.

### 4.29 Research pipeline

The research chain is part of the architecture from Phase 1 (schemas, registry entries, store,
events), even though only some roles run in the minimum executable V1 (§5.2). Research is
**never** collapsed into one agent.

```
Research Agents ─> Source Validation ─> Macro/Causal Analysis ─> Market-Specific Analysis ─┐
 (specialised      (source, freshness,   (Causal/Macro Analyst)    (one specialist per       │
  collectors)       duplicates, F/R/I)                               instrument)             │
                                                                                            v
             Technical Analysis (deterministic agents + Technical Analyst) ──────────> Debate (upstream)
                                                                                            v
      Trader (upstream) ─> Deterministic Risk ─> Execution ─> Post-Trade Review ─> Memory/Attribution
```

#### 4.29.1 Research roles (collectors)

Each role gathers items for **its own domain** from sources on an owner-approved allowlist and
emits typed `ResearchItem` records. Retrieval is deterministic code; extracting claims from text
may use a quick-tier LLM. No provider, feed or subscription is assumed here (§13.2 D-2 … D-6).

| Role | Domain | Source *types* (no provider assumed) | Most relevant instruments | Typical trigger |
|---|---|---|---|---|
| **Central Bank Research** | Policy decisions, statements, minutes, speeches (Fed, ECB, BoJ) | official central-bank publications | all four | scheduled meetings; publication of statements |
| **Economic Data Research** | Scheduled macro releases: actual vs prior (and consensus if a source provides it) | economic calendar | all four | calendar events after release |
| **Market News Research** | General market and financial news | news/headline source | all four | periodic |
| **Geopolitical Research** | Conflicts, sanctions, elections, official intervention statements | news/official statements | XAU/USD, USD/JPY (safe-haven and intervention), NAS100 (risk sentiment) | periodic; event-driven |
| **Rates/Bonds Research** | Government yields, curve shape, real yields, rate differentials | rates/bond data source | XAU/USD (real yields), USD/JPY (US–JP spread), EUR/USD (EU–US spread), NAS100 (discount rates) | on setup-timeframe close |
| **Corporate/Earnings Research** | Earnings and guidance of the largest index constituents | corporate/earnings source | NAS100 | earnings calendar |

`ResearchItem` fields: `item_id`, `role`, `source_id`, `source_ref`, `published_at`,
`retrieved_at`, `affected` (currencies / instruments), `excerpt`, `content_hash`, `claims`
[{`claim_id`, `statement`, `value`, `unit`, `period`}].

#### 4.29.2 Research validation

| Validator | Kind | Rule | Output |
|---|---|---|---|
| **Source Validator** | Deterministic | Source is on the owner allowlist with a trust tier; provenance fields present; source type matches the role | accept / reject + reason |
| **Freshness Checker** | Deterministic | `published_at` ≤ run `as_of` (no look-ahead) and within the role's freshness window for the profile | accept / stale / future |
| **Duplicate Detector** | Deterministic | Exact duplicates by content hash; near duplicates clustered; the earliest primary source is kept, others linked | canonical item + duplicates |
| **Fact vs Reaction vs Interpretation Classifier** | LLM (quick tier) + deterministic checks | Labels each claim **FACT** (a verifiable event, data release or official statement), **REACTION** (a market move or response to an event) or **INTERPRETATION** (opinion, forecast, analysis). A FACT carrying a number must match the structured calendar value when one exists; mismatch → rejected | per-claim label + confidence + check results |

Only **accepted** items with **classified** claims reach analysis. Everything, including
rejections, is journaled and emits events.

#### 4.29.3 Causal / Macro Analyst
- **Kind:** LLM (deep tier). **Input:** only validated research as of the run time, plus the
  calendar window. **Output:** typed `MacroAssessment`: drivers [{driver, affected asset,
  direction, strength, evidence claim ids, based on FACT or INTERPRETATION}], regime description,
  upcoming event risk, stated uncertainties, and `coverage` (which research roles contributed).
- Every driver must cite claim ids; uncited statements are flagged by the Contradiction Checker.

#### 4.29.4 Market-specific specialists
- **XAU/USD, EUR/USD, USD/JPY and NAS100 Specialists.** One identity per instrument,
  one shared implementation with per-instrument configuration (which drivers matter; §6).
- **Kind:** LLM (quick or deep tier, configurable). **Input:** `MacroAssessment`,
  instrument-specific research (for example NAS100 earnings), session context.
  **Output:** typed `MarketAssessment`: directional pressure on the instrument, event-risk
  windows, conditions that would invalidate a setup, `coverage`.
- Only the specialist for the instrument in focus runs in a given decision cycle.

#### 4.29.5 Research store, cadence and coverage
- Collectors and validators run on **their own schedules** and write to a Research Store. A
  decision cycle reads a **research snapshot**: the set of accepted items as of `as_of`, with its
  own id and hash, recorded for replay.
- **Coverage is explicit.** Every assessment lists which roles contributed and which were
  missing, so the debate and the owner can see when a decision was made with thin research.
- **Mapping to upstream state (U2):** `news_report` = rendered `MacroAssessment` + the focus
  instrument's `MarketAssessment`, including their coverage lines.

---

## 5. Stellar agent rosters

Three rosters, kept separate so that no one mistakes the architecture for what runs on every
decision:

- **§5.1 Architectural roster:** every role the architecture and its interfaces support from
  Phase 1 (schemas, registry entries, events), whether or not it runs yet.
- **§5.2 Minimum executable V1 roster:** the roles that must run for V1 to work end to end on
  paper.
- **§5.3 Deferred / optional roster:** roles defined in the architecture but not in the minimum
  V1, each with the condition for adding it.

"Deterministic" agents are code with an identity for telemetry and the station; they call no LLM.
"Cadence" says when a role runs: **cycle** = every decision cycle for the instrument in focus;
**entry** = on every entry-timeframe close while a Setup is armed; **scheduled** = on its own
schedule, independent of decision cycles; **event** = when its input event occurs.

### 5.1 Architectural roster

| # | Agent | Group | Purpose | Inputs → outputs | Kind | Source | Room | Cadence |
|---|---|---|---|---|---|---|---|---|
| R1 | Central Bank Research | Research | Policy decisions, statements, minutes, speeches | allowlisted publications → `ResearchItem` | Deterministic retrieval + LLM extraction | STELLAR | Macro & News Observatory | scheduled / event |
| R2 | Economic Data Research | Research | Scheduled releases: actual vs prior (vs consensus if available) | calendar → `ResearchItem` | Deterministic (+ optional LLM) | STELLAR | Observatory | event (after release) |
| R3 | Market News Research | Research | General market news | news source → `ResearchItem` | Deterministic retrieval + LLM extraction | STELLAR | Observatory | scheduled |
| R4 | Geopolitical Research | Research | Conflicts, sanctions, elections, intervention statements | news / official statements → `ResearchItem` | Deterministic retrieval + LLM extraction | STELLAR | Observatory | scheduled / event |
| R5 | Rates/Bonds Research | Research | Yields, curve, real yields, rate differentials | rates data → `ResearchItem` | Deterministic | STELLAR | Observatory | scheduled |
| R6 | Corporate/Earnings Research | Research | Earnings and guidance of the largest NAS100 constituents | earnings source → `ResearchItem` | Deterministic retrieval + LLM extraction | STELLAR | Observatory | event (earnings calendar) |
| V1 | Source Validator | Research validation | Allowlist, trust tier, provenance | `ResearchItem` → accept/reject | Deterministic | STELLAR | Data Core | scheduled (on new items) |
| V2 | Freshness Checker | Research validation | No look-ahead; freshness window | `ResearchItem` → accept/stale/future | Deterministic | STELLAR | Data Core | scheduled |
| V3 | Duplicate Detector | Research validation | Exact and near duplicates; keep primary source | items → canonical item + links | Deterministic | STELLAR | Data Core | scheduled |
| V4 | Fact vs Reaction vs Interpretation Classifier | Research validation | Label each claim FACT / REACTION / INTERPRETATION; numeric FACT cross-check | claims → labelled claims | LLM (quick) + deterministic checks | STELLAR | Data Core | scheduled |
| M1 | Causal / Macro Analyst | Macro analysis | Causal drivers from validated research | research snapshot + calendar → `MacroAssessment` | LLM (deep) | STELLAR | Observatory | cycle (reused while the research snapshot is unchanged) |
| S1–S4 | XAU/USD, EUR/USD, USD/JPY, NAS100 Specialists | Market-specific analysis | Translate macro into instrument-specific pressure and event risk | `MacroAssessment`, instrument research, session → `MarketAssessment` | LLM (configurable tier) | STELLAR | Market Analysis Wing, instrument desks | cycle (focus instrument only) |
| T1 | Data Validator | Technical | Build and validate `MarketSnapshot` | market data → snapshot / rejection | Deterministic | STELLAR | Data Core | cycle + entry |
| T2 | Market Session Agent | Technical | Session, overlaps, time to close, per-instrument calendars | clock, config → `SessionContext` | Deterministic | STELLAR (ARIA sessions) | Market Analysis Wing | cycle + entry |
| T3 | Market Structure Agent (includes higher-timeframe bias) | Technical | Trend state and key levels per timeframe | snapshot → `StructureAssessment` | Deterministic | STELLAR (ARIA MTF context, S/R) | Market Analysis Wing | cycle |
| T4 | Technical Indicator Agent (includes momentum) | Technical | Indicator features and `MomentumAssessment` | snapshot → features, momentum | Deterministic | STELLAR (ARIA EMA/RSI/MACD/ATR) | Market Analysis Wing | cycle + entry |
| T5 | Candle / Price Action Agent | Technical | Candle and price-action features tied to structure levels | snapshot, structure → `PriceActionAssessment` | Deterministic | STELLAR (ARIA candles, REDESIGNED) | Market Analysis Wing | cycle + entry |
| T6 | Pullback / Setup Agent | Technical | Detect and manage Setups | structure, momentum, price action, session → `Setup` | Deterministic | STELLAR (ARIA pullback, RESEARCH) | Market Analysis Wing | cycle |
| T7 | Entry Timing Agent | Technical | Deterministic entry trigger while a Setup is armed | setup, price action, momentum on entry timeframe → trigger event | Deterministic | STELLAR | Market Analysis Wing | entry |
| T8 | Technical Analyst | Technical | Write `market_report` from typed assessments; cite only snapshot values | assessments → `market_report` + cited values | LLM (quick) | STELLAR | Market Analysis Wing | cycle |
| U1–U2 | Bull Researcher, Bear Researcher | Debate | Argue for and against the setup | reports → debate state | LLM | UPSTREAM (U6) | Debate Chamber | cycle |
| U3 | Research Manager | Debate | Judge the debate | debate → `investment_plan` | LLM (deep) | UPSTREAM (U7) | Command Deck | cycle |
| U4 | Trader | Decision | Transaction view; levels advisory | plan, reports, portfolio → `trader_investment_plan` | LLM | UPSTREAM (U8), wrapped | Command Deck | cycle |
| U5–U7 | Aggressive, Conservative, Neutral Risk Debaters | Debate | Argue the plan's risk (advisory) | trader plan, reports → risk debate | LLM | UPSTREAM (U9) | Debate Chamber | cycle |
| U8 | Portfolio Manager | Decision | Typed rating = approval strength for the setup | risk debate, plan, lessons → `final_rating` | LLM (deep) | UPSTREAM (U10), wrapped | Command Deck | cycle |
| P1 | Trade Proposal Builder | Proposal | Setup + rating → typed `TradeProposal`; deterministic levels | setup, structure, rating → `TradeProposal` | Deterministic | STELLAR | Command Deck | cycle |
| P2 | Contradiction Checker | Validation | Conflicts between reports, assessments, advisory levels and snapshot | reports, assessments, proposal → contradictions | Deterministic | STELLAR | Risk Control Vault (intake) | cycle |
| P3 | Risk Auditor (the Risk Engine) | Risk | All hard rules (§8); sizing; breaker | proposal, account, quotes, calendar → `RiskDecision`, `OrderIntent` | Deterministic | STELLAR | Risk Control Vault | cycle + entry |
| P4 | Execution Checker | Execution validation | Pre-flight and reconciliation | intent, broker state → pass/fail | Deterministic | STELLAR | Execution Bay | entry / event |
| E1 | Paper Execution Agent | Execution | Submit to the Paper Broker; track fills and closes | intent → execution results | Deterministic | STELLAR | Execution Bay | event |
| E2 | MT5 Execution Agent | Execution | Submit to the MT5 bridge (demo only) | intent → execution results | Deterministic | STELLAR | Execution Bay | event |
| L1 | Post-Trade Reviewer | Review | Typed `TradeReview` per closed trade; optional LLM narrative | trade, journal → `TradeReview` | Deterministic (LLM narrative mode optional) | STELLAR (may reuse UPSTREAM U18) | Memory Archive | event (trade closed) |
| L2 | Performance / Attribution Agent | Review | Settlement, metrics, attribution | trades, reviews, journal → metrics | Deterministic | STELLAR | Memory Archive | event / scheduled |
| O1 | Supervisor | Operational | Scheduling, run lifecycle, pause | clock, config, breaker, budgets → run events | Deterministic | STELLAR | Command Deck | continuous |
| O2 | Operational Wellbeing Monitor | Operational | Errors, rate limits, budgets; pause requests | telemetry → health events | Deterministic | STELLAR | Wellbeing Room | continuous |

**Design decision: the LLM decision chain runs only when there is a Setup to judge.** Research
roles run on their own schedules; T1–T6 run every cycle; M1, S*, T8 and U1–U8 run only when the
Pullback / Setup Agent has produced a candidate Setup (setup-first framing, §4.13). This keeps
LLM cost proportional to opportunities, not to clock ticks.

### 5.2 Minimum executable V1 roster

> **Station room names** in the roster tables below (for example "Risk Control Vault") refer to the earlier stacked-deck concept. The approved visual topology is `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` revision C and the Visual Foundation v2 registries; for example, P2 / P3 work in the Risk Control Room (L10). The roster itself is unchanged.

Everything needed to run the full chain end to end on **paper**:

| Group | Agents in minimum V1 |
|---|---|
| Research | **R1 Central Bank Research**, **R2 Economic Data Research** (both may run from owner-supplied local files until sources are chosen, §13.2 D-2, D-4) |
| Research validation | **V1 Source Validator**, **V2 Freshness Checker**, **V3 Duplicate Detector**, **V4 Fact/Reaction/Interpretation Classifier** |
| Macro analysis | **M1 Causal / Macro Analyst** |
| Market-specific analysis | **S1–S4** (one per instrument; only the focus instrument's specialist runs in a cycle) |
| Technical | **T1–T8**, including **T5 Candle / Price Action** and **T7 Entry Timing** |
| Debate and decision | **U1–U8** (upstream, reused unchanged) |
| Proposal, validation, risk | **P1–P4** |
| Execution | **E1 Paper Execution Agent** |
| Review | **L1 Post-Trade Reviewer** (deterministic mode), **L2 Performance / Attribution** (basic metrics) |
| Operational | **O1 Supervisor**, **O2 Operational Wellbeing Monitor** (minimal) |

Research coverage in minimum V1 is intentionally partial. Every `MacroAssessment` and
`MarketAssessment` states the missing roles in its `coverage` field, and the debate sees it.

**MT5 Execution Agent (E2)** is not part of V1. It joins at Phase 8, the separate MT5 / Vantage demo
integration gate that follows a stable paper V1 (D-15, approved).

### 5.3 Deferred / optional roster

| Agent | Status | Why not in minimum V1 | Condition to add |
|---|---|---|---|
| R3 Market News Research | Deferred | No news source chosen (D-3) | Source approved and allowlisted |
| R4 Geopolitical Research | Deferred | Same source dependency (D-3) | Source approved |
| R5 Rates/Bonds Research | Deferred (first candidate to add) | No rates data source chosen (D-5); highly relevant to XAU/USD and USD/JPY | Source approved |
| R6 Corporate/Earnings Research | Deferred | No earnings source chosen (D-6); relevant to NAS100 only | Source approved; NAS100 specialist then fills `fundamentals_report` |
| L1 Post-Trade Reviewer, LLM narrative mode | Deferred | Needs a body of closed trades | ≥ owner-set number of reviewed trades |
| L2 statistical attribution | Deferred | Needs sample sizes (layer design §6.3) | Minimum samples reached |
| E2 MT5 Execution Agent | Phase 8 | Windows host not chosen (owner decision Q1) | Phase 7 exit; host chosen |
| Upstream News Analyst / Sentiment Analyst | Optional, evaluate after V1 | Stock-oriented sources (Yahoo ticker news, StockTwits, Reddit) of unknown relevance here | Evaluation shows value, as additional research inputs through validation |
| Upstream Fundamentals Analyst | Not used | L3 | — |
| Crypto Analyst (layer design) | Out of scope | Crypto is not in the first markets | New market decision |
| Station personas: Station Medic, Quartermaster, Café Host; Vault sub-personas (Signal Validator, Risk Officer, Exposure Controller, Circuit Breaker) | Phase 10 visuals only | They are visual personas of O2 and P3 functions, not separate decision-makers (§13.1 R-4) | Station V1/V2 work |

**Merged:** Long-Term Bias Agent → T3 Market Structure Agent (same method on higher timeframes).
**Superseded:** layer design FX Session Analyst → T2 Market Session Agent; the single
"News / Macro Agent" of v0.1 of this plan → the R/V/M/S research chain.

---

## 6. First four markets

Market descriptions below are general market knowledge used for design, **not** broker
specifications. All execution values come from the broker at runtime.

| Aspect | XAU/USD | EUR/USD | USD/JPY | NAS100 |
|---|---|---|---|---|
| **Asset class** | Spot precious metal quoted in USD (OTC) | Spot FX major | Spot FX major | CFD on the Nasdaq-100 index |
| **Data requirements** | Spot bid/ask quotes; OHLC on all profile timeframes; history deep enough for the slowest indicator warm-up on the context timeframe | Same | Same | Same, plus awareness that CFD prices track the index future outside cash hours |
| **Symbol mapping concerns** | Upstream maps `XAUUSD` → `GC=F` (a future, L2): analysis-only proxy at best. Broker symbols may carry suffixes. Must map to a **spot** source for levels | `EURUSD=X` on Yahoo is daily-oriented in upstream; broker suffixes | Same as EUR/USD | Upstream maps `NAS100` → `^NDX` (cash index, no overnight prices). Broker names vary (e.g. NAS100, US100, USTEC). Analysis and execution prices must come from the same kind of series |
| **Session behaviour** | Trades nearly around the clock on weekdays; liquidity and volatility typically rise in London and the London/New York overlap; quieter in late New York and Asia | Most liquid in London and the London/New York overlap | Tokyo session relevant in addition to London/New York | Liquidity concentrated in the US cash session; opening gaps and extended-hours CFD trading with thinner liquidity |
| **Relevant macro / news** | USD strength, US real yields, Fed policy, US CPI and payrolls, geopolitical risk, central-bank gold demand | ECB and Fed policy, rate differentials, euro-area and US data releases | BoJ and Fed policy, US yields, risk of official intervention, carry flows | Fed policy, US CPI and payrolls, US Treasury yields, earnings of the largest index constituents, broad risk sentiment |
| **Research roles most relevant (§4.29)** | Central Bank (Fed), Economic Data (US), Rates/Bonds (real yields), Geopolitical | Central Bank (ECB, Fed), Economic Data (euro area, US), Rates/Bonds (EU–US spread) | Central Bank (BoJ, Fed), Economic Data (Japan, US), Rates/Bonds (US–JP spread), Geopolitical (incl. intervention statements) | Central Bank (Fed), Economic Data (US), Corporate/Earnings, Rates/Bonds |
| **Technical-analysis applicability** | Widely traded technically; high volatility makes ATR-scaled rules important | Widely traded technically; tight spreads in liquid sessions | As EUR/USD; sensitive to event-driven jumps | Applicable; gaps and session boundaries need explicit handling in indicators and stops |
| **Upstream analysis that does NOT apply** | Fundamentals, SEC, insider, company identity, StockTwits/Reddit stock sentiment, SPY-alpha settlement | Same | Same | Company fundamentals of a single issuer, SEC filings, insider data; SPY alpha partly overlapping but not the right benchmark |
| **Execution metadata needed from broker/MT5 (fields only, no values assumed)** | contract size, digits / point size, tick size and tick value, minimum volume, volume step, maximum volume, stops level (minimum stop distance), freeze level, trading sessions and trading-halt periods, margin requirements, swap long/short, commission, current spread, filling modes, account currency conversion | same list | same list | same list plus trading hours for the cash-session and extended-session periods, and any dividend or rollover adjustments the broker applies |

---

## 7. Trading horizons

**No V1 timeframe profile is chosen in this plan.** Profiles are configuration. Which profile(s)
are used for paper and demo validation is an open decision (§13.2 D-7), informed by measurement
in Phases 6–7.

### 7.1 Timeframe profile (configurable)

A **profile** describes one way of trading an instrument as an ordered chain of **levels**. Each
level has a role and one or more timeframes; roles may share a timeframe.

| Field | Meaning |
|---|---|
| `name` | Profile identifier |
| `levels.context` | One or more higher timeframes that set bias (Market Structure Agent) |
| `levels.setup` | Medium-term timeframe where Setups are detected and where the LLM chain runs (on candle close, only when a Setup exists) |
| `levels.pullback` | Shorter timeframe where the pullback is tracked (Pullback / Setup, Candle / Price Action, momentum) |
| `levels.entry` | Fastest timeframe where the Entry Timing Agent triggers entries while a Setup is armed |
| `analysis_cadence` | When the LLM chain may run (default: `setup` close, subject to budget and a Setup existing) |
| `setup_validity` | How many `entry`-level bars a Setup / Proposal stays valid |
| `max_holding` | Time-based exit limit |
| `session_filter` | Allowed sessions for new entries (optional) |
| `instruments` | Which instruments use this profile |

### 7.2 The hierarchy (the first strategy family)

```
context   (e.g. D1 / H4)   → higher-timeframe bias              Market Structure Agent      deterministic
setup     (e.g. H1 / M15)  → medium-term setup in bias direction Pullback / Setup Agent      deterministic
                           → judgement of the setup              research chain + debate + PM LLM, slow
pullback  (e.g. M15 / M5)  → short-term pullback; candle /       Candle / Price Action,      deterministic
                             price action; momentum confirmation Technical Indicator Agents
entry     (e.g. M5 / M1)   → precise entry timing                Entry Timing Agent          deterministic, fast
                           → hard gate with a fresh quote        Risk Engine                 deterministic
```

**Principle: "slow judgement, fast reflex."** The LLM chain runs at most at the `setup` cadence,
because it is slow and costly; everything faster is deterministic and acts only inside the
validity window of an approved Setup.

### 7.3 Candidate profiles (all unvalidated)

| Profile | Context | Setup | Pullback | Entry | Origin | Status |
|---|---|---|---|---|---|---|
| **Owner hypothesis** | D1 / H4 | H1 / M15 | M15 / M5 | M5 / M1 | Owner's stated strategy interest | **Strategy hypothesis to test**, not a validated trading rule |
| ARIA swing | D1 (+ W1) | H4 | H1 | H1 | ARIA mode H4/Daily | Candidate |
| ARIA day trade | H4 | H1 | M15 | M15 | ARIA mode M15/H1 | Candidate |
| ARIA scalp | H1 | M15 | M5 | M5 | ARIA mode M5/M15 | Candidate for the deterministic levels only; LLM at M15 cadence likely infeasible |

Feasibility notes for the owner hypothesis (to be measured, not assumed):
- **M1 / M5 entry** needs intraday data at that granularity for simulation and live paper
  (D-1); it runs deterministically, so its LLM cost is zero.
- **H1 / M15 setup cadence** bounds how often the LLM chain can run; per-cycle latency and cost
  are measured in Phase 6 and must fit inside one setup bar with margin.
- Session behaviour (§6) matters more at M1–M15 than at D1; session filters are per profile.

### 7.4 Supporting other strategies later

A **strategy** = a profile + a setup detector + a pullback/price-action rule set + an entry
trigger + a proposal level policy (how stops and targets are derived). Each is a pluggable,
deterministic component behind a fixed interface, and every strategy produces the same `Setup`
and `TradeProposal` types. The research chain, Risk Engine, execution, journal, telemetry and UI
are strategy-agnostic, so adding a strategy changes none of them.

---

## 8. Hard risk foundation

### 8.1 Controls

No numeric values are chosen here (owner decision Q5). "Missing input" means the data needed to
evaluate the rule is absent or stale; the behaviour column says what happens then.

| Control | Stage | Config key (illustrative) | Needs | Missing input → |
|---|---|---|---|---|
| Malformed proposal / order rejection | proposal, pre-order | schema validation (no key) | typed objects | reject |
| Required stop-loss (present, correct side, minimum distance ≥ broker stops level) | proposal | `risk.require_stop_loss` (always true), broker stops level | proposal, metadata | reject |
| Minimum reward:risk | proposal | `risk.min_reward_risk` | proposal | reject |
| Max risk per trade | sizing | `risk.max_risk_per_trade_pct` | equity, stop distance, tick value | reject |
| Max position size | sizing | `risk.max_position_volume` per instrument | metadata | reject |
| Max open positions | pre-order | `risk.max_open_positions` | positions | reject |
| Correlated exposure (clusters such as USD-leg exposure across XAU/USD, EUR/USD, USD/JPY) | pre-order | `risk.clusters`, `risk.max_cluster_risk_pct` | positions, cluster config | reject |
| Max daily loss | station | `risk.max_daily_loss_pct` | equity history | trip breaker |
| Max drawdown | station | `risk.max_drawdown_pct` | equity peak | trip breaker |
| Max spread | pre-order | `risk.instruments.<id>.max_spread` | fresh quote | reject |
| Stale quote rejection | pre-order | `risk.max_quote_age_s` | quote timestamp | reject |
| Slippage tolerance | order / post-fill | `risk.instruments.<id>.max_slippage` | fill price | reject order (max deviation); breach after fill → event + breaker count |
| Duplicate order prevention | pre-order | idempotency key = hash(proposal_id); `risk.duplicate_window` | journal | reject |
| Cooldowns (after a loss, after a close, per instrument) | proposal | `risk.cooldowns.*` | journal | reject |
| News / event restriction (no new entries within a window around configured high-impact events) | proposal, pre-order | `risk.news_blackout.*` | calendar | reject (calendar unavailable = unknown = reject, configurable only to stricter) |
| Proposal expiry / stale plan | pre-order | `valid_until`, `risk.max_price_drift_atr` | quote, ATR | reject |
| Circuit breaker | station | the rules marked "trip breaker" + reconciliation mismatch + data failure + budget exhaustion + manual | all | stays tripped |
| DEMO_ONLY mode | every order | `execution.mode` ∈ {`PAPER`, `DEMO`}; `LIVE` does not exist in V1 | account info | refuse |

### 8.2 Evaluation rules
1. **Fail closed.** Any exception, missing value or unknown state → reject.
2. **Order of evaluation** is fixed and recorded: schema → proposal rules → sizing → portfolio
   rules → pre-flight. Every check is recorded with value and limit, pass or fail.
3. **Limits are immutable at runtime.** Risk configuration is loaded at start; a change needs a
   restart and is recorded by config hash.
4. **REVIEW or unparseable rating → no proposal.** Hold → no proposal.

### 8.3 Circuit breaker reset (owner decision Q6)
- Any rule or agent can **trip** it. No agent, scheduler, retry, API call or UI element can
  **reset** it.
- V1 reset: a local, owner-run command on the Mac that requires typed confirmation, records the
  owner's reason, and emits `circuit_breaker.reset`. The station UI shows state only.

### 8.4 "No LLM may bypass these rules" — enforced structurally
- LLM agents receive state and return text or typed ratings. They hold **no reference** to the
  Risk Engine, the Broker, the Journal writer or configuration.
- An `OrderIntent` can only be constructed by the Risk Engine from an APPROVED `RiskDecision`
  (constructor restricted by module boundary; verified by tests).
- The Execution service accepts only `OrderIntent` objects whose `decision_id` exists as APPROVED
  in the Journal.
- Import-boundary tests (pattern from upstream `tests/test_layering.py`, U30) fail if any agent
  module imports `stellar.execution` or `stellar.risk` internals.

---

## 9. Data → decision → execution contract

### 9.1 Canonical pipeline

The chain follows the owner's research pipeline. Market data feeds it in parallel as a validated
snapshot.

| # | Stage | Producer | Artifact | Typed? | Validated by |
|---|---|---|---|---|---|
| 0 | Raw market data → validated snapshot | `MarketDataSource` → Data Validator | candles, quotes → `MarketSnapshot` (id, as_of, candles per timeframe with hashes, quote, session, quality flags) | **Typed** | Data Validator |
| 1 | Research | Research roles R1–R6 | `ResearchItem` (claims with source, times, hash) | **Typed** (excerpt text inside) | stage 2 |
| 2 | Source validation | V1–V4 | accepted / rejected items; per-claim FACT / REACTION / INTERPRETATION labels → research snapshot (id, as_of, hash) | **Typed** | V1–V4 rules |
| 3 | Macro / causal analysis | M1 Causal / Macro Analyst | `MacroAssessment` (drivers with cited claim ids, coverage) + narrative | **Typed** + text | Contradiction Checker (uncited claims) |
| 4 | Market-specific analysis | S1–S4 | `MarketAssessment` (pressure, event-risk windows, invalidation conditions, coverage) + narrative | **Typed** + text | Contradiction Checker |
| 5 | Technical analysis | T2–T7 (deterministic), T8 Technical Analyst | `StructureAssessment`, `MomentumAssessment`, `PriceActionAssessment`, `SessionContext`, `Setup`; `market_report` + cited values | **Typed**; report is text + typed sidecar | unit-tested functions; Contradiction Checker |
| 6 | Debate | Upstream Bull/Bear, Research Manager, risk debaters | debate histories, `investment_plan` | Text (free text allowed) | not trusted for execution |
| 7 | Trader | Upstream Trader (wrapped) | `trader_investment_plan`; parsed advisory levels | Text + parsed advisory values | Contradiction Checker |
| 7a | Final judgement | Upstream Portfolio Manager (wrapped) | `final_rating` | **Typed enum** (5-tier or REVIEW) | wrapper (U10) |
| 7b | Structured trade proposal | P1 Trade Proposal Builder | `TradeProposal` | **Typed** | schema + P2 Contradiction Checker |
| 8 | Deterministic risk | P3 Risk Engine | `RiskDecision` (checks, sizing); `OrderIntent` if approved | **Typed** | Risk Engine |
| 9 | Execution | T7 trigger → P4 Execution Checker → E1 Paper (E2 MT5 later) | `ExecutionResult`, fills, `TradeRecord` | **Typed** | reconciliation |
| 10 | Post-trade review | L1 Post-Trade Reviewer | `TradeReview` | **Typed** (optional narrative later) | review tests |
| 11 | Memory / attribution | L2 Performance / Attribution (+ optional upstream memory log, U16) | journal rows, settlements, metrics, optional `past_context` | **Typed** (journal) | — |

**Rule:** free text is allowed only in narratives (stages 3–5) and the debate and Trader (stages
6–7), where humans and LLMs read it. Every boundary that feeds a later decision or an order
(stages 0–2, the typed parts of 3–5, and 7a onward) is typed. Free text never crosses into stage
7b or later except as an attached, hashed reference for the journal.

### 9.2 Identity chain
`research_item_id → research_snapshot_id ┐`
`snapshot_id → setup_id ─────────────────┴→ run_id → proposal_id → decision_id → intent_id →
order_id → fill_id → trade_id → review_id → settlement_id`. Every record stores its parent ids,
so any trade is traceable to the exact market data, research and reports behind it.

---

## 10. Telemetry and visual-station foundation

### 10.1 Minimum V1 event set

Envelope as in the layer design §4.2 (`event_id`, `schema_version`, `type`, `ts`, `seq`,
`run_id`, `agent_id`, `room`, `instrument`, `correlation_id`, `payload`).

| Event | Emitted by | Key payload |
|---|---|---|
| `agent.task.started` | any agent wrapper | task kind, inputs' ids |
| `agent.task.completed` | any agent wrapper | outputs' ids, duration, tokens (LLM) |
| `agent.state.changed` | station state tracker | from, to, reason |
| `market.focus.changed` | Supervisor | instrument, profile, reason |
| `snapshot.created` / `snapshot.rejected` | Data Validator | snapshot id, quality flags / reason |
| `research.item.collected` | research roles R1–R6 | item id, role, source id, published_at |
| `research.item.accepted` / `research.item.rejected` | validators V1–V4 | item id, validator, reason, claim labels |
| `research.snapshot.created` | research store | research snapshot id, item count, coverage |
| `analysis.created` | M1, S1–S4, T2–T8 | analysis id, kind (macro, market, structure, momentum, price action, session, report), coverage |
| `setup.state.changed` | Pullback / Setup Agent | setup id, from, to, rule |
| `debate.started` / `debate.completed` | Stellar graph observer | debate kind, rounds, verdict |
| `trade.proposed` | Trade Proposal Builder | proposal id, direction, levels, contradictions |
| `risk.approved` / `risk.rejected` | Risk Engine | decision id, checks, volume or reasons |
| `order.created` / `order.sent` / `order.filled` / `order.rejected` | Execution | intent/order ids, prices, slippage |
| `trade.closed` | Execution / Attribution | trade id, P&L, R multiple, exit reason |
| `agent.resting` / `agent.overloaded` | Operational Wellbeing Monitor | agent/provider, cause, cooldown |
| `system.paused` / `system.resumed` | Supervisor | reason |
| `budget.warning` | Operational Wellbeing Monitor | scope, used, budget |
| `circuit_breaker.tripped` / `circuit_breaker.reset` | Risk Engine / owner command | rule / owner reason |

### 10.2 Rules
- The visual layer **consumes** events and snapshots. It **never** controls risk, never places or
  cancels orders, and never resets the breaker (V1 UI is read-only).
- Telemetry failure never blocks a run; **journal** failure for decision/order records halts
  execution (layer design §4.5).
- Event names here are the canonical V1 names; the layer design's catalogue is reconciled to them
  later (§13.1 R-3).

---

## 11. Implementation roadmap

Phase numbering here is the canonical implementation numbering proposed in §13.1 R-2.

### 11.1 Changes from the owner's suggested order, and why

| Change | Reason (repository evidence or owner requirement) |
|---|---|
| Telemetry **core** (event envelope, bus, journal store) moves into Phase 1 | Replay and the journal need events from the first run; retrofitting ids and events later is costlier. Attribution/metrics stay later |
| **Research-chain interfaces in Phase 1** (schemas, registry entries, research store) | Owner requirement: the architecture supports the full research chain from the beginning, even where roles are deferred |
| **Risk Engine and Paper Broker before any LLM or research agent** (Phases 3–4) | Upstream has no execution or hard risk (L5, L6). The gate must exist and be tested before anything can produce a proposal |
| **Candle / Price Action, momentum and entry timing in Phase 5**, before simulation and demo | Owner requirement: the first strategy family needs them; strategy validation (Phases 7–8) is meaningless without them |
| New phase: **research pipeline + LLM integration** (Phase 6) | The suggested list had no step for building the research chain and the Stellar graph that reuses upstream agents; that integration carries most upstream-drift risk (L13) |
| Simulation/backtesting combined with attribution (Phase 7) | Simulation needs the full pipeline and produces the data attribution needs |

### 11.2 Phases

Each phase lists: **Objective · Files/modules · Entry · Exit · Tests · Must NOT start.**
File paths are proposals under `stellar/src/stellar/` unless stated.

**Phase 0 — Foundation documentation** *(this document)*
- Objective: approved foundation plan; §13.1 reconciliations approved (done: D-16); §13.2
  decisions answered or given owners and deadlines.
- Files: `docs/STELLAR_FOUNDATION_PLAN.md`.
- Entry: approved layer design. Exit: owner approval of this plan.
- Tests: none. Must NOT start: any code, dependency or scaffolding.

**Phase 1 — Stellar package, contracts, config, telemetry core**
- Objective: installable `stellar` project beside upstream; all typed schemas of §9 (market,
  research, assessments, proposal, risk, order, execution, review); config system; event
  envelope, bus and SQLite journal; agent registry containing the **whole architectural roster**
  (§5.1) with status flags; upstream contract tests; breaker state object (no trading yet).
- Files: `stellar/pyproject.toml`, `config/`, `schemas/`, `telemetry/`, `journal/`,
  `agents/registry.py`, `risk/breaker.py`, `stellar/tests/contract/`,
  `.github/workflows/stellar.yml`.
- Entry: Phase 0 approved. Exit: `pip install -e ./stellar` works on the Mac; upstream test suite
  passes untouched; contract tests pin U1, U2, U4–U12, U15, U16, U22, U29.
- Tests: schema round-trip; config validation (missing risk config → trading disabled); event
  ordering; journal append-only; contract tests; import-boundary tests.
- Must NOT start: data providers, LLM calls, research collectors, broker code.

**Phase 2 — Market data and the first four instruments**
- Objective: `MarketDataSource`, file importer, symbol map, timeframes, candle validation,
  `MarketSnapshot`, Data Validator (T1), Market Session Agent (T2) with per-instrument calendars.
- Files: `marketdata/`, `sessions/`, `stellar/tests/fixtures/`.
- Entry: Phase 1 exit; owner-supplied data files **or** D-1 answered.
- Exit: snapshots for all four instruments on the timeframes of every candidate profile (§7.3),
  reproducible from fixtures; as-of guarantee tested.
- Tests: no-look-ahead; gap/duplicate detection; DST session boundaries; proxy-flag enforcement.
- Must NOT start: analysis agents, risk, broker, research.

**Phase 3 — Deterministic Risk Engine**
- Objective: every control in §8 against **synthetic** proposals; sizing; breaker; owner reset
  command; DEMO_ONLY mode; news restriction against a **fixture** calendar.
- Files: `risk/`, `cli/owner.py` (owner reset command).
- Entry: Phase 2 exit. Exit: 100% rule coverage; fault-injection suite yields zero approvals on
  bad input. Test-only limit values are labelled as such and never used as defaults.
- Tests: table tests per rule; property tests (no path to an intent without APPROVED); breaker
  persistence across restart; reset refused from every non-owner path.
- Must NOT start: LLM or research agents, MT5.

**Phase 4 — Paper Broker and execution abstraction**
- Objective: `Broker` interface, `PaperBroker`, Execution Checker (P4), Paper Execution Agent
  (E1), settlement into `TradeRecord`, deterministic Post-Trade Reviewer (L1).
- Files: `execution/broker.py`, `execution/paper.py`, `execution/checker.py`, `settlement/`,
  `review/`.
- Entry: Phase 3 exit; D-8 answered. Exit: synthetic proposals flow proposal → risk → intent →
  paper fill → close → review → settlement, fully journaled and replayable.
- Tests: fill/stop/target rules including same-candle ambiguity; idempotency; reconciliation.
- Must NOT start: MT5 bridge, LLM or research agents.

**Phase 5 — Deterministic technical foundation (first strategy family)**
- Objective: T3 Market Structure (with higher-timeframe bias), T4 Technical Indicator (with
  momentum), **T5 Candle / Price Action**, T6 Pullback / Setup, **T7 Entry Timing**; Setup
  lifecycle; P1 Trade Proposal Builder in **deterministic-only mode** (setups taken by rule, no
  LLM); configurable profiles (§7).
- Files: `analysis/structure/`, `analysis/indicators/`, `analysis/price_action/`, `setups/`,
  `entry/`, `proposals/builder.py`, `profiles/`.
- Entry: Phase 4 exit.
- Exit: the chain bias → pullback → candle/price action → momentum → entry runs end to end on
  paper over historical data for each candidate profile the data supports; every feature is
  reproducible; ARIA-inspired RESEARCH features are present but **off by default**.
- Tests: hand-computed indicator fixtures; candle and price-action definitions on constructed
  candles; setup state machine; entry-trigger tests on multi-timeframe fixtures.
- Must NOT start: LLM or research agents, MT5.

**Phase 6 — Research pipeline and LLM integration**
- **6a Research chain:** R1 Central Bank and R2 Economic Data Research, V1–V4 validators,
  research store and research snapshots, M1 Causal / Macro Analyst, S1–S4 specialists. Sources
  may be owner-supplied local files.
- **6b Decision chain:** T8 Technical Analyst; Stellar graph reusing upstream U1–U8 (§1.3);
  setup-first framing; full P2 Contradiction Checker; LLM tiers and budgets; recorded LLM outputs
  for replay; latency and cost measured **per candidate profile**.
- Files: `research/collectors/`, `research/validation/`, `research/store.py`, `analysis/macro/`,
  `analysis/markets/`, `analysis/technical_report.py`, `pipeline/`, `llm/tiers.py`,
  `telemetry/langchain_handler.py`.
- Entry: Phase 5 exit; D-11, D-13 answered; D-2 and D-4 answered **or** owner-supplied files in
  place.
- Exit: full chain on paper; zero proposals built from free text; every assessment carries
  coverage; measured latency/cost report per profile.
- Tests: validator rules (allowlist, freshness/no look-ahead, duplicates, numeric FACT
  cross-check); fake-LLM tests for M1, S*, T8; contract tests on reused upstream agents; Trader
  layout parser; REVIEW/Hold → no proposal; replay from recorded outputs is identical.
- Must NOT start: MT5, visual station, deferred research roles without an approved source.

**Phase 7 — Simulation, backtesting and attribution**
- Objective: event-driven simulator (§4.17) in deterministic-only and recorded-LLM modes; metrics
  and basic attribution; comparison of candidate profiles (input to D-7); evidence for risk
  threshold values (input to D-12).
- Files: `simulation/`, `metrics/`.
- Entry: Phase 6 exit. Exit: reproducible simulation reports with sample sizes; profile and
  threshold proposals with evidence, approved by the owner; all §12 criteria met. **This exit is
  Stellar Agents V1 (paper)** (D-15).
- Tests: point-in-time integrity (market data and research); identical results on re-run.
- Must NOT start: MT5 live connection; any statement of profitability.

**Phase 8 — MT5 / Vantage demo integration gate (after V1)**
- Scope (D-15, approved): a separate integration and validation gate. It starts only after the
  paper V1 foundation is complete and stable, and passing it is not part of the V1 definition.
- Objective: bridge service, MT5 data source, E2 MT5 Execution Agent, demo guard, reconciliation.
- Files: `mt5_bridge/` (repository root), `execution/mt5_client.py`,
  `marketdata/providers/mt5.py`.
- Entry: V1 complete (Phase 7 exit, §12) and stable on paper; D-17 (Windows host) answered. Exit: layer design Phase 4 gate (≥ 2 weeks of
  clean demo reconciliation, zero demo-guard bypasses).
- Tests: demo-guard refusal; bridge contract tests with a fake bridge; reconciliation.
- Must NOT start: any LIVE mode.

**Phase 9 — Visual station V1**
- Objective: read-only localhost UI per layer design §5 and its Phase 5; art direction per owner
  decision Q7.
- Files: `stellar_ui/` (repository root), `api/`.
- Entry: Phase 6 exit at minimum (events exist); may run in parallel with Phases 7–8.
- Exit: layer design Phase 5 gate. Tests: UI consumes recorded event streams; no write endpoints.
- Must NOT start: movement/life animation.

**Phase 10 — Animated station, movement, lounge, wellbeing**
- Objective: layer design Phase 6, including station personas (§5.3). Entry: Phase 9 exit.
- Exit: layer design Phase 6 gate. Tests: deterministic idle behaviour on replay; UI disabled →
  trading unchanged.
- Must NOT start: anything that lets the UI influence trading.

**Phase 11 — Long-duration demo validation**
- Objective: extended demo operation to observe stability, risk-rule behaviour, research
  coverage and costs.
- Entry: Phase 8 exit; D-18 answered. Exit: owner review of the validation report.
  Profitability is reported, never assumed, and is not an exit criterion.
- Must NOT start: live-money trading. That would require a separate, explicit owner decision and a
  new design review.

---

## 12. V1 definition of done

**V1 does not mean profitable.** V1 means the system is complete, safe, observable and
reproducible **on paper**. V1 is reached at the Phase 7 exit.

**Scope (D-15, approved 2026-09-29):** Stellar Agents V1 is functionally complete with paper
trading. The MT5 / Vantage demo is a separate integration and validation gate (Phase 8) after the
paper V1 foundation is stable. Neither V1 nor passing the demo gate implies profitability.

Stellar Agents V1 is done when **all** of the following hold:

1. **Four markets:** XAU/USD, EUR/USD, USD/JPY and NAS100 produce validated snapshots on the
   timeframes of every configured profile under evaluation.
2. **Research chain:** the minimum V1 research roles (§5.2) run; every research item passes or
   fails validation with a recorded reason; every assessment carries its coverage.
3. **Technical chain:** bias → pullback → candle/price action → momentum → entry timing runs
   deterministically for each configured profile.
4. **Typed decision boundary:** every proposal, risk decision, order intent, execution, review
   and settlement is a typed record; no order ever originates from free text.
5. **Deterministic risk:** every §8 control is implemented, configured and covered by tests;
   fault injection yields zero approvals on bad input.
6. **Execution:** paper execution end to end through the same `Broker` interface the MT5 client
   will later implement. MT5 demo is **not** a V1 criterion (D-15); it is the Phase 8 gate.
7. **No accidental live trading:** `LIVE` mode does not exist; the demo guard refuses non-demo
   accounts in tests (and in the bridge, once built).
8. **Circuit breaker:** trips on its rules; persists across restarts; only the owner command
   resets it.
9. **Persistent journal:** every record traceable through the §9.2 id chain.
10. **Telemetry:** the §10.1 event set is emitted, ordered and stored.
11. **Reproducible replay:** deterministic stages recompute identically; LLM stages replay from
    recorded outputs; research and market snapshots are replayed as recorded.
12. **Architecture complete for deferred roles:** every §5.1 role has its schema, registry entry
    and a fixture-based interface test, even if it does not run in V1.
13. **Tests:** upstream's suite passes unchanged; Stellar unit, contract, boundary,
    fault-injection and replay tests pass in CI.
14. **Clean separation:** zero modified files under `tradingagents/`, `cli/`, `tests/` and
    upstream root files, verified by a CI check against the upstream baseline.

The visual station (Phases 9–10) is a separate milestone, "Station V1", and is not required for
Stellar Agents V1.

---

## 13. Reconciliation with the layer design, and open decisions

### 13.1 Reconciliation with `docs/STELLAR_LAYER_DESIGN.md`

Neither document silently overrides the other. Each row states both versions and the canonical
version. **The owner approved all recommendations in this table as the canonical foundation
decisions on 2026-09-29 (D-16).** `docs/STELLAR_LAYER_DESIGN.md` was then updated in a dedicated
documentation-only reconciliation task (layer design v0.4, 2026-09-30, its §8.3) so that both
documents agree. If a conflict is found later, this table is canonical.

| # | Topic | Layer design (approved v0.3) | Foundation plan proposal | Canonical version (approved, D-16) | Why |
|---|---|---|---|---|---|
| R-1 | **Rating → action mapping** | §7 Phase 3 table: on a flat book, Buy → open long ×1.0, Overweight → long ×0.5, Hold → no order, Underweight → open short ×0.5 (FX) / no order (long-only markets), Sell → open short ×1.0 (FX) / no order (long-only markets), REVIEW → no order | Setup-first framing (§4.13): deterministic code proposes a directional Setup; the PM's rating is the approval strength for **that** setup. Buy / Overweight → take (size factors, D-9); Hold / Underweight / Sell → do not take; REVIEW → no trade, owner flag | **Foundation plan (setup-first)** | Verified upstream semantics: the rating prompts define Sell as "exiting or avoiding the position" (L8), so treating Sell as "open a short" reads a meaning the model was never asked for. Setup-first gives one unambiguous direction per decision, keeps direction deterministic and testable, and runs the LLM chain only when there is something to judge (§5.1) |
| R-2 | **Phase numbering** | Phases 1–6: design; telemetry; risk hardening; MT5 demo; station V1; station V2 | Phases 0–11 (§11) | **Foundation plan numbering for implementation.** The layer design's phases become named themes, mapped: LD-1 → FP-0; LD-2 → FP-1 (core) + FP-6/7 (LLM telemetry, metrics); LD-3 → FP-3, FP-4, FP-5; LD-4 → FP-8; LD-5 → FP-9; LD-6 → FP-10. FP-2, FP-6, FP-7 and FP-11 are new | Finer gates; safety components (risk, paper broker) before any agent can propose; explicit research, technical-foundation and simulation phases that the layer design did not have. Keeping the old numbers as theme names avoids breaking existing references |
| R-3 | **Event names** | `object_verb` style, e.g. `agent.state_changed`, `risk.breaker_tripped`, `order.filled`; broad catalogue (§4.3 there) | Dotted `domain.entity.verb` style, e.g. `agent.state.changed`, `research.item.accepted`, `circuit_breaker.tripped`; minimum V1 set (§10.1) | **Foundation plan convention**: `<domain>.<entity>.<past-tense verb>` (or `<domain>.<past-tense verb>` when the entity is the domain, e.g. `risk.approved`). The §10.1 set is the V1 minimum; the rest of the layer design catalogue is renamed to this convention when implemented, with the same payload fields | One convention, matching the owner's examples; the payloads of the layer design are kept, so nothing is lost; renaming now costs nothing because no code exists |
| R-4 | **Agent roster** | Upstream analysts + FX Session and Crypto Analysts; Signal Validator, Risk Officer, Exposure Controller, Circuit Breaker; Execution Pilot, Position Monitor; Station Controller, Data Core Keeper, Memory Archivist; Station Medic, Quartermaster, Café Host | Architectural roster (§5.1) with research, validation, macro, specialist, technical, upstream decision, proposal/risk, execution, review and operational roles; minimum V1 (§5.2); deferred (§5.3) | **Foundation plan rosters.** Layer design agents map as: FX Session → T2; Crypto → out of scope; Signal Validator → P1 schema + P2; Risk Officer, Exposure Controller, Circuit Breaker → components of P3 (kept as Vault visual personas); Execution Pilot → E1/E2; Position Monitor → P4 + E1/E2; Station Controller → O1; Data Core Keeper → T1 + O2 (provider health); Memory Archivist → L1 + L2; Medic, Quartermaster → personas of O2; Café Host → cosmetic | Each decision-making identity has one typed contract, and the owner's research chain and first strategy family are fully represented. Visual personas keep the station's richness without creating agents that decide nothing |
| R-5 | **Circuit-breaker reset** | Owner-only reset "with confirmation", recorded as an event; the station's RED banner "requires the owner's reset"; mechanism (UI or CLI) not specified | V1: a **local owner command** on the Mac with typed confirmation and a reason; the UI is read-only | **Foundation plan (local owner command in V1; UI shows state only).** A UI reset may be designed later, only together with authentication (owner decision Q8 excludes auth from V1) | V1 has no authentication. A reset button on an unauthenticated localhost page could be triggered by any local process or a malicious web page (cross-site request), which would let something other than the owner re-enable trading, contradicting owner decision Q6 |
| R-6 | Research chain *(new difference)* | Upstream News and Sentiment Analysts in the Observatory; no research validation | Research chain R → V → M → S (§4.29) | **Foundation plan** | Owner requirement; the layer design predates it |

### 13.2 Open decisions

No provider, subscription, broker specification or numeric risk threshold is chosen here.
Rows the owner has decided are marked **APPROVED** or **DECIDED** in the last column; all other rows remain open.
"Safe temporary default" is what the system does until the owner decides; where none is safe,
the dependent function stays off.

| # | Question | Why it matters | Options | Safe temporary default | Resolve by |
|---|---|---|---|---|---|
| D-1 | Historical market-data source for the four instruments before MT5 exists | Simulation and paper trading need intraday OHLC and ideally bid/ask or spread history | (a) owner-supplied files; (b) a third-party data service, to be evaluated for coverage, granularity and terms; (c) MT5 history via the bridge (needs the Windows host) | File importer with owner-supplied data only; no provider assumed | Phase 2 entry (files) / Phase 7 (for simulation depth) |
| D-2 | Economic-calendar source | Drives Economic Data Research and the news/event risk rule | (a) owner-maintained local calendar file; (b) a calendar service, to be evaluated; (c) a broker/MT5 calendar, if one exists (unverified) | Owner-maintained file; **no calendar → no new entries** (fail closed) | Phase 3 (fixture for rule tests); Phase 6 entry (real data) |
| D-3 | News / headline source (Market News, Geopolitical Research) | Two research roles depend on it | (a) none in V1; (b) public sources, subject to their terms; (c) a paid service, not assumed | None; R3/R4 deferred; coverage shows them missing | Before adding R3/R4 (after V1 unless the owner decides otherwise) |
| D-4 | Central-bank publication source | R1 in minimum V1 depends on it | (a) owner-supplied files of official publications; (b) automated retrieval from official sites, subject to their terms | Owner-supplied files | Phase 6 entry |
| D-5 | Rates/bonds data source | R5 is highly relevant to XAU/USD and USD/JPY | (a) owner-supplied files; (b) a data service, to be evaluated | R5 deferred; coverage shows it missing | After V1, or earlier if the owner prioritises R5 |
| D-6 | Corporate/earnings source for NAS100 | R6 and NAS100 specialist depth | (a) none in V1; (b) a source, to be evaluated | R6 deferred; NAS100 coverage shows it missing | After V1 |
| D-7 | Which timeframe profile(s) are validated first on paper and demo | Data needs, LLM cadence, cost and validation plan all depend on it | Owner hypothesis (D1/H4 → H1/M15 → M15/M5 → M5/M1); ARIA-derived candidates (§7.3); several in parallel | No profile chosen; all candidates configurable; Phase 7 compares them | Phase 7 exit (before Phase 8 demo) |
| D-8 | Paper account currency and starting balance | Sizing and P&L | Owner choice | Required config with no default; Paper Broker refuses to start without it | Phase 4 entry |
| D-9 | Size factors for Buy vs Overweight under setup-first framing | Position size | (a) equal; (b) Overweight smaller; (c) Overweight = no trade | **Overweight = no trade** (most conservative) until decided | Phase 6 exit |
| D-10 | Use of upstream memory log (U16) | Past lessons for the PM vs a second record | (a) not used; (b) only for profiles with ≤ 1 decision per instrument per day; (c) `past_context` generated from the Stellar Journal | Not used; `past_context` empty | Phase 6 |
| D-11 | LLM tiers, models and budgets | Cost and cadence (owner decision Q4: configurable) | Owner configuration after measurement | Budgets are required config; missing → LLM stages disabled, deterministic-only mode still runs | Phase 6 entry |
| D-12 | Risk threshold values | Every §8 limit | Values proposed from Phase 7 evidence, approved by the owner | Required config; missing or invalid → trading disabled. Test-only values in Phase 3 are labelled and never defaults | Phase 7 exit (paper values); before Phase 8 (demo values) |
| D-13 | Research source allowlist and trust tiers | Source Validator cannot work without it | Owner-defined list | Empty allowlist → no research accepted; coverage shows none | Phase 6 entry |
| D-14 | Research cadence per role | LLM cost and freshness | Per-role schedules in config | Event-driven roles only (R2 after releases, R1 on publication); no periodic polling | Phase 6 |
| D-15 | Does V1 require MT5 demo, or is V1 paper-only with demo as the next milestone? | V1 scope and dependency on the Windows host | (a) V1 = paper + demo; (b) V1 = paper, "V1-Demo" next | — | **APPROVED 2026-09-29:** option (b). V1 is functionally complete with paper trading; the MT5 / Vantage demo is a separate integration and validation gate (Phase 8) after the paper V1 foundation is stable; V1 does not imply profitability. Applied in §5.2, §11 (Phase 8), §12 |
| D-16 | Approval of the §13.1 reconciliations and the follow-up edit of the layer design | Removes conflicting guidance before code starts | Approve / amend each R-row | — | **APPROVED 2026-09-29:** all §13.1 recommendations (R-1 to R-6) are the canonical foundation decisions. `docs/STELLAR_LAYER_DESIGN.md` reconciled in v0.4 (2026-09-30). Applied in the header, §4.13, §13.1 |
| D-17 | Windows host for MT5 | Phase 8 cannot start without it (owner decision Q1: not chosen yet) | Local Windows PC; Windows VPS | Not chosen | Phase 8 entry |
| D-18 | Duration and review criteria for long-duration demo validation | Defines when validation ends | Owner choice | — | Phase 11 entry |
| D-19 | Should the Master Roadmap be added to the repository? | Future reconciliations can then be checked against its text, not a summary | Add under `docs/`; keep outside | — | **DECIDED 2026-09-30 by the owner:** added as `docs/STELLAR_MASTER_ROADMAP.md` |
