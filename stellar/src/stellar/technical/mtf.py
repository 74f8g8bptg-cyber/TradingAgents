"""Multi-timeframe evidence: the same ``as_of`` on every timeframe, closed bars only.

Each timeframe is analysed independently with the same ``as_of``. A higher-timeframe bar
that has not closed at ``as_of`` is simply absent: an H4 bar that is still forming
contributes nothing. No bar of one timeframe is built from another (no resampling).

Per timeframe the reading reports:
- whether it is available, and the analysis id and hash;
- the last closed bar's close time, and how many timeframe intervals ``as_of`` is past it
  (a calendar-naive number, not a staleness verdict);
- the structure state.

Alignment compares the structure states of the available timeframes whose state is
UP, DOWN, RANGE or MIXED:
- fewer than two → INSUFFICIENT;
- all UP / all DOWN / all RANGE → AGREE_UP / AGREE_DOWN / AGREE_RANGE;
- anything else → DISAGREE.

Missing timeframes are listed and carried as a limitation. This is evidence about
agreement, not a bias or a trading decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from pydantic import Field

from stellar.marketdata import MarketDataResponse
from stellar.marketdata.timeframes import DURATIONS
from stellar.schemas.common import (
    AnalysisId,
    FiniteDecimal,
    InstrumentId,
    Sha256Hex,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import Timeframe
from stellar.serialization import content_hash
from stellar.technical.config import TechnicalConfig
from stellar.technical.engine import TechnicalInputError, analyse
from stellar.technical.models import Limitation, StructureState, TechnicalAnalysis
from stellar.technical.numeric import calc


class Alignment(StrEnum):
    AGREE_UP = "AGREE_UP"
    AGREE_DOWN = "AGREE_DOWN"
    AGREE_RANGE = "AGREE_RANGE"
    DISAGREE = "DISAGREE"
    INSUFFICIENT = "INSUFFICIENT"


class TimeframeReading(StellarModel):
    timeframe: Timeframe
    available: bool
    analysis_id: AnalysisId | None = None
    content_hash: Sha256Hex | None = None
    last_closed_bar_close_time: UtcDatetime | None = None
    intervals_since_last_close: FiniteDecimal | None = None
    structure_state: StructureState | None = None
    unavailable_reason: str | None = Field(default=None, max_length=200)


class MultiTimeframeAnalysis(StellarModel):
    instrument: InstrumentId
    as_of: UtcDatetime
    readings: tuple[TimeframeReading, ...]
    alignment: Alignment
    missing_timeframes: tuple[Timeframe, ...]
    limitations: tuple[Limitation, ...]
    analyses: tuple[TechnicalAnalysis, ...]
    content_hash: Sha256Hex


_AGREE = {StructureState.UP: Alignment.AGREE_UP, StructureState.DOWN: Alignment.AGREE_DOWN,
          StructureState.RANGE: Alignment.AGREE_RANGE}


def analyse_mtf(instrument: str, responses: Mapping[Timeframe, MarketDataResponse | None], *,
                timeframes: Sequence[Timeframe], as_of: datetime,
                config: TechnicalConfig) -> MultiTimeframeAnalysis:
    """``timeframes`` lists the timeframes wanted, in any order; readings are ordered from
    the longest timeframe to the shortest."""
    ordered = sorted(set(timeframes), key=lambda tf: DURATIONS[tf], reverse=True)
    readings, analyses, missing = [], [], []
    for tf in ordered:
        response = responses.get(tf)
        if response is None:
            missing.append(tf)
            readings.append(TimeframeReading(timeframe=tf, available=False,
                                             unavailable_reason="no_data_supplied"))
            continue
        if response.request.timeframe is not tf or response.request.instrument != instrument:
            raise TechnicalInputError(f"the {tf.value} response is for another series")
        try:
            analysis = analyse(response, as_of=as_of, config=config)
        except TechnicalInputError as exc:
            missing.append(tf)
            readings.append(TimeframeReading(timeframe=tf, available=False,
                                             unavailable_reason=str(exc)[:200]))
            continue
        analyses.append(analysis)
        last = analysis.source.last_bar_close_time
        assert last is not None
        micro = timedelta(microseconds=1)
        with calc():  # exact integer microseconds; no float division
            behind = Decimal((as_of - last) // micro) / Decimal(DURATIONS[tf] // micro)
        readings.append(TimeframeReading(
            timeframe=tf, available=True, analysis_id=analysis.analysis_id,
            content_hash=analysis.content_hash, last_closed_bar_close_time=last,
            intervals_since_last_close=behind,
            structure_state=analysis.structure.state))
    comparable = [r.structure_state for r in readings if r.available and r.structure_state
                  in (StructureState.UP, StructureState.DOWN, StructureState.RANGE,
                      StructureState.MIXED)]
    if len(comparable) < 2:
        alignment = Alignment.INSUFFICIENT
    elif len(set(comparable)) == 1 and comparable[0] in _AGREE:
        alignment = _AGREE[comparable[0]]
    else:
        alignment = Alignment.DISAGREE
    limitations = {Limitation.CALENDAR_NAIVE_CONTEXT}
    if missing:
        limitations.add(Limitation.MISSING_TIMEFRAME)
    body = {"instrument": instrument, "as_of": as_of, "readings": tuple(readings),
            "alignment": alignment, "missing_timeframes": tuple(missing),
            "limitations": tuple(sorted(limitations, key=lambda x: x.value)),
            "analyses": tuple(analyses)}
    draft = MultiTimeframeAnalysis.model_validate({**body, "content_hash": "0" * 64})
    digest = content_hash(draft.model_dump(mode="json", exclude={"content_hash"}))
    return draft.model_copy(update={"content_hash": digest})

