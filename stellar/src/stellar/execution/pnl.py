"""P&L: a price move becomes money only with explicit economics and, if needed, a rate.

- ``price_change`` (per unit, signed in the position's favour) is always known.
- Money needs the owner's ``InstrumentEconomics`` for the instrument; without it
  the status is MISSING_ECONOMICS and the amount is unknown (never zero).
- If the instrument's P&L currency is not the account currency, an explicit
  ``ConversionRate`` from that currency to the account currency, stamped at or
  before ``as_of``, is required. Rates are never inverted, chained or guessed;
  without one the status is MISSING_CONVERSION.
- No rounding is applied (currency rounding is an open decision, P4-5).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from stellar.execution.config import InstrumentEconomics
from stellar.execution.models import ConversionRate, PnL, PnlStatus
from stellar.execution.pricing import InvalidMarketInput
from stellar.schemas.common import OrderSide


def price_change(side: OrderSide, entry: Decimal, price: Decimal) -> Decimal:
    return price - entry if side is OrderSide.BUY else entry - price


def find_rate(conversions: Iterable[ConversionRate], base: str, quote: str,
              as_of: datetime) -> ConversionRate | None:
    matches = []
    for rate in conversions:
        if rate.as_of > as_of:
            raise InvalidMarketInput("a conversion rate is stamped after as_of (look-ahead)")
        if rate.base == base and rate.quote == quote:
            matches.append(rate)
    if len({(r.rate, r.as_of, r.source) for r in matches}) > 1:
        raise InvalidMarketInput(f"more than one {base}/{quote} rate was supplied")
    return matches[0] if matches else None


def compute_pnl(*, side: OrderSide, entry: Decimal, price: Decimal, volume: Decimal,
                economics: InstrumentEconomics | None, account_currency: str,
                conversions: Iterable[ConversionRate], as_of: datetime) -> PnL:
    change = price_change(side, entry, price)
    if economics is None:
        return PnL(price_change=change, status=PnlStatus.MISSING_ECONOMICS,
                   currency=account_currency)
    native = change * volume * economics.value_per_price_unit_per_lot
    base = {"price_change": change, "currency": account_currency,
            "instrument_currency": economics.pnl_currency, "instrument_amount": native}
    if economics.pnl_currency == account_currency:
        return PnL(**base, status=PnlStatus.KNOWN, amount=native)
    rate = find_rate(conversions, economics.pnl_currency, account_currency, as_of)
    if rate is None:
        return PnL(**base, status=PnlStatus.MISSING_CONVERSION)
    return PnL(**base, status=PnlStatus.KNOWN, amount=native * rate.rate, conversion=rate)


def risk_at_stop(*, entry: Decimal, stop: Decimal, volume: Decimal,
                 economics: InstrumentEconomics | None, account_currency: str) -> Decimal | None:
    """Loss at the stop in the account currency, only when no conversion is needed."""
    if economics is None or economics.pnl_currency != account_currency:
        return None
    return abs(entry - stop) * volume * economics.value_per_price_unit_per_lot
