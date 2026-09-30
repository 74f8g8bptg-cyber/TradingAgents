"""Helpers for the Phase 6b setup / trader / proposal tests.

Everything here is SYNTHETIC and TEST-ONLY:
- the bar paths are constructed shapes (not market history); the prices, quotes, validity,
  evidence grades, entry models and profile are labelled fixtures, never defaults;
- the Trader is a deterministic script, not a model;
- decision-support *variants* (``decision_variant``) copy a real pipeline output and change
  one field to exercise a rule; they are labelled as such.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from research_helpers import (
    AS_OF,
    CB_DECISION,
    CPI_OFFICIAL,
    MODEL,
    EvidenceScript,
    inputs as pipeline_inputs,
    pipeline as research_pipeline,
)
from stellar.marketdata import (
    MappingKind,
    MarketDataRequest,
    MarketDataSourceInfo,
    ProviderSymbolMapping,
    build_verified_snapshot,
)
from stellar.marketdata.providers import InMemoryMarketDataSource
from stellar.pipeline import LlmBudget
from stellar.pipeline.records import EvidenceGrade, TechnicalRef
from stellar.proposals import Approval, ApprovalSource, LevelSelection, SelectionSource
from stellar.reasoning import ScriptedProvider
from stellar.schemas.market import Quote, Timeframe
from stellar.schemas.proposal import Rating
from stellar.serialization import sha256_hex
from stellar.setups import EntryModelKind, OptionKind, Setup, SetupConfig, evaluate_setup
from stellar.technical import analyse
from stellar.trader import TraderConfig
from technical_helpers import TEST_CONFIG, from_closes, response

H = timedelta(hours=1)
CONFIG_HASH = sha256_hex("synthetic-trader-test-config")

LONG_CLOSES = [122, 126, 130, 127, 124, 120, 116, 119, 121, 118, 112, 105, 110, 115, 119, 114,
               "109.5", 115, 120, 126, 123, 121, 122]
"""An up-structure (last swings HL 109.0, HH 126.5) with a pullback that has not formed a
confirmed low: a SUPPORT zone [115, 116] lies inside the last leg, a RESISTANCE zone
[130, 131] lies beyond it, and the latest low (120.5) is only a CANDIDATE pivot."""

SHORT_CLOSES = [250 - Decimal(str(c)) for c in LONG_CLOSES]
"""The mirror image: a down-structure with a pullback up."""

INVALIDATED_CLOSES = LONG_CLOSES[:20] + [115, 107]
"""The same up-structure, but the pullback closes below the leg's start swing (109.0)."""

WICK_BREACH_CLOSES = LONG_CLOSES[:20] + [115, "109.2"]
"""The pullback's wick (108.7) trades below the leg's start swing, but no bar closes below it:
the level is breached without a structure break."""

SINGLE_CLOSES = [100, 104, 108, 105, 103, 107, 111, 115, 112, 110, 114, 118, 122, 119, 117, 121]
"""Rising swings with one target option only (no opposing zone beyond the last high)."""

RANGE_CLOSES = [100, 104, 108, 104, 100, 104, 108, 104, 100, 104, 108, 104, 100, 102]

# TEST-ONLY setup configuration (labelled; never a default).
SETUP_CONFIG = SetupConfig(
    version="test_setup_1", test_only=True, setup_validity_bars=4,
    ready_evidence_grades=(EvidenceGrade.LIMITED, EvidenceGrade.ADEQUATE),
    entry_models=(EntryModelKind.MARKET_AT_QUOTE, EntryModelKind.LIMIT_AT_ZONE),
    profile="test_profile")
MARKET_ONLY = SETUP_CONFIG.model_copy(update={"entry_models": (EntryModelKind.MARKET_AT_QUOTE,)})
TRADER_CONFIG = TraderConfig(version="test_trader_1", test_only=True, llm_enabled=True,
                             budget=LlmBudget(max_calls_per_run=3, test_only=True), model=MODEL,
                             max_attempts=1)


def approve(setup: Setup, rating: Rating = Rating.BUY, *,
            source: ApprovalSource = ApprovalSource.OWNER, direction=None) -> Approval:
    """A TEST-ONLY approval of exactly this setup, in its own direction unless overridden."""
    return Approval(setup_id=setup.setup_id,
                    direction=direction or setup.direction.trade_direction(), rating=rating,
                    source=source, reference="test_fixture")


def approve_for(analysis, decision, *, config: SetupConfig = SETUP_CONFIG,
                rating: Rating = Rating.BUY, **kw) -> Approval:
    """Approval for the setup these inputs produce (setup ids are stable for a leg)."""
    setup = evaluate_setup(technical=analysis, decision=decision, as_of=analysis.as_of,
                           config=config)
    return approve(setup, rating, **kw)


def bars_for(closes, *, end: datetime = AS_OF, instrument: str = "XAUUSD"):
    return from_closes(closes, start=end - len(closes) * H, instrument=instrument)


def technical(closes, *, end: datetime = AS_OF):
    bars = bars_for(closes, end=end)
    return analyse(response(bars), as_of=end, config=TEST_CONFIG)


def market(closes, *, bid, ask, end: datetime = AS_OF, quote_at: datetime | None = None,
           snapshot_id: str = "snap_trader_01", instrument: str = "XAUUSD", with_quote=True):
    bars = bars_for(closes, end=end, instrument=instrument)
    info = MarketDataSourceInfo(provider_id="mem", name="Synthetic", kind="IN_MEMORY",
                                price_side="bid", volume_kind="none", synthetic=True,
                                supports_quotes=True)
    mapping = ProviderSymbolMapping(provider_id="mem", instrument=instrument,
                                    kind=MappingKind.EXACT, provider_symbol=instrument)
    quotes = {instrument: [Quote(instrument=instrument, bid=Decimal(str(bid)),
                                 ask=Decimal(str(ask)), ts=quote_at or end, source="mem",
                                 provider_symbol=instrument)]} if with_quote else {}
    source = InMemoryMarketDataSource(info, [mapping], {(instrument, Timeframe.H1.value): bars},
                                      quotes=quotes, clock=lambda: end)
    resp = source.candles(MarketDataRequest(instrument=instrument, timeframe=Timeframe.H1,
                                            as_of=end))
    quote = source.quote(instrument, end) if with_quote else None
    return build_verified_snapshot(resp, snapshot_id=snapshot_id, created_at=end,
                                   config_hash=CONFIG_HASH, quote=quote)


def decision_support(journal, analysis, *, stances: dict | None = None):
    """A real Phase 6 pipeline run over synthetic research and this technical analysis."""
    pipe, _ = research_pipeline(journal, script=EvidenceScript(stances=stances))
    return pipe.run(pipeline_inputs(CB_DECISION, CPI_OFFICIAL, technical=[analysis]))


def decision_variant(decision, **update: Any):
    """SYNTHETIC variant of a real decision support: one field changed to exercise a rule."""
    return decision.model_copy(update=update)


def reviewed(decision, analysis):
    """SYNTHETIC variant: the decision support re-pointed at another technical analysis."""
    return decision.model_copy(update={"technical": (TechnicalRef(
        analysis_id=analysis.analysis_id, content_hash=analysis.content_hash,
        timeframe=analysis.timeframe),)})


def option_of(setup: Setup, kind: OptionKind, index: int = 0):
    return [o for o in setup.options if o.kind is kind][index]


def owner_selection(setup: Setup, *, entry: OptionKind = OptionKind.MARKET_AT_QUOTE,
                    stop: OptionKind = OptionKind.STRUCTURE_STOP,
                    targets=(OptionKind.PRIOR_SWING_TARGET,)) -> LevelSelection:
    return LevelSelection(setup_id=setup.setup_id, setup_fingerprint=setup.fingerprint,
                          entry_option_id=option_of(setup, entry).option_id,
                          stop_option_id=option_of(setup, stop).option_id,
                          target_option_ids=tuple(option_of(setup, t).option_id
                                                  for t in targets),
                          source=SelectionSource.OWNER)


class TraderScript:
    """Deterministic Trader: selects option ids by kind from the offered task, or replies
    with an override (raw text, consumed in order)."""

    def __init__(self, *, entry: str = "MARKET_AT_QUOTE", stop: str = "STRUCTURE_STOP",
                 targets: tuple[str, ...] = ("PRIOR_SWING_TARGET", "ZONE_TARGET"),
                 decision: str = "SELECT", direction: str | None = None,
                 overrides: list | None = None, extra: dict | None = None) -> None:
        self.entry, self.stop, self.targets = entry, stop, targets
        self.decision, self.direction = decision, direction
        self.overrides = list(overrides or [])
        self.extra = extra or {}

    def __call__(self, request):
        if self.overrides:
            return self.overrides.pop(0)
        task = json.loads(request.task)
        options = task["options"]

        def pick(kind):
            return next(o["option_id"] for o in options if o["kind"] == kind)

        reply: dict[str, Any] = {
            "setup_id": task["setup"]["setup_id"],
            "direction": self.direction or task["setup"]["direction"],
            "decision": self.decision, "rationale": "Fixture rationale over offered options.",
            "risks": ["Fixture risk: the pullback may continue."]}
        if self.decision == "SELECT":
            reply.update(entry_option_id=pick(self.entry), stop_option_id=pick(self.stop),
                         target_option_ids=[pick(k) for k in self.targets],
                         evidence_ids=[task["setup"]["invalidation_evidence_id"]])
        reply.update(self.extra)
        return json.dumps(reply)


def trader_provider(script: TraderScript | None = None) -> ScriptedProvider:
    return ScriptedProvider(script or TraderScript())
