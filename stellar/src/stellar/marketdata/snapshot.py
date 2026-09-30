"""``VerifiedMarketSnapshot``: the numbers agents may cite (Phase 2).

Adapted from TradingAgents' verified-snapshot discipline ("cite only computed or
verified numbers", knowledge audit K17), without its defects: no 2-decimal
formatting, no proxy substitution, no indicator values.

The snapshot is built only from a validated ``MarketDataResponse`` (and
optionally a ``QuoteResponse``). Its latest bar and quote are the input objects
themselves, so every price in it is a value that was present in the validated
data, with its original precision. The only derived fields are counts,
timestamps taken from the bars, and the series hash. No indicator is computed.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from stellar.marketdata.contracts import (
    ErrorCode,
    Freshness,
    MarketDataError,
    MarketDataQuality,
    MarketDataResponse,
    MarketDataSourceInfo,
    QuoteResponse,
)
from stellar.marketdata.symbols import MappingKind, ProviderSymbolMapping
from stellar.schemas.common import (
    SCHEMA_VERSION,
    InstrumentId,
    Provenance,
    SchemaVersion,
    Sha256Hex,
    SnapshotId,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import Candle, Quote, Timeframe

DATA_VALIDATOR_ID = "data_validator"


class VerifiedMarketSnapshot(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    snapshot_id: SnapshotId
    instrument: InstrumentId
    timeframe: Timeframe
    as_of: UtcDatetime
    created_at: UtcDatetime
    latest_bar: Candle
    latest_quote: Quote | None = None
    quote_source: MarketDataSourceInfo | None = None
    quote_mapping: ProviderSymbolMapping | None = None
    bar_count: int = Field(ge=1)
    first_bar_open_time: UtcDatetime
    last_bar_close_time: UtcDatetime
    series_hash: Sha256Hex
    source: MarketDataSourceInfo
    mapping: ProviderSymbolMapping
    quality: MarketDataQuality
    freshness: Freshness
    provenance: Provenance

    @model_validator(mode="after")
    def _consistent(self) -> VerifiedMarketSnapshot:
        bar = self.latest_bar
        if bar.instrument != self.instrument or bar.timeframe != self.timeframe:
            raise ValueError("the latest bar must match the snapshot instrument and timeframe")
        if bar.close_time != self.last_bar_close_time or bar.close_time > self.as_of:
            raise ValueError("the latest bar must close at last_bar_close_time, at or before as_of")
        if self.first_bar_open_time > bar.open_time:
            raise ValueError("first_bar_open_time cannot be after the latest bar")
        if bar.proxy != (self.mapping.kind is not MappingKind.EXACT):
            raise ValueError("the latest bar's proxy label must match the mapping")
        if (self.latest_quote is None) != (self.quote_source is None) or \
                (self.latest_quote is None) != (self.quote_mapping is None):
            raise ValueError("a quote comes with its source and mapping")
        if self.latest_quote is not None:
            if self.latest_quote.instrument != self.instrument:
                raise ValueError("the quote must match the snapshot instrument")
            if self.latest_quote.ts > self.as_of:
                raise ValueError("the quote is stamped after as_of (look-ahead)")
        if self.freshness.as_of != self.as_of:
            raise ValueError("freshness must describe this as_of")
        if self.created_at < self.as_of:
            raise ValueError("created_at cannot be before as_of")
        return self


def build_verified_snapshot(
    response: MarketDataResponse,
    *,
    snapshot_id: str,
    created_at: datetime,
    config_hash: str,
    quote: QuoteResponse | None = None,
) -> VerifiedMarketSnapshot:
    """Summarise a validated response; refuses an empty one."""
    if response.series is None:
        raise MarketDataError(ErrorCode.NO_DATA,
                              f"no {response.request.instrument} {response.request.timeframe} "
                              f"bar at or before {response.request.as_of.isoformat()}")
    as_of = response.request.as_of
    if quote is not None and (quote.instrument != response.request.instrument
                              or quote.as_of > as_of):
        raise MarketDataError(ErrorCode.MALFORMED_SOURCE,
                              "the quote response is for another instrument or a later as_of")
    candles = response.series.candles
    return VerifiedMarketSnapshot(
        snapshot_id=snapshot_id,
        instrument=response.request.instrument,
        timeframe=response.request.timeframe,
        as_of=as_of,
        created_at=created_at,
        latest_bar=candles[-1],
        latest_quote=quote.quote if quote else None,
        quote_source=quote.source if quote else None,
        quote_mapping=quote.mapping if quote else None,
        bar_count=len(candles),
        first_bar_open_time=candles[0].open_time,
        last_bar_close_time=candles[-1].close_time,
        series_hash=response.series.content_hash,
        source=response.source,
        mapping=response.mapping,
        quality=response.quality,
        freshness=response.freshness,
        provenance=Provenance(produced_by=DATA_VALIDATOR_ID, config_hash=config_hash),
    )
