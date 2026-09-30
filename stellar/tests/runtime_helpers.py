"""Helpers for the Phase 7 V1 PAPER end-to-end tests.

Everything here is SYNTHETIC and TEST-ONLY:
- bars and quotes are constructed shapes (not market history), served by the in-memory
  Phase 2 source; research items are the Phase 6 fixtures; the LLM is a deterministic script;
- the runtime, technical, research, setup, trader, risk and paper-account configurations are
  labelled ``test_only`` values from the earlier phases' helpers. None is a default, a
  recommendation or a claim about any market or strategy.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from broker_helpers import PAPER_CONFIG
from research_helpers import (
    ALLOWLIST,
    AS_OF,
    CB_DECISION,
    CPI_OFFICIAL,
    DECLARED,
    STATION,
    VALIDATION,
    WORKFLOW,
    EvidenceScript,
    collections,
)
from risk_helpers import TEST_POLICY, engine
from stellar.marketdata import MappingKind, MarketDataSourceInfo, ProviderSymbolMapping
from stellar.marketdata.providers import InMemoryMarketDataSource
from stellar.proposals import Approval
from stellar.reasoning import ScriptedProvider
from stellar.risk.state import (
    DailyRiskState,
    EventRestrictionState,
    InstrumentRiskMetadata,
)
from stellar.runtime import (
    OperatorRiskInputs,
    PaperRuntime,
    RunRecord,
    RunRequest,
    RunStage,
    RuntimeConfig,
    TakeProfitPolicy,
)
from stellar.schemas.market import Candle, Quote, Timeframe
from stellar.setups import Setup
from stellar.technical import TechnicalConfig
from technical_helpers import TEST_CONFIG
from trader_helpers import (
    LONG_CLOSES,
    SETUP_CONFIG,
    SHORT_CLOSES,
    TRADER_CONFIG,
    TraderScript,
    approve,
    bars_for,
)

M = timedelta(minutes=1)
H = timedelta(hours=1)
OPENED_AT = AS_OF - 24 * H

# TEST-ONLY runtime wiring (labelled; never a default).
RUNTIME_CONFIG = RuntimeConfig(
    version="test_runtime_1", test_only=True, profile="test_profile", timeframe=Timeframe.H1,
    broker_symbols={"XAUUSD": "XAUUSD"}, take_profit=TakeProfitPolicy.NEAREST_PROPOSAL_TARGET,
    enabled_instruments=("XAUUSD",))

POINT_ZONES = TechnicalConfig.model_validate({**TEST_CONFIG.model_dump(),
                                              "version": "test_technical_point_zones",
                                              "zone_tolerance": {"price": "0"}})
"""TEST-ONLY: zero zone tolerance, so a zone is one pivot price and a limit entry is a single
price (the Risk Engine does not size a zone entry, RK-4)."""


def operator(at: datetime = AS_OF, *, volume: str | None = "0.50",
             realised: str = "0", **update: Any) -> OperatorRiskInputs:
    """TEST-ONLY operator inputs (daily window, event restriction, instrument metadata)."""
    data: dict[str, Any] = {
        "daily": DailyRiskState(trading_day=at.date(), start_equity=Decimal("100000"),
                                realised_pnl=Decimal(realised), unrealised_pnl=Decimal("0"),
                                as_of=at, source="test_fixture"),
        "cooldowns": (),
        "event_restriction": EventRestrictionState(instrument="XAUUSD", restricted=False,
                                                   evaluated_at=at, source="test_fixture"),
        "metadata": InstrumentRiskMetadata(instrument="XAUUSD", account_currency="USD",
                                           value_per_price_unit_per_lot=Decimal("100"),
                                           lot_step=Decimal("0.01"), min_volume=Decimal("0.01"),
                                           max_volume=Decimal("50"), source="test_fixture"),
        "requested_volume": None if volume is None else Decimal(volume),
    }
    data.update(update)
    return OperatorRiskInputs(**data)


def quote(bid, ask, ts: datetime = AS_OF) -> Quote:
    return Quote(instrument="XAUUSD", bid=Decimal(str(bid)), ask=Decimal(str(ask)), ts=ts,
                 source="mem", provider_symbol="XAUUSD")


def source(closes=LONG_CLOSES, quotes=(("122.0", "122.2", AS_OF),), *, end=AS_OF,
           supports_quotes: bool = True, extra_bars=()) -> InMemoryMarketDataSource:
    """A deterministic in-memory Phase 2 source: H1 bars ending at ``end`` plus quotes.
    ``extra_bars`` may add bars *after* ``end`` (never visible to an earlier ``as_of``)."""
    bars = bars_for(closes, end=end) + list(extra_bars)
    info = MarketDataSourceInfo(provider_id="mem", name="Synthetic", kind="IN_MEMORY",
                                price_side="bid", volume_kind="none", synthetic=True,
                                supports_quotes=supports_quotes)
    mapping = ProviderSymbolMapping(provider_id="mem", instrument="XAUUSD",
                                    kind=MappingKind.EXACT, provider_symbol="XAUUSD")
    qs = [quote(b, a, t) for b, a, t in quotes]
    return InMemoryMarketDataSource(info, [mapping], {("XAUUSD", "H1"): bars},
                                    quotes={"XAUUSD": qs} if supports_quotes else None,
                                    clock=lambda: end)


class Script:
    """One deterministic provider for research roles (EvidenceScript) and the U4 Trader."""

    def __init__(self, *, stances: dict | None = None, trader: TraderScript | None = None,
                 overrides: dict | None = None):
        self.research = EvidenceScript(stances=stances, overrides=overrides)
        self.trader = trader or TraderScript(targets=("PRIOR_SWING_TARGET",))

    def __call__(self, request):
        return self.trader(request) if request.role == "trader" else self.research(request)


class Clock:
    def __init__(self, now: datetime = AS_OF) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def runtime(journal, *, market=None, provider=None, config=RUNTIME_CONFIG,
            technical_config=TEST_CONFIG, setup_config=SETUP_CONFIG, trader=TRADER_CONFIG,
            policy=TEST_POLICY, broker_config=PAPER_CONFIG, clock=None, workflow=WORKFLOW,
            **kw) -> PaperRuntime:
    return PaperRuntime(journal=journal, market_source=market or source(),
                        provider=provider or ScriptedProvider(Script()), config=config,
                        technical_config=technical_config, workflow=workflow,
                        allowlist=ALLOWLIST, validation=VALIDATION, setup_config=setup_config,
                        trader_config=trader, risk_engine=engine(policy),
                        broker_config=broker_config, station_id=STATION,
                        account_opened_at=OPENED_AT, clock=clock or Clock(), **kw)


def request(*, items=(CB_DECISION, CPI_OFFICIAL), as_of=AS_OF, approval: Approval | None = None,
            op: OperatorRiskInputs | None = None, **kw) -> RunRequest:
    return RunRequest(instrument="XAUUSD", as_of=as_of,
                      collections=tuple(collections(*items, as_of=as_of)),
                      declared_labels=DECLARED, operator=op or operator(as_of),
                      approval=approval, **kw)


def setup_of(rt: PaperRuntime, record: RunRecord) -> Setup:
    cp = rt.ledger.checkpoints(record.run_id)[RunStage.SETUP]
    return Setup.model_validate(cp.outputs["setup"])


def approved(rt: PaperRuntime, record: RunRecord, **kw) -> Approval:
    """A TEST-ONLY Buy approval of the run's own setup, in its own direction (any source)."""
    return approve(setup_of(rt, record), **kw)


def run_to_proposal(rt: PaperRuntime, req: RunRequest | None = None) -> RunRecord:
    """First pass parks at AWAITING_APPROVAL; the second supplies a TEST-ONLY approval."""
    req = req or request()
    parked = rt.run(req)
    if parked.state.value != "AWAITING_APPROVAL":
        return parked
    return rt.run(req.model_copy(update={"approval": approved(rt, parked)}))


def m5(o, h, low, c, *, start: datetime, side: str = "ask") -> Candle:
    return Candle(instrument="XAUUSD", timeframe="M5", open_time=start,
                  close_time=start + 5 * M, open=Decimal(str(o)), high=Decimal(str(h)),
                  low=Decimal(str(low)), close=Decimal(str(c)), volume_kind="none",
                  price_side=side, source="mem", provider_symbol="XAUUSD", is_closed=True)


def run_types(journal, run_id: str) -> list[str]:
    return [e.type for e in journal.read(run_id=run_id)]


def dumps(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


SHORT = SHORT_CLOSES
