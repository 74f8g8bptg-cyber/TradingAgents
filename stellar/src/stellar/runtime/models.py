"""The V1 PAPER run contract: request, stages, states, failures, checkpoints, run record.

**Stages** run in a fixed order; each writes one checkpoint (``run.stage.completed``) with
its input fingerprint, the state the run reached, typed outputs and references:

| Stage | Component (unchanged) | State reached |
|---|---|---|
| MARKET_DATA | Phase 2 source → ``VerifiedMarketSnapshot`` | MARKET_DATA_READY |
| TECHNICAL | Phase 5 ``analyse`` | TECHNICAL_COMPLETE |
| RESEARCH | Phase 6 ``ResearchPipeline`` | RESEARCH_COMPLETE |
| SETUP | Phase 6b ``TraderDesk`` (setup + selection) | SETUP_COMPLETE, or a stop state |
| PROPOSAL | Phase 6b P1 builder (inside the desk) | PROPOSAL_CREATED |
| RISK | Phase 3 ``RiskService.evaluate`` | RISK_REVIEWED, REVIEW_REQUIRED or REJECTED |
| ORDER_AUTHORISATION | Phase 3 ``authorize_intent`` | ORDER_AUTHORISED |
| PAPER_SUBMISSION | Phase 4 ``PaperBroker.submit`` | PAPER_SUBMITTED / POSITION_OPEN / … |

After submission the run's state follows the paper order, position and trade, all read from
the Phase 4 journal-backed book: PAPER_SUBMITTED (PENDING), ORDER_BLOCKED (BLOCKED),
POSITION_OPEN, then COMPLETED when the trade closes, or CANCELLED / EXPIRED / ORDER_REJECTED.

**Stop states** (the run ends there; none is an error unless ``failure`` says so):
- NO_SETUP: the desk found no setup (including INSUFFICIENT / CONFLICTING evidence,
  INVALIDATED, EXPIRED). A successful outcome;
- SETUP_CANDIDATE: a setup, but no proposal (not ready, no selection, the Trader declined, or
  a builder refusal, then with ``PROPOSAL_FAILED``);
- AWAITING_APPROVAL: parked; the run resumes when an approval is supplied;
- REVIEW_REQUIRED, REJECTED: Phase 3 outcomes; nothing is authorised or submitted;
- BLOCKED: authorisation or submission refused for safety (stale context, breaker, preflight);
- FAILED: a stage could not run (typed ``RuntimeFailure``).

Nothing here decides a trade: states only record what the components returned.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from stellar.proposals.models import Approval, LevelSelection
from stellar.research import CalendarValue, CollectionResult
from stellar.runtime.config import OperatorRiskInputs
from stellar.schemas.common import (
    InstrumentId,
    Label,
    RunId,
    Sha256Hex,
    ShortText,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import Timeframe
from stellar.schemas.research import ClaimLabel


class RunStage(StrEnum):
    MARKET_DATA = "MARKET_DATA"
    TECHNICAL = "TECHNICAL"
    RESEARCH = "RESEARCH"
    SETUP = "SETUP"
    PROPOSAL = "PROPOSAL"
    RISK = "RISK"
    ORDER_AUTHORISATION = "ORDER_AUTHORISATION"
    PAPER_SUBMISSION = "PAPER_SUBMISSION"


STAGE_ORDER = tuple(RunStage)


class RunState(StrEnum):
    CREATED = "CREATED"
    MARKET_DATA_READY = "MARKET_DATA_READY"
    TECHNICAL_COMPLETE = "TECHNICAL_COMPLETE"
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    SETUP_COMPLETE = "SETUP_COMPLETE"
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    RISK_REVIEWED = "RISK_REVIEWED"
    ORDER_AUTHORISED = "ORDER_AUTHORISED"
    PAPER_SUBMITTED = "PAPER_SUBMITTED"
    ORDER_BLOCKED = "ORDER_BLOCKED"
    POSITION_OPEN = "POSITION_OPEN"
    COMPLETED = "COMPLETED"
    NO_SETUP = "NO_SETUP"
    SETUP_CANDIDATE = "SETUP_CANDIDATE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    ORDER_REJECTED = "ORDER_REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset({
    RunState.COMPLETED, RunState.NO_SETUP, RunState.SETUP_CANDIDATE, RunState.REVIEW_REQUIRED,
    RunState.REJECTED, RunState.BLOCKED, RunState.ORDER_REJECTED, RunState.CANCELLED,
    RunState.EXPIRED, RunState.FAILED})
"""No further stage runs. AWAITING_APPROVAL is parked (it resumes with an approval);
PAPER_SUBMITTED, ORDER_BLOCKED and POSITION_OPEN move on with later market inputs."""

LIVE_ORDER_STATES = frozenset({RunState.PAPER_SUBMITTED, RunState.ORDER_BLOCKED,
                               RunState.POSITION_OPEN})


class RuntimeFailure(StrEnum):
    MARKET_DATA_FAILED = "MARKET_DATA_FAILED"
    TECHNICAL_FAILED = "TECHNICAL_FAILED"
    RESEARCH_FAILED = "RESEARCH_FAILED"
    SETUP_FAILED = "SETUP_FAILED"
    PROPOSAL_FAILED = "PROPOSAL_FAILED"
    RISK_REVIEW_REQUIRED = "RISK_REVIEW_REQUIRED"
    RISK_REJECTED = "RISK_REJECTED"
    RISK_FAILED = "RISK_FAILED"
    ORDER_AUTHORISATION_FAILED = "ORDER_AUTHORISATION_FAILED"
    PAPER_BROKER_FAILED = "PAPER_BROKER_FAILED"
    PAPER_PREFLIGHT_FAILED = "PAPER_PREFLIGHT_FAILED"
    CHECKPOINT_CONFLICT = "CHECKPOINT_CONFLICT"
    STALE_CONTEXT = "STALE_CONTEXT"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"


class RunRequest(StellarModel):
    """Everything one PAPER run is asked to do, except the approval (a later owner or PM
    decision that does not change what the run analyses)."""

    instrument: InstrumentId
    as_of: UtcDatetime
    collections: tuple[CollectionResult, ...]
    declared_labels: dict[str, ClaimLabel] = {}
    calendar: tuple[CalendarValue, ...] = ()
    operator: OperatorRiskInputs = OperatorRiskInputs()
    approval: Approval | None = None
    owner_selection: LevelSelection | None = None

    def identity(self) -> dict[str, Any]:
        return {"instrument": self.instrument.value, "as_of": self.as_of.isoformat(),
                "collections": [c.model_dump(mode="json") for c in self.collections],
                "declared": sorted((k, v.value) for k, v in self.declared_labels.items()),
                "calendar": [c.model_dump(mode="json") for c in self.calendar],
                "operator": self.operator.identity()}


class StageCheckpoint(StellarModel):
    run_id: RunId
    stage: RunStage
    fingerprint: Sha256Hex
    state: RunState
    failure: RuntimeFailure | None = None
    detail: ShortText | None = None
    refs: dict[str, str | None] = {}
    outputs: dict[str, Any] = {}
    seq: int | None = None
    ts: UtcDatetime | None = None


class RunRecord(StellarModel):
    """The run as reconstructed from the journal (checkpoints + the paper book)."""

    run_id: RunId
    instrument: InstrumentId
    timeframe: Timeframe
    profile: Label | None = None
    as_of: UtcDatetime
    workflow_version: Label
    config_hashes: dict[str, Sha256Hex]
    state: RunState
    stage: RunStage | None = None
    """The last completed stage."""
    failure: RuntimeFailure | None = None
    detail: ShortText | None = None
    refs: dict[str, str | None] = Field(default_factory=dict)
    """Every reference the stages produced: snapshot id, technical analysis id and hash,
    research run id and outputs hash, setup id and fingerprint, proposal id, risk decision id
    and fingerprint, intent id, order id, position id, trade id."""
    stages: tuple[StageCheckpoint, ...] = ()
    started_at: UtcDatetime | None = None
    finished_at: UtcDatetime | None = None
    resumed: int = 0

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES
