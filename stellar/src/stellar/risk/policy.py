"""The owner's risk policy: versioned, validated, hashed (Foundation §8.1, §4.26).

**No numeric threshold is chosen here.** Every numeric control starts ``UNSET``:
- ``UNSET``: no limit configured. The rule reports NOT_CONFIGURED, which is
  never a pass and blocks approval (a REVIEW outcome: configuration incomplete,
  fail closed, Foundation §4.26).
- ``DISABLED``: the owner explicitly turned the control off. The rule reports
  NOT_CONFIGURED (still not a pass) but does not block. Mandatory controls
  (``MANDATORY_CONTROLS``) cannot be disabled.
- ``ENABLED``: evaluated against the owner's limit.

Units are fixed per control and stated in its docstring. Limits apply as they
are written, with no rounding. A policy built from test-only values must say
``test_only=True``, and such a policy is refused where real decisions are made
(``RiskEngine`` requires ``allow_test_policy`` to accept it).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from stellar.schemas.common import InstrumentId, Label, StellarModel, strict_number
from stellar.serialization import content_hash

PositiveLimit = Annotated[
    Decimal, BeforeValidator(strict_number), Field(gt=0, allow_inf_nan=False)
]
FractionLimit = Annotated[
    Decimal, BeforeValidator(strict_number), Field(gt=0, le=1, allow_inf_nan=False)
]


class ControlState(StrEnum):
    UNSET = "UNSET"
    DISABLED = "DISABLED"
    ENABLED = "ENABLED"


class FractionControl(StellarModel):
    """A limit expressed as a fraction of equity (0.01 = 1 %)."""

    state: ControlState = ControlState.UNSET
    limit: FractionLimit | None = None

    @model_validator(mode="after")
    def _limit_iff_enabled(self) -> FractionControl:
        if (self.state is ControlState.ENABLED) != (self.limit is not None):
            raise ValueError("a limit is given exactly when the control is ENABLED")
        return self


class CountControl(StellarModel):
    """A limit on a count (positions, orders)."""

    state: ControlState = ControlState.UNSET
    limit: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _limit_iff_enabled(self) -> CountControl:
        if (self.state is ControlState.ENABLED) != (self.limit is not None):
            raise ValueError("a limit is given exactly when the control is ENABLED")
        return self


class SecondsControl(StellarModel):
    """A limit in seconds."""

    state: ControlState = ControlState.UNSET
    limit: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _limit_iff_enabled(self) -> SecondsControl:
        if (self.state is ControlState.ENABLED) != (self.limit is not None):
            raise ValueError("a limit is given exactly when the control is ENABLED")
        return self


class PerInstrumentControl(StellarModel):
    """A per-instrument limit in the instrument's own unit (price units or lots).

    ENABLED with no entry for an instrument means NOT_CONFIGURED for that one.
    """

    state: ControlState = ControlState.UNSET
    limits: dict[InstrumentId, PositiveLimit] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _limits_iff_enabled(self) -> PerInstrumentControl:
        if self.state is not ControlState.ENABLED and self.limits:
            raise ValueError("limits are given only when the control is ENABLED")
        if self.state is ControlState.ENABLED and not self.limits:
            raise ValueError("an ENABLED per-instrument control needs at least one limit")
        return self


class SwitchControl(StellarModel):
    """A control with no numeric limit (cooldowns, event restrictions)."""

    state: ControlState = ControlState.UNSET


class CorrelatedExposureControl(StellarModel):
    """Open risk (fraction of equity) summed over an owner-defined cluster of instruments.

    Clusters are configuration; no correlation coefficient is computed or assumed.
    """

    state: ControlState = ControlState.UNSET
    clusters: tuple[tuple[InstrumentId, ...], ...] = ()
    limit: FractionLimit | None = None

    @model_validator(mode="after")
    def _consistent(self) -> CorrelatedExposureControl:
        enabled = self.state is ControlState.ENABLED
        if enabled != (self.limit is not None) or enabled != bool(self.clusters):
            raise ValueError("clusters and a limit are given exactly when ENABLED")
        for cluster in self.clusters:
            if len(set(cluster)) < 2 or len(set(cluster)) != len(cluster):
                raise ValueError("a cluster lists at least two distinct instruments")
        return self


class TripPolicy(StellarModel):
    """Which rule failures also trip the circuit breaker (Foundation §8.1 "trip breaker").

    A trade rejection alone never trips the breaker. Only these systemic breaches
    do, and only when their limits are configured.
    """

    on_daily_loss_breach: bool = True
    on_drawdown_breach: bool = True


class MissingInputOutcome(StrEnum):
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class RiskPolicy(StellarModel):
    policy_schema: Label = "stellar_risk_policy_1"
    version: Label = "unset"
    """Owner's version label for this policy (recorded on every decision)."""
    test_only: bool = False
    """True for policies whose values exist only for tests. Never for real decisions."""

    missing_input_outcome: MissingInputOutcome = MissingInputOutcome.FAIL
    """Foundation §8.1: a control whose required input is missing rejects."""

    max_risk_per_trade: FractionControl = FractionControl()
    """Risk of the stop being hit, as a fraction of equity (sizing and check)."""
    max_position_volume: PerInstrumentControl = PerInstrumentControl()
    """Lots, per instrument."""
    max_open_positions: CountControl = CountControl()
    max_pending_orders: CountControl = CountControl()
    max_instrument_exposure: FractionControl = FractionControl()
    """Open risk in one instrument, including the new trade, as a fraction of equity."""
    correlated_exposure: CorrelatedExposureControl = CorrelatedExposureControl()
    max_daily_loss: FractionControl = FractionControl()
    """Today's loss (realised + unrealised), as a fraction of the day's starting equity."""
    max_drawdown: FractionControl = FractionControl()
    """(peak equity − equity) / peak equity."""
    max_spread: PerInstrumentControl = PerInstrumentControl()
    """Ask − bid, in price units, per instrument."""
    max_quote_age_seconds: SecondsControl = SecondsControl()
    max_slippage: PerInstrumentControl = PerInstrumentControl()
    """Maximum slippage in price units, per instrument; carried into OrderIntent."""
    cooldowns: SwitchControl = SwitchControl()
    event_restrictions: SwitchControl = SwitchControl()

    allow_proxy_market_data: bool = False
    """Proxy/derived snapshots may inform analysis only when explicitly allowed. Quotes
    used for order levels or spread are never accepted from a proxy (Foundation L2)."""
    overweight_allowed: bool = False
    """Foundation D-9 is open; its safe default is "Overweight → no trade" (REVIEW)."""
    size_to_max_risk: bool = False
    """When True and all inputs are explicit, size the trade by formula to the
    max-risk-per-trade limit (× size factor). When False, a requested volume must
    be supplied and is only validated."""
    trip: TripPolicy = TripPolicy()

    @model_validator(mode="after")
    def _mandatory_not_disabled(self) -> RiskPolicy:
        for name in MANDATORY_CONTROLS:
            if getattr(self, name).state is ControlState.DISABLED:
                raise ValueError(f"{name} is mandatory and cannot be DISABLED")
        if self.size_to_max_risk and self.max_risk_per_trade.state is not ControlState.ENABLED:
            raise ValueError("size_to_max_risk needs max_risk_per_trade ENABLED")
        return self

    def policy_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


MANDATORY_CONTROLS = ("max_risk_per_trade", "max_daily_loss", "max_drawdown")
"""Controls the owner may leave UNSET (blocking) but never DISABLE."""


def load_risk_policy(data: dict) -> RiskPolicy:
    """Validate a policy from plain data (for example a parsed TOML table)."""
    return RiskPolicy.model_validate(data)
