"""The typed Setup contract (Foundation §4.12) and its evidence-derived level options.

**Status and lifecycle.** ``SetupStatus`` is what one evaluation found. ``SetupState`` is the
canonical §4.12 lifecycle. Each status maps to exactly one state:

| Status | State | Meaning |
|---|---|---|
| NO_SETUP | NO_SETUP | no directional pullback structure |
| INSUFFICIENT_EVIDENCE | NO_SETUP | the evidence cannot support a setup |
| CONFLICTING_EVIDENCE | NO_SETUP | the evidence disagrees; the disagreement is kept, not averaged |
| CANDIDATE | WATCHING | a directional setup exists, but something required for a proposal is missing |
| READY_FOR_PROPOSAL | ARMED | every input a proposal needs is present, except the selection and the approval |
| INVALIDATED | INVALIDATED | the setup's invalidation level was breached |
| EXPIRED | EXPIRED | ``valid_until`` has passed |

PROPOSED is set only when the builder has built a proposal. APPROVED, REJECTED and FILLED
belong to the Risk Engine and the broker; nothing in this layer sets them.

**Direction** is LONG, SHORT or NONE. There is no Buy / Sell here: the upstream rating's
"Sell" means "avoid the position", never "go short" (Foundation L8, R-1).

**Numbers.** Every price in an option comes from Phase 5 evidence, the market snapshot or the
setup configuration, and names its sources and evidence ids. No option holds a number taken
from model text.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from stellar.pipeline.records import ChallengeKind, EvidenceGrade, RunStatus
from stellar.reasoning.contracts import Stance
from stellar.schemas.common import (
    SCHEMA_VERSION,
    Direction,
    InstrumentId,
    Label,
    NonNegativeDecimal,
    PositiveDecimal,
    Price,
    ResearchSnapshotId,
    RunId,
    SchemaVersion,
    SetupId,
    Sha256Hex,
    StellarModel,
    UtcDatetime,
)
from stellar.schemas.market import Timeframe
from stellar.setups.config import EntryModelKind
from stellar.technical.mtf import Alignment

OptionId = Annotated[str, StringConstraints(pattern=r"^opt_[0-9a-f]{16}$")]
EvidenceRef = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,6}_[0-9a-f]{16}$")]


class SetupStatus(StrEnum):
    NO_SETUP = "NO_SETUP"
    CANDIDATE = "CANDIDATE"
    READY_FOR_PROPOSAL = "READY_FOR_PROPOSAL"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class SetupState(StrEnum):
    """Foundation §4.12 lifecycle states."""

    NO_SETUP = "NO_SETUP"
    WATCHING = "WATCHING"
    ARMED = "ARMED"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


STATE_FOR_STATUS: dict[SetupStatus, SetupState] = {
    SetupStatus.NO_SETUP: SetupState.NO_SETUP,
    SetupStatus.INSUFFICIENT_EVIDENCE: SetupState.NO_SETUP,
    SetupStatus.CONFLICTING_EVIDENCE: SetupState.NO_SETUP,
    SetupStatus.CANDIDATE: SetupState.WATCHING,
    SetupStatus.READY_FOR_PROPOSAL: SetupState.ARMED,
    SetupStatus.INVALIDATED: SetupState.INVALIDATED,
    SetupStatus.EXPIRED: SetupState.EXPIRED,
}


class SetupDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

    def trade_direction(self) -> Direction | None:
        return None if self is SetupDirection.NONE else Direction(self.value)


class SetupType(StrEnum):
    """Only the canonical first strategy family (Foundation §4.11, §7.2) is defined:
    a pullback against the last with-structure leg, in the direction of the structure.
    Other setup families have no canonical definition and are not classified."""

    PULLBACK_CONTINUATION = "PULLBACK_CONTINUATION"


class NumericSource(StrEnum):
    """Where a number in an option came from. There is no LLM source."""

    PHASE5_PIVOT = "PHASE5_PIVOT"
    PHASE5_ZONE = "PHASE5_ZONE"
    PHASE5_ATR = "PHASE5_ATR"
    MARKET_QUOTE = "MARKET_QUOTE"
    SETUP_CONFIG = "SETUP_CONFIG"


class LevelRole(StrEnum):
    ENTRY = "ENTRY"
    STOP = "STOP"
    TARGET = "TARGET"


class OptionKind(StrEnum):
    MARKET_AT_QUOTE = "MARKET_AT_QUOTE"
    LIMIT_AT_ZONE = "LIMIT_AT_ZONE"
    STRUCTURE_STOP = "STRUCTURE_STOP"
    """Beyond the reference leg's start swing (the setup's invalidation level)."""
    ATR_STOP = "ATR_STOP"
    """``atr_stop_multiple`` × ATR from the chosen entry's far edge; resolved at build time."""
    PRIOR_SWING_TARGET = "PRIOR_SWING_TARGET"
    """The reference leg's end swing (where the pullback started)."""
    ZONE_TARGET = "ZONE_TARGET"
    """The near edge of an opposing Phase 5 zone beyond the prior swing."""


ROLE_FOR_KIND: dict[OptionKind, LevelRole] = {
    OptionKind.MARKET_AT_QUOTE: LevelRole.ENTRY,
    OptionKind.LIMIT_AT_ZONE: LevelRole.ENTRY,
    OptionKind.STRUCTURE_STOP: LevelRole.STOP,
    OptionKind.ATR_STOP: LevelRole.STOP,
    OptionKind.PRIOR_SWING_TARGET: LevelRole.TARGET,
    OptionKind.ZONE_TARGET: LevelRole.TARGET,
}

ENTRY_MODEL_FOR_KIND: dict[OptionKind, EntryModelKind] = {
    OptionKind.MARKET_AT_QUOTE: EntryModelKind.MARKET_AT_QUOTE,
    OptionKind.LIMIT_AT_ZONE: EntryModelKind.LIMIT_AT_ZONE,
}


class LevelOption(StellarModel):
    """One evidence-derived choice for an entry, a stop or a target."""

    option_id: OptionId
    kind: OptionKind
    role: LevelRole
    price: Price | None = None
    zone_low: Price | None = None
    zone_high: Price | None = None
    atr_distance: PositiveDecimal | None = None
    buffer: NonNegativeDecimal | None = None
    sources: tuple[NumericSource, ...] = Field(min_length=1)
    evidence_ids: tuple[EvidenceRef, ...] = ()
    basis: Label

    @model_validator(mode="after")
    def _shape(self) -> LevelOption:
        if self.role is not ROLE_FOR_KIND[self.kind]:
            raise ValueError("the option role does not match its kind")
        zone = self.zone_low is not None or self.zone_high is not None
        if zone and (self.zone_low is None or self.zone_high is None
                     or self.zone_low >= self.zone_high):
            raise ValueError("a zone needs zone_low below zone_high")
        shape = {OptionKind.MARKET_AT_QUOTE: not (self.price or zone or self.atr_distance),
                 OptionKind.LIMIT_AT_ZONE: (self.price is not None) != zone
                 and self.atr_distance is None,
                 OptionKind.ATR_STOP: self.atr_distance is not None and self.price is None
                 and not zone}.get(self.kind, self.price is not None and not zone
                                   and self.atr_distance is None)
        if not shape:
            raise ValueError(f"malformed {self.kind.value} option")
        if self.kind is not OptionKind.MARKET_AT_QUOTE and not self.evidence_ids:
            raise ValueError("a level option must cite its Phase 5 evidence")
        return self


class SetupEvidence(StellarModel):
    """Exactly which evidence the setup was evaluated on (all point in time)."""

    technical_analysis_id: str
    technical_content_hash: Sha256Hex
    technical_as_of: UtcDatetime
    run_id: RunId
    research_snapshot_id: ResearchSnapshotId
    decision_outputs_hash: Sha256Hex
    decision_as_of: UtcDatetime
    decision_status: RunStatus
    final_stance: Stance
    evidence_grade: EvidenceGrade
    challenge_kinds: tuple[ChallengeKind, ...] = ()
    mtf_content_hash: Sha256Hex | None = None
    mtf_alignment: Alignment | None = None


class Setup(StellarModel):
    """One deterministic evaluation of one setup identity (T6 ``pullback_setup``)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    setup_id: SetupId
    """Stable identity: instrument, timeframe, type, direction, reference leg and config."""
    fingerprint: Sha256Hex
    """Hash of everything below: changes whenever any evidence or config changes."""
    instrument: InstrumentId
    timeframe: Timeframe
    setup_type: SetupType
    direction: SetupDirection
    status: SetupStatus
    state: SetupState
    as_of: UtcDatetime
    reasons: tuple[Label, ...] = ()
    limitations: tuple[Label, ...] = ()
    unevaluated: tuple[Label, ...] = ()
    reference_leg_id: EvidenceRef | None = None
    invalidation_level: Price | None = None
    invalidation_evidence_id: EvidenceRef | None = None
    valid_from: UtcDatetime | None = None
    valid_until: UtcDatetime | None = None
    options: tuple[LevelOption, ...] = ()
    evidence: SetupEvidence
    config_hash: Sha256Hex
    produced_by: Label = "pullback_setup"

    @model_validator(mode="after")
    def _consistent(self) -> Setup:
        if self.state is not STATE_FOR_STATUS[self.status]:
            raise ValueError("state does not match status")
        if self.status is SetupStatus.NO_SETUP and self.direction is not SetupDirection.NONE:
            raise ValueError("NO_SETUP has no direction")
        if self.status in (SetupStatus.CANDIDATE, SetupStatus.READY_FOR_PROPOSAL) and \
                self.direction is SetupDirection.NONE:
            raise ValueError("a candidate setup has a direction")
        if self.status is SetupStatus.READY_FOR_PROPOSAL:
            roles = {o.role for o in self.options}
            if roles != set(LevelRole) or self.valid_until is None or \
                    self.invalidation_level is None:
                raise ValueError("READY_FOR_PROPOSAL needs entry, stop and target options, "
                                 "an invalidation level and valid_until")
        if self.valid_until is not None and (self.valid_from is None
                                             or self.valid_until <= self.valid_from):
            raise ValueError("valid_until must follow valid_from")
        ids = [o.option_id for o in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError("option ids must be unique")
        if self.evidence.technical_as_of > self.as_of or self.evidence.decision_as_of > self.as_of:
            raise ValueError("setup evidence dated after as_of (look-ahead)")
        return self

    def option(self, option_id: str) -> LevelOption | None:
        return next((o for o in self.options if o.option_id == option_id), None)

    def options_for(self, role: LevelRole) -> tuple[LevelOption, ...]:
        return tuple(o for o in self.options if o.role is role)
