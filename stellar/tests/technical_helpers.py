"""Helpers for the Phase 5 technical tests.

Every price, period, window and threshold here is a TEST-ONLY, SYNTHETIC fixture. The bars
are constructed shapes, not historical market data, and no value here is a default,
a recommendation or a claim about any market.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from stellar.marketdata import (
    MappingKind,
    MarketDataRequest,
    MarketDataSourceInfo,
    ProviderSymbolMapping,
    SubstitutionPolicy,
    build_verified_snapshot,
)
from stellar.marketdata.providers import InMemoryMarketDataSource
from stellar.marketdata.timeframes import DURATIONS
from stellar.schemas.market import Candle, Timeframe
from stellar.serialization import sha256_hex
from stellar.technical import TechnicalConfig

T0 = datetime(2026, 9, 1, tzinfo=UTC)  # synthetic series start
CONFIG_HASH = sha256_hex("synthetic-technical-test-config")

# TEST-ONLY synthetic engine configuration (labelled; never a default).
TEST_CONFIG = TechnicalConfig.model_validate({
    "version": "test_technical_1",
    "test_only": True,
    "candles": {"doji_max_body_ratio": "0.1", "small_body_max_ratio": "0.3",
                "large_body_min_ratio": "0.7", "rejection_wick_min_ratio": "0.5",
                "relative_range_lookback": 3, "expansion_min_relative_range": "1.5",
                "contraction_max_relative_range": "0.5"},
    "pivots": {"left": 2, "right": 2},
    "atr_period": 3,
    "range_lookback": 3,
    "zone_tolerance": {"price": "0.5"},
    "consolidation": {"lookback": 4, "max_range_atr": "2", "min_overlap_ratio": "0.6"},
    "indicators": {"sma_periods": [3], "ema_periods": [3], "rsi_period": 3,
                   "macd": {"fast": 2, "slow": 3, "signal": 2},
                   "bollinger": {"period": 3, "deviations": "2"}},
    "relative_volume_lookback": 3,
})


def config(**overrides: Any) -> TechnicalConfig:
    return TechnicalConfig.model_validate({**TEST_CONFIG.model_dump(), **overrides})


def D(value) -> Decimal:
    return Decimal(str(value))


def candle(o, h, low, c, *, i: int, tf: Timeframe = Timeframe.H1, start: datetime = T0,
           volume=None, volume_kind: str = "none", instrument: str = "XAUUSD",
           side: str = "bid") -> Candle:
    step = DURATIONS[tf]
    return Candle(instrument=instrument, timeframe=tf, open_time=start + i * step,
                  close_time=start + (i + 1) * step, open=D(o), high=D(h), low=D(low),
                  close=D(c), volume=None if volume is None else D(volume),
                  volume_kind=volume_kind, price_side=side, source="mem",
                  provider_symbol=instrument, is_closed=True)


def from_ohlc(rows, **kw) -> list[Candle]:
    """rows: (open, high, low, close) or (open, high, low, close, volume)."""
    out = []
    for i, row in enumerate(rows):
        o, h, low, c, *rest = row
        extra = {"volume": rest[0], "volume_kind": kw.get("volume_kind", "real")} if rest else {}
        out.append(candle(o, h, low, c, i=i, **{k: v for k, v in kw.items()
                                                  if k != "volume_kind"}, **extra))
    return out


def from_closes(closes, *, wick: str = "0.5", **kw) -> list[Candle]:
    """Bars that open at the previous close and close at the given close (synthetic path).

    The wick beyond the close is ``wick``; the wick beyond the open is half of it, so a
    turning bar's extreme is strictly beyond its neighbours' (no accidental equal highs).
    """
    rows, prev, w = [], D(closes[0]), D(wick)
    for c in closes:
        c = D(c)
        o = prev
        if c >= o:
            rows.append((o, c + w, o - w / 2, c))
        else:
            rows.append((o, o + w / 2, c - w, c))
        prev = c
    return from_ohlc(rows, **kw)


def response(bars: list[Candle], *, as_of: datetime | None = None, proxy: bool = False,
             volume_kind: str = "none", instrument: str = "XAUUSD"):
    tf = bars[0].timeframe
    kind = MappingKind.PROXY if proxy else MappingKind.EXACT
    info = MarketDataSourceInfo(provider_id="mem", name="Synthetic", kind="IN_MEMORY",
                                price_side="bid", volume_kind=volume_kind, synthetic=True)
    mapping = ProviderSymbolMapping(provider_id="mem", instrument=instrument, kind=kind,
                                    provider_symbol=instrument,
                                    description="synthetic proxy" if proxy else None)
    if proxy:
        bars = [b.model_copy(update={"proxy": True}) for b in bars]
    as_of = as_of or bars[-1].close_time
    source = InMemoryMarketDataSource(info, [mapping], {(instrument, tf.value): bars},
                                      clock=lambda: as_of)
    allow = SubstitutionPolicy(allow_proxy=proxy)
    return source.candles(MarketDataRequest(instrument=instrument, timeframe=tf, as_of=as_of,
                                            substitution=allow))


def snapshot(resp, snapshot_id: str = "snap_tech_01"):
    return build_verified_snapshot(resp, snapshot_id=snapshot_id,
                                   created_at=resp.request.as_of, config_hash=CONFIG_HASH)


# Synthetic shapes (constructed; not market history) -------------------------------------

UP_ZIGZAG = [100, 104, 108, 105, 103, 107, 111, 115, 112, 110, 114, 118, 122, 119, 117, 121]
"""Rising swings: lows 103 → 110 → 117, highs 108 → 115 → 122 (with pivots left=right=2)."""

DOWN_ZIGZAG = [200 - (c - 100) for c in UP_ZIGZAG]
"""The mirror image: falling swings."""
