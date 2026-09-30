"""Helpers for the Phase 3 risk tests.

Every number here is a TEST-ONLY, SYNTHETIC value. ``TEST_POLICY`` is marked
``test_only=True`` and is refused by ``RiskEngine`` unless a test passes
``allow_test_policy=True``; none of these values is a recommendation or a default.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from factories import T0, make_proposal
from stellar.marketdata import (
    MappingKind,
    MarketDataRequest,
    MarketDataSourceInfo,
    ProviderSymbolMapping,
    SubstitutionPolicy,
    build_verified_snapshot,
)
from stellar.marketdata.providers import InMemoryMarketDataSource
from stellar.risk import (
    AccountRiskState,
    CircuitBreakerState,
    DailyRiskState,
    ExecutionModeInput,
    InstrumentRiskMetadata,
    RiskContext,
    RiskEngine,
    RiskPolicy,
)
from stellar.schemas.market import Candle, DataQualityFlag, Quote
from stellar.serialization import sha256_hex

AS_OF = T0 + timedelta(minutes=10)  # proposal created at T0, valid until T0 + 1h
H = timedelta(hours=1)
CONFIG_HASH = sha256_hex("synthetic-test-config")

# TEST-ONLY limits (labelled; never defaults).
TEST_POLICY = RiskPolicy.model_validate({
    "version": "test_policy_1",
    "test_only": True,
    "max_risk_per_trade": {"state": "ENABLED", "limit": "0.01"},
    "max_position_volume": {"state": "ENABLED", "limits": {"XAUUSD": "5", "EURUSD": "5"}},
    "max_open_positions": {"state": "ENABLED", "limit": 3},
    "max_pending_orders": {"state": "ENABLED", "limit": 3},
    "max_instrument_exposure": {"state": "ENABLED", "limit": "0.02"},
    "correlated_exposure": {"state": "ENABLED", "clusters": [["XAUUSD", "EURUSD", "USDJPY"]],
                            "limit": "0.03"},
    "max_daily_loss": {"state": "ENABLED", "limit": "0.03"},
    "max_drawdown": {"state": "ENABLED", "limit": "0.10"},
    "max_spread": {"state": "ENABLED", "limits": {"XAUUSD": "0.50"}},
    "max_quote_age_seconds": {"state": "ENABLED", "limit": 60},
    "max_slippage": {"state": "ENABLED", "limits": {"XAUUSD": "0.30"}},
    "cooldowns": {"state": "ENABLED"},
    "event_restrictions": {"state": "ENABLED"},
})


def policy(**overrides: Any) -> RiskPolicy:
    return RiskPolicy.model_validate({**TEST_POLICY.model_dump(), **overrides})


def engine(p: RiskPolicy | None = None) -> RiskEngine:
    return RiskEngine(p or TEST_POLICY, allow_test_policy=True)


def _bar(i: int, symbol: str, proxy: bool) -> Candle:
    start = AS_OF - 6 * H
    open_ = Decimal("2398.00") + Decimal(i)
    return Candle(instrument="XAUUSD", timeframe="H1", open_time=start + i * H,
                  close_time=start + (i + 1) * H, open=open_, high=open_ + Decimal("2.40"),
                  low=open_ - Decimal("1.10"), close=open_ + Decimal("0.60"), volume=Decimal("100"),
                  volume_kind="tick", price_side="bid", source="mem", provider_symbol=symbol,
                  proxy=proxy, is_closed=True)


def market(*, kind: MappingKind = MappingKind.EXACT, symbol: str = "XAUUSD",
           bid: str = "2399.80", ask: str = "2400.10", quote_ts=None, bars=None,
           allow: SubstitutionPolicy | None = None):
    """A synthetic in-memory source for XAUUSD; returns (snapshot, quote response)."""
    proxy = kind is not MappingKind.EXACT
    info = MarketDataSourceInfo(provider_id="mem", name="Synthetic", kind="IN_MEMORY",
                                price_side="bid", volume_kind="tick", supports_quotes=True,
                                synthetic=True)
    mapping = ProviderSymbolMapping(provider_id="mem", instrument="XAUUSD", kind=kind,
                                    provider_symbol=symbol,
                                    description="synthetic proxy" if proxy else None)
    quotes = [Quote(instrument="XAUUSD", bid=bid, ask=ask, ts=quote_ts or AS_OF - timedelta(
        seconds=5), source="mem", provider_symbol=symbol, proxy=proxy)]
    source = InMemoryMarketDataSource(
        info, [mapping], {("XAUUSD", "H1"): bars or [_bar(i, symbol, proxy) for i in range(5)]},
        quotes={"XAUUSD": quotes}, clock=lambda: AS_OF)
    allow = allow or SubstitutionPolicy(allow_proxy=proxy, allow_derived=proxy)
    response = source.candles(MarketDataRequest(instrument="XAUUSD", timeframe="H1",
                                                as_of=AS_OF, substitution=allow))
    snap = build_verified_snapshot(response, snapshot_id="snap_risk_test", created_at=AS_OF,
                                   config_hash=CONFIG_HASH)
    return snap, source.quote("XAUUSD", AS_OF, allow)


def context(**overrides: Any) -> RiskContext:
    snap, quote = market()
    data: dict[str, Any] = {
        "as_of": AS_OF,
        "proposal": make_proposal(),  # XAUUSD SHORT, limit 2400.00, stop 2412.00
        "execution": ExecutionModeInput(mode="PAPER"),
        "breaker": CircuitBreakerState(updated_at=T0 - H),
        "account": AccountRiskState(currency="USD", equity="100000", peak_equity="100000",
                                    as_of=AS_OF, source="test_fixture"),
        "daily": DailyRiskState(trading_day=AS_OF.date(), start_equity="100000",
                                realised_pnl="0", unrealised_pnl="0", as_of=AS_OF,
                                source="test_fixture"),
        "positions": (),
        "pending_orders": (),
        "snapshot": snap,
        "quote": quote,
        "metadata": InstrumentRiskMetadata(instrument="XAUUSD", account_currency="USD",
                                           value_per_price_unit_per_lot="100", lot_step="0.01",
                                           min_volume="0.01", max_volume="50",
                                           source="test_fixture"),
        "requested_volume": Decimal("0.50"),  # risk 0.50 × 12.00 × 100 = 600 USD = 0.6 %
        "cooldowns": (),
        "event_restriction": {"instrument": "XAUUSD", "restricted": False,
                              "evaluated_at": AS_OF, "source": "test_fixture"},
    }
    data.update(overrides)
    return RiskContext.model_validate(
        {k: (v.model_dump() if hasattr(v, "model_dump") else v) for k, v in data.items()})


def result(evaluation, check: str):
    return next(r for r in evaluation.results if r.check == check)


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


__all__ = ["AS_OF", "CONFIG_HASH", "DataQualityFlag", "H", "TEST_POLICY", "context", "engine",
           "market", "policy", "result", "utc"]
