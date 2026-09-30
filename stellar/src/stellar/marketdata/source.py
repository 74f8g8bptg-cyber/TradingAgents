"""The market-data provider interface (Foundation §4.1) and its shared safety pipeline.

Every provider answers through ``BaseMarketDataSource``, so every provider gets
the same guarantees:

1. **Mapping first.** The request's canonical instrument is resolved through the
   provider's declared mapping. UNSUPPORTED → error. PROXY or DERIVED → error
   unless the request's ``SubstitutionPolicy`` explicitly allows it.
2. **Source consistency.** Every bar must carry the provider id, the mapped
   provider symbol and the matching ``proxy`` label, or the source is malformed.
3. **Validation.** The whole loaded series is validated (``validate_series``);
   any ERROR rejects the request with every issue listed. Nothing is repaired.
4. **Point in time.** Only bars with ``close_time <= as_of`` are kept, then the
   ``[start, end]`` window is applied.
5. **Quality and freshness.** Flags (proxy, gaps, missing volume, partial
   coverage, staleness) and freshness are computed deterministically.

Foundation §4.1 names ``candles(instrument, timeframe, start, end, as_of)``;
here those arguments travel in one ``MarketDataRequest``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from stellar.marketdata.contracts import (
    DataIssue,
    ErrorCode,
    FreshnessStatus,
    IssueCode,
    IssueSeverity,
    MarketDataError,
    MarketDataQuality,
    MarketDataRequest,
    MarketDataResponse,
    MarketDataSourceInfo,
    QuoteResponse,
    sorted_flags,
)
from stellar.marketdata.freshness import evaluate_freshness
from stellar.marketdata.instruments import InstrumentSpec, get_instrument
from stellar.marketdata.pointintime import in_window, known_at, latest_quote_at
from stellar.marketdata.symbols import (
    MappingKind,
    ProviderSymbolMapping,
    SubstitutionPolicy,
    SymbolMap,
)
from stellar.marketdata.timeframes import duration
from stellar.marketdata.validation import DuplicatePolicy, OrderPolicy, validate_series
from stellar.schemas.common import InstrumentId
from stellar.schemas.market import Candle, CandleSeries, DataQualityFlag, Quote, Timeframe

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@runtime_checkable
class MarketDataSource(Protocol):
    """What every Stellar market-data provider offers."""

    def info(self) -> MarketDataSourceInfo: ...

    def instruments(self) -> tuple[InstrumentId, ...]: ...

    def timeframes(self, instrument: InstrumentId) -> tuple[Timeframe, ...]: ...

    def mapping(self, instrument: InstrumentId) -> ProviderSymbolMapping: ...

    def metadata(self, instrument: InstrumentId) -> InstrumentSpec: ...

    def candles(self, request: MarketDataRequest) -> MarketDataResponse: ...

    def quote(
        self, instrument: InstrumentId, as_of: datetime,
        substitution: SubstitutionPolicy = ...,
    ) -> QuoteResponse: ...


class BaseMarketDataSource(ABC):
    """Shared pipeline; subclasses only load raw bars (and optionally quotes)."""

    def __init__(
        self,
        info: MarketDataSourceInfo,
        symbol_map: SymbolMap,
        *,
        clock: Clock | None = None,
        duplicate_policy: DuplicatePolicy = DuplicatePolicy.REJECT,
        order_policy: OrderPolicy = OrderPolicy.REJECT,
        instrument_specs: dict[InstrumentId, InstrumentSpec] | None = None,
    ) -> None:
        if symbol_map.provider_id != info.provider_id:
            raise ValueError("the symbol map belongs to another provider")
        self._info = info
        self._symbols = symbol_map
        self._clock = clock or _utc_now
        self._duplicate_policy = duplicate_policy
        self._order_policy = order_policy
        self._specs = instrument_specs or {}

    # ------------------------------------------------------------- subclass API --

    @abstractmethod
    def _available(self) -> dict[InstrumentId, tuple[Timeframe, ...]]:
        """Instruments and timeframes this provider can serve."""

    @abstractmethod
    def _load_candles(
        self, instrument: InstrumentId, timeframe: Timeframe
    ) -> tuple[tuple[Candle, ...], tuple[int, ...] | None, tuple[DataIssue, ...]]:
        """All raw bars, their source rows (or ``None``) and load-time issues."""

    def _declared_price_decimals(self, instrument: InstrumentId, timeframe: Timeframe) -> int | None:
        return self._info.declared_price_decimals

    def _load_quotes(self, instrument: InstrumentId) -> tuple[Quote, ...]:
        raise MarketDataError(ErrorCode.UNSUPPORTED_OPERATION,
                              f"{self._info.provider_id} does not serve quotes")

    # --------------------------------------------------------------- public API --

    def info(self) -> MarketDataSourceInfo:
        return self._info

    def instruments(self) -> tuple[InstrumentId, ...]:
        return tuple(sorted(self._available(), key=lambda i: i.value))

    def timeframes(self, instrument: InstrumentId) -> tuple[Timeframe, ...]:
        return self._available().get(InstrumentId(instrument), ())

    def mapping(self, instrument: InstrumentId) -> ProviderSymbolMapping:
        return self._symbols.get(InstrumentId(instrument))

    def metadata(self, instrument: InstrumentId) -> InstrumentSpec:
        instrument = InstrumentId(instrument)
        return self._specs.get(instrument) or get_instrument(instrument)

    def candles(self, request: MarketDataRequest) -> MarketDataResponse:
        mapping = self._resolve(request.instrument, request.substitution)
        if request.timeframe not in self.timeframes(request.instrument):
            raise MarketDataError(ErrorCode.UNSUPPORTED_TIMEFRAME,
                                  f"{self._info.provider_id} has no {request.timeframe} data "
                                  f"for {request.instrument}")
        raw, rows, load_issues = self._load_candles(request.instrument, request.timeframe)
        self._check_source_labels(raw, mapping)

        spec = self.metadata(request.instrument)
        full = validate_series(
            raw, instrument=request.instrument, timeframe=request.timeframe,
            duplicate_policy=self._duplicate_policy, order_policy=self._order_policy,
            declared_price_decimals=self._declared_price_decimals(request.instrument,
                                                                  request.timeframe),
            instrument_price_decimals=spec.precision.price_decimals, rows=rows,
        )
        issues = (*load_issues, *full.issues)
        if full.has_errors or any(i.severity is IssueSeverity.ERROR for i in load_issues):
            raise MarketDataError(ErrorCode.VALIDATION_FAILED,
                                  f"{request.instrument} {request.timeframe} from "
                                  f"{self._info.provider_id} failed validation", issues)

        selected = in_window(known_at(full.candles, request.as_of), request.start, request.end)
        # Gaps and missing volume are re-derived for the slice actually returned;
        # source-level handling (sorting, dropped duplicates) is carried over.
        sliced = validate_series(selected, instrument=request.instrument,
                                 timeframe=request.timeframe) if selected else None
        flags = set(sliced.flags if sliced else ())
        flags |= {f for f in full.flags if f in {DataQualityFlag.OUT_OF_ORDER,
                                                  DataQualityFlag.DUPLICATE_BAR,
                                                  DataQualityFlag.SOURCE_PRECISION_LOSS}}
        if mapping.kind is MappingKind.PROXY:
            flags.add(DataQualityFlag.PROXY_SOURCE)
        if mapping.kind is MappingKind.DERIVED:
            flags.add(DataQualityFlag.DERIVED_SOURCE)
        if selected and self._partial(selected, request):
            flags.add(DataQualityFlag.PARTIAL_SERIES)

        retrieved_at = self._clock()
        freshness = evaluate_freshness(
            as_of=request.as_of, retrieved_at=retrieved_at,
            source_timestamp=selected[-1].close_time if selected else None,
            timeframe=request.timeframe,
            max_staleness_intervals=request.max_staleness_intervals,
        )
        if freshness.status is FreshnessStatus.STALE:
            flags.add(DataQualityFlag.STALE)

        # Source-level warnings (handled duplicates, sorting, precision) are kept;
        # gap and volume warnings come from the returned slice only.
        rederived = {IssueCode.GAP_DETECTED, IssueCode.MISSING_VOLUME}
        kept_issues = tuple(i for i in issues if i.code not in rederived)
        quality = MarketDataQuality(
            flags=sorted_flags(flags),
            issues=(*kept_issues, *(sliced.issues if sliced else ())),
            bar_count=len(selected),
            gap_count=len(sliced.gaps) if sliced else 0,
            observed_price_decimals=sliced.observed_price_decimals if sliced else None,
            declared_price_decimals=self._declared_price_decimals(request.instrument,
                                                                  request.timeframe),
        )
        return MarketDataResponse(
            request=request, source=self._info, mapping=mapping,
            series=CandleSeries.build(request.timeframe, list(selected)) if selected else None,
            quality=quality, freshness=freshness, retrieved_at=retrieved_at,
        )

    def quote(
        self,
        instrument: InstrumentId,
        as_of: datetime,
        substitution: SubstitutionPolicy | None = None,
    ) -> QuoteResponse:
        instrument = InstrumentId(instrument)
        mapping = self._resolve(instrument, substitution or SubstitutionPolicy())
        quotes = self._load_quotes(instrument)
        for q in quotes:
            if (q.instrument != instrument or q.source != self._info.provider_id
                    or q.provider_symbol != mapping.provider_symbol
                    or q.proxy != (mapping.kind is not MappingKind.EXACT)):
                raise MarketDataError(ErrorCode.MALFORMED_SOURCE,
                                      "a quote does not carry this provider's mapping labels")
        latest = latest_quote_at(quotes, as_of)
        if latest is None:
            raise MarketDataError(ErrorCode.NO_DATA,
                                  f"no {instrument} quote at or before {as_of.isoformat()}")
        return QuoteResponse(instrument=instrument, as_of=as_of, source=self._info,
                             mapping=mapping, quote=latest, retrieved_at=self._clock())

    # ----------------------------------------------------------------- helpers --

    def _resolve(self, instrument: InstrumentId, policy: SubstitutionPolicy) -> ProviderSymbolMapping:
        try:
            instrument = InstrumentId(instrument)
        except ValueError:
            raise MarketDataError(ErrorCode.UNKNOWN_INSTRUMENT,
                                  f"{instrument!r} is not a canonical Stellar instrument") from None
        mapping = self._symbols.get(instrument)
        if mapping.kind is MappingKind.UNSUPPORTED or instrument not in self._available():
            raise MarketDataError(ErrorCode.UNSUPPORTED_INSTRUMENT,
                                  f"{self._info.provider_id} has no data for {instrument}")
        if mapping.kind is MappingKind.PROXY and not policy.allow_proxy:
            raise MarketDataError(
                ErrorCode.PROXY_NOT_ALLOWED,
                f"{self._info.provider_id} only has a proxy for {instrument}: "
                f"{mapping.provider_symbol} ({mapping.description}); pass "
                f"SubstitutionPolicy(allow_proxy=True) to use it explicitly")
        if mapping.kind is MappingKind.DERIVED and not policy.allow_derived:
            raise MarketDataError(
                ErrorCode.DERIVED_NOT_ALLOWED,
                f"{self._info.provider_id} only has derived data for {instrument}: "
                f"{mapping.description}; pass SubstitutionPolicy(allow_derived=True)")
        return mapping

    def _check_source_labels(self, candles: tuple[Candle, ...], mapping: ProviderSymbolMapping) -> None:
        substitute = mapping.kind is not MappingKind.EXACT
        for c in candles:
            if (c.source != self._info.provider_id or c.provider_symbol != mapping.provider_symbol
                    or c.proxy != substitute):
                raise MarketDataError(
                    ErrorCode.MALFORMED_SOURCE,
                    f"a bar does not carry {self._info.provider_id}'s labels "
                    f"(source, provider symbol {mapping.provider_symbol}, proxy={substitute})")

    @staticmethod
    def _partial(selected: tuple[Candle, ...], request: MarketDataRequest) -> bool:
        step = duration(request.timeframe)
        if request.start is not None and selected[0].open_time - request.start >= step:
            return True
        if request.end is not None:
            end_bound = min(request.end + step, request.as_of)
            if end_bound - selected[-1].close_time >= step:
                return True
        return False

