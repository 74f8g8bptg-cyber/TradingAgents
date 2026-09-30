"""``RiskDecision``: the Risk Engine's verdict on one proposal (Foundation §8, §9.1 stage 8).

Phase 1 fixes the shape and its internal consistency only. The rules, their
order of evaluation and every limit value belong to the Risk Engine (Phase 3);
no threshold is defined here.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    DecisionId,
    FiniteDecimal,
    InstrumentId,
    PositiveDecimal,
    ProposalId,
    Provenance,
    RunId,
    SchemaVersion,
    StellarModel,
    UnitInterval,
    UtcDatetime,
)

RISK_ENGINE_ID = "risk_engine"


class RiskOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"
    """No approval; flagged for the owner. Never leads to an order."""


class RiskRule(StrEnum):
    """Deterministic reason codes: one per control in Foundation §8.1."""

    SCHEMA_INVALID = "schema_invalid"
    STOP_LOSS_REQUIRED = "stop_loss_required"
    MIN_REWARD_RISK = "min_reward_risk"
    MAX_RISK_PER_TRADE = "max_risk_per_trade"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_OPEN_POSITIONS = "max_open_positions"
    CORRELATED_EXPOSURE = "correlated_exposure"
    MAX_DAILY_LOSS = "max_daily_loss"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_SPREAD = "max_spread"
    STALE_QUOTE = "stale_quote"
    SLIPPAGE_TOLERANCE = "slippage_tolerance"
    DUPLICATE_ORDER = "duplicate_order"
    COOLDOWN = "cooldown"
    NEWS_RESTRICTION = "news_restriction"
    PROPOSAL_EXPIRED = "proposal_expired"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXECUTION_MODE = "execution_mode"
    OWNER_REVIEW_REQUIRED = "owner_review_required"
    MISSING_INPUT = "missing_input"


class RiskCheck(StellarModel):
    """One evaluated rule, with its value and limit (Foundation §8.2 rule 2)."""

    rule: RiskRule
    passed: bool
    value: FiniteDecimal | None = None
    limit: FiniteDecimal | None = None


class RiskDecision(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    decision_id: DecisionId
    proposal_id: ProposalId
    run_id: RunId | None = None
    instrument: InstrumentId
    outcome: RiskOutcome
    reasons: tuple[RiskRule, ...] = ()
    checks: tuple[RiskCheck, ...] = ()
    volume: PositiveDecimal | None = Field(default=None, description="Lots, from sizing")
    risk_pct_equity: UnitInterval | None = None
    decided_at: UtcDatetime
    provenance: Provenance

    @field_validator("reasons")
    @classmethod
    def _unique_reasons(cls, value: tuple[RiskRule, ...]) -> tuple[RiskRule, ...]:
        if len(set(value)) != len(value):
            raise ValueError("reasons must be unique")
        return value

    @model_validator(mode="after")
    def _outcome_consistent(self) -> RiskDecision:
        if self.provenance.produced_by != RISK_ENGINE_ID:
            raise ValueError("risk decisions are made only by risk_engine (P3)")
        failed = {c.rule for c in self.checks if not c.passed}
        if not failed <= set(self.reasons):
            raise ValueError("every failed check must appear in reasons")
        if self.outcome is RiskOutcome.APPROVED:
            if not self.checks:
                raise ValueError("an approval must record the checks it passed")
            if failed or self.reasons:
                raise ValueError("an approval cannot have failed checks or reasons")
            if self.volume is None or self.risk_pct_equity is None:
                raise ValueError("an approval must carry volume and risk_pct_equity")
        else:
            if not self.reasons:
                raise ValueError(f"a {self.outcome.value} decision must give reason codes")
            if self.volume is not None:
                raise ValueError(f"a {self.outcome.value} decision carries no volume")
        return self
