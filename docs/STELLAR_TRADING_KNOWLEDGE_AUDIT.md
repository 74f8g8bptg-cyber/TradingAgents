# Stellar Agents — Trading Knowledge Audit of the TradingAgents Base

| | |
|---|---|
| **Status** | Audit only. No code, dependency or other document was changed |
| **Revision audited** | Branch `claude/focused-fermi-r17548` at commit `265d710` ("feat: add Stellar Agents Phase 1 core foundation"). The upstream code in this fork is TradingAgents **v0.5.2** (`tradingagents/__init__.py`) and is unchanged by Stellar |
| **Date** | 2026-09-30 |
| **Environment facts used** | Python 3.11; installed `stockstats` 0.6.9, `yfinance` 1.7.0, `pandas` 3.0.6. Indicator formulas below were read from the installed `stockstats` source, because the repository delegates them to that library |
| **Purpose** | Know exactly what trading knowledge, calculations, prompts, data tools and capabilities already exist, so Stellar does not rebuild them — and does not mistake a prompt sentence for an implemented capability |

---

## Contents

1. [Scope and methodology](#1-scope-and-methodology)
2. [Summary of findings](#2-summary-of-findings)
3. [Complete capability inventory and classification](#3-complete-capability-inventory-and-classification)
4. [Technical-analysis inventory](#4-technical-analysis-inventory)
5. [Indicator calculations](#5-indicator-calculations)
6. [Candle / price-action audit](#6-candle--price-action-audit)
7. [Macro / fundamental / news knowledge](#7-macro--fundamental--news-knowledge)
8. [Market-specific knowledge and stock-centric assumptions](#8-market-specific-knowledge-and-stock-centric-assumptions)
9. [Trade decision logic](#9-trade-decision-logic)
10. [Risk knowledge](#10-risk-knowledge)
11. [Memory / learning](#11-memory--learning)
12. [Backtesting / simulation](#12-backtesting--simulation)
13. [Data provider inventory](#13-data-provider-inventory)
14. [Hidden knowledge findings](#14-hidden-knowledge-findings)
15. [Reuse matrix](#15-reuse-matrix)
16. [Gap analysis for Stellar](#16-gap-analysis-for-stellar)
17. [Recommendations: what NOT to rebuild](#17-recommendations-what-not-to-rebuild)

---

## 1. Scope and methodology

**Code read** (all of `tradingagents/` and `cli/`, about 12,000 lines):
`agents/` (analysts, researchers, managers, trader, risk_mgmt, `tools.py`, `schemas.py`,
`structured.py`, `rating.py`, `context.py`, `state.py`, `post_screen.py`), `dataflows/` (router,
config, date window, symbols, errors, files, net, and every vendor: Yahoo, Alpha Vantage, FRED,
Polymarket, SEC EDGAR, StockTwits, Reddit), `graph/` (setup, conditional logic, propagation,
trading graph, checkpointer, analyst execution), `memory/` (log, reflection, settlement),
`backtest.py`, `portfolio.py`, `reporting.py`, `default_config.py`, `llm_clients/`, and the CLI.
The 82 upstream test files under `tests/` were inventoried by name and test functions, and the
indicator-related ones read. `README.md` and `CHANGELOG.md` were not used as evidence. There are
no example notebooks in the repository.

**Method.**
1. Every module was read for what it *computes*, not what it *mentions*.
2. A keyword sweep over all upstream Python code covered every term in the brief (§14 lists the
   meaningful hits).
3. Each capability was classified by **implementation type**:
   - **Deterministic (repo):** code in this repository computes it.
   - **Deterministic (library):** computed locally by a third-party library the repository calls
     (`stockstats`).
   - **External:** fetched from a data provider already computed.
   - **LLM-only:** the only trace is an instruction or description in a prompt; any result is
     whatever the model writes.
4. Indicator formulas were taken from the installed `stockstats` source, not from textbooks.
5. Whether a capability is **used in the graph** was traced from `graph/setup.py` →
   analyst nodes → `TOOLS` tuples → `route_to_vendor` → vendor functions.

**Out of scope.** Provider marketing claims (no web research was needed), LLM-provider plumbing
beyond a one-line inventory, CLI display code.

---

## 2. Summary of findings

1. **TradingAgents is a stock-research debate engine with a decision-quality evaluator, not a
   trading system.** It has no order execution, no deterministic risk control, no position sizing,
   no intraday data and no price-action logic.
2. **Real deterministic trading calculations are few and delegated.**
   - A whitelist of 13 daily indicators is computed locally by `stockstats`; Alpha Vantage can
     fetch 12 of them.
   - A **verified market snapshot** table is built deterministically.
   - Settlement computes raw return and alpha against a benchmark.
   - Everything else about markets is LLM prose.
3. **All technical analysis beyond indicator values is prompt-only.** This includes support and
   resistance, trend, breakout, reversal, divergence, crossovers and overbought/oversold. There is
   **no** candle, wick/body, pattern, swing-point, market-structure, pullback, multi-timeframe,
   session, correlation or seasonality code anywhere.
4. **The strongest reusable assets are engineering disciplines, not trading methods:**
   - point-in-time data rules (look-ahead guards, vintage pinning, withholding live-only data);
   - typed vendor errors and "no data" sentinels that stop agents inventing numbers;
   - the verified-snapshot pattern;
   - structured output with fallback;
   - the REVIEW sentinel.
5. **Several behaviours are unsafe for Stellar's four markets:**
   - XAU/USD is priced from the COMEX future `GC=F`, and NAS100 from the cash index `^NDX`.
   - Yahoo OHLCV text and the snapshot are **rounded to 2 decimals**, which destroys EUR/USD
     precision.
   - VWMA and MFI depend on volume that spot FX does not have.
   - All data is daily.
   - The Trader's levels are floats, and are silently dropped when written as a percentage or a
     range.
6. **Memory and backtesting evaluate ratings, not trades.** Settlement scores a rating's direction
   over N daily closes against a benchmark. There are no fills, no stops, no P&L in currency and no
   equity curve.

---

## 3. Complete capability inventory and classification

Classes: **ALREADY EXISTS**, **PARTIAL**, **EXISTS BUT LLM-ONLY**, **EXISTS BUT UNSAFE / TOO
TEXTUAL**, **NEEDS ADAPTATION**, **MISSING**, **NOT RELEVANT TO STELLAR**. "Graph" = used in
the default graph path. Quality: H/M/L. Reuse codes are those of §15.

### 3.1 Market data, indicators and technical analysis

| # | Capability | Source file(s) | Type | Graph | Class | Quality | Reuse | Risk / limitation |
|---|---|---|---|---|---|---|---|---|
| K1 | Daily OHLCV as CSV text (`get_stock_data`) | `agents/tools.py`; `dataflows/vendors/yahoo/market.py::get_YFin_data_online`; `alpha_vantage/stock.py::get_stock` | External | Yes (market analyst) | EXISTS BUT UNSAFE / TOO TEXTUAL | M | REPLACE | Prices **rounded to 2 dp** (Yahoo); CSV text for an LLM; daily only; AV uses equity endpoint `TIME_SERIES_DAILY_ADJUSTED` |
| K2 | Cached 5-year daily frame with as-of cut (`load_ohlcv`) | `yahoo/ohlcv.py` | Deterministic (repo) | Yes (indicators, snapshot) | PARTIAL | H | ADAPT | Daily only; cache per symbol per day; `ffill().bfill()` gap fill for indicators |
| K3 | OHLCV staleness guard (latest row > 10 days before as-of → no data) | `yahoo/ohlcv.py::_assert_ohlcv_not_stale` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | Threshold is calendar days, stock-oriented |
| K4 | Unsettled-bar handling (closeless last bar dropped; 900 s same-day cache TTL for partial candles) | `yahoo/ohlcv.py` | Deterministic (repo) | Yes | PARTIAL | M | ADAPT (idea) | A partial daily bar with a Close is indistinguishable from a final one; only a TTL refresh |
| K5 | Symbol normalisation (broker → Yahoo) | `dataflows/symbols.py::normalize_symbol` | Deterministic (repo) | Yes (every Yahoo path) | EXISTS BUT UNSAFE / TOO TEXTUAL | M | REPLACE | `XAUUSD→GC=F` (future), `NAS100→^NDX` (cash index), `EURUSD→EURUSD=X`; silent proxying (Foundation L2) |
| K6 | Path-safe ticker validation | `dataflows/symbols.py::safe_ticker_component` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | — |
| K7 | Indicator engine: `stockstats.wrap` with a 13-name whitelist | `yahoo/market.py::get_stock_stats_indicators_window` | Deterministic (library) | Yes | PARTIAL | M | WRAP | Daily; whitelist excludes most of stockstats; warm-up values not blanked (§5) |
| K8 | SMA 50 / 200 | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | M | WRAP | `min_periods=1`: early values are averages of fewer bars |
| K9 | EMA 10 | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | M | WRAP | `ewm(adjust=True, min_periods=1)` |
| K10 | MACD 12/26/9 (+ signal, histogram) | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | M | WRAP | Values shown with 2 dp in the snapshot, so EUR/USD MACD reads 0.00 |
| K11 | RSI 14 (Wilder smoothing) | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | H | WRAP | First value forced to 50 |
| K12 | Bollinger 20 / 2σ | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | M | WRAP | Sample std, `min_periods=1` |
| K13 | ATR 14 (Wilder SMMA of true range) | stockstats via K7 | Deterministic (library) | Yes | ALREADY EXISTS | H | WRAP | Daily only |
| K14 | VWMA 14 | stockstats via K7 | Deterministic (library) | Yes | PARTIAL | L | NOT USED | Weighs **typical price** (H+L+C)/3, not close; spot FX has no volume, so the output is 0 |
| K15 | MFI 14 | stockstats via K7 (yfinance whitelist only) | Deterministic (library) | Tool only; not in prompt list | PARTIAL | L | NOT USED | Volume-based; returns 0.5 when volume is 0; Alpha Vantage does not serve it |
| K16 | Alpha Vantage indicator endpoints (SMA, EMA, MACD, RSI, BBANDS, ATR) | `alpha_vantage/indicator.py` | External | Only if configured | NEEDS ADAPTATION | M | NOT USED | Raw symbol passed (no normalisation); daily; key-gated; no VWMA or MFI |
| K17 | **Verified market snapshot** (latest OHLCV row, 11 indicators, last ≤ 30 closes, as-of cut, "source of truth" instruction) | `yahoo/snapshot.py`; tool `get_verified_market_snapshot` | Deterministic (repo + library) | Yes | ALREADY EXISTS | H | ADAPT | 2-dp formatting; daily; Yahoo only |
| K18 | Indicator usage rules (RSI 70/30, golden/death cross, band ride, ATR for stops) | prompt `analysts/market_analyst.py`; descriptions in `yahoo/market.py`, `alpha_vantage/indicator.py` | LLM-only | Yes | EXISTS BUT LLM-ONLY | L | NOT USED | Rules are advice text; nothing evaluates them |
| K19 | Market analyst report (trend, support/resistance, "actionable insights") | `analysts/market_analyst.py` | LLM-only | Yes | EXISTS BUT LLM-ONLY | M | REPLACE (by T3–T8) | Free text; numbers only as good as the model's reading of K17 |
| K20 | Timeframes | none (no `interval` argument on any Yahoo call) | — | — | PARTIAL | L | REPLACE | **Daily only**; AV indicator `interval` fixed to `daily` |
| K21 | Sessions / market hours | none (only cache comments) | — | — | MISSING | — | — | — |
| K22 | Multi-timeframe analysis | none | — | — | MISSING | — | — | — |
| K23 | Candle / price-action analysis | none | — | — | MISSING | — | — | See §6 |
| K24 | Support / resistance | prompts only (market analyst, trader, snapshot footer) | LLM-only | Yes | EXISTS BUT LLM-ONLY | L | NOT USED | The snapshot footer tells the model *not* to claim bounces without dated evidence |
| K25 | Market structure / swing points (HH/HL/LH/LL) | none | — | — | MISSING | — | — | — |
| K26 | Correlation / relative strength / cross-market | none (benchmark alpha only, K59) | — | — | MISSING | — | — | — |
| K27 | Seasonality | none ("seasonal" only as FRED's seasonal-adjustment label) | — | — | MISSING | — | — | — |
| K28 | Statistical / probability pattern testing | none (only rating hit rate, K61; external odds, K30) | — | — | MISSING | — | — | — |
| K29 | Intraday bars | none | — | — | MISSING | — | — | — |
| K30 | Bid/ask quotes and spread | none | — | — | MISSING | — | — | — |

### 3.2 Macro, news, sentiment and fundamentals

| # | Capability | Source file(s) | Type | Graph | Class | Quality | Reuse | Risk / limitation |
|---|---|---|---|---|---|---|---|---|
| K31 | **FRED macro series** (~30 aliases or raw ids; **point-in-time vintage** via ALFRED realtime pin; change-over-window summary; 40-row cap) | `dataflows/vendors/fred.py`; tool `get_macro_indicators` | External (deterministic retrieval) | Yes (news analyst) | ALREADY EXISTS | H | WRAP | US series only in aliases (no ECB/BoJ rates, no JGB yields); needs `FRED_API_KEY` |
| K32 | Polymarket event probabilities (live only; **withheld for historical dates**) | `vendors/polymarket.py`; tool `get_prediction_markets` | External | Yes (news analyst) | ALREADY EXISTS | M | NOT USED (V1) | No history, so not replayable; LLM picks the topic |
| K33 | Yahoo ticker news (window filter, coverage-gap notice) | `yahoo/news.py::get_news_yfinance` | External | Yes (news, sentiment) | NEEDS ADAPTATION | M | ADAPT | Symbol mapped to `GC=F`/`^NDX`/`EURUSD=X`; latest-N articles only, not archived |
| K34 | Yahoo global news (fixed query list incl. "ECB Bank of England BOJ central bank policy") | `yahoo/news.py::get_global_news_yfinance`; `default_config.py::global_news_queries` | External | Yes | NEEDS ADAPTATION | M | ADAPT | Search-ranked, not archived; queries are config |
| K35 | Alpha Vantage news & sentiment (tickers or topics) | `alpha_vantage/news.py` | External | If configured | NEEDS ADAPTATION | M | NOT USED (V1) | Key-gated; ticker vocabulary is equity-oriented |
| K36 | News analyst report | `analysts/news_analyst.py` | LLM-only | Yes | EXISTS BUT LLM-ONLY | M | REPLACE (by R/V/M/S chain) | No citation structure, no fact/interpretation split |
| K37 | Sentiment analyst (pre-fetched news + StockTwits + Reddit; typed `SentimentReport` band / score / confidence) | `analysts/sentiment_analyst.py`; `schemas.py` | LLM with typed output | Yes | NOT RELEVANT TO STELLAR | M | NOT USED | Retail stock chatter; not point-in-time |
| K38 | StockTwits stream fetcher | `vendors/stocktwits.py` | External | Yes | NOT RELEVANT TO STELLAR | M | NOT USED | Cashtag streams |
| K39 | Reddit RSS search (r/wallstreetbets, r/stocks, r/investing) | `vendors/reddit.py` | External | Yes | NOT RELEVANT TO STELLAR | M | NOT USED | — |
| K40 | Social-post screening (TypeSafe "Jev" relevance/stance probabilities) | `agents/post_screen.py` | External LLM service | Optional | NOT RELEVANT TO STELLAR | M | NOT USED | Third-party service |
| K41 | Company fundamentals (profile, ratios) and statements (Yahoo, AV, **SEC EDGAR as-filed**) | `yahoo/fundamentals.py`, `alpha_vantage/fundamentals.py`, `vendors/sec_edgar.py` | External | Yes (fundamentals analyst) | NOT RELEVANT TO STELLAR | H (EDGAR) | NOT USED | Single-issuer data; possibly for R6 (NAS100 constituents) later |
| K42 | Insider transactions | `yahoo/fundamentals.py`, `alpha_vantage/news.py` | External | Yes | NOT RELEVANT TO STELLAR | M | NOT USED | — |
| K43 | Fundamentals analyst report | `analysts/fundamentals_analyst.py` | LLM-only | Yes | NOT RELEVANT TO STELLAR | M | NOT USED | Foundation L3 |
| K44 | Economic calendar (scheduled releases, actual / prior / consensus) | none | — | — | MISSING | — | — | FRED gives revised series, not a release calendar |
| K45 | Central-bank publications feed (statements, minutes, speeches) | none (only as news search terms) | — | — | MISSING | — | — | — |
| K46 | Currency-strength measure | none | — | — | MISSING | — | — | FRED `DTWEXBGS` (broad dollar index) alias is the only USD gauge |
| K47 | Risk-on / risk-off regime | none (FRED `VIXCLS` alias only) | — | — | MISSING | — | — | — |

### 3.3 Decision chain

| # | Capability | Source file(s) | Type | Graph | Class | Quality | Reuse | Risk / limitation |
|---|---|---|---|---|---|---|---|---|
| K48 | Bull / Bear debate | `researchers/bull_researcher.py`, `bear_researcher.py` | LLM-only | Yes | ALREADY EXISTS | M | KEEP (Foundation D1, C12) | Prompts say "company", "growth", "competitive advantages" |
| K49 | Debate orchestration (round counting, speaker order, path maps) | `graph/conditional_logic.py`, `graph/setup.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP | — |
| K50 | Research Manager typed `ResearchPlan` (5-tier recommendation + rationale + strategic actions) | `managers/research_manager.py`; `schemas.py` | LLM, typed rating | Yes | ALREADY EXISTS | M | KEEP | "Sized against a standard allocation" is free text |
| K51 | Trader `TraderProposal` (Buy/Hold/Sell; `entry_price`, `stop_loss` as float; `position_sizing` as text) | `trader/trader.py`; `schemas.py` | LLM, partly typed | Yes | EXISTS BUT UNSAFE / TOO TEXTUAL | M | WRAP (advisory only) | No target; floats; sizing is prose; % or range values are **silently dropped** (K53) |
| K52 | Risk debaters (aggressive / conservative / neutral) | `risk_mgmt/*.py` | LLM-only | Yes | EXISTS BUT LLM-ONLY | M | KEEP (as debaters, not risk control) | Not a risk control (layer design §3.1) |
| K53 | LLM number coercion (drop "None"/"N/A", **drop "15%"**, drop ranges and hedges, strip "$" and ",") | `schemas.py::_coerce_optional_float` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | Correct for advisory values; loses information silently |
| K54 | Portfolio Manager typed `PortfolioDecision` (rating, summary, thesis, `price_target` float, `time_horizon` text) | `managers/portfolio_manager.py`; `schemas.py` | LLM, typed rating | Yes | ALREADY EXISTS | M | KEEP (wrapped, R-1) | Rating vocabulary is equity-position language |
| K55 | Rating vocabulary, rating parser and **REVIEW** sentinel | `agents/rating.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP | — |
| K56 | Structured output with free-text fallback; `NO_EXTERNAL_TOOLS` | `agents/structured.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | — |
| K57 | Anti-fabrication prompt helpers (`report_or_absent`, opening marker, `DATA_UNAVAILABLE` / `NO_DATA_AVAILABLE` sentinels) | `agents/context.py`; `dataflows/router.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | — |
| K58 | Instrument identity and context prompt | `agents/context.py` | Deterministic lookup + prompt | Yes | NEEDS ADAPTATION | M | ADAPT | Company name / sector from Yahoo profile; "company" framing |
| K59 | Portfolio context (positions with signed quantity, cash, currency) | `tradingagents/portfolio.py` | Deterministic (repo) | Optional | PARTIAL | M | ADAPT | Units generic; no margin, lots, or per-position stops |
| K60 | Hard risk controls, sizing, stop validation, exposure, breaker | none | — | — | MISSING | — | — | See §10 |
| K61 | Order execution / broker / paper fills | none (`backtest.py` explicitly refuses to simulate) | — | — | MISSING | — | — | — |

### 3.4 Memory, evaluation and infrastructure

| # | Capability | Source file(s) | Type | Graph | Class | Quality | Reuse | Risk / limitation |
|---|---|---|---|---|---|---|---|---|
| K62 | Memory log (markdown; pending → resolved; idempotent per ticker/date; rotation; **point-in-time lesson filter** by resolution date) | `memory/log.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | NOT USED in V1 (Foundation D-10 open) | Markdown parsing; keyed by ticker/date, not by trade |
| K63 | Reflection (2–4 sentence lesson on a settled decision) | `memory/reflection.py` | LLM-only | Yes (at settlement) | EXISTS BUT LLM-ONLY | M | ADAPT (L1 narrative mode later) | Reflects on rating vs alpha, not on a trade |
| K64 | Settlement: raw return and alpha vs regional benchmark over N **daily** closes; resolution date | `memory/settlement.py`; `default_config.py::benchmark_map` | Deterministic (repo) | Yes | NEEDS ADAPTATION | M | NOT USED | Stock benchmarks (SPY default); no stops, fills, costs or currency P&L |
| K65 | Past-context injection into the Portfolio Manager | `memory/log.py::get_past_context`; `graph/trading_graph.py` | Deterministic (repo) | Yes | ALREADY EXISTS | M | NOT USED in V1 | Same-ticker and cross-ticker lessons as prose |
| K66 | Backtest grid and summary (hit rate and mean alpha by rating) | `tradingagents/backtest.py` | Deterministic (repo) + LLM runs | CLI `backtest` | NEEDS ADAPTATION | M | NOT USED (replaced, Foundation §4.17) | Decision-quality evaluation, explicitly **not** a portfolio simulator |
| K67 | Point-in-time rules (`as_of`, `as_of_window`, `in_window`, `coverage_gap`, `withhold_live_profile`, `withhold_undisclosed_trades`, `withhold_undated_statements`) | `dataflows/date_window.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | Date granularity is a day |
| K68 | Vendor router with explicit fallback chain and typed errors | `dataflows/router.py`, `dataflows/errors.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | Tool-string interface |
| K69 | Yahoo retry / rate-limit backoff / reachability probe | `yahoo/common.py`, `dataflows/net.py` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP (pattern) | — |
| K70 | Checkpoint / resume of graph runs | `graph/checkpointer.py` | Deterministic (repo) | Optional | ALREADY EXISTS | H | KEEP (via C3) | — |
| K71 | Output-language handling that keeps labelled lines in English | `agents/context.py::get_language_instruction` | Deterministic (repo) | Yes | ALREADY EXISTS | M | KEEP | — |
| K72 | LLM provider clients, capabilities and model catalogue | `llm_clients/` | Deterministic (repo) | Yes | ALREADY EXISTS | H | KEEP | Provider-agnostic tiers match owner Q4 |
| K73 | Report saving | `tradingagents/reporting.py` | Deterministic (repo) | Yes | ALREADY EXISTS | M | NOT USED | Stellar journals instead |
| K74 | Crypto asset mode (drops fundamentals analyst; crypto prompts) | `cli/prompts.py`, `agents/context.py`, researchers | Deterministic switch + prompts | CLI | NOT RELEVANT TO STELLAR | M | NOT USED | Shows the pattern for an asset-type switch |
| K75 | CLI (interactive run, headless run, backtest command, prefs) | `cli/` | Deterministic (repo) | — | NOT RELEVANT TO STELLAR | M | NOT USED | Stellar has its own entry points |

**Totals: 75 capabilities.**

| Class | Count |
|---|---|
| ALREADY EXISTS | 28 |
| PARTIAL | 7 |
| EXISTS BUT LLM-ONLY | 6 |
| EXISTS BUT UNSAFE / TOO TEXTUAL | 3 |
| NEEDS ADAPTATION | 7 |
| MISSING | 15 |
| NOT RELEVANT TO STELLAR | 9 |

---

## 4. Technical-analysis inventory

For every term in the brief: what the repository really contains. Unless stated, "graph" means the
Market Analyst node, the only technical consumer.

| Concept | Where | Deterministic or LLM | Inputs → outputs | In graph | Limitations | Tests | Stellar reuse |
|---|---|---|---|---|---|---|---|
| OHLCV | K1, K2 | Deterministic retrieval (Yahoo `Ticker.history`, AV `TIME_SERIES_DAILY_ADJUSTED`) | symbol, dates → CSV text (K1) or DataFrame (K2) | Yes | Daily; K1 rounded to 2 dp; Yahoo prices are adjusted (`auto_adjust=True` in K2) | `test_ohlcv_*`, `test_yfinance_stale_ohlcv_guard`, `test_yahoo_rate_limit` | Concepts only; Stellar's `MarketDataSource` replaces it |
| Candle / candlestick | only the word "candle" in a cache comment about Yahoo's partial daily candle | — | — | — | No candle logic | — | None |
| Open/high/low/close | K2 frame columns; K17 latest-row table | Deterministic | — | Yes | No OHLC consistency validation (Stellar's `Candle` has it) | — | None |
| Price series | K2, `get_closes` (settlement) | Deterministic | — | Yes | Daily closes | `test_ohlcv_latest_bar` | Idea |
| Timeframe handling | none | — | — | — | Daily only everywhere | — | None |
| SMA | K8 | Deterministic (library) | close → series | Yes | 50/200 only; `min_periods=1` | `test_ohlcv_date_column` computes a 5-SMA exists (no value check) | WRAP or reimplement |
| EMA | K9 | Deterministic (library) | close → series | Yes | 10 only | none | WRAP or reimplement |
| RSI | K11 | Deterministic (library) | close → 0–100 | Yes | 14 only | none | WRAP |
| MACD | K10 | Deterministic (library) | close → 3 series | Yes | 12/26/9 | none | WRAP |
| ATR | K13 | Deterministic (library) | H/L/C → series | Yes | 14 only | none | WRAP |
| Bollinger Bands | K12 | Deterministic (library) | close → 3 series | Yes | 20 / 2σ | none | WRAP |
| VWMA | K14 | Deterministic (library) | typical price × volume | Yes | Not close-weighted; FX volume absent | none | Not for FX/metal |
| VWAP | none | — | — | — | Absent (stockstats has no session VWAP either) | — | — |
| Volume | K2 column; K14, K15 | Deterministic | — | Yes | Yahoo spot FX volume is 0; `GC=F` / `^NDX` volume is not the traded CFD's | — | None |
| Volatility | ATR, Bollinger; FRED `VIXCLS` alias | Deterministic / External | — | Yes | No realised-volatility or regime measure | — | ATR only |
| Momentum | RSI, MACD; prompt text | Deterministic values + LLM reading | — | Yes | No momentum *assessment* | — | Values only |
| Trend | prompt text ("identify trend direction") | LLM-only | — | Yes | No trend state code | — | None |
| Support / resistance | prompt text (market analyst, trader, snapshot footer) | LLM-only | — | Yes | No level computation | — | None |
| Breakout | indicator descriptions (Bollinger "breakout zones") | LLM-only | — | Yes | — | — | None |
| Pullback | none | — | — | — | Absent | — | — |
| Reversal | descriptions (RSI, Bollinger) | LLM-only | — | Yes | — | — | None |
| Divergence | descriptions (MACD, RSI, MFI) | LLM-only | — | Yes | No divergence detector | — | None |
| Overbought / oversold | descriptions (RSI 70/30, MFI 80/20) | LLM-only | — | Yes | Thresholds are prose | — | None |
| Moving-average crossovers | descriptions ("golden/death cross", "MACD crossovers") | LLM-only | — | Yes | No crossover detector | — | None |
| Market structure, HH/HL/LH/LL | none | — | — | — | Absent | — | — |
| Wick / body analysis, candle patterns | none | — | — | — | Absent | — | — |
| Price action | none | — | — | — | Absent | — | — |
| Gaps | K2 `ffill().bfill()` fills missing *rows*, not price gaps | Deterministic (data hygiene) | — | Yes | No gap detection or classification | `test_ohlcv_latest_bar` | None |
| Sessions | none | — | — | — | Absent | — | — |
| Multi-timeframe | none | — | — | — | Absent | — | — |
| Correlation / relative strength | none; alpha vs benchmark in settlement (K64) | Deterministic (settlement only) | — | Post-run | Not an analysis input | `test_memory_log` | None |
| Seasonality | none | — | — | — | Absent | — | — |
| Statistics / probability | Polymarket odds (external); backtest hit rate (post-run) | External / Deterministic | — | News analyst / CLI | No statistical testing of patterns | `test_polymarket`, `test_backtest` | None |
| Pattern matching / chart-shape | none | — | — | — | Absent | — | — |

---

## 5. Indicator calculations

A = computed locally · B = fetched from a provider · C = only described in a prompt · D =
delegated to an LLM · E = deterministic value test in the repository.

| Indicator | A | B | C | D | E | Implementation (as installed) |
|---|---|---|---|---|---|---|
| `close_50_sma`, `close_200_sma` | Yes (stockstats) | Yes (AV `SMA`, 50/200) | Described | Interpretation only | **No** | `close.rolling(n, min_periods=1).mean()` — values exist from the first bar, averaged over fewer than n bars until n bars exist |
| `close_10_ema` | Yes | Yes (AV `EMA`, 10) | Described | Interpretation | No | `close.ewm(span=10, adjust=True, min_periods=1).mean()` |
| `macd`, `macds`, `macdh` | Yes | Yes (AV `MACD`) | Described | Interpretation | No | EMA12 − EMA26; signal = EMA9 of MACD; histogram = MACD − signal (EMAs as above) |
| `rsi` | Yes | Yes (AV `RSI`, `time_period` 14) | Described (70/30) | Interpretation | No | Wilder: gains and losses smoothed with `ewm(alpha=1/14, adjust=True)`; RSI = 100·up/(up+down); 50 when no change; first value set to 50 |
| `boll`, `boll_ub`, `boll_lb` | Yes | Yes (AV `BBANDS`, 20) | Described | Interpretation | No | SMA20 ± 2 × rolling sample std(20), `min_periods=1` |
| `atr` | Yes | Yes (AV `ATR`, 14) | Described | Interpretation | No | TR = max(H−L, \|H−C₋₁\|, \|L−C₋₁\|); ATR = Wilder SMMA(14) of TR |
| `vwma` | Yes | **No** (AV raises "not served") | Described | Interpretation | No | Σ(typical price × volume)/Σ volume over 14 bars; 0 where volume sum is 0 |
| `mfi` | Yes (yfinance path only) | No | **Not** in the market-analyst prompt list; description in `yahoo/market.py` | Interpretation | No | Typical-price money flow ratio over 14 bars; 0.5 when no flow; first 14 values set to 0.5 |
| `stochrsi` | Not whitelisted (would raise) | No | Named in the prompt only as an example of redundancy | — | No | — |

Notes:
- **Where the formulas live.** The repository shows the indicator *names*; the formulas are in the
  third-party `stockstats` package. A `stockstats` upgrade can change values with no repository
  change.
- **No value tests.** `tests/test_yahoo_snapshot.py` checks that future rows are excluded and the
  window is capped. `tests/test_ohlcv_date_column.py` checks that a `close_5_sma` column appears.
  **No test pins an indicator value.**
- **Warm-up.** Because of `min_periods=1` and `adjust=True`, early values are not blanked. The
  5-year cache usually hides this for daily bars, but a short history would silently report
  partial averages as if they were full ones.
- **Gap filling.** Indicators run on a frame whose gaps were filled with `ffill().bfill()`. The
  back-fill takes a later value only for leading gaps.
- **Alpha Vantage** requests always use `interval=daily`. The symbol is passed through
  unnormalised, and the returned CSV is parsed by column name.

---

## 6. Candle / price-action audit

| Capability | Status | Evidence |
|---|---|---|
| Candle body size | **Absent** | No code; no prompt mention |
| Upper / lower wick size | **Absent** | "wick" has zero hits in upstream code |
| Candle direction | **Absent** | No close-vs-open logic anywhere |
| Engulfing | **Absent** | zero hits |
| Hammer / shooting star | **Absent** | only hit is a test comment ("don't hammer the vendor") |
| Doji | **Absent** | zero hits |
| Inside bar / outside bar | **Absent** | zero hits |
| Consecutive candles | **Absent** | — |
| Impulse vs consolidation | **Absent** | — |
| Rejection candles | **Absent** | — |
| Break / retest | **LLM prompt-only** (partial wording) | "breakout zones" in the Bollinger description; no retest concept |
| Pullback | **Absent** | zero hits |
| Swing highs / lows | **Absent** | "swing" appears only in an LLM-client file |
| Market structure | **Absent** | zero hits |
| Chart patterns | **Absent** | "pattern" hits are regexes and a comment about the model "pattern-matching the price action to a narrative" |
| Geometry / shape recognition | **Absent** | — |
| Support / resistance | **LLM prompt-only** | market analyst and trader prompts; the snapshot footer forbids unsupported bounce claims |
| Gap handling | **Partial (data hygiene only)** | missing rows are filled for indicators; no gap detection |

**What Stellar's Candle / Price Action agent (T5), Market Structure agent (T3), Pullback / Setup
agent (T6) and Entry Timing agent (T7) still need: all of it.** Nothing in TradingAgents gives a
deterministic candle feature, swing point, level, structure state, pullback measure, pattern or
entry trigger. The only reusable pieces are:
- the verified-snapshot discipline, in which models may cite only computed values;
- ATR for scaling;
- the as-of cut on the input frame.

---

## 7. Macro / fundamental / news knowledge

| Topic | Source / provider | Agent / tool | Deterministic data vs LLM | Freshness handling | Provenance / citation | Limitations |
|---|---|---|---|---|---|---|
| News (ticker) | Yahoo `Ticker.get_news`; Alpha Vantage `NEWS_SENTIMENT` | News analyst, sentiment analyst (`get_news`) | Retrieval deterministic; interpretation LLM | Window filter on publish time; `coverage_gap` notice when the feed cannot reach the window | Title, publisher and link per article in the text; the report does not cite them structurally | Latest N items only (not archived); ticker mapped to `GC=F`/`^NDX`/`EURUSD=X` |
| News (global) | Yahoo `Search` over 5 configured queries; AV topics `financial_markets,economy_macro,economy_monetary` | News analyst (`get_global_news`) | Retrieval deterministic; LLM interprets | 7-day look-back; window filter | Titles / publishers only | Relevance-ranked search; not reproducible historically |
| Sentiment | StockTwits, Reddit, Yahoo news; optional Jev screening | Sentiment analyst | LLM with a typed band / score / confidence | 7-day window; not point-in-time (stated in the module) | Counts and posts in the prompt | Retail equity chatter |
| Macro data (rates, yields, inflation, employment, GDP) | FRED (aliases: fed funds, 2y/10y/30y, 10y–2y, CPI, core CPI, PCE, core PCE, 10y breakeven, real GDP, GDP, industrial production, unemployment, payrolls, claims, M2, VIX, broad dollar index, consumer sentiment, housing starts, retail sales) | News analyst (`get_macro_indicators`) | **Deterministic retrieval**; LLM picks the series and interprets | **Point-in-time vintage pinned** (`realtime_start = realtime_end = as_of`, clamped to FRED's Chicago "today") | Series id, title, units, frequency, window in the output | US only in aliases; raw ids allowed, but the LLM must know them; no release calendar |
| Central banks | Only as news search terms ("Federal Reserve…", "ECB Bank of England BOJ…") and FRED fed funds | News analyst | LLM | News window | None | No statements, minutes, decisions or ECB/BoJ rate series |
| Interest rates / yields | FRED US series | News analyst | Deterministic retrieval | Vintage pinned | Yes | No non-US yields; no real-yield series in aliases (10y breakeven only) |
| Inflation / employment / GDP | FRED | News analyst | Deterministic retrieval | Vintage pinned | Yes | US only |
| PMI | none | — | — | — | — | Absent (PMIs are not FRED series) |
| Earnings / company fundamentals | Yahoo profile and statements; AV; SEC EDGAR as-filed | Fundamentals analyst | Retrieval deterministic; LLM interprets | EDGAR by filing date; others withheld for historical dates | Filing-dated for EDGAR | Single issuer |
| Geopolitics | News search term; Polymarket topics | News analyst | LLM | News window; Polymarket live only | Market question and odds | — |
| Currency strength | FRED broad dollar index alias | News analyst | Deterministic retrieval | Vintage pinned | Yes | No per-currency strength |
| Risk-on / risk-off | FRED VIX alias; prompt prose | News analyst | LLM | — | — | No regime computation |
| Prediction markets | Polymarket Gamma API | News analyst | External probabilities; LLM picks the topic | Withheld for historical dates | Question, odds, volume | Not replayable |

---

## 8. Market-specific knowledge and stock-centric assumptions

**Asset coverage in code.**
- **Stocks:** the full pipeline.
- **Crypto:** an `asset_type="crypto"` switch drops the fundamentals analyst and changes some
  labels (K74).
- **Forex, gold, indices:** handled only by symbol aliasing (K5). No analysis logic knows they
  differ.

| Assumption | Where | Why it matters for Stellar |
|---|---|---|
| Ticker = company | `agents/context.py` (identity from `longName`/sector); researchers' "company", "competitive advantages", "growth potential"; fundamentals analyst | Meaningless for XAU/USD, EUR/USD, USD/JPY; for NAS100 only at constituent level |
| Proxy instruments | `symbols.py` aliases | XAU/USD priced as the **COMEX gold future** (roll gaps, different hours, contango); NAS100 as the **cash index** `^NDX` (no overnight prices); FX as Yahoo `=X` daily series |
| Price precision | `market.py` rounds OHLC to 2 dp; `snapshot.py::_fmt` formats floats to 2 dp | EUR/USD needs 4–5 decimals; USD/JPY needs 3; indicator values for FX (MACD, ATR) collapse to 0.00 |
| Volume | VWMA, MFI; "volume analyses" in prompts | Spot FX has no centralised volume; gold/index proxy volume is the future's or index's, not the CFD's |
| Daily bars only | every Yahoo call; AV `interval=daily`; settlement counts daily closes | Stellar's profiles need intraday timeframes (Foundation §7) |
| Market hours / sessions | none; staleness threshold in calendar days | FX and metals trade ~24/5; NAS100 CFD trades extended hours |
| Earnings, valuation, insider, SEC | fundamentals analyst and vendors | Not applicable to three of the four markets |
| Benchmark alpha | `benchmark_map` (SPY default; equity indices by exchange suffix) | Alpha vs SPY is not a meaningful yardstick for EUR/USD or USD/JPY |
| Order semantics | none (no orders) | — |
| Short selling | `Position.quantity` may be negative ("negative is short"); prompts never discuss shorting | A short is not a first-class decision |
| Rating vocabulary | Buy / Overweight / Hold / Underweight / Sell = **position management** ("Sell: exit position or avoid entry"; "Underweight: reduce exposure, take partial profits") | "Sell" ≠ open a short (Foundation L8); resolved in Stellar by setup-first R-1 |
| Holding horizon | `holding_period_days = 5`; PM `time_horizon` free text ("3-6 months") | Stellar horizons come from timeframe profiles |
| Sentiment sources | StockTwits cashtags, stock subreddits | Not meaningful for FX or metals |

**What each Stellar market needs adapted.**
- **XAU/USD.** A spot bid/ask source (never `GC=F` for levels), precision beyond 2 dp, no volume
  indicators, sessions around London/New York, and a US real-yield and USD macro set.
- **EUR/USD.** 5-decimal precision, spot quotes, ECB and Fed policy data, the EU–US rate spread,
  and no volume indicators.
- **USD/JPY.** 3-decimal precision, BoJ policy and the US–JP spread, intervention statements, and
  the Tokyo session.
- **NAS100.** The CFD price series rather than `^NDX` cash, extended-hours and gap handling,
  constituent earnings (research role R6), and the Fed and US-yields set.

---

## 9. Trade decision logic

Flow (`graph/setup.py`): analysts in parallel → Bull ↔ Bear (`max_debate_rounds`, default 1) →
Research Manager → Trader → Aggressive → Conservative → Neutral (`max_risk_discuss_rounds`,
default 1) → Portfolio Manager → end.

| Agent | Inputs | Output | Structured? | Buy / Hold / Sell semantics | Levels, sizing, execution |
|---|---|---|---|---|---|
| Bull / Bear Researcher | 4 analyst reports (or "absent" markers), debate history, last opponent argument | Prose argument appended to debate state | Free text | Argue for / against "investing in the stock / asset" | None |
| Research Manager | Debate history | `ResearchPlan`: `recommendation` (5-tier), `rationale`, `strategic_actions` | **Typed recommendation**, text rest | Buy "take or grow", Overweight "gradually increase", Hold "maintain", Underweight "trim", Sell "exit or avoid" | "Sizing guidance relative to a standard allocation" in prose |
| Trader | Investment plan, market report (for grounding), portfolio context | `TraderProposal`: `action` Buy/Hold/Sell; `entry_price` float?; `stop_loss` float?; `position_sizing` text? | **Partly typed** | Overweight → Buy, Underweight → Sell | Entry and stop as floats (percentages and ranges dropped); **no take-profit**; sizing is text; rendered with `FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**` |
| Risk debaters | Trader plan, 4 reports, portfolio, histories | Prose | Free text | Argue risk appetite | Mention volatility and stops in prose only |
| Portfolio Manager | Risk debate, research plan, trader plan, past lessons, portfolio | `PortfolioDecision`: `rating` 5-tier; `executive_summary`; `investment_thesis`; `price_target` float?; `time_horizon` text? | **Typed rating** (the run's `final_rating`); free-text fallback read by `parse_rating`, else **REVIEW** | Position management: "Sell: exit position or avoid entry" | Price target float; nothing typed for entry, stop or size |

**Findings.**
- **Sell means "exit or avoid", never "open a short".** No prompt or schema defines a short entry.
- **Entry, stop and target are LLM floats, typed as numbers but advisory and incomplete.** The
  Trader has entry and stop; the PM has a target. There is no single object holding all three.
- **Sizing** exists only as prose (`position_sizing`, "strategic actions").
- **No execution assumptions** exist. `backtest.py` explicitly refuses to invent quantities, fill
  prices or a cash ledger.
- The final output is a **rating**, not a trade.

---

## 10. Risk knowledge

**A. LLM risk reasoning (exists).**
- The three risk debaters argue appetite: upside versus capital protection and volatility.
- The market-analyst prompt advises "ATR … set stop-loss levels and adjust position sizes".
- The Trader is told to ground stop-loss "in … ATR / support-resistance".
- The PM summary is asked for "key risk levels".
- None of this is enforced.

**B. Deterministic hard risk controls.**

| Control | Status |
|---|---|
| Max position size | **Missing** |
| Stop-loss rules (presence, side, distance) | **Missing** (the stop is optional and unchecked) |
| Drawdown | **Missing** (zero hits) |
| Max daily loss | **Missing** |
| Volatility controls | **Missing** (ATR is displayed only) |
| Spread / slippage | **Missing** (zero hits) |
| Stale data | **Exists for data**: OHLCV staleness guard (K3), news coverage gaps, withheld live-only data (K67). Not a trading control |
| Exposure / correlation | **Missing** |
| Open-position limits | **Missing** (portfolio context is informational) |
| Circuit breaker | **Missing** |
| News restrictions | **Missing** |
| Cooldown | **Missing** |
| Order validation | **Missing** (no orders) |
| Output validation | **Exists for LLM outputs**: rating parsing with REVIEW fallback (K55); number coercion (K53) |

Conclusion: TradingAgents offers **no** hard risk control. Everything in Foundation §8 is Stellar's
to build, as already planned (Phase 3).

---

## 11. Memory / learning

| Aspect | What exists |
|---|---|
| Memory store | `TradingMemoryLog`: one append-only **markdown** file. Entries are tagged `[date \| ticker \| rating \| pending]`, then `[… \| raw \| alpha \| holding \| resolved:date]` |
| Reflection | `Reflector`: one quick-tier LLM call per settled entry, giving 2–4 sentences that name the alpha, the part of the thesis supported or undercut, and one lesson |
| Prior-trade review | Rating-level only: raw return and alpha over `holding_period_days` (default 5) daily closes vs a regional benchmark. There are no trades to review |
| Retrieval | `get_past_context`: last 5 same-ticker entries in full plus 3 cross-ticker reflections, injected into the **Portfolio Manager** prompt only |
| Point-in-time learning | Yes. A historical run sees only lessons whose `resolved` date is on or before its date (#1251) |
| Embeddings / vector memory | **None** |
| Failed decisions stored | Every decision is stored, whatever the outcome. REVIEW decisions are stored and excluded from scoring |
| Knowledge change over time | Only through accumulated prose reflections |
| Rule promotion, hypotheses, candidate rules | **None.** Nothing turns a lesson into a rule, tests a hypothesis or tracks a candidate |

**Compared with the future Stellar Research Lab concept** (reported, not designed): the base
provides an outcome-to-lesson loop in prose with correct point-in-time hygiene. It provides no
structured hypothesis store, no statistical test of a lesson, no promotion path from observation to
rule, and no trade-level attribution. Foundation D-10 keeps the upstream memory log optional.

---

## 12. Backtesting / simulation

| Item | What exists |
|---|---|
| Backtesting | `backtest.run_backtest`: runs the full LLM graph on a ticker × date grid, each cell independent, into a separate memory log; then settles |
| Historical replay | Re-runs, not replays. LLM calls are made again (no cassette), and news and social feeds are not archived, so results are "indicative rather than repeatable" (its own words) |
| Simulated execution | **None, by design** ("must not grow one") |
| Benchmark comparison | Alpha vs the benchmark map (SPY default) |
| Settlement | `fetch_returns`: close at entry vs close `holding_days` sessions later; the benchmark valued as-of the same dates |
| Performance metrics | `summarize`: per rating, count, directional hit rate and mean alpha, accurate to 0.1 percentage point (rounded storage) |
| P/L | Percentage returns only; no currency P&L, costs, stops or equity curve |

**Suitability:**
- **Intraday:** no (daily closes).
- **Forex:** no (alpha vs SPY; 2-dp prices).
- **Gold:** no (the future proxy).
- **Indices:** partly, for the cash index at daily resolution.
- **Paper trading:** no (no orders, fills or ledger).

It remains a useful model for **evaluating decision quality by rating**. Stellar replaces it with
event-driven simulation (Foundation §4.17, U27).

---

## 13. Data provider inventory

| Provider | Module | Asset classes | OHLCV | Intraday | News | Fundamentals | Limits / assumptions | Stellar |
|---|---|---|---|---|---|---|---|---|
| **Yahoo Finance** (`yfinance`) | `dataflows/vendors/yahoo/` | Equities, ETFs, indices, futures, `=X` FX, crypto | Daily (5-year cache) | **Not used** (no `interval` argument) | Ticker news, search news | Profile, statements, insider | Unofficial API; rate limits with backoff; adjusted prices; proxies for gold/indices; 2-dp text rounding; FX volume 0 | **IGNORE for levels; optional for analysis-only proxy data, flagged `proxy=true`** (Foundation §4.2) |
| **Alpha Vantage** | `vendors/alpha_vantage/` | Equities (used); the API has FX/commodity endpoints the code does not call | Daily equity series | No | News and sentiment | Overview, statements, insider | `ALPHA_VANTAGE_API_KEY`; free tier limits; indicators daily | **IGNORE** in V1 (D-1 still open) |
| **FRED** | `vendors/fred.py` | US macro | — | — | — | — | `FRED_API_KEY`; point-in-time vintages; US series | **WRAP** as a candidate R2/R5 source (subject to owner approval, D-2/D-5) |
| **Polymarket** | `vendors/polymarket.py` | Event contracts | — | — | — | — | Keyless; live only; withheld historically | **IGNORE** in V1 (not replayable) |
| **SEC EDGAR** | `vendors/sec_edgar.py` | US filers | — | — | — | As-filed statements | Keyless; User-Agent required | **IGNORE** in V1; possible R6 source later |
| **StockTwits** | `vendors/stocktwits.py` | Equities, crypto | — | — | Social | — | Keyless; recent only | **IGNORE** |
| **Reddit** | `vendors/reddit.py` | Equities | — | — | Social | — | Public RSS; rate limits | **IGNORE** |
| **TypeSafe Jev** | `agents/post_screen.py` | Post screening | — | — | — | — | `TYPESAFE_API_KEY` | **IGNORE** |

None of these providers supplies intraday spot FX or metal bid/ask quotes, a CFD series for NAS100,
an economic calendar with consensus, or central-bank publications. Those remain Stellar decisions
(Foundation D-1 to D-6).

---

## 14. Hidden knowledge findings

Meaningful hits from the keyword sweep; zero-hit terms are listed at the end.

| Term(s) | Meaningful hits | Finding |
|---|---|---|
| support, resistance, breakout, reversal, divergence, overbought, crossover, golden | market-analyst prompt; indicator description dicts (Yahoo and AV); trader prompt; snapshot footer | Technical interpretation exists **only as advice text** duplicated in three places |
| RSI, MACD, ATR, EMA, SMA, Bollinger, VWMA | `yahoo/market.py`, `snapshot.py`, `alpha_vantage/indicator.py`, market-analyst prompt | Names are whitelisted; formulas live in `stockstats` (§5) |
| mfi, stochrsi | `yahoo/market.py` (MFI description and whitelist); market-analyst prompt (stochrsi as an example) | MFI is callable but not advertised; stochrsi is advertised as a name to avoid, but is not callable |
| volatility, momentum | prompts and descriptions | No volatility or momentum *assessment* code |
| stop, entry, target | `schemas.py` (`entry_price`, `stop_loss`, `price_target`); trader prompt; `_coerce_optional_float` | Advisory floats; percentages and ranges discarded |
| position siz(ing) | `schemas.py` (`position_sizing: str`), trader prompt, ATR description | Prose only |
| short | `portfolio.py` ("negative is short") | The only notion of a short position |
| sell, buy | `rating.py`, `schemas.py`, prompts | Position-management vocabulary |
| probability | Polymarket vendor and tool | External market-implied odds |
| seasonal | FRED seasonal-adjustment label | Not seasonality analysis |
| spread | FRED `T10Y2Y` "10y_2y_spread" alias | Yield-curve spread, not bid/ask |
| session | Yahoo cache and settlement comments | Trading-day sessions, not FX sessions |
| intraday, market hours | `ohlcv.py` comments on Yahoo's partial daily candle | The only intraday awareness |
| candle | `ohlcv.py` comment | No candle logic |
| forex, gold, index | `symbols.py` aliases; descriptions | Symbol mapping only |
| leverage | bull/bear prompts ("leverage the provided research") | Not financial leverage |
| pattern | `context.py` comment on the model "pattern-matching the price action to a narrative" | A documented failure mode (#814), not a capability |
| correlation, drawdown, slippage, pullback, engulf, doji, wick, inside/outside bar, higher high, market structure, VWAP, take-profit | — | **Zero hits** |

**Biggest hidden discoveries.**
1. **Precision loss for FX.**
   - `get_YFin_data_online` rounds Open/High/Low/Close to 2 decimals.
   - The verified snapshot formats every float, prices and indicators alike, to 2 decimals.
   - EUR/USD 1.08537 becomes 1.09, and a daily EUR/USD ATR of about 0.006 becomes 0.01.
2. **Silent instrument substitution.**
   - `XAUUSD`, `XAU` and `GOLD` all become the COMEX future `GC=F`.
   - `NAS100`, `US100` and `USTEC` become the cash index `^NDX`.
   - This happens in every Yahoo path, including news and settlement.
3. **Indicator warm-up is never blanked**, and VWMA is typical-price-weighted, contrary to its
   description. No test pins any indicator value.
4. **The verified-snapshot pattern (#830)** already implements "LLMs cite only computed values".
   This is a direct precedent for Stellar's T8 rule.
5. **Point-in-time machinery is mature:**
   - FRED vintage pinning via ALFRED;
   - look-ahead-safe news and social windows;
   - withholding live-only profiles, undated statements and undisclosed insider trades;
   - SEC EDGAR as-filed statements with restatement vintages;
   - memory lessons filtered by resolution date.
6. **The Trader's number coercion** silently turns "15%", "150-160" or "around 150" into *no
   value*. This is safe for advisory levels, and hidden if anyone treats them as authoritative.
7. **`stockstats` already computes dozens more indicators**, including ADX/DMI, Supertrend,
   Ichimoku, KDJ, CCI, Williams %R, Aroon, KAMA, TRIX and PPO. They are unreachable because of the
   13-name whitelist. This is a library capability, not a repository one, and needs the same
   warm-up scrutiny.

---

## 15. Reuse matrix

KEEP = use as-is (or its pattern as-is) · WRAP = call it behind a Stellar interface · ADAPT = take
the design, change behaviour · REPLACE = Stellar builds its own · NOT USED.

| Component | Files | Decision | Why | What Stellar changes | Expected value |
|---|---|---|---|---|---|
| Downstream decision agents (Bull, Bear, Research Manager, Trader, risk debaters, Portfolio Manager) | `agents/researchers/`, `managers/`, `trader/`, `risk_mgmt/` | **KEEP** (imported unchanged, Foundation D1 / C12) | Mature debate and synthesis | Stellar supplies the reports; the PM rating is read as approval strength (R-1); the Trader's levels stay advisory | High |
| Debate orchestration | `graph/conditional_logic.py`, `graph/setup.py` path maps | **KEEP** | Deterministic and tested | Composed inside the Stellar graph | Medium |
| Rating vocabulary, parser, REVIEW | `agents/rating.py` | **KEEP** | Exactly what R-1 needs; pinned by a Stellar contract test | — | High |
| Structured output helpers | `agents/structured.py`, `agents/schemas.py` | **KEEP** (pattern and schemas as read) | Typed rating with safe fallback | Stellar parses `TraderProposal` into advisory levels only | High |
| Number coercion | `schemas.py::_coerce_optional_float` | **KEEP** (pattern) | Correct handling of LLM numbers | Record *why* a value was dropped (for P2) | Medium |
| Anti-fabrication helpers and sentinels | `agents/context.py`, `dataflows/router.py` | **KEEP** (pattern) | Proven against hallucinated data | Use in Stellar prompts and research tools | High |
| Point-in-time rules | `dataflows/date_window.py` | **ADAPT** | Same rules at timestamp resolution, not days | Re-implemented on `as_of` timestamps (Foundation §4.1) | High |
| Verified market snapshot | `vendors/yahoo/snapshot.py` | **ADAPT** | The pattern Stellar's T8 needs | Built from Stellar's `MarketSnapshot`; per-instrument precision; no 2-dp formatting | High |
| Indicator engine | `vendors/yahoo/market.py` + `stockstats` | **WRAP** (or reimplement) | Correct Wilder RSI/ATR, MACD, Bollinger | Stellar-owned input frames; explicit warm-up blanking; value tests; per-instrument precision; no volume indicators for FX/metal | Medium–High |
| OHLCV retrieval and cache | `vendors/yahoo/ohlcv.py`, `market.py` | **REPLACE** | Daily, proxied, rounded | `MarketDataSource` (Foundation §4.1); keep the staleness and unsettled-bar ideas | Low as code, medium as ideas |
| Symbol normalisation | `dataflows/symbols.py` | **REPLACE** | Silent proxying | Stellar symbol map with `proxy=true` flags (Foundation §4.2) | Low (idea only) |
| Vendor router pattern | `dataflows/router.py`, `errors.py` | **ADAPT** | Explicit chains, typed failures | Stellar provider registry | Medium |
| FRED vendor | `vendors/fred.py` | **WRAP** (if approved as a source) | Point-in-time US macro | Add ECB/BoJ/JGB series ids or other sources; typed `ResearchItem` output instead of markdown | Medium |
| News vendors | `vendors/yahoo/news.py`, `alpha_vantage/news.py` | **ADAPT** or **NOT USED** | Not archived; ticker-centric | Only via Stellar's allowlist and validation (V1–V4) | Low–medium |
| Polymarket | `vendors/polymarket.py` | **NOT USED** (V1) | Not replayable | — | Low |
| Market analyst | `analysts/market_analyst.py` | **REPLACE** | LLM-only technicals | T2–T8 deterministic agents plus T8 report | — |
| News analyst | `analysts/news_analyst.py` | **REPLACE** | Unstructured research | R/V/M/S chain | — |
| Sentiment, fundamentals analysts; StockTwits, Reddit, Jev, SEC EDGAR, insider | respective files | **NOT USED** | Stock-specific | EDGAR possibly for R6 later | — |
| Instrument context | `agents/context.py` | **ADAPT** | Identity prompt pattern | Instrument, not company | Medium |
| Portfolio context | `tradingagents/portfolio.py` | **ADAPT** | Book-in-prompt pattern | Fed from the Paper Broker account; lots and per-position stops | Medium |
| Memory log and reflection | `memory/log.py`, `memory/reflection.py` | **NOT USED** in V1 (D-10) / **ADAPT** later | Prose lessons, rating-level | L1 narrative mode may reuse the Reflector (U18) | Low–medium |
| Settlement | `memory/settlement.py` | **NOT USED** | Rating-vs-benchmark over daily closes | Stellar settles real paper trades | Low |
| Backtest | `tradingagents/backtest.py` | **NOT USED** (replaced, U27) | Evaluates ratings, not trades | Stellar simulation (Foundation §4.17) | Low (the summary idea is useful) |
| Checkpointing | `graph/checkpointer.py` | **KEEP** (via C3) | Resume long runs | — | Medium |
| LLM clients | `llm_clients/` | **KEEP** | Provider-agnostic, matches owner Q4 | Tier mapping | High |
| CLI, reporting | `cli/`, `reporting.py` | **NOT USED** | Stellar has its own entry points and journal | — | — |

---

## 16. Gap analysis for Stellar

Nothing below is filled here. "Base provides" states what TradingAgents contributes.

| Gap | Base provides | Status |
|---|---|---|
| Serious candle analysis (body, wicks, direction, named patterns, sequences) | Nothing | **Missing** |
| Price action (rejection, impulse vs consolidation, break/retest) | Prompt words only | **Missing** |
| Market structure (swing highs/lows, HH/HL/LH/LL, trend state, key levels) | Nothing; S/R is LLM prose | **Missing** |
| Multi-timeframe analysis | Nothing (daily only) | **Missing** |
| Pullback analysis | Nothing | **Missing** |
| Chart-shape / pattern discovery | Nothing | **Missing** |
| Seasonality | Nothing | **Missing** |
| Probability / statistical pattern testing | Rating hit rate and mean alpha only | **Missing** |
| Cross-market relationships (correlation, USD-leg exposure, relative strength) | Benchmark alpha after the fact | **Missing** |
| Market-specific macro intelligence | US FRED series; generic news queries | **Partial** (US macro data only) |
| XAU/USD knowledge (spot source, real yields, USD, sessions, precision) | Future proxy; FRED US yields, breakeven, dollar index | **Mostly missing** |
| EUR/USD knowledge (ECB and Fed, EU–US spread, 5-dp precision) | FRED US side only; news query mentions ECB | **Mostly missing** |
| USD/JPY knowledge (BoJ, US–JP spread, intervention, Tokyo session) | FRED US side only; news query mentions BoJ | **Mostly missing** |
| NAS100 knowledge (CFD series, extended hours, constituent earnings) | Cash-index proxy; SEC EDGAR / fundamentals for single issuers | **Partial** (constituent data possible later) |
| Intraday data, quotes, spread | Nothing | **Missing** |
| Sessions and calendars | Nothing | **Missing** |
| Economic calendar and central-bank feeds | Nothing | **Missing** |
| Deterministic risk, sizing, execution | Nothing | **Missing** (Stellar Phases 3–4) |
| Trade-level review and attribution | Rating-level settlement and prose lessons | **Partial** |

---

## 17. Recommendations: what NOT to rebuild

1. **Do not rebuild the debate and decision agents.** Import Bull, Bear, Research Manager,
   Trader, the risk debaters and the Portfolio Manager unchanged (already decided, D1).
2. **Do not rebuild rating handling.** Use `RATINGS_5_TIER`, `RATING_REVIEW`, `parse_rating` and
   `is_review` (pinned by Stellar's contract test).
3. **Do not rebuild structured-output-with-fallback or LLM number coercion.** Reuse
   `structured.py` and the `_coerce_optional_float` rules when parsing advisory levels.
4. **Do not re-derive the point-in-time rules.** Port the rules in `date_window.py` and the FRED
   vintage pin to timestamp resolution, and keep their test ideas (look-ahead, coverage gap,
   withholding).
5. **Do not re-invent the verified-snapshot discipline.** Adapt it for T8, with per-instrument
   precision.
6. **Do not rewrite standard indicator maths from scratch without reason.** `stockstats` already
   implements Wilder RSI/ATR, MACD and Bollinger correctly. Either wrap it behind Stellar's
   indicator spec with warm-up blanking and value tests, or reimplement with the same formulas and
   pin them against it.
7. **Do not rebuild vendor-failure semantics.** Reuse the typed error classes and the "no data /
   unavailable" sentinel idea.
8. **Do not rebuild the LLM provider layer or checkpointing.** Use `llm_clients/` and the
   checkpointer through C1/C3.
9. **Do not reuse, and do not try to fix inside upstream:**
   - `normalize_symbol` proxies for execution levels;
   - 2-dp price rounding;
   - volume indicators for FX/metal;
   - `backtest.py` as a simulator;
   - the market and news analysts as Stellar's technical or research layer.

   Stellar replaces these in its own layer; upstream stays untouched.
10. **Build fresh** (nothing to reuse): candle / price-action / structure / pullback / entry-timing
    logic; sessions; multi-timeframe; correlation and exposure; seasonality and statistical
    testing; the economic calendar and central-bank feeds; hard risk; execution; trade-level
    review.
