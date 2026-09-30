"""Technical engine configuration. Every threshold, window and period is UNSET by default.

No canonical document approves a numeric technical value. The Foundation plan drops
ARIA's thresholds as defaults, and keeps EMA 9/21/50/200, RSI and MACD only as
concepts whose parameters are research. So:

- a value left ``None`` (or an empty tuple) is **UNSET**;
- the calculation or classification that needs it is not performed, and is reported
  as unevaluated with the missing setting;
- raw measurements that need no threshold (candle geometry, true range, bar
  relationships, run lengths) are always produced.

Tests use labelled synthetic configurations; none of their values is a default or a
recommendation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import Field, model_validator

from stellar.schemas.common import Label, NonNegativeDecimal, PositiveDecimal, StellarModel
from stellar.serialization import content_hash

Period = Annotated[int, Field(ge=1, le=10_000)]
Ratio = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]


class CandleConfig(StellarModel):
    """Body/wick thresholds are fractions of the bar's range; relative range is range divided
    by the mean range of the preceding ``relative_range_lookback`` bars."""

    doji_max_body_ratio: Ratio | None = None
    small_body_max_ratio: Ratio | None = None
    large_body_min_ratio: Ratio | None = None
    rejection_wick_min_ratio: Ratio | None = None
    relative_range_lookback: Period | None = None
    expansion_min_relative_range: PositiveDecimal | None = None
    contraction_max_relative_range: PositiveDecimal | None = None


class PivotConfig(StellarModel):
    """A swing needs ``left`` bars before and ``right`` bars after it (strictly exceeded)."""

    left: Period | None = None
    right: Period | None = None

    @property
    def configured(self) -> bool:
        return self.left is not None and self.right is not None


class ToleranceConfig(StellarModel):
    """A price tolerance, either in price units or as a multiple of ATR; at most one."""

    price: NonNegativeDecimal | None = None
    atr_multiple: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def _one(self) -> ToleranceConfig:
        if self.price is not None and self.atr_multiple is not None:
            raise ValueError("give the tolerance in price units or as an ATR multiple, not both")
        return self

    @property
    def configured(self) -> bool:
        return self.price is not None or self.atr_multiple is not None


class ConsolidationConfig(StellarModel):
    lookback: Period | None = None
    """Window of the most recent bars measured. None: no consolidation measurements."""
    max_range_atr: PositiveDecimal | None = None
    """Classify CONSOLIDATION only when the window range is at most this many ATRs ..."""
    min_overlap_ratio: Ratio | None = None
    """... and at least this fraction of consecutive bars overlap."""


class MacdSpec(StellarModel):
    fast: Period
    slow: Period
    signal: Period

    @model_validator(mode="after")
    def _order(self) -> MacdSpec:
        if self.fast >= self.slow:
            raise ValueError("the MACD fast period must be shorter than the slow period")
        return self


class BollingerSpec(StellarModel):
    period: Period
    deviations: PositiveDecimal


class IndicatorConfig(StellarModel):
    sma_periods: tuple[Period, ...] = ()
    ema_periods: tuple[Period, ...] = ()
    rsi_period: Period | None = None
    rsi_upper: Annotated[Decimal, Field(gt=0, lt=100)] | None = None
    rsi_lower: Annotated[Decimal, Field(gt=0, lt=100)] | None = None
    macd: MacdSpec | None = None
    bollinger: BollingerSpec | None = None

    @model_validator(mode="after")
    def _consistent(self) -> IndicatorConfig:
        for name in ("sma_periods", "ema_periods"):
            periods = getattr(self, name)
            if len(set(periods)) != len(periods):
                raise ValueError(f"{name} must be unique")
        if (self.rsi_upper is None) != (self.rsi_lower is None):
            raise ValueError("RSI zone levels are given together or not at all")
        if self.rsi_upper is not None and self.rsi_lower is not None and \
                self.rsi_lower >= self.rsi_upper:
            raise ValueError("rsi_lower must be below rsi_upper")
        return self


class TechnicalConfig(StellarModel):
    version: Label = "unset"
    test_only: bool = False
    candles: CandleConfig = CandleConfig()
    pivots: PivotConfig = PivotConfig()
    equal_tolerance: ToleranceConfig = ToleranceConfig()
    """Swing prices within this tolerance are EQUAL; unset: only exactly equal prices are."""
    zone_tolerance: ToleranceConfig = ToleranceConfig()
    """Support/resistance zones need a tolerance; unset: no zones."""
    atr_period: Period | None = None
    range_lookback: Period | None = None
    consolidation: ConsolidationConfig = ConsolidationConfig()
    indicators: IndicatorConfig = IndicatorConfig()
    relative_volume_lookback: Period | None = None
    allow_substitute_data: bool = False
    """Proxy or derived series (Phase 2) are refused unless explicitly allowed; if allowed,
    every analysis carries the PROXY_SOURCE / DERIVED_SOURCE limitation."""

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
