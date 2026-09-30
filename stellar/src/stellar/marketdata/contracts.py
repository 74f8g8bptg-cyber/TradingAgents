"""Provider-agnostic market-data contracts (Phase 2).

``Candle``, ``Quote``, ``CandleSeries`` and ``Timeframe`` are the Phase 1
contracts in ``stellar.schemas.market``; this module adds the request/response
envelope around them. A ``MarketDataResponse`` cannot be constructed if it would
break a safety rule: bars after ``as_of``, bars of another instrument or
timeframe, a proxy the request did not allow, an unlabelled proxy, or data with
validation errors.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from stellar.marketdata.symbols import MappingKind, ProviderSymbolMapping, SubstitutionPolicy
from stellar.schemas.common import (
    SCHEMA_VERSION,
    InstrumentId,
    Label,
    SchemaVersion,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import (
    Candle,
    CandleSeries,
    DataQualityFlag,
    PriceSide,
    Quote,
    Timeframe,
    VolumeKind,
)

# ----------------------------------------------------------------- errors ---


class ErrorCode(StrEnum):
    UNKNOWN_INSTRUMENT = "UNKNOWN_INSTRUMENT"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"
    UNSUPPORTED_TIMEFRAME = "UNSUPPORTED_TIMEFRAME"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    PROXY_NOT_ALLOWED = "PROXY_NOT_ALLOWED"
    DERIVED_NOT_ALLOWED = "DERIVED_NOT_ALLOWED"
    NO_DATA = "NO_DATA"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MALFORMED_SOURCE = "MALFORMED_SOURCE"


class MarketDataError(Exception):
    """A typed market-data failure. ``issues`` lists the validation problems, if any."""

    def __init__(self, code: ErrorCode, detail: str, issues: Iterable[DataIssue] = ()) -> None:
        self.code = ErrorCode(code)
        self.detail = detail
        self.issues = tuple(issues)
        super().__init__(f"{self.code.value}: {detail}")

    def to_record(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "detail": self.detail,
            "issues": [i.model_dump(mode="json") for i in self.issues],
        }


# ------------------------------------------------------------ data quality ---


class IssueSeverity(StrEnum):
    ERROR = "ERROR"
    """The data is rejected."""
    WARNING = "WARNING"
    """The data is kept and flagged."""


class IssueCode(StrEnum):
    MALFORMED_ROW = "MALFORMED_ROW"
    MISSING_COLUMN = "MISSING_COLUMN"
    INVALID_NUMBER = "INVALID_NUMBER"
    INVALID_PRICE_RELATION = "INVALID_PRICE_RELATION"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    NAIVE_TIMESTAMP = "NAIVE_TIMESTAMP"
    AMBIGUOUS_LOCAL_TIME = "AMBIGUOUS_LOCAL_TIME"
    NONEXISTENT_LOCAL_TIME = "NONEXISTENT_LOCAL_TIME"
    INSTRUMENT_MISMATCH = "INSTRUMENT_MISMATCH"
    TIMEFRAME_MISMATCH = "TIMEFRAME_MISMATCH"
    WRONG_DURATION = "WRONG_DURATION"
    NOT_CLOSED = "NOT_CLOSED"
    DUPLICATE_BAR = "DUPLICATE_BAR"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    OVERLAPPING_BARS = "OVERLAPPING_BARS"
    GAP_DETECTED = "GAP_DETECTED"
    MISSING_VOLUME = "MISSING_VOLUME"
    PRECISION_EXCEEDS_DECLARED = "PRECISION_EXCEEDS_DECLARED"
    SOURCE_PRECISION_LOSS = "SOURCE_PRECISION_LOSS"


class DataIssue(StellarModel):
    code: IssueCode
    severity: IssueSeverity
    message: ShortText
    row: int | None = Field(default=None, ge=1)
    open_time: UtcDatetime | None = None


class MarketDataQuality(StellarModel):
    flags: tuple[DataQualityFlag, ...] = ()
    issues: tuple[DataIssue, ...] = ()
    bar_count: int = Field(ge=0)
    gap_count: int = Field(default=0, ge=0)
    observed_price_decimals: int | None = Field(default=None, ge=0)
    declared_price_decimals: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _sorted_unique_flags(self) -> MarketDataQuality:
        if list(self.flags) != sorted(set(self.flags), key=lambda f: f.value):
            raise ValueError("flags must be unique and sorted (deterministic serialization)")
        return self

    @property
    def has_errors(self) -> bool:
        return any(i.severity is IssueSeverity.ERROR for i in self.issues)


def sorted_flags(flags: Iterable[DataQualityFlag]) -> tuple[DataQualityFlag, ...]:
    return tuple(sorted(set(flags), key=lambda f: f.value))


# -------------------------------------------------------------- freshness ---


class FreshnessStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    """No staleness threshold is configured, so none is claimed."""
    NO_DATA = "NO_DATA"


class StaleReason(StrEnum):
    OLDER_THAN_MAX_INTERVALS = "OLDER_THAN_MAX_INTERVALS"
    NO_SOURCE_TIMESTAMP = "NO_SOURCE_TIMESTAMP"


class Freshness(StellarModel):
    as_of: UtcDatetime
    retrieved_at: UtcDatetime
    source_timestamp: UtcDatetime | None = None
    """Newest bar close time (or quote time) in the response."""
    expected_interval_seconds: int | None = Field(default=None, ge=1)
    intervals_behind: int | None = Field(default=None, ge=0)
    max_staleness_intervals: int | None = Field(default=None, ge=1)
    status: FreshnessStatus
    stale_reason: StaleReason | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Freshness:
        if self.source_timestamp is not None and self.source_timestamp > self.as_of:
            raise ValueError("source_timestamp cannot be after as_of (look-ahead)")
        if (self.status is FreshnessStatus.STALE) != (self.stale_reason is not None):
            raise ValueError("a stale reason is given exactly when the status is STALE")
        if self.status is FreshnessStatus.NO_DATA and self.source_timestamp is not None:
            raise ValueError("NO_DATA has no source timestamp")
        return self


# ---------------------------------------------------------- source / request ---


class SourceKind(StrEnum):
    LOCAL_FILE = "LOCAL_FILE"
    IN_MEMORY = "IN_MEMORY"
    HISTORICAL_API = "HISTORICAL_API"
    BROKER = "BROKER"


class MarketDataSourceInfo(StellarModel):
    """What a provider is, and what it can and cannot do."""

    provider_id: Label
    name: ShortText
    kind: SourceKind
    price_side: PriceSide
    volume_kind: VolumeKind
    declared_price_decimals: int | None = Field(default=None, ge=0, le=12)
    timestamp_convention: ShortText = "bar open time, UTC"
    daily_boundary: ShortText | None = None
    """How the provider's D1/W1 bars are cut (Foundation §4.7); ``None`` if not declared."""
    supports_quotes: bool = False
    limitations: tuple[ShortText, ...] = ()
    synthetic: bool = False
    """True for test or simulated data that must never be read as market history."""


class MarketDataRequest(StellarModel):
    """A point-in-time request. Only bars with ``close_time <= as_of`` are ever returned."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    instrument: InstrumentId
    timeframe: Timeframe
    as_of: UtcDatetime
    start: UtcDatetime | None = None
    end: UtcDatetime | None = None
    """Bars whose ``open_time`` is in ``[start, end]``, further bounded by ``as_of``."""
    substitution: SubstitutionPolicy = SubstitutionPolicy()
    max_staleness_intervals: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _window(self) -> MarketDataRequest:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must not be after end")
        if self.start is not None and self.start > self.as_of:
            raise ValueError("start must not be after as_of")
        return self


class MarketDataResponse(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    request: MarketDataRequest
    source: MarketDataSourceInfo
    mapping: ProviderSymbolMapping
    series: CandleSeries | None = None
    quality: MarketDataQuality
    freshness: Freshness
    retrieved_at: UtcDatetime

    @model_validator(mode="after")
    def _safe(self) -> MarketDataResponse:
        req = self.request
        if self.mapping.instrument != req.instrument:
            raise ValueError("the mapping is for another instrument")
        if self.mapping.provider_id != self.source.provider_id:
            raise ValueError("the mapping belongs to another provider")
        if self.mapping.kind is MappingKind.UNSUPPORTED:
            raise ValueError("an unsupported mapping cannot produce data")
        if not req.substitution.permits(self.mapping.kind):
            raise ValueError(f"{self.mapping.kind.value} data was not allowed by the request")
        if self.quality.has_errors:
            raise ValueError("a response cannot carry data with validation errors")
        flags = set(self.quality.flags)
        if (self.mapping.kind is MappingKind.PROXY) != (DataQualityFlag.PROXY_SOURCE in flags):
            raise ValueError("PROXY_SOURCE is flagged exactly when the mapping is a proxy")
        if (self.mapping.kind is MappingKind.DERIVED) != (DataQualityFlag.DERIVED_SOURCE in flags):
            raise ValueError("DERIVED_SOURCE is flagged exactly when the mapping is derived")
        if self.freshness.as_of != req.as_of or self.freshness.retrieved_at != self.retrieved_at:
            raise ValueError("freshness must describe this request")
        candles = self.series.candles if self.series is not None else ()
        if self.quality.bar_count != len(candles):
            raise ValueError("bar_count must equal the number of bars")
        substitute = self.mapping.kind is not MappingKind.EXACT
        for candle in candles:
            if candle.instrument != req.instrument or candle.timeframe != req.timeframe:
                raise ValueError("every bar must match the requested instrument and timeframe")
            if candle.close_time > req.as_of:
                raise ValueError("a bar closes after as_of (look-ahead)")
            if not candle.is_closed:
                raise ValueError("responses carry closed bars only")
            if req.start is not None and candle.open_time < req.start:
                raise ValueError("a bar opens before the requested start")
            if req.end is not None and candle.open_time > req.end:
                raise ValueError("a bar opens after the requested end")
            if candle.provider_symbol != self.mapping.provider_symbol:
                raise ValueError("every bar must carry the provider symbol actually used")
            if candle.source != self.source.provider_id:
                raise ValueError("every bar must name its provider")
            if candle.proxy != substitute:
                raise ValueError("a substitute bar must be labelled proxy=True, an exact bar not")
        return self


class QuoteResponse(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    instrument: InstrumentId
    as_of: UtcDatetime
    source: MarketDataSourceInfo
    mapping: ProviderSymbolMapping
    quote: Quote
    retrieved_at: UtcDatetime

    @model_validator(mode="after")
    def _safe(self) -> QuoteResponse:
        if self.quote.instrument != self.instrument or self.mapping.instrument != self.instrument:
            raise ValueError("quote and mapping must match the instrument")
        if self.quote.ts > self.as_of:
            raise ValueError("the quote is stamped after as_of (look-ahead)")
        if self.quote.provider_symbol != self.mapping.provider_symbol:
            raise ValueError("the quote must carry the provider symbol actually used")
        if self.quote.proxy != (self.mapping.kind is not MappingKind.EXACT):
            raise ValueError("a substitute quote must be labelled proxy=True")
        if self.mapping.kind is MappingKind.UNSUPPORTED:
            raise ValueError("an unsupported mapping cannot produce data")
        return self


# ------------------------------------------------------------ normalized access ---

CANDLE_COLUMNS = ("open_time", "close_time", "open", "high", "low", "close", "volume",
                  "tick_volume")


def candle_columns(candles: Iterable[Candle]) -> dict[str, tuple[Any, ...]]:
    """Column-oriented, order-preserving view for research code. Values are the
    original ``datetime`` / ``Decimal`` objects (or ``None``); nothing is converted."""
    rows = list(candles)
    return {name: tuple(getattr(c, name) for c in rows) for name in CANDLE_COLUMNS}


def decimal_places(value: Decimal) -> int:
    """Number of decimal places written in a Decimal (``1.08537`` → 5, ``2385`` → 0)."""
    exponent = value.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def latest_close_time(candles: Iterable[Candle]) -> datetime | None:
    times = [c.close_time for c in candles]
    return max(times) if times else None
