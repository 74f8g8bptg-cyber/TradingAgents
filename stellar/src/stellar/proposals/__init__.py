"""Phase 6b proposals: the deterministic Trade Proposal Builder (P1).

The only Stellar code that constructs a ``TradeProposal``. It never evaluates risk, sizes a
position, builds an order intent or calls a broker.
"""

from stellar.proposals.builder import (
    PRODUCER,
    build_proposal,
    load_proposal,
    proposal_identity,
    resolve_levels,
)
from stellar.proposals.models import (
    Approval,
    ApprovalSource,
    LevelSelection,
    ProposalFailure,
    ProposalOutcome,
    ProposalStatus,
    SelectionSource,
)

__all__ = [
    "PRODUCER",
    "Approval",
    "ApprovalSource",
    "LevelSelection",
    "ProposalFailure",
    "ProposalOutcome",
    "ProposalStatus",
    "SelectionSource",
    "build_proposal",
    "load_proposal",
    "proposal_identity",
    "resolve_levels",
]
