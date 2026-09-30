"""Execution prices: pure, deterministic, from explicit market input only.

- **A quote** gives exact prices: BUY executes at the ask, SELL at the bid; the
  spread is ``ask - bid``. A mid price is never used for an execution.
- **A bar** is on one price side (``Candle.price_side``). An execution on that side
  uses the bar as it is. The other side needs the owner's explicit synthetic
  spread (``SYNTHETIC_FIXED``); a mid or last bar needs it for both sides (half
  each way). Without it the price is unavailable: no spread is ever invented.
- **Slippage** is ZERO or the owner's FIXED value, always adverse.
- **Input checks.** No proxy prices; no quote stamped, or bar closed, after
  ``as_of``; only closed bars.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from stellar.execution.config import SlippageMode, SlippageModel, SpreadMode, SpreadModel
from stellar.execution.models import PriceSource, SlippageSource, SpreadSource
from stellar.schemas.common import InstrumentId, OrderSide
from stellar.schemas.market import Candle, PriceSide, Quote

MarketInput = Quote | Candle


class InvalidMarketInput(ValueError):
    """The market input cannot be used at all (a caller error; nothing is journaled)."""


class PriceUnavailable(ValueError):
    """No execution price can be derived without inventing one."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class SidePrices:
    """One input seen from one executing side."""

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    spread: Decimal | None
    spread_source: SpreadSource
    price_source: PriceSource
    start: datetime
    """A quote's instant, or a bar's open time."""
    end: datetime
    """A quote's instant, or a bar's close time."""
    source: str
    provider_symbol: str


def check_input(market: MarketInput, as_of: datetime, *,
                max_quote_age_seconds: int | None = None) -> None:
    if not isinstance(market, Quote | Candle):
        raise InvalidMarketInput("market input must be a Quote or a Candle")
    if market.proxy:
        raise InvalidMarketInput("a proxy price cannot execute a paper order")
    if isinstance(market, Quote):
        if market.ts > as_of:
            raise InvalidMarketInput("the quote is stamped after as_of (look-ahead)")
        if max_quote_age_seconds is not None and \
                (as_of - market.ts).total_seconds() > max_quote_age_seconds:
            raise InvalidMarketInput("the quote is older than max_quote_age_seconds")
    else:
        if not market.is_closed:
            raise InvalidMarketInput("only closed bars are used")
        if market.close_time > as_of:
            raise InvalidMarketInput("the bar closes after as_of (look-ahead)")


def input_window(market: MarketInput) -> tuple[datetime, datetime]:
    if isinstance(market, Quote):
        return market.ts, market.ts
    return market.open_time, market.close_time


def side_prices(market: MarketInput, side: OrderSide, spread: SpreadModel) -> SidePrices:
    start, end = input_window(market)
    if isinstance(market, Quote):
        price = market.ask if side is OrderSide.BUY else market.bid
        return SidePrices(price, price, price, price, market.ask - market.bid,
                          SpreadSource.QUOTE, PriceSource.QUOTE, start, end, market.source,
                          market.provider_symbol)
    ohlc = (market.open, market.high, market.low, market.close)
    native = {OrderSide.BUY: PriceSide.ASK, OrderSide.SELL: PriceSide.BID}[side]
    if market.price_side is native:
        return SidePrices(*ohlc, None, SpreadSource.BAR_SIDE, PriceSource.BAR, start, end,
                          market.source, market.provider_symbol)
    synthetic = _synthetic(spread, market.instrument)
    # A mid or last bar is half a spread from each side; a bar on the other side, a whole one.
    two_sided = market.price_side in {PriceSide.MID, PriceSide.LAST}
    shift = synthetic / 2 if two_sided else synthetic
    signed = shift if side is OrderSide.BUY else -shift
    shifted = tuple(p + signed for p in ohlc)
    if min(shifted) <= 0:
        raise PriceUnavailable("synthetic_price_not_positive")
    return SidePrices(*shifted, synthetic, SpreadSource.SYNTHETIC, PriceSource.BAR, start, end,
                      market.source, market.provider_symbol)


def _synthetic(spread: SpreadModel, instrument: InstrumentId) -> Decimal:
    if spread.mode is not SpreadMode.SYNTHETIC_FIXED:
        raise PriceUnavailable("spread_unavailable")
    value = spread.synthetic.get(instrument)
    if value is None:
        raise PriceUnavailable("spread_unavailable")
    return value


def slippage_for(model: SlippageModel, instrument: InstrumentId) -> tuple[Decimal,
                                                                          SlippageSource]:
    if model.mode is SlippageMode.ZERO:
        return Decimal(0), SlippageSource.ZERO
    value = model.fixed.get(instrument)
    if value is None:
        raise PriceUnavailable("slippage_unavailable")
    return value, SlippageSource.FIXED


def adverse(price: Decimal, slippage: Decimal, side: OrderSide) -> Decimal:
    """Apply slippage against the executing side: a BUY pays more, a SELL receives less."""
    result = price + slippage if side is OrderSide.BUY else price - slippage
    if result <= 0:
        raise PriceUnavailable("slipped_price_not_positive")
    return result


def opposite(side: OrderSide) -> OrderSide:
    return OrderSide.SELL if side is OrderSide.BUY else OrderSide.BUY
