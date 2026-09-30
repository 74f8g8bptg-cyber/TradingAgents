"""Helpers for the Phase 2 market-data tests. All data here is SYNTHETIC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from stellar.marketdata import (
    MappingKind,
    MarketDataRequest,
    MarketDataSourceInfo,
    ProviderSymbolMapping,
)
from stellar.marketdata.providers import CsvFileProvider, CsvFileSpec, InMemoryMarketDataSource
from stellar.schemas.market import Candle, PriceSide, Quote, VolumeKind

FIXTURES = Path(__file__).resolve().parent / "fixtures"
T0 = datetime(2030, 1, 7, 8, 0, tzinfo=UTC)  # synthetic fixtures start here (H1)
FIXED_NOW = datetime(2030, 1, 8, 0, 0, tzinfo=UTC)
H = timedelta(hours=1)


def clock() -> datetime:
    return FIXED_NOW


def fixture_provider(**overrides: Any) -> CsvFileProvider:
    """The four synthetic fixture files, all mapped EXACT."""
    files = [
        CsvFileSpec(path=FIXTURES / "synthetic_eurusd_h1.csv", instrument="EURUSD",
                    timeframe="H1", provider_symbol="EURUSD", declared_price_decimals=5),
        CsvFileSpec(path=FIXTURES / "synthetic_usdjpy_h1.csv", instrument="USDJPY",
                    timeframe="H1", provider_symbol="USDJPY", declared_price_decimals=3),
        CsvFileSpec(path=FIXTURES / "synthetic_xauusd_h1.csv", instrument="XAUUSD",
                    timeframe="H1", provider_symbol="XAUUSD", declared_price_decimals=2),
        CsvFileSpec(path=FIXTURES / "synthetic_nas100_h1.csv", instrument="NAS100",
                    timeframe="H1", provider_symbol="NAS100", declared_price_decimals=2),
    ]
    kwargs = {"provider_id": "synthetic_csv", "name": "Synthetic fixture files", "files": files,
              "price_side": PriceSide.BID, "volume_kind": VolumeKind.TICK, "synthetic": True,
              "clock": clock}
    kwargs.update(overrides)
    return CsvFileProvider(**kwargs)


def write_csv(tmp_path: Path, body: str, name: str = "bars.csv") -> Path:
    path = tmp_path / name
    path.write_text("# SYNTHETIC TEST DATA - NOT MARKET HISTORY\n" + body, encoding="utf-8")
    return path


def csv_provider(path: Path, *, instrument="EURUSD", timeframe="H1", symbol="EURUSD",
                 kind=MappingKind.EXACT, description=None, **spec_kw) -> CsvFileProvider:
    provider_kw = {k: spec_kw.pop(k) for k in ("duplicate_policy", "order_policy")
                   if k in spec_kw}
    spec = CsvFileSpec(path=path, instrument=instrument, timeframe=timeframe,
                       provider_symbol=symbol, mapping_kind=kind,
                       mapping_description=description, **spec_kw)
    return CsvFileProvider(provider_id="test_csv", name="Test CSV", files=[spec],
                           price_side=PriceSide.MID, volume_kind=VolumeKind.TICK,
                           synthetic=True, clock=clock, **provider_kw)


def request(instrument="EURUSD", timeframe="H1", as_of=None, **kw) -> MarketDataRequest:
    return MarketDataRequest(instrument=instrument, timeframe=timeframe,
                             as_of=as_of or FIXED_NOW, **kw)


def bar(i: int, *, instrument="XAUUSD", source="mem", symbol="XAUUSD", proxy=False,
        start=T0, base=Decimal("2385.12"), **overrides: Any) -> Candle:
    """Synthetic H1 bar number ``i`` after ``start``."""
    open_ = base + Decimal(i)
    data = {"instrument": instrument, "timeframe": "H1", "open_time": start + i * H,
            "close_time": start + (i + 1) * H, "open": open_, "high": open_ + Decimal("2.50"),
            "low": open_ - Decimal("1.25"), "close": open_ + Decimal("1.00"),
            "volume": Decimal("100"), "volume_kind": "tick", "price_side": "bid",
            "source": source, "provider_symbol": symbol, "proxy": proxy, "is_closed": True}
    data.update(overrides)
    return Candle.model_validate(data)


def memory_provider(instrument="XAUUSD", *, symbol="XAUUSD", kind=MappingKind.EXACT,
                    description=None, n=5, quotes=None, bars=None,
                    supports_quotes=True) -> InMemoryMarketDataSource:
    proxy = kind is not MappingKind.EXACT
    info = MarketDataSourceInfo(provider_id="mem", name="Synthetic in-memory", kind="IN_MEMORY",
                                price_side=PriceSide.BID, volume_kind=VolumeKind.TICK,
                                supports_quotes=supports_quotes, synthetic=True)
    mapping = ProviderSymbolMapping(provider_id="mem", instrument=instrument, kind=kind,
                                    provider_symbol=symbol, description=description)
    series = bars if bars is not None else [
        bar(i, instrument=instrument, symbol=symbol, proxy=proxy) for i in range(n)]
    return InMemoryMarketDataSource(info, [mapping], {(instrument, "H1"): series},
                                    quotes=quotes, clock=clock)


def quote(ts: datetime, *, instrument="XAUUSD", symbol="XAUUSD", proxy=False,
          bid="2390.11", ask="2390.43") -> Quote:
    return Quote(instrument=instrument, bid=bid, ask=ask, ts=ts, source="mem",
                 provider_symbol=symbol, proxy=proxy)
