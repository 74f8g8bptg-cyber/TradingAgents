"""Stellar-owned market data (Foundation Phase 2).

Provider-independent, point-in-time and precision-preserving. No indicators, no
strategy, no execution: this package only delivers validated bars and quotes.
"""

from stellar.marketdata.contracts import (
    DataIssue,
    ErrorCode,
    Freshness,
    FreshnessStatus,
    IssueCode,
    IssueSeverity,
    MarketDataError,
    MarketDataQuality,
    MarketDataRequest,
    MarketDataResponse,
    MarketDataSourceInfo,
    QuoteResponse,
    SourceKind,
    StaleReason,
    candle_columns,
    decimal_places,
)
from stellar.marketdata.freshness import Gap, evaluate_freshness, find_gaps
from stellar.marketdata.instruments import (
    INSTRUMENTS,
    ContractSpec,
    InstrumentSpec,
    PrecisionSpec,
    SessionSpec,
    get_instrument,
)
from stellar.marketdata.pointintime import (
    LookAheadError,
    assert_no_look_ahead,
    in_window,
    known_at,
    latest_quote_at,
)
from stellar.marketdata.snapshot import VerifiedMarketSnapshot, build_verified_snapshot
from stellar.marketdata.source import BaseMarketDataSource, MarketDataSource
from stellar.marketdata.symbols import (
    TRADINGAGENTS_YAHOO_REFERENCE,
    MappingKind,
    ProviderSymbolMapping,
    SubstitutionPolicy,
    SymbolMap,
)
from stellar.marketdata.timeframes import DURATIONS, duration, parse_timeframe
from stellar.marketdata.validation import (
    DuplicatePolicy,
    OrderPolicy,
    SeriesValidation,
    validate_series,
)

__all__ = [
    "DURATIONS",
    "INSTRUMENTS",
    "TRADINGAGENTS_YAHOO_REFERENCE",
    "BaseMarketDataSource",
    "ContractSpec",
    "DataIssue",
    "DuplicatePolicy",
    "ErrorCode",
    "Freshness",
    "FreshnessStatus",
    "Gap",
    "InstrumentSpec",
    "IssueCode",
    "IssueSeverity",
    "LookAheadError",
    "MappingKind",
    "MarketDataError",
    "MarketDataQuality",
    "MarketDataRequest",
    "MarketDataResponse",
    "MarketDataSource",
    "MarketDataSourceInfo",
    "OrderPolicy",
    "PrecisionSpec",
    "ProviderSymbolMapping",
    "QuoteResponse",
    "SeriesValidation",
    "SessionSpec",
    "SourceKind",
    "StaleReason",
    "SubstitutionPolicy",
    "SymbolMap",
    "VerifiedMarketSnapshot",
    "assert_no_look_ahead",
    "build_verified_snapshot",
    "candle_columns",
    "decimal_places",
    "duration",
    "evaluate_freshness",
    "find_gaps",
    "get_instrument",
    "in_window",
    "known_at",
    "latest_quote_at",
    "parse_timeframe",
    "validate_series",
]
