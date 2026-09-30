"""Decimal arithmetic for technical calculations.

Every calculation runs in ``Decimal`` under one explicit context, never in float:
- **Precision:** 34 significant digits (the IEEE 754 decimal128 precision). Only
  division and square root can produce more digits than their inputs.
- **Rounding:** ROUND_HALF_EVEN, applied only by those operations, at 34 digits.
- **No quantisation:** market prices are never rounded to a fixed number of decimals.
  Sums and differences of prices stay exact. A value's digits beyond the source's
  precision can only come from division or square root.

``calc()`` is the context manager every public entry point uses, so results do not
depend on the caller's ambient decimal context.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

CALC_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
ZERO = Decimal(0)


def calc():
    return localcontext(CALC_CONTEXT)


def mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("mean of no values")
    return sum(values, ZERO) / len(values)


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """``numerator / denominator``, or None when the denominator is zero (never a fake 0)."""
    return None if denominator == 0 else numerator / denominator


def total(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)
