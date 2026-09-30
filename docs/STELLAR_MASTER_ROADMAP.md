# Stellar Agents — Master Roadmap

| | |
|---|---|
| **Status** | v1.0 — Phase 0 documentation. No code yet. |
| **Date** | 2026-09-30 |
| **Owner** | Project owner (single user, V1) |
| **Built on** | Tauric Research TradingAgents v0.5.2 (upstream, untouched) |
| **Not a claim of** | Profitability. Nothing in this roadmap assumes or promises that any strategy makes money. |

---

## Document map and precedence

Stellar Agents has three documents. This roadmap is the overview; it does not add design.

| Document | Role | Precedence |
|---|---|---|
| `docs/STELLAR_MASTER_ROADMAP.md` (this file) | Vision, scope, milestones, phase overview, decision log | Summary. Where it is less precise than the two below, they govern |
| `docs/STELLAR_FOUNDATION_PLAN.md` (v0.3, approved) | Canonical build plan: reuse map, rosters, contracts, risk foundation, phases, open decisions | **Canonical** for phases, rosters, contracts and decisions (its §13.1 reconciliations are approved, D-16) |
| `docs/STELLAR_LAYER_DESIGN.md` (v0.4, reconciled) | Architecture and visual-station detail: layers, integration points, rooms, per-agent visuals, events, metrics | Architecture reference, reconciled with the Foundation Plan |

If any conflict is found between them, the Foundation Plan governs and the conflict is fixed in a
documentation-only change.

---

## 1. Vision

Stellar Agents is a **multi-agent trading research and paper-trading system** presented as an
**intergalactic trading station**. Specialised agents research markets, validate sources, analyse
macro causes and price structure, debate, and propose trades. **Deterministic code**, not language
models, decides whether any trade may happen. Every agent's real runtime state is visible in a
living spaceship interior where agents work, meet, rest and move between rooms.

The goals, in order:

1. **Safe:** no order without deterministic risk approval; no live-money trading; fail closed.
2. **Honest:** every decision traceable to its data, research and reasoning; no profitability
   assumed; every metric shown with its sample size.
3. **Observable:** every agent's work visible through telemetry, in logs first and in the station
   later.
4. **Extensible:** new markets, research roles and strategies added behind fixed interfaces.

---

## 2. Three sources, never merged

| Source | What it is | How it is used |
|---|---|---|
| **UPSTREAM — TradingAgents** | Tauric Research's multi-agent LLM trading framework, v0.5.2 | The technical foundation. Its debate, research-manager, trader, risk-debate and portfolio-manager agents, rating vocabulary, LLM provider layer and state model are **reused unchanged**. Its files are **never modified**. Its stock-oriented data providers and analysts are **not used** for Stellar's markets |
| **ARIA — ARIA Gold V2 concepts** | The owner's earlier experimental XAU/USD prototype | **Inspiration only.** Useful ideas (timeframe modes, sessions, EMA/RSI/MACD/ATR, candle patterns, pullbacks, stop/target, reward:risk, news proximity, WAIT/WATCH/TRADE IDEA states, lot calculator, journal) are classified and redesigned. **No ARIA formula, threshold or code is carried over as truth** |
| **STELLAR** | Everything new | Research chain, validation, market data, technical analysis, deterministic risk, paper broker, telemetry, journal, replay, station UI, and the future MT5 bridge |

Details: Foundation Plan §1 (upstream reuse map), §2 (upstream limits), §3 (ARIA classification).

---

## 3. Non-negotiable principles

1. **Upstream stays untouched.** Stellar imports TradingAgents; TradingAgents never imports Stellar.
2. **LLMs propose, code decides.** No LLM output can size, approve or send an order.
3. **Fail closed.** Missing data, configuration, calendar, quote or account state → no trade.
4. **Paper V1 first.** V1 is functionally complete with paper trading (D-15).
5. **Demo before anything else.** The MT5 / Vantage demo is a separate gate after a stable paper V1.
6. **No live trading in V1**, and no live mode exists in the code. Live trading would need a
   separate owner decision and a new design review.
7. **No profitability assumption.** V1 and the demo gate are about completeness, safety and
   observability, never about returns.
8. **Only the owner resets the circuit breaker**, with a local owner command. Agents can stop
   trading; they can never restart it.
9. **Visuals never lie and never control.** The station only consumes events; it cannot change
   risk, place orders or reset the breaker.
10. **Model-provider agnostic.** Cheaper, faster models for routine roles; stronger models for
    manager and high-value reasoning roles; all configurable.

---

## 4. First markets

| Market | Asset class | Notes |
|---|---|---|
| **XAU/USD** | Spot gold vs USD | Drivers include USD, real yields, Fed, geopolitics |
| **EUR/USD** | FX major | ECB vs Fed, rate differentials, euro-area and US data |
| **USD/JPY** | FX major | BoJ vs Fed, US–JP yields, intervention risk |
| **NAS100** | Index CFD | Fed, US data, earnings of the largest constituents, session gaps |

Upstream's stock data, fundamentals and SEC tools do not apply. Upstream maps these symbols to
proxies (a gold future, the cash index) that must never be used for order levels. Stellar owns
its market-data layer. Details: Foundation Plan §6; layer design §1.6.

---

## 5. The pipeline

```
Research ─> Source Validation ─> Macro/Causal Analysis ─> Market Specialists ─> Technical Analysis
                                                                                        │
      Memory/Attribution <─ Post-Trade Review <─ Execution <─ Deterministic Risk <─ Trader <─ Debate
```

- Market data feeds the chain in parallel as a validated, time-stamped snapshot.
- **Setup-first:** deterministic technical agents find a directional setup first. The research
  chain, debate and Portfolio Manager then judge **that setup**, and the PM's rating is read as its
  approval strength (canonical decision R-1). The expensive LLM chain runs only when there is a
  setup to judge.
- Every boundary that feeds a decision or an order is **typed**; free text lives only in
  narratives and the debate.
- Every record links to its parents, so any trade is traceable to the exact market data, research
  and reports behind it.

Details: Foundation Plan §4.29, §9.

---

## 6. The agents

Codes follow the Foundation Plan §5.1 architectural roster (41 roles). Not every role runs on every
decision; the minimum executable V1 roster is Foundation Plan §5.2.

| Area | Roles | V1 |
|---|---|---|
| **Specialised research** | R1 Central Bank, R2 Economic Data, R3 Market News, R4 Geopolitical, R5 Rates/Bonds, R6 Corporate/Earnings | R1, R2 (R3–R6 deferred until sources are chosen) |
| **Source validation** | V1 Source Validator, V2 Freshness Checker, V3 Duplicate Detector, V4 Fact vs Reaction vs Interpretation Classifier | All |
| **Macro / causal analysis** | M1 Causal/Macro Analyst | Yes |
| **Market specialists** | S1 XAU/USD, S2 EUR/USD, S3 USD/JPY, S4 NAS100 | Yes (only the focus instrument's runs per cycle) |
| **Technical, candle and pullback** | T1 Data Validator, T2 Market Session, T3 Market Structure (higher-timeframe bias), T4 Technical Indicator (momentum), T5 Candle/Price Action, T6 Pullback/Setup, T7 Entry Timing, T8 Technical Analyst | All |
| **Debate and research roles (upstream)** | U1 Bull, U2 Bear, U3 Research Manager, U5–U7 Aggressive/Conservative/Neutral Risk Debaters | All (reused unchanged; risk debate is advisory) |
| **Trader and Portfolio Manager (upstream)** | U4 Trader (levels advisory), U8 Portfolio Manager (typed rating) | Both |
| **Proposal and deterministic risk** | P1 Trade Proposal Builder, P2 Contradiction Checker, P3 Risk Engine (Risk Auditor) | All |
| **Execution** | P4 Execution Checker, E1 Paper Execution Agent (Paper Broker), E2 MT5 Execution Agent | P4, E1 (E2 at the demo gate) |
| **Review and learning** | L1 Post-Trade Reviewer, L2 Performance/Attribution | Both (basic; LLM narrative and statistical attribution later) |
| **Supervision and wellbeing** | O1 Supervisor, O2 Operational Wellbeing Monitor | Both (minimal) |
| **Station personas (visual only)** | Station Medic, Quartermaster (personas of O2), Café Host (cosmetic), Vault personas of P3 | Station milestones only |

**Wellbeing** means operational health made visible: latency, retries, rate limits, errors and
budgets. It can pause or slow work; it can never change a trading decision.

---

## 7. Deterministic risk

All controls are deterministic, configurable, and fail closed. **No numeric thresholds are chosen
yet**; values are proposed from simulation evidence and approved by the owner (Foundation §8,
D-12).

- Malformed proposal/order rejection; required stop-loss; minimum reward:risk
- Max risk per trade; max position size; max open positions; correlated exposure
- Max daily loss and max drawdown (trip the breaker)
- Max spread; stale-quote rejection; slippage tolerance
- Duplicate-order prevention; cooldowns; proposal expiry
- News/event restrictions (no calendar → no new entries)
- Circuit breaker with **owner-only reset** (local owner command; the UI is read-only)
- DEMO_ONLY execution modes: `PAPER` and `DEMO` only; no `LIVE`

No LLM holds a reference to the risk engine, the broker, the journal writer or configuration, and
an order intent can only be created from an approved risk decision.

---

## 8. Execution path

| Stage | What | When |
|---|---|---|
| **Paper Broker** | Simulated fills from quotes, documented stop/target rules, spread and slippage models | V1 (Foundation Phase 4 onward) |
| **Execution Checker** | Pre-flight (mode, market open, spread, quote age, idempotency) and reconciliation | V1 |
| **MT5 / Vantage demo bridge** | A dedicated service on a separate Windows machine or VPS (host not chosen yet), narrow API, demo guard checked twice, reconciliation | **After** V1, as a separate integration and validation gate (Foundation Phase 8) |
| **Live trading** | — | **Not planned.** Requires a separate owner decision and a new design review |

Stellar itself runs on the owner's Mac in V1.

---

## 9. Learning, attribution and reputation

- **Post-Trade Review:** every closed trade gets a typed review: outcome, R multiple, MAE/MFE,
  exit reason, which setup, price-action and momentum features were present, how close risk checks
  were to their limits, and research coverage at decision time.
- **Performance attribution:** links each trade to its research, assessments, ratings and risk
  checks. Per-agent statistics are shown only with sample sizes and hidden below a minimum.
- **Reward / reputation — idea, not yet designed.** The station may show an agent's *reputation*:
  its measured calibration and contribution (layer design §6.3), for example on the lounge's "hall
  of fame". Guardrails that any future design must keep:
  - reputation is **derived from recorded outcomes with sample sizes**, never self-reported;
  - reputation **never** changes risk limits or lets any agent bypass a check;
  - in V1, reputation **does not** change how much any agent's output counts in a decision;
  - using reputation to weight agents would be a new design decision, requiring evidence from
    simulation (Foundation Phase 7) and owner approval.

---

## 10. Telemetry and event bus

- One event envelope (id, sequence, time, run, agent, room, instrument, correlation id, payload),
  an in-process bus, and an append-only store with the journal.
- Naming convention: `<domain>.<entity>.<past-tense verb>` (canonical decision R-3), for example
  `agent.state.changed`, `research.item.accepted`, `trade.proposed`, `risk.rejected`,
  `circuit_breaker.tripped`.
- Emitted from Foundation Phase 1 onward, so replay and metrics exist from the first run.
- Replay: deterministic stages recompute identically; LLM stages replay from recorded outputs.
- Telemetry failure never blocks a run; journal failure for decision or order records halts
  execution.

Details: Foundation Plan §10; layer design §4.

---

## 11. The station

> **Topology superseded (visual layer only).** The station map, rooms, lifts, vault and airlock described in this section belong to the earlier stacked-deck concept. The owner-approved physical topology is `docs/STELLAR_MASTER_FLOOR_PLAN_V1.md` **revision C** (a flat vessel with 3 hubs, L1–L10, R1–R6 and 21 explicit doors), detailed in the Visual Foundation v2 registries (`STELLAR_STATION_TOPOLOGY.md`, `STELLAR_ROOM_REGISTRY.md`, `STELLAR_CHARACTER_REGISTRY.md`, `STELLAR_SCREEN_REGISTRY.md`, `STELLAR_ASSET_REGISTRY.md`). Risk isolation is now a logical access rule (Risk Control Room L10, Execution Bay L9), not a vault, lift or airlock. The engine's rules (risk gate before execution; the UI never writes) are unchanged.

**Art direction:** a futuristic spaceship / trading-station interior, semi-realistic stylized
sci-fi, **not pixel art**: large screens, command rooms, corridors, analysis stations, risk
control, execution bay, lounge, café, billiard room and wellbeing areas.

**The floor plan is the control flow.** The only agent door into the Execution Bay is the one-way
airlock from the Risk Control Vault, just as no order can skip the risk engine.

| Room | Who works there |
|---|---|
| Main Command Deck | Portfolio Manager, Research Manager, Trader, Trade Proposal Builder, Supervisor |
| Market Analysis Wing | Technical agents T2–T8; instrument desks for the four market specialists |
| Macro & News Observatory | Research roles R1–R6; Causal/Macro Analyst |
| Debate Chamber | Bull and Bear (inner ring); three Risk Debaters (outer ring) |
| Risk Control Vault | Contradiction Checker; Risk Engine (with its Vault personas) |
| Execution Bay | Execution Checker; Paper Execution Agent (MT5 later) |
| Data Core | Data Validator; research validators; telemetry bus and event store |
| Memory Archive | Post-Trade Reviewer; Performance/Attribution |
| Wellbeing Room | Operational Wellbeing Monitor (Medic and Quartermaster personas); resting agents |
| Lounge / Café / Billiard Room | Off-duty agents; Café Host (cosmetic) |

**Movement follows real runtime state.** Every avatar's status badge updates the moment its event
arrives; walking animation follows and never delays the truth. Agents walk to podiums when they
debate, carry reports to the next room, rest in the Wellbeing Room when overloaded, and relax in the
lounge when off duty. Idle life is seeded and deterministic, so replays look identical. Details:
layer design §2, §5.

---

## 12. Milestones

| Milestone | Meaning | Reached at |
|---|---|---|
| **Foundation approved** | Documentation complete and consistent | Phase 0 exit |
| **Stellar Agents V1 (paper)** | All Foundation §12 criteria met on paper: four markets, research chain with coverage, technical chain, typed boundaries, deterministic risk, paper execution, journal, telemetry, replay, tests, clean upstream separation. **Not** a profitability claim | Phase 7 exit |
| **MT5 / Vantage demo gate** | Demo integration validated: clean reconciliation, zero demo-guard bypasses | Phase 8 exit |
| **Station V1** | Read-only visual station, truthful at every moment | Phase 9 exit |
| **Station V2** | Movement, life, lounge, wellbeing visuals | Phase 10 exit |
| **Long-duration demo validation** | Stability, risk behaviour and cost observed over a period the owner sets | Phase 11 exit |

---

## 13. Phased implementation roadmap

Canonical phases and gates: Foundation Plan §11.

| Phase | Name | Objective | Gate (summary) |
|---|---|---|---|
| **0** | Foundation documentation | Master Roadmap, Foundation Plan, reconciled layer design | Owner approval; documents consistent |
| **1** | Stellar package, contracts, config, telemetry core | Separate `stellar/` project; all typed schemas; config; event bus and journal; agent registry with the whole roster; upstream contract tests | Installs on the Mac; upstream tests untouched and passing |
| **2** | Market data and the four instruments | Market-data abstraction, file importer, symbol map, timeframes, validated snapshots, sessions | Reproducible snapshots; no look-ahead |
| **3** | Deterministic Risk Engine | Every control, breaker, owner reset command, DEMO_ONLY modes | Full rule coverage; zero approvals on bad input |
| **4** | Paper Broker and execution | Broker interface, Paper Broker, Execution Checker, settlement, post-trade review | Synthetic trades flow end to end and replay |
| **5** | Deterministic technical foundation | Structure, momentum, candle/price action, pullback/setup, entry timing, proposal builder (rules only) | First strategy family runs deterministically on paper |
| **6** | Research pipeline and LLM integration | Research chain (R1, R2, validators, macro, specialists); Stellar graph reusing upstream agents; recorded LLM outputs; cost/latency measured per profile | Full chain on paper; no proposal from free text |
| **7** | Simulation, backtesting, attribution | Simulator; metrics; profile comparison; risk-threshold evidence | Reproducible reports; **V1 (paper) reached** |
| **8** | MT5 / Vantage demo gate | Windows bridge, MT5 data and execution, demo guard, reconciliation | Clean demo reconciliation for the agreed period |
| **9** | Visual station V1 | Read-only localhost station | Truthful live view matching the event log |
| **10** | Animated station | Movement, life, lounge, wellbeing, personas | UI off → trading unchanged |
| **11** | Long-duration demo validation | Extended demo operation | Owner review; profitability reported, never assumed |

Phase 9 may run in parallel with Phases 7–8 once events exist (after Phase 6).

---

## 14. Decision log

| Ref | Decision | Date |
|---|---|---|
| Q1 | Stellar runs on the owner's Mac; MT5 later on a separate Windows machine/VPS via a bridge; host not chosen yet | 2026-09-29 |
| Q2 | First markets: XAU/USD, EUR/USD, USD/JPY, NAS100 | 2026-09-29 |
| Q3 | Stellar-owned market-data abstraction; MT5 a future data source; data separate from execution | 2026-09-29 |
| Q4 | Model-provider agnostic; tiered models; models and budget configurable | 2026-09-29 |
| Q5 | No hard-coded risk numbers; validate thresholds first | 2026-09-29 |
| Q6 | Only the owner resets the circuit breaker | 2026-09-29 |
| Q7 | Semi-realistic stylized sci-fi interior; not pixel art | 2026-09-29 |
| Q8 | V1 single-user, local only; remote viewing not built | 2026-09-29 |
| D1 | Stellar-owned data adapters and market/technical analysts for the four markets; upstream data code untouched; downstream upstream agents reused | 2026-09-29 |
| D-15 | V1 = paper; MT5/Vantage demo is a separate gate after a stable paper V1; no profitability implied | 2026-09-29 |
| D-16 | Foundation Plan §13.1 reconciliations R-1 to R-6 canonical; layer design reconciled (v0.4) | 2026-09-29 (reconciled 2026-09-30) |
| D-19 | Master Roadmap added to the repository (this file) | 2026-09-30 |
| — | Foundation Plan v0.3 approved | 2026-09-30 |

Canonical reconciliations (Foundation §13.1): **R-1** setup-first rating mapping; **R-2** Foundation
phase numbering; **R-3** `<domain>.<entity>.<past-tense verb>` event names; **R-4** Foundation
rosters, with old layer-design agents mapped to new roles or visual personas; **R-5** local
owner-command breaker reset, UI read-only; **R-6** the research chain.

### Open decisions

Tracked with options, safe defaults and deadlines in Foundation Plan §13.2: D-1 market-data
source, D-2 economic calendar, D-3 news source, D-4 central-bank publications, D-5 rates/bonds data,
D-6 earnings data, D-7 timeframe profile(s) to validate first, D-8 paper account currency and
balance, D-9 Buy vs Overweight sizing, D-10 upstream memory-log use, D-11 LLM tiers and budgets,
D-12 risk threshold values, D-13 research source allowlist, D-14 research cadence, D-17 Windows
host, D-18 demo-validation duration.

The owner's strategy interest, **D1/H4 context → H1/M15 setup → short-term pullback → M5/M1
entry**, is recorded as a **hypothesis to test** (Foundation §7.3), not a validated rule.
