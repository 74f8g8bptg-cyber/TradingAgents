"""``RiskDecision``: the Risk Engine's verdict on one proposal (Foundation §8, §9.1 stage 8).

Phase 1 fixed the shape. Phase 3 adds, additively: a per-check ``status``,
``reason`` code and ``blocking`` flag (so a control that is NOT_CONFIGURED is
never counted as passed), and reason codes for the structural checks. Limit
values still live only in the owner's risk policy, never here.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    DecisionId,
    FiniteDecimal,
    InstrumentId,
    Label,
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
    # Phase 3 additions (structural and data checks)
    INSTRUMENT_UNSUPPORTED = "instrument_unsupported"
    LOOK_AHEAD = "look_ahead"
    MARKET_DATA_UNAVAILABLE = "market_data_unavailable"
    MARKET_DATA_INVALID = "market_data_invalid"
    PROXY_DATA = "proxy_data"
    CONFIG_INVALID = "config_invalid"
    MAX_PENDING_ORDERS = "max_pending_orders"
    MAX_INSTRUMENT_EXPOSURE = "max_instrument_exposure"
    POSITION_SIZING = "position_sizing"
    SIZE_FACTOR = "size_factor"


class CheckStatus(StrEnum):
    """Result of one rule (Phase 3)."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    """No limit is set. Never a pass; blocking unless the policy explicitly disabled it."""


_PASSING = {CheckStatus.PASS, CheckStatus.NOT_APPLICABLE}


class RiskCheck(StellarModel):
    """One evaluated rule, with its value and limit (Foundation §8.2 rule 2).

    Phase 1 checks carry only ``passed``. Phase 3 checks also carry ``status``,
    ``reason`` and ``blocking``; then ``passed`` is true only for PASS and
    NOT_APPLICABLE, so NOT_CONFIGURED can never look like a pass.
    """

    rule: RiskRule
    passed: bool
    value: FiniteDecimal | None = None
    limit: FiniteDecimal | None = None
    status: CheckStatus | None = None
    reason: Label | None = None
    blocking: bool | None = None

    @model_validator(mode="after")
    def _status_consistent(self) -> RiskCheck:
        if self.status is None:
            if self.blocking is not None:
                raise ValueError("blocking is given only with a status")
            return self
        if self.passed != (self.status in _PASSING):
            raise ValueError("passed is true exactly for PASS and NOT_APPLICABLE")
        if self.blocking is None:
            raise ValueError("a check with a status states whether it blocks")
        if self.status in _PASSING and self.blocking:
            raise ValueError("a passing check cannot block")
        if self.status in {CheckStatus.FAIL, CheckStatus.REVIEW} and not self.blocking:
            raise ValueError("FAIL and REVIEW always block")
        return self

    @property
    def blocks(self) -> bool:
        """Legacy checks without status block when not passed."""
        return (not self.passed) if self.blocking is None else self.blocking


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
        failed = {c.rule for c in self.checks if c.blocks}
        if not failed <= set(self.reasons):
            raise ValueError("every failed check must appear in reasons")
        statuses = {c.status for c in self.checks if c.status is not None and c.blocks}
        if CheckStatus.FAIL in statuses and self.outcome is not RiskOutcome.REJECTED:
            raise ValueError("a FAIL check makes the decision REJECTED")
        if statuses and CheckStatus.FAIL not in statuses and \
                self.outcome is RiskOutcome.REJECTED:
            raise ValueError("a REJECTED decision with statuses needs a FAIL check")
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
