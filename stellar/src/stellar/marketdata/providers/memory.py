"""In-memory provider for tests, fixtures and future simulation or research runs.

It holds already-built ``Candle`` and ``Quote`` objects and serves them through
the same safety pipeline as every other provider (mapping, labels, validation,
point in time). Its source info should say ``synthetic=True`` unless the data is
real history.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from stellar.marketdata.contracts import MarketDataSourceInfo
from stellar.marketdata.instruments import InstrumentSpec
from stellar.marketdata.source import BaseMarketDataSource, Clock
from stellar.marketdata.symbols import ProviderSymbolMapping, SymbolMap
from stellar.marketdata.validation import DuplicatePolicy, OrderPolicy
from stellar.schemas.common import InstrumentId
from stellar.schemas.market import Candle, Quote, Timeframe


class InMemoryMarketDataSource(BaseMarketDataSource):
    def __init__(
        self,
        info: MarketDataSourceInfo,
        mappings: Iterable[ProviderSymbolMapping],
        candles: Mapping[tuple[InstrumentId, Timeframe], Sequence[Candle]],
        quotes: Mapping[InstrumentId, Sequence[Quote]] | None = None,
        *,
        clock: Clock | None = None,
        duplicate_policy: DuplicatePolicy = DuplicatePolicy.REJECT,
        order_policy: OrderPolicy = OrderPolicy.REJECT,
        instrument_specs: dict[InstrumentId, InstrumentSpec] | None = None,
    ) -> None:
        self._candles = {(InstrumentId(i), Timeframe(t)): tuple(v) for (i, t), v in candles.items()}
        self._quotes = {InstrumentId(i): tuple(v) for i, v in (quotes or {}).items()}
        super().__init__(info, SymbolMap(info.provider_id, mappings), clock=clock,
                         duplicate_policy=duplicate_policy, order_policy=order_policy,
                         instrument_specs=instrument_specs)

    def _available(self) -> dict[InstrumentId, tuple[Timeframe, ...]]:
        available: dict[InstrumentId, list[Timeframe]] = {}
        for instrument, timeframe in self._candles:
            available.setdefault(instrument, []).append(timeframe)
        for instrument in self._quotes:
            available.setdefault(instrument, [])
        order = list(Timeframe)
        return {i: tuple(sorted(tfs, key=order.index)) for i, tfs in available.items()}

    def _load_candles(self, instrument: InstrumentId, timeframe: Timeframe):
        return self._candles[(instrument, timeframe)], None, ()

    def _load_quotes(self, instrument: InstrumentId) -> tuple[Quote, ...]:
        if not self.info().supports_quotes:
            return super()._load_quotes(instrument)
        return self._quotes.get(instrument, ())
