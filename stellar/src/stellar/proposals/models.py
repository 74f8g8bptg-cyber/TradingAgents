"""Typed inputs and outcomes of the Trade Proposal Builder.

- ``Approval``: the typed rating that approves one setup in its direction (Foundation §4.13,
  R-1). It comes from the Portfolio Manager (U10, not wired in Phase 6b) or the owner. There is
  no default rating, and the rating is never a side.
- ``LevelSelection``: which of the setup's own options are used. It holds option ids only,
  never a number, and is bound to one setup evaluation (id and fingerprint).
- ``ProposalOutcome``: BUILT with a proposal, or REFUSED with a typed failure.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stellar.schemas.common import (
    Direction,
    Label,
    Price,
    SetupId,
    Sha256Hex,
    ShortText,
    StellarModel,
)
from stellar.schemas.proposal import Rating, TradeProposal
from stellar.setups.models import OptionId


class ApprovalSource(StrEnum):
    PORTFOLIO_MANAGER = "portfolio_manager"
    OWNER = "owner"


class Approval(StellarModel):
    """Approval of **one** setup, in **its** direction (Foundation §4.13, R-1).

    ``rating`` is the upstream 5-tier vocabulary read as *approval strength for this setup*:
    Buy = "take this setup as proposed". It is never a side and never a direction:
    - Buy on a SHORT setup approves opening that SHORT; Buy on a LONG setup approves the LONG;
    - Sell ("exit or avoid the position", L8) never approves anything and never means short.

    The direction of a proposal comes only from the setup. ``setup_id`` and ``direction`` name
    what was approved; the builder refuses an approval for another setup or the other
    direction, so a Buy can never turn a SHORT setup into a LONG proposal (or the reverse).
    """

    setup_id: SetupId
    direction: Direction
    rating: Rating
    source: ApprovalSource
    reference: Label | None = None


class SelectionSource(StrEnum):
    OWNER = "OWNER"
    """The owner named the options."""
    TRADER = "TRADER"
    """The U4 Trader chose among the offered options (typed ids, validated)."""
    SINGLE_OPTION = "SINGLE_OPTION"
    """Each role had exactly one option, so there was nothing to choose."""


class LevelSelection(StellarModel):
    setup_id: SetupId
    setup_fingerprint: Sha256Hex
    entry_option_id: OptionId
    stop_option_id: OptionId
    target_option_ids: tuple[OptionId, ...] = Field(min_length=1)
    source: SelectionSource

    @model_validator(mode="after")
    def _unique(self) -> LevelSelection:
        if len(set(self.target_option_ids)) != len(self.target_option_ids):
            raise ValueError("target options must not repeat")
        return self


class ProposalFailure(StrEnum):
    SETUP_NOT_READY = "setup_not_ready"
    SELECTION_REQUIRED = "selection_required"
    SELECTION_FOR_OTHER_EVIDENCE = "selection_for_other_evidence"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_FOR_OTHER_SETUP = "approval_for_other_setup"
    APPROVAL_DIRECTION_MISMATCH = "approval_direction_mismatch"
    OVERWEIGHT_D9_UNRESOLVED = "overweight_d9_unresolved"
    RATING_DOES_NOT_APPROVE = "rating_does_not_approve"
    PROFILE_NOT_CONFIGURED = "profile_not_configured"
    CONFIG_MISMATCH = "config_mismatch"
    CREATED_BEFORE_SETUP = "created_before_setup"
    EXPIRY_NOT_CONFIGURED = "expiry_not_configured"
    SETUP_EXPIRED = "setup_expired"
    SETUP_ALREADY_PROPOSED = "setup_already_proposed"
    MARKET_DATA_MISMATCH = "market_data_mismatch"
    FUTURE_MARKET_DATA = "future_market_data"
    MARKET_DATA_OLDER_THAN_EVIDENCE = "market_data_older_than_evidence"
    MARKET_DATA_STALE = "market_data_stale"
    UNKNOWN_OPTION = "unknown_option"
    OPTION_ROLE_MISMATCH = "option_role_mismatch"
    MISSING_TARGET = "missing_target"
    NO_QUOTE = "no_quote"
    ENTRY_UNRESOLVED = "entry_unresolved"
    LIMIT_WOULD_BE_MARKETABLE = "limit_would_be_marketable"
    INVALID_STOP_GEOMETRY = "invalid_stop_geometry"
    INVALID_TARGET_GEOMETRY = "invalid_target_geometry"
    PROPOSAL_SCHEMA_REJECTED = "proposal_schema_rejected"


class ProposalStatus(StrEnum):
    BUILT = "BUILT"
    REFUSED = "REFUSED"


class ProposalOutcome(StellarModel):
    status: ProposalStatus
    setup_id: SetupId
    setup_fingerprint: Sha256Hex
    failure: ProposalFailure | None = None
    detail: ShortText | None = None
    proposal: TradeProposal | None = None
    proposal_hash: Sha256Hex | None = None
    reference_price: Price | None = None
    """The market reference the entry was checked against (quote side or last close)."""
    reference_basis: Label | None = None

    @model_validator(mode="after")
    def _consistent(self) -> ProposalOutcome:
        built = self.status is ProposalStatus.BUILT
        if built != (self.proposal is not None) or built == (self.failure is not None):
            raise ValueError("BUILT carries a proposal and no failure; REFUSED the reverse")
        return self
