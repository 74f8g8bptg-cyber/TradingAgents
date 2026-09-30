"""Typed technical evidence (Foundation §4.9–§4.11; agents T3, T4, T5).

Two kinds of content, kept apart:
- **measurements** (facts): prices, differences, ratios, counts, timestamps;
- **descriptive labels**: named observations defined by an explicit rule
  (``INSIDE_BAR``, ``HH``, ``STRUCTURE_BREAK_UP``, ``RETEST_HELD``, ...).

Nothing here is a trade signal. There is no buy, sell, bias, entry, stop, target or
size field, and no label claims that anything is likely, strong or profitable.
``None`` always means *not computable* (unset configuration or insufficient history),
never zero.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from stellar.marketdata.symbols import MappingKind
from stellar.schemas.common import (
    SCHEMA_VERSION,
    AnalysisId,
    FiniteDecimal,
    InstrumentId,
    Label,
    NonNegativeDecimal,
    Price,
    Provenance,
    SchemaVersion,
    Sha256Hex,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import PriceSide, Timeframe, VolumeKind
from stellar.technical.config import TechnicalConfig

EvidenceId = Annotated[str, StringConstraints(pattern=r"^[a-z]+_[0-9a-f]{16}$")]


# ----------------------------------------------------------------- vocabulary --


class BarDirection(StrEnum):
    UP = "UP"          # close > open
    DOWN = "DOWN"      # close < open
    FLAT = "FLAT"      # close == open


class CandleLabel(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    DOJI_LIKE = "DOJI_LIKE"
    SMALL_BODY = "SMALL_BODY"
    LARGE_BODY = "LARGE_BODY"
    UPPER_REJECTION = "UPPER_REJECTION"
    LOWER_REJECTION = "LOWER_REJECTION"
    INSIDE_BAR = "INSIDE_BAR"
    OUTSIDE_BAR = "OUTSIDE_BAR"
    BULLISH_ENGULFING = "BULLISH_ENGULFING"
    BEARISH_ENGULFING = "BEARISH_ENGULFING"
    EXPANSION_BAR = "EXPANSION_BAR"
    CONTRACTION_BAR = "CONTRACTION_BAR"


class PivotKind(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class PivotStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANDIDATE = "CANDIDATE"
    """Beats its left window and every right-window bar closed so far, but the right
    window is not complete at ``as_of``. Never used by structure, legs or zones."""


class SwingLabel(StrEnum):
    HH = "HH"
    LH = "LH"
    EQH = "EQH"
    HL = "HL"
    LL = "LL"
    EQL = "EQL"


class StructureState(StrEnum):
    UP = "UP"                    # last swing high HH and last swing low HL
    DOWN = "DOWN"                # last swing high LH and last swing low LL
    RANGE = "RANGE"              # last swing high EQH and last swing low EQL
    MIXED = "MIXED"              # any other combination
    INSUFFICIENT = "INSUFFICIENT"


class StructureEventKind(StrEnum):
    STRUCTURE_BREAK_UP = "STRUCTURE_BREAK_UP"
    STRUCTURE_BREAK_DOWN = "STRUCTURE_BREAK_DOWN"


class LegDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"


class LegRole(StrEnum):
    WITH_STRUCTURE = "WITH_STRUCTURE"
    COUNTER_STRUCTURE = "COUNTER_STRUCTURE"
    UNCLASSIFIED = "UNCLASSIFIED"


class ZoneKind(StrEnum):
    SUPPORT = "SUPPORT"          # derived from swing lows only
    RESISTANCE = "RESISTANCE"    # derived from swing highs only
    MIXED = "MIXED"              # derived from both


class ZoneEventKind(StrEnum):
    CLOSE_ABOVE = "CLOSE_ABOVE"
    CLOSE_BELOW = "CLOSE_BELOW"
    WICK_ABOVE = "WICK_ABOVE"
    WICK_BELOW = "WICK_BELOW"
    RETEST_ATTEMPT = "RETEST_ATTEMPT"
    RETEST_HELD = "RETEST_HELD"
    RETEST_FAILED = "RETEST_FAILED"


class IndicatorKind(StrEnum):
    SMA = "SMA"
    EMA = "EMA"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER = "BOLLINGER"
    ATR = "ATR"


class Limitation(StrEnum):
    INSUFFICIENT_HISTORY = "insufficient_history"
    MISSING_VOLUME = "missing_volume"
    TICK_VOLUME_ONLY = "tick_volume_only"
    CALENDAR_NAIVE_CONTEXT = "calendar_naive_context"
    UNCONFIRMED_PIVOT = "unconfirmed_pivot"
    MISSING_TIMEFRAME = "missing_timeframe"
    PROXY_SOURCE = "proxy_source"
    DERIVED_SOURCE = "derived_source"
    PARTIAL_SERIES = "partial_series"
    GAP_DETECTED = "gap_detected"
    STALE_SOURCE = "stale_source"
    SYNTHETIC_SOURCE = "synthetic_source"
    THRESHOLD_UNSET = "threshold_unset"
    PIVOT_WINDOW_UNSET = "pivot_window_unset"


class Unevaluated(StellarModel):
    """A classification or calculation not performed, and why."""

    item: Label
    reason: Label  # e.g. "threshold_unset", "insufficient_history", "missing_volume"


# ------------------------------------------------------------------- candles --


class CandleFeatures(StellarModel):
    """Measurements of one closed bar. Ratios are None when the range is zero."""

    index: int = Field(ge=0)
    open_time: UtcDatetime
    close_time: UtcDatetime
    open: Price
    high: Price
    low: Price
    close: Price
    direction: BarDirection
    range: NonNegativeDecimal
    body: NonNegativeDecimal
    signed_body: FiniteDecimal
    upper_wick: NonNegativeDecimal
    lower_wick: NonNegativeDecimal
    body_ratio: NonNegativeDecimal | None = None
    upper_wick_ratio: NonNegativeDecimal | None = None
    lower_wick_ratio: NonNegativeDecimal | None = None
    close_location: NonNegativeDecimal | None = None
    """(close - low) / range: 0 at the low, 1 at the high."""
    gap: FiniteDecimal | None = None
    """open - previous close; None for the first bar."""
    true_range: NonNegativeDecimal
    true_range_uses_previous_close: bool
    relative_range: NonNegativeDecimal | None = None
    """range / mean range of the preceding ``relative_range_lookback`` bars."""


class CandleEvidence(StellarModel):
    features: CandleFeatures
    labels: tuple[CandleLabel, ...] = ()
    unevaluated: tuple[Unevaluated, ...] = ()


# -------------------------------------------------------------------- pivots --


class Pivot(StellarModel):
    evidence_id: EvidenceId
    kind: PivotKind
    status: PivotStatus
    index: int = Field(ge=0)
    bar_open_time: UtcDatetime
    bar_close_time: UtcDatetime
    price: Price
    left: int = Field(ge=1)
    right: int = Field(ge=1)
    confirmed_at: UtcDatetime | None = None
    """Close time of the bar that completed the right window; None for a CANDIDATE."""
    right_bars_seen: int = Field(ge=0)

    @model_validator(mode="after")
    def _consistent(self) -> Pivot:
        confirmed = self.status is PivotStatus.CONFIRMED
        if confirmed != (self.confirmed_at is not None):
            raise ValueError("confirmed_at is set exactly for a CONFIRMED pivot")
        if confirmed and self.right_bars_seen != self.right:
            raise ValueError("a confirmed pivot has seen its whole right window")
        if not confirmed and self.right_bars_seen >= self.right:
            raise ValueError("a candidate has not completed its right window")
        return self


# ----------------------------------------------------------------- structure --


class SwingPoint(StellarModel):
    pivot_id: EvidenceId
    kind: PivotKind
    label: SwingLabel | None = None
    """None for the first swing of its kind (nothing to compare with)."""
    price: Price
    previous_price: Price | None = None
    difference: FiniteDecimal | None = None
    tolerance: NonNegativeDecimal | None = None
    """The EQUAL tolerance at this swing's confirmation (ATR-based tolerances use the ATR of
    that bar). None when it could not be computed; the swing is then left unlabelled."""
    confirmed_at: UtcDatetime


class StructureEvent(StellarModel):
    kind: StructureEventKind
    reference_pivot_id: EvidenceId
    level: Price
    bar_index: int = Field(ge=0)
    bar_close_time: UtcDatetime
    close: Price


class MarketStructure(StellarModel):
    """Descriptive structure from CONFIRMED swings only. Not a trading bias."""

    swings: tuple[SwingPoint, ...] = ()
    state: StructureState
    last_swing_high: SwingPoint | None = None
    last_swing_low: SwingPoint | None = None
    events: tuple[StructureEvent, ...] = ()
    break_against_state: bool = False
    """The latest structure event is opposite to ``state`` (UP with a break down, or
    DOWN with a break up). An observation, not a claim of reversal."""
    equal_tolerance_method: Label  # "exact", "price" or "atr_multiple"


# ----------------------------------------------------- impulse / pullback --


class StructureLeg(StellarModel):
    """A move between two consecutive alternating confirmed swings (impulse measurements)."""

    evidence_id: EvidenceId
    direction: LegDirection
    role: LegRole
    start_pivot_id: EvidenceId
    end_pivot_id: EvidenceId
    start_time: UtcDatetime
    end_time: UtcDatetime
    start_price: Price
    end_price: Price
    bars: int = Field(ge=1)
    net_move: FiniteDecimal
    path_length: NonNegativeDecimal
    efficiency: NonNegativeDecimal | None = None
    """|net_move| / path_length (sum of |close change|); None when the path is zero."""
    cumulative_body: FiniteDecimal
    mean_range: NonNegativeDecimal
    range_expansion: NonNegativeDecimal | None = None
    """mean range in the leg / mean range of the preceding ``relative_range_lookback`` bars."""
    atr_normalised_move: FiniteDecimal | None = None
    """net_move / ATR at the leg's end bar."""
    confirmed_at: UtcDatetime


class Pullback(StellarModel):
    """Price action since the end of the last completed leg (the reference leg)."""

    reference_leg_id: EvidenceId
    reference_direction: LegDirection
    started_at: UtcDatetime
    bars: int = Field(ge=0)
    max_adverse_price: Price | None = None
    depth: NonNegativeDecimal | None = None
    """How far price moved against the reference leg from its end price."""
    retracement_ratio: NonNegativeDecimal | None = None
    """depth / |reference net move|; above 1 means price went beyond the leg's start."""
    current_retracement_ratio: FiniteDecimal | None = None
    counter_direction_bars: int = Field(ge=0)
    with_direction_bars: int = Field(ge=0)
    counter_body_total: NonNegativeDecimal
    with_body_total: NonNegativeDecimal
    mean_close_location: NonNegativeDecimal | None = None


class Consolidation(StellarModel):
    lookback: int = Field(ge=1)
    window_start: UtcDatetime
    window_end: UtcDatetime
    high: Price
    low: Price
    range: NonNegativeDecimal
    net_displacement: FiniteDecimal
    path_length: NonNegativeDecimal
    efficiency: NonNegativeDecimal | None = None
    overlap_ratio: NonNegativeDecimal | None = None
    """Fraction of consecutive bar pairs whose high-low ranges overlap."""
    mean_range: NonNegativeDecimal
    range_atr: NonNegativeDecimal | None = None
    is_consolidation: bool | None = None
    """None when the classification thresholds are unset."""


class SequenceEvidence(StellarModel):
    """Run lengths ending at the latest bar. No fixed N is assumed."""

    consecutive_up: int = Field(ge=0)
    consecutive_down: int = Field(ge=0)
    alternating: int = Field(ge=0)
    shrinking_bodies: int = Field(ge=0)
    expanding_bodies: int = Field(ge=0)
    shrinking_ranges: int = Field(ge=0)
    expanding_ranges: int = Field(ge=0)
    lower_highs: int = Field(ge=0)
    higher_lows: int = Field(ge=0)
    upper_rejections: int | None = None
    lower_rejections: int | None = None
    """None when the rejection threshold is unset."""


# ---------------------------------------------------------- zones / breakouts --


class ZoneEvent(StellarModel):
    kind: ZoneEventKind
    bar_index: int = Field(ge=0)
    bar_close_time: UtcDatetime


class PriceZone(StellarModel):
    evidence_id: EvidenceId
    kind: ZoneKind
    lower: Price
    upper: Price
    derivation: Label  # "confirmed_pivot_cluster"
    tolerance: NonNegativeDecimal
    tolerance_method: Label
    source_pivot_ids: tuple[EvidenceId, ...]
    first_known_at: UtcDatetime
    interactions: int = Field(ge=0)
    """Bars after ``first_known_at`` whose high-low range overlaps the zone."""
    last_tested_at: UtcDatetime | None = None
    events: tuple[ZoneEvent, ...] = ()
    state: Label = "untested"

    @model_validator(mode="after")
    def _bounds(self) -> PriceZone:
        if self.lower > self.upper:
            raise ValueError("a zone's lower bound cannot exceed its upper bound")
        return self


# --------------------------------------------------------- volatility / indicators --


class IndicatorValue(StellarModel):
    name: Label
    kind: IndicatorKind
    parameters: dict[str, str]
    warmup_bars: int = Field(ge=1)
    bars_available: int = Field(ge=0)
    ready: bool
    value: FiniteDecimal | None = None
    previous: FiniteDecimal | None = None
    slope: FiniteDecimal | None = None
    components: dict[str, FiniteDecimal | None] = Field(default_factory=dict)
    """MACD signal/histogram, Bollinger bands, ... (None while warming up)."""
    labels: tuple[Label, ...] = ()
    """Descriptive only (e.g. ``close_above``, ``rsi_above_upper``). No signals."""

    @model_validator(mode="after")
    def _ready(self) -> IndicatorValue:
        if self.ready != (self.value is not None):
            raise ValueError("a value exists exactly when the indicator is ready")
        if self.ready and self.bars_available < self.warmup_bars:
            raise ValueError("an indicator cannot be ready before its warm-up")
        return self


class Volatility(StellarModel):
    true_range: NonNegativeDecimal
    atr: IndicatorValue | None = None
    range_lookback: int | None = None
    mean_range: NonNegativeDecimal | None = None
    min_range: NonNegativeDecimal | None = None
    max_range: NonNegativeDecimal | None = None
    latest_relative_range: NonNegativeDecimal | None = None
    """Latest range / mean range of the preceding ``range_lookback`` bars (>1 expansion)."""


class VolumeEvidence(StellarModel):
    kind: VolumeKind
    available: bool
    latest: NonNegativeDecimal | None = None
    lookback: int | None = None
    relative_volume: NonNegativeDecimal | None = None
    """Latest volume / mean of the preceding ``lookback`` bars' volume (same kind)."""


# ------------------------------------------------------------------ analysis --


class SourceRef(StellarModel):
    provider_id: Label
    provider_symbol: ShortText
    mapping_kind: MappingKind
    price_side: PriceSide
    volume_kind: VolumeKind
    synthetic: bool
    response_as_of: UtcDatetime
    response_series_hash: Sha256Hex | None
    bars_used_hash: Sha256Hex
    bar_count: int = Field(ge=0)
    first_bar_open_time: UtcDatetime | None = None
    last_bar_close_time: UtcDatetime | None = None


class TechnicalAnalysis(StellarModel):
    """One deterministic, point-in-time technical reading of one instrument and timeframe."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    engine_version: Label
    analysis_id: AnalysisId
    content_hash: Sha256Hex
    instrument: InstrumentId
    timeframe: Timeframe
    as_of: UtcDatetime
    source: SourceRef
    config: TechnicalConfig
    config_hash: Sha256Hex
    candles: tuple[CandleEvidence, ...]
    pivots: tuple[Pivot, ...]
    structure: MarketStructure
    legs: tuple[StructureLeg, ...]
    pullback: Pullback | None = None
    consolidation: Consolidation | None = None
    sequences: SequenceEvidence | None = None
    volatility: Volatility | None = None
    indicators: tuple[IndicatorValue, ...]
    ma_ordering: tuple[Label, ...] | None = None
    """Configured moving averages from highest to lowest value; None unless all are ready."""
    volume: VolumeEvidence
    zones: tuple[PriceZone, ...]
    limitations: tuple[Limitation, ...]
    unevaluated: tuple[Unevaluated, ...]
    provenance: Provenance

    @model_validator(mode="after")
    def _point_in_time(self) -> TechnicalAnalysis:
        """Nothing in the analysis may be dated after ``as_of`` (no look-ahead)."""
        times = [c.features.close_time for c in self.candles]
        times += [p.confirmed_at or p.bar_close_time for p in self.pivots]
        times += [e.bar_close_time for e in self.structure.events]
        times += [z.first_known_at for z in self.zones]
        times += [z.last_tested_at for z in self.zones if z.last_tested_at is not None]
        times += [leg.confirmed_at for leg in self.legs]
        if any(t > self.as_of for t in times):
            raise ValueError("technical evidence dated after as_of (look-ahead)")
        if self.source.last_bar_close_time is not None and \
                self.source.last_bar_close_time > self.as_of:
            raise ValueError("a bar used closes after as_of")
        return self
