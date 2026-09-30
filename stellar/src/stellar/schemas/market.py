"""Market contracts: candles, quotes and the validated MarketSnapshot.

Fields follow Foundation §4.7 (timeframes), §4.8 (candles), §4.2 (provider
symbol and proxy flag) and §9.1 stage 0 (snapshot). Phase 1 defines the shapes
and their structural checks only; building snapshots from a provider is Phase 2.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    InstrumentId,
    Label,
    NonNegativeDecimal,
    Price,
    Provenance,
    SchemaVersion,
    Sha256Hex,
    ShortText,
    SnapshotId,
    StellarModel,
    UtcDatetime,
)
from stellar.serialization import content_hash


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"


class VolumeKind(StrEnum):
    TICK = "tick"
    REAL = "real"
    NONE = "none"


class PriceSide(StrEnum):
    BID = "bid"
    ASK = "ask"
    MID = "mid"
    LAST = "last"


class Candle(StellarModel):
    """One OHLC bar (Foundation §4.8)."""

    instrument: InstrumentId
    timeframe: Timeframe
    open_time: UtcDatetime
    close_time: UtcDatetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: NonNegativeDecimal
    volume_kind: VolumeKind
    price_side: PriceSide
    source: ShortText
    provider_symbol: ShortText
    proxy: bool = False
    is_closed: bool

    @model_validator(mode="after")
    def _ohlc_consistent(self) -> Candle:
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")
        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= min(open, close)")
        return self


class Quote(StellarModel):
    """A bid/ask quote at a point in time."""

    instrument: InstrumentId
    bid: Price
    ask: Price
    ts: UtcDatetime
    source: ShortText
    provider_symbol: ShortText
    proxy: bool = False

    @model_validator(mode="after")
    def _ask_not_below_bid(self) -> Quote:
        if self.ask < self.bid:
            raise ValueError("ask must be >= bid")
        return self


class CandleSeries(StellarModel):
    """Candles of one timeframe, strictly ordered, with their content hash."""

    timeframe: Timeframe
    candles: tuple[Candle, ...] = Field(min_length=1)
    content_hash: Sha256Hex

    @staticmethod
    def hash_candles(candles: tuple[Candle, ...] | list[Candle]) -> str:
        return content_hash([c.model_dump(mode="json") for c in candles])

    @classmethod
    def build(cls, timeframe: Timeframe, candles: list[Candle]) -> CandleSeries:
        return cls(timeframe=timeframe, candles=tuple(candles),
                   content_hash=cls.hash_candles(candles))

    @model_validator(mode="after")
    def _ordered_and_hashed(self) -> CandleSeries:
        for candle in self.candles:
            if candle.timeframe != self.timeframe:
                raise ValueError("every candle must match the series timeframe")
        opens = [c.open_time for c in self.candles]
        if any(later <= earlier for earlier, later in zip(opens, opens[1:], strict=False)):
            raise ValueError("candles must be strictly increasing by open_time, no duplicates")
        if self.hash_candles(self.candles) != self.content_hash:
            raise ValueError("content_hash does not match the candles")
        return self


class MarketSnapshot(StellarModel):
    """Validated market input for one decision cycle (Foundation §9.1 stage 0).

    No candle may close, and no quote may be stamped, after ``as_of``: the
    snapshot can never carry look-ahead data.
    """

    schema_version: SchemaVersion = SCHEMA_VERSION
    snapshot_id: SnapshotId
    instrument: InstrumentId
    as_of: UtcDatetime
    series: tuple[CandleSeries, ...] = Field(min_length=1)
    quote: Quote | None = None
    session: Label | None = None
    quality_flags: tuple[Label, ...] = ()
    created_at: UtcDatetime
    provenance: Provenance

    @model_validator(mode="after")
    def _consistent_and_point_in_time(self) -> MarketSnapshot:
        timeframes = [s.timeframe for s in self.series]
        if len(set(timeframes)) != len(timeframes):
            raise ValueError("at most one series per timeframe")
        for s in self.series:
            for candle in s.candles:
                if candle.instrument != self.instrument:
                    raise ValueError("every candle must match the snapshot instrument")
                if candle.close_time > self.as_of:
                    raise ValueError("a candle closes after as_of (look-ahead)")
        if self.quote is not None:
            if self.quote.instrument != self.instrument:
                raise ValueError("the quote must match the snapshot instrument")
            if self.quote.ts > self.as_of:
                raise ValueError("the quote is stamped after as_of (look-ahead)")
        if self.created_at < self.as_of:
            raise ValueError("created_at cannot be before as_of")
        return self
