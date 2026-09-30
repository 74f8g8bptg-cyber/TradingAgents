"""The deterministic technical engine: one validated Phase 2 series in, typed evidence out.

``analyse(response, as_of=..., config=...)``:
- **Input:** a Phase 2 ``MarketDataResponse`` (validated bars, their source, mapping,
  quality and freshness). The engine never fetches, resamples or synthesises bars.
- **Point in time:**
  - only bars that are closed and have ``close_time <= as_of`` are used;
  - ``as_of`` may not be after the response's own ``as_of`` (bars in between would be
    unknown, not absent);
  - every downstream step (pivot confirmation, structure, zones, indicators) works on
    those bars alone.
- **Substitutes:** proxy or derived series are refused unless
  ``config.allow_substitute_data``; if allowed, they are labelled as limitations.
- **Determinism:** no clock, no randomness, no network, no model. Arithmetic is
  Decimal under one explicit context (``numeric``). ``content_hash`` is the canonical
  hash of everything except the id and the hash; ``analysis_id`` is derived from it.
  Same bars + config + ``as_of`` + engine version → same analysis, byte for byte.
"""

from __future__ import annotations

from datetime import datetime

from stellar.marketdata import MarketDataResponse
from stellar.marketdata.contracts import FreshnessStatus
from stellar.marketdata.symbols import MappingKind
from stellar.schemas.common import Provenance
from stellar.schemas.market import CandleSeries, DataQualityFlag, VolumeKind
from stellar.serialization import content_hash
from stellar.technical.candles import candle_features, classify
from stellar.technical.config import TechnicalConfig
from stellar.technical.indicators import indicators, ma_ordering
from stellar.technical.legs import consolidation, legs, pullback
from stellar.technical.levels import zone_tolerance, zones
from stellar.technical.models import (
    Limitation,
    PivotStatus,
    SourceRef,
    StructureState,
    TechnicalAnalysis,
    Unevaluated,
)
from stellar.technical.numeric import calc
from stellar.technical.pivots import confirmed, find_pivots
from stellar.technical.sequences import sequences
from stellar.technical.structure import market_structure
from stellar.technical.volatility import atr_series, volatility
from stellar.technical.volume import volume_evidence

ENGINE_VERSION = "phase5_1"
TECHNICAL_ENGINE_ID = "technical_engine"


class TechnicalInputError(ValueError):
    """The input cannot be analysed without breaking a point-in-time or data rule."""


def analyse(response: MarketDataResponse, *, as_of: datetime, config: TechnicalConfig,
            snapshot_id: str | None = None) -> TechnicalAnalysis:
    with calc():
        return _analyse(MarketDataResponse.model_validate(response.model_dump()), as_of,
                        TechnicalConfig.model_validate(config.model_dump()), snapshot_id)


def _analyse(response: MarketDataResponse, as_of: datetime, config: TechnicalConfig,
             snapshot_id: str | None) -> TechnicalAnalysis:
    request = response.request
    if as_of.tzinfo is None:
        raise TechnicalInputError("as_of must be timezone-aware")
    if as_of > request.as_of:
        raise TechnicalInputError("as_of is after the data's as_of: later bars are unknown")
    kind = response.mapping.kind
    if kind is not MappingKind.EXACT and not config.allow_substitute_data:
        raise TechnicalInputError(f"{kind.value} data is refused unless explicitly allowed")
    series = response.series
    candles = [c for c in (series.candles if series else ())
               if c.is_closed and c.close_time <= as_of]
    if not candles:
        raise TechnicalInputError("no closed bar at or before as_of")

    unevaluated: list[Unevaluated] = []
    limitations: set[Limitation] = {Limitation.CALENDAR_NAIVE_CONTEXT}
    insufficient = False

    features = candle_features(candles, config.candles)
    evidence = classify(features, config.candles)
    seen = set()
    for e in evidence:
        for item in e.unevaluated:
            if item.reason == "threshold_unset" and item.item not in seen:
                seen.add(item.item)
                unevaluated.append(item)

    atr = None
    if config.atr_period is None:
        unevaluated.append(Unevaluated(item="atr", reason="period_unset"))
    else:
        atr = atr_series(features, config.atr_period)
        insufficient |= atr[-1] is None
    latest_atr = atr[-1] if atr else None

    pivots = []
    if config.pivots.configured:
        pivots = find_pivots(candles, config.pivots.left, config.pivots.right)  # type: ignore[arg-type]
        if any(p.status is PivotStatus.CANDIDATE for p in pivots):
            limitations.add(Limitation.UNCONFIRMED_PIVOT)
    else:
        limitations.add(Limitation.PIVOT_WINDOW_UNSET)
        unevaluated.append(Unevaluated(item="pivots", reason="pivot_window_unset"))
    swing_points = confirmed(pivots)
    structure = market_structure(features, swing_points, config.equal_tolerance, atr)
    if config.pivots.configured and structure.state is StructureState.INSUFFICIENT:
        insufficient = True
    legs_ = legs(features, swing_points, structure.state,
                 lookback=config.candles.relative_range_lookback, atr=atr)
    pull = pullback(features, legs_, swing_points)

    cons = consolidation(features, config.consolidation, latest_atr)
    if config.consolidation.lookback is None:
        unevaluated.append(Unevaluated(item="consolidation", reason="lookback_unset"))
    elif cons is None:
        insufficient = True
        unevaluated.append(Unevaluated(item="consolidation", reason="insufficient_history"))
    elif cons.is_consolidation is None:
        unevaluated.append(Unevaluated(
            item="consolidation_classification",
            reason="threshold_unset" if config.consolidation.max_range_atr is None
            or config.consolidation.min_overlap_ratio is None else "insufficient_history"))

    closes = [f.close for f in features]
    values = indicators(closes, config.indicators)
    if not values:
        unevaluated.append(Unevaluated(item="indicators", reason="none_configured"))
    insufficient |= any(not v.ready for v in values)

    tol = zone_tolerance(config.zone_tolerance, latest_atr)
    zones_ = []
    if not config.zone_tolerance.configured:
        unevaluated.append(Unevaluated(item="zones", reason="tolerance_unset"))
    elif tol is None:
        insufficient = True
        unevaluated.append(Unevaluated(item="zones", reason="insufficient_history"))
    else:
        zones_ = zones(features, swing_points, tol, config.zone_tolerance)

    volume = volume_evidence(candles, config.relative_volume_lookback)
    if not volume.available:
        limitations.add(Limitation.MISSING_VOLUME)
        unevaluated.append(Unevaluated(item="volume", reason="missing_volume"))
    elif volume.kind is VolumeKind.TICK:
        limitations.add(Limitation.TICK_VOLUME_ONLY)

    flags = set(response.quality.flags)
    for flag, limitation in ((DataQualityFlag.PARTIAL_SERIES, Limitation.PARTIAL_SERIES),
                             (DataQualityFlag.GAP_DETECTED, Limitation.GAP_DETECTED),
                             (DataQualityFlag.PROXY_SOURCE, Limitation.PROXY_SOURCE),
                             (DataQualityFlag.DERIVED_SOURCE, Limitation.DERIVED_SOURCE)):
        if flag in flags:
            limitations.add(limitation)
    if response.freshness.status is FreshnessStatus.STALE:
        limitations.add(Limitation.STALE_SOURCE)
    if response.source.synthetic:
        limitations.add(Limitation.SYNTHETIC_SOURCE)
    if insufficient:
        limitations.add(Limitation.INSUFFICIENT_HISTORY)
    if any(u.reason == "threshold_unset" for u in unevaluated):
        limitations.add(Limitation.THRESHOLD_UNSET)

    source = SourceRef(
        provider_id=response.source.provider_id,
        provider_symbol=response.mapping.provider_symbol, mapping_kind=kind,
        price_side=response.source.price_side, volume_kind=response.source.volume_kind,
        synthetic=response.source.synthetic, response_as_of=request.as_of,
        response_series_hash=series.content_hash if series else None,
        bars_used_hash=CandleSeries.hash_candles(candles), bar_count=len(candles),
        first_bar_open_time=candles[0].open_time, last_bar_close_time=candles[-1].close_time)
    body = {
        "engine_version": ENGINE_VERSION, "instrument": request.instrument,
        "timeframe": request.timeframe, "as_of": as_of, "source": source, "config": config,
        "config_hash": config.config_hash(), "candles": tuple(evidence), "pivots": tuple(pivots),
        "structure": structure, "legs": tuple(legs_), "pullback": pull, "consolidation": cons,
        "sequences": sequences(evidence,
                               rejection_configured=config.candles.rejection_wick_min_ratio
                               is not None),
        "volatility": volatility(features, atr_period=config.atr_period,
                                 range_lookback=config.range_lookback, atr=atr),
        "indicators": tuple(values), "ma_ordering": ma_ordering(values), "volume": volume,
        "zones": tuple(zones_),
        "limitations": tuple(sorted(limitations, key=lambda x: x.value)),
        "unevaluated": tuple(unevaluated),
        "provenance": Provenance(produced_by=TECHNICAL_ENGINE_ID,
                                 config_hash=config.config_hash(),
                                 input_ids=(snapshot_id,) if snapshot_id else ()),
    }
    draft = TechnicalAnalysis.model_validate(
        {**body, "analysis_id": "an_pending", "content_hash": "0" * 64})
    digest = content_hash(draft.model_dump(mode="json", exclude={"analysis_id", "content_hash"}))
    return draft.model_copy(update={"analysis_id": f"an_{digest[:40]}", "content_hash": digest})


def verify(analysis: TechnicalAnalysis) -> bool:
    """True when ``content_hash`` and ``analysis_id`` match the analysis content."""
    digest = content_hash(analysis.model_dump(mode="json", exclude={"analysis_id",
                                                                    "content_hash"}))
    return digest == analysis.content_hash and analysis.analysis_id == f"an_{digest[:40]}"
