"""The run ledger: V1 PAPER run checkpoints in the journal, and the fold that rebuilds a run.

The journal is the only source of truth. A run is:
- ``run.started`` (identity: instrument, timeframe, profile, ``as_of``, config hashes, and the
  operator inputs used by later re-authorisations);
- one ``run.stage.completed`` per stage execution (fingerprint, state, typed outputs, refs).
  A stage may have several (for example SETUP again once an approval arrives); the latest
  one is current, earlier ones stay as history;
- ``run.resumed`` each time an interrupted run continues;
- ``run.completed`` or ``run.failed`` once, when the run stops.

Every event carries the run id (the ``run_id`` field and ``correlation_id``). Nothing is
mutated or deleted; replaying the journal gives the same record.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from stellar.journal import StellarJournal
from stellar.runtime.models import (
    STAGE_ORDER,
    RunRecord,
    RunStage,
    RunState,
    RuntimeFailure,
    StageCheckpoint,
)
from stellar.telemetry import EventBus, StellarEvent, new_event

SOURCE = "stellar.runtime"
RUN_EVENTS = ("run.started", "run.stage.completed", "run.resumed", "run.completed",
              "run.failed")


class RunLedger:
    def __init__(self, journal: StellarJournal, *, station_id: str,
                 clock: Callable[[], datetime]) -> None:
        self._journal = journal
        self._bus = EventBus(journal)
        self._station = station_id
        self._clock = clock

    # ------------------------------------------------------------------- write --

    def emit(self, event_type: str, run_id: str, payload: dict[str, Any], *,
             instrument: str | None = None) -> StellarEvent | None:
        return self._bus.publish(new_event(
            event_type, station_id=self._station, source=SOURCE, agent_id="supervisor",
            instrument=instrument, run_id=run_id, correlation_id=run_id, ts=self._clock(),
            payload={"run_id": run_id, **payload}))

    def checkpoint(self, cp: StageCheckpoint, *, instrument: str) -> StageCheckpoint:
        data = cp.model_dump(mode="json", exclude={"seq", "ts", "run_id"})
        stored = self.emit("run.stage.completed", cp.run_id, data, instrument=instrument)
        assert stored is not None
        return cp.model_copy(update={"seq": stored.seq, "ts": stored.ts})

    # -------------------------------------------------------------------- read --

    def events(self, run_id: str) -> list[StellarEvent]:
        return self._journal.read(run_id=run_id, types=RUN_EVENTS)

    def started(self, run_id: str) -> StellarEvent | None:
        return next(iter(self._journal.read(run_id=run_id, types=["run.started"], limit=1)),
                    None)

    def checkpoints(self, run_id: str) -> dict[RunStage, StageCheckpoint]:
        latest: dict[RunStage, StageCheckpoint] = {}
        for e in self._journal.read(run_id=run_id, types=["run.stage.completed"]):
            body = {k: v for k, v in e.payload.items() if k != "run_id"}
            cp = StageCheckpoint.model_validate({**body, "run_id": run_id, "seq": e.seq,
                                                 "ts": e.ts})
            latest[cp.stage] = cp
        return latest

    def run_ids(self) -> list[str]:
        return [e.payload["run_id"] for e in self._journal.read(types=["run.started"])]

    def record(self, run_id: str) -> RunRecord | None:
        """The run from its own events only (the paper book overlay is the runtime's)."""
        events = self.events(run_id)
        if not events or events[0].type != "run.started":
            return None
        start = events[0].payload
        cps = self.checkpoints(run_id)
        refs: dict[str, str | None] = {}
        for stage in STAGE_ORDER:
            if stage in cps:
                refs.update(cps[stage].refs)
        ordered = sorted(cps.values(), key=lambda c: c.seq or 0)
        state, stage, failure, detail = RunState.CREATED, None, None, None
        if ordered:
            last = ordered[-1]
            state, stage, failure, detail = last.state, last.stage, last.failure, last.detail
        finished = None
        for e in events:
            if e.type in ("run.completed", "run.failed"):
                state = RunState(e.payload["state"])
                failure = RuntimeFailure(e.payload["failure"]) if e.payload.get("failure") \
                    else failure
                detail = e.payload.get("detail") or detail
                refs.update(e.payload.get("refs") or {})
                finished = e.ts
        return RunRecord(
            run_id=run_id, instrument=start["instrument"], timeframe=start["timeframe"],
            profile=start.get("profile"), as_of=start["as_of"],
            workflow_version=start["workflow_version"], config_hashes=start["config_hashes"],
            state=state, stage=stage, failure=failure, detail=detail, refs=refs,
            stages=tuple(sorted(cps.values(), key=lambda c: STAGE_ORDER.index(c.stage))),
            started_at=events[0].ts, finished_at=finished,
            resumed=sum(e.type == "run.resumed" for e in events))

    def finished(self, run_id: str) -> bool:
        return bool(self._journal.read(run_id=run_id, types=["run.completed", "run.failed"],
                                       limit=1))
