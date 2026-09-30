"""Publishing a technical analysis with the existing ``analysis.created`` event.

No new event name is needed. One ``TechnicalAnalysis`` is published as three Phase 1
``AnalysisReport`` records, one per facet and producing agent, each linked to the
Phase 2 ``VerifiedMarketSnapshot`` built from the same series:

| Facet | ``AnalysisKind`` | Agent |
|---|---|---|
| swings, structure, legs, pullback, zones | ``structure`` | T3 ``market_structure`` |
| indicators, volatility | ``momentum`` | T4 ``technical_indicator`` |
| candles, sequences, consolidation | ``price_action`` | T5 ``price_action`` |

Each event carries the technical analysis id and content hash, so the full evidence can
be recomputed and verified from the same bars, configuration and engine version. The
event is descriptive: no proposal, direction or order is created.
"""

from __future__ import annotations

from datetime import datetime

from stellar.journal import StellarJournal
from stellar.marketdata import VerifiedMarketSnapshot
from stellar.schemas.analysis import AnalysisKind, AnalysisReport
from stellar.schemas.common import Provenance
from stellar.technical.models import TechnicalAnalysis
from stellar.telemetry import EventBus, StellarEvent, new_event

FACETS = (
    (AnalysisKind.STRUCTURE, "market_structure"),
    (AnalysisKind.MOMENTUM, "technical_indicator"),
    (AnalysisKind.PRICE_ACTION, "price_action"),
)


class SnapshotMismatch(ValueError):
    """The snapshot does not describe the series the analysis was computed from."""


def technical_reports(analysis: TechnicalAnalysis, snapshot: VerifiedMarketSnapshot, *,
                      created_at: datetime) -> tuple[AnalysisReport, ...]:
    if (snapshot.instrument, snapshot.timeframe) != (analysis.instrument, analysis.timeframe):
        raise SnapshotMismatch("the snapshot is for another instrument or timeframe")
    if snapshot.series_hash != analysis.source.response_series_hash:
        raise SnapshotMismatch("the snapshot was built from another series")
    return tuple(
        AnalysisReport(
            analysis_id=f"{analysis.analysis_id}_{kind.value}", kind=kind,
            instrument=analysis.instrument, snapshot_id=snapshot.snapshot_id,
            as_of=analysis.as_of, created_at=created_at,
            provenance=Provenance(produced_by=agent, config_hash=analysis.config_hash,
                                  input_ids=(snapshot.snapshot_id, analysis.analysis_id)))
        for kind, agent in FACETS)


def publish_technical_analysis(journal: StellarJournal, analysis: TechnicalAnalysis,
                               snapshot: VerifiedMarketSnapshot, *, station_id: str,
                               created_at: datetime) -> list[StellarEvent]:
    bus = EventBus(journal)
    events = []
    for report, (_, agent) in zip(technical_reports(analysis, snapshot, created_at=created_at),
                                  FACETS, strict=True):
        event = new_event(
            "analysis.created", station_id=station_id, source="stellar.technical",
            agent_id=agent, instrument=analysis.instrument,
            correlation_id=analysis.analysis_id, ts=created_at,
            payload={"analysis_id": report.analysis_id, "kind": report.kind.value,
                     "technical_analysis_id": analysis.analysis_id,
                     "content_hash": analysis.content_hash,
                     "engine_version": analysis.engine_version,
                     "timeframe": analysis.timeframe.value,
                     "as_of": analysis.as_of.isoformat(),
                     "snapshot_id": snapshot.snapshot_id,
                     "structure_state": analysis.structure.state.value,
                     "limitations": [x.value for x in analysis.limitations],
                     "report": report.model_dump(mode="json")})
        stored = bus.publish(event)
        if stored is not None:
            events.append(stored)
    return events
