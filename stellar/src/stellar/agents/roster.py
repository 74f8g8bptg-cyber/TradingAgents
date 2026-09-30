"""The architectural roster (Foundation §5.1) as registry data.

Codes, roles, groups, kinds and roster status come from Foundation §5.1–5.3.
Technical ids are the layer design's (§3) and, where the layer design had none
(R*, V*, M1, S*, T*), the ids proposed in the visual world plan §5.3, confirmed
here as Phase 1 (VW-5). Display personas are deliberately absent: they belong to
the UI persona registry and to the owner's local override.

Phase 1 has no agent runtime; ``enabled`` marks roster membership only (minimum
V1 roles on, deferred and demo-gate roles off).
"""

from __future__ import annotations

from stellar.agents.registry import (
    AgentGroup,
    AgentIdentity,
    AgentKind,
    AgentRegistry,
    AgentSource,
    LlmTier,
    RosterStatus,
)

G, K, S, T, R = AgentGroup, AgentKind, AgentSource, LlmTier, RosterStatus


def _agent(code, technical_id, role, group, responsibilities, kind, *, tier=None,
           source=S.STELLAR, status=R.MINIMUM_V1, upstream_node=None) -> AgentIdentity:
    return AgentIdentity(
        code=code,
        technical_id=technical_id,
        role=role,
        group=group,
        responsibilities=responsibilities,
        kind=kind,
        source=source,
        llm_tier=tier,
        roster_status=status,
        enabled=status is R.MINIMUM_V1,
        upstream_node=upstream_node,
    )


ARCHITECTURAL_ROSTER: tuple[AgentIdentity, ...] = (
    # Research (R1–R6)
    _agent("R1", "research_central_bank", "Central Bank Research", G.RESEARCH,
           ("Collect policy decisions, statements, minutes and speeches",), K.HYBRID,
           tier=T.QUICK),
    _agent("R2", "research_economic_data", "Economic Data Research", G.RESEARCH,
           ("Collect scheduled macro releases: actual vs prior (vs consensus if available)",),
           K.DETERMINISTIC),
    _agent("R3", "research_market_news", "Market News Research", G.RESEARCH,
           ("Collect general market and financial news",), K.HYBRID, tier=T.QUICK,
           status=R.DEFERRED),
    _agent("R4", "research_geopolitical", "Geopolitical Research", G.RESEARCH,
           ("Collect conflicts, sanctions, elections and intervention statements",), K.HYBRID,
           tier=T.QUICK, status=R.DEFERRED),
    _agent("R5", "research_rates_bonds", "Rates/Bonds Research", G.RESEARCH,
           ("Collect yields, curve shape, real yields and rate differentials",),
           K.DETERMINISTIC, status=R.DEFERRED),
    _agent("R6", "research_corporate_earnings", "Corporate/Earnings Research", G.RESEARCH,
           ("Collect earnings and guidance of the largest NAS100 constituents",), K.HYBRID,
           tier=T.QUICK, status=R.DEFERRED),
    # Research validation (V1–V4)
    _agent("V1", "source_validator", "Source Validator", G.RESEARCH_VALIDATION,
           ("Check allowlist, trust tier and provenance",), K.DETERMINISTIC),
    _agent("V2", "freshness_checker", "Freshness Checker", G.RESEARCH_VALIDATION,
           ("Enforce no look-ahead and the freshness window",), K.DETERMINISTIC),
    _agent("V3", "duplicate_detector", "Duplicate Detector", G.RESEARCH_VALIDATION,
           ("Cluster exact and near duplicates; keep the primary source",), K.DETERMINISTIC),
    _agent("V4", "claim_classifier", "Fact vs Reaction vs Interpretation Classifier",
           G.RESEARCH_VALIDATION,
           ("Label each claim FACT, REACTION or INTERPRETATION",
            "Cross-check numeric facts against the calendar"), K.HYBRID, tier=T.QUICK),
    # Macro and market-specific analysis
    _agent("M1", "causal_macro_analyst", "Causal / Macro Analyst", G.MACRO_ANALYSIS,
           ("Derive causal drivers from validated research, citing claim ids",), K.LLM,
           tier=T.DEEP),
    _agent("S1", "specialist_xauusd", "XAU/USD Specialist", G.MARKET_ANALYSIS,
           ("Translate macro drivers into XAU/USD pressure and event risk",), K.LLM,
           tier=T.CONFIGURABLE),
    _agent("S2", "specialist_eurusd", "EUR/USD Specialist", G.MARKET_ANALYSIS,
           ("Translate macro drivers into EUR/USD pressure and event risk",), K.LLM,
           tier=T.CONFIGURABLE),
    _agent("S3", "specialist_usdjpy", "USD/JPY Specialist", G.MARKET_ANALYSIS,
           ("Translate macro drivers into USD/JPY pressure and event risk",), K.LLM,
           tier=T.CONFIGURABLE),
    _agent("S4", "specialist_nas100", "NAS100 Specialist", G.MARKET_ANALYSIS,
           ("Translate macro drivers into NAS100 pressure and event risk",), K.LLM,
           tier=T.CONFIGURABLE),
    # Technical (T1–T8)
    _agent("T1", "data_validator", "Data Validator", G.TECHNICAL,
           ("Build and validate the MarketSnapshot",), K.DETERMINISTIC),
    _agent("T2", "market_session", "Market Session Agent", G.TECHNICAL,
           ("Sessions, overlaps, time to close, per-instrument calendars",), K.DETERMINISTIC),
    _agent("T3", "market_structure", "Market Structure Agent", G.TECHNICAL,
           ("Trend state and key levels per timeframe, including higher-timeframe bias",),
           K.DETERMINISTIC),
    _agent("T4", "technical_indicator", "Technical Indicator Agent", G.TECHNICAL,
           ("Indicator features and momentum assessment",), K.DETERMINISTIC),
    _agent("T5", "price_action", "Candle / Price Action Agent", G.TECHNICAL,
           ("Candle and price-action features tied to structure levels",), K.DETERMINISTIC),
    _agent("T6", "pullback_setup", "Pullback / Setup Agent", G.TECHNICAL,
           ("Detect and manage Setups",), K.DETERMINISTIC),
    _agent("T7", "entry_timing", "Entry Timing Agent", G.TECHNICAL,
           ("Deterministic entry trigger while a Setup is armed",), K.DETERMINISTIC),
    _agent("T8", "technical_analyst", "Technical Analyst", G.TECHNICAL,
           ("Write the market report from typed assessments, citing only snapshot values",),
           K.LLM, tier=T.QUICK),
    # Upstream debate and decision (U1–U8), reused unchanged
    _agent("U1", "bull_researcher", "Bull Researcher", G.DEBATE,
           ("Argue for the setup",), K.LLM, tier=T.QUICK, source=S.UPSTREAM,
           upstream_node="Bull Researcher"),
    _agent("U2", "bear_researcher", "Bear Researcher", G.DEBATE,
           ("Argue against the setup",), K.LLM, tier=T.QUICK, source=S.UPSTREAM,
           upstream_node="Bear Researcher"),
    _agent("U3", "research_manager", "Research Manager", G.DEBATE,
           ("Judge the investment debate; write the investment plan",), K.LLM, tier=T.DEEP,
           source=S.UPSTREAM, upstream_node="Research Manager"),
    _agent("U4", "trader", "Trader", G.DECISION,
           ("Transaction view on the setup; levels are advisory only",), K.LLM, tier=T.QUICK,
           source=S.UPSTREAM, upstream_node="Trader"),
    _agent("U5", "risk_aggressive", "Aggressive Risk Debater", G.DEBATE,
           ("Argue the high-reward view of the plan (advisory)",), K.LLM, tier=T.QUICK,
           source=S.UPSTREAM, upstream_node="Aggressive Analyst"),
    _agent("U6", "risk_conservative", "Conservative Risk Debater", G.DEBATE,
           ("Argue for caution (advisory)",), K.LLM, tier=T.QUICK, source=S.UPSTREAM,
           upstream_node="Conservative Analyst"),
    _agent("U7", "risk_neutral", "Neutral Risk Debater", G.DEBATE,
           ("Balance the aggressive and conservative views (advisory)",), K.LLM,
           tier=T.QUICK, source=S.UPSTREAM, upstream_node="Neutral Analyst"),
    _agent("U8", "portfolio_manager", "Portfolio Manager", G.DECISION,
           ("Typed rating = approval strength for the setup",), K.LLM, tier=T.DEEP,
           source=S.UPSTREAM, upstream_node="Portfolio Manager"),
    # Proposal, validation, risk and execution (deterministic)
    _agent("P1", "trade_proposal_builder", "Trade Proposal Builder", G.PROPOSAL,
           ("Build the typed TradeProposal with deterministic levels",), K.DETERMINISTIC),
    _agent("P2", "contradiction_checker", "Contradiction Checker", G.VALIDATION,
           ("Flag conflicts between reports, assessments, advisory levels and the snapshot",),
           K.DETERMINISTIC),
    _agent("P3", "risk_engine", "Risk Auditor (Risk Engine)", G.RISK,
           ("Apply every hard risk rule", "Size by formula", "Own the circuit breaker"),
           K.DETERMINISTIC),
    _agent("P4", "execution_checker", "Execution Checker", G.EXECUTION_VALIDATION,
           ("Pre-flight checks and reconciliation",), K.DETERMINISTIC),
    _agent("E1", "paper_execution", "Paper Execution Agent", G.EXECUTION,
           ("Submit order intents to the Paper Broker; track fills and closes",),
           K.DETERMINISTIC),
    _agent("E2", "mt5_execution", "MT5 Execution Agent", G.EXECUTION,
           ("Submit order intents to the MT5 bridge, demo accounts only",), K.DETERMINISTIC,
           status=R.DEMO_GATE),
    # Review and operations
    _agent("L1", "post_trade_reviewer", "Post-Trade Reviewer", G.REVIEW,
           ("Write a typed TradeReview for every closed trade",), K.DETERMINISTIC),
    _agent("L2", "attribution", "Performance / Attribution Agent", G.REVIEW,
           ("Settlement, metrics and attribution",), K.DETERMINISTIC),
    _agent("O1", "supervisor", "Supervisor", G.OPERATIONAL,
           ("Scheduling, market focus, run lifecycle and pauses",), K.DETERMINISTIC),
    _agent("O2", "wellbeing_monitor", "Operational Wellbeing Monitor", G.OPERATIONAL,
           ("Track errors, rate limits and budgets; request pauses and cooldowns",),
           K.DETERMINISTIC),
)


def default_registry() -> AgentRegistry:
    """The full architectural roster, without display personas."""
    return AgentRegistry(ARCHITECTURAL_ROSTER)
