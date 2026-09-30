"""V1 PAPER runtime configuration and the explicit operator inputs of one run.

The runtime owns **no** trading setting. It only references the existing configurations
(market data request, ``TechnicalConfig``, ``WorkflowConfig`` / allowlist / validation,
``SetupConfig`` / ``TraderConfig``, ``RiskPolicy`` inside the ``RiskEngine``,
``PaperBrokerConfig``) by hash, and adds the few wiring choices no earlier phase makes:

- ``broker_symbols``: the paper broker symbol per instrument. UNSET for an instrument: no
  order intent can be built (fail closed, ``ORDER_AUTHORISATION_FAILED``);
- ``take_profit``: which take-profit the order intent carries (RK-9 undecided). Default
  ``NONE``, the Phase 3 safe default ("none unless the caller passes one of the proposal's
  targets");
- ``profile``: the timeframe profile label (D-7 undecided). It must equal the setup config's
  profile when both are set; the runtime never invents one.

``OperatorRiskInputs`` are the risk-context inputs that no component produces yet (daily
P&L window RK-6, cooldowns, event restrictions, broker/owner instrument metadata, requested
volume, currency conversions). They are passed explicitly per run and are part of the run
identity. Anything left ``None`` reaches the Risk Engine as unknown, and its missing-input
rule decides (FAIL or REVIEW). Nothing is estimated here.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from stellar.execution.models import ConversionRate
from stellar.risk.state import (
    CooldownState,
    DailyRiskState,
    EventRestrictionState,
    InstrumentRiskMetadata,
)
from stellar.schemas.common import (
    InstrumentId,
    Label,
    PositiveDecimal,
    ProfileId,
    ShortText,
    StellarModel,
)
from stellar.schemas.market import Timeframe
from stellar.serialization import content_hash

WORKFLOW_VERSION = "v1_paper_1"


class TakeProfitPolicy(StrEnum):
    NONE = "NONE"
    """No take-profit on the order intent (Phase 3 RK-9 safe default)."""
    NEAREST_PROPOSAL_TARGET = "NEAREST_PROPOSAL_TARGET"
    """The proposal's first (nearest) target; the owner's explicit choice."""


class RuntimeConfig(StellarModel):
    version: Label = "unset"
    test_only: bool = False
    workflow_version: Label = WORKFLOW_VERSION
    profile: ProfileId | None = None
    timeframe: Timeframe | None = None
    """The setup timeframe the run analyses (a profile decision, D-7). UNSET: no run."""
    broker_symbols: dict[InstrumentId, ShortText] = {}
    take_profit: TakeProfitPolicy = TakeProfitPolicy.NONE
    enabled_instruments: tuple[InstrumentId, ...] = ()
    """Instruments this station trades on paper. UNSET: the Risk Engine refuses every
    instrument (``instrument_not_enabled``); nothing is enabled by default."""

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class OperatorRiskInputs(StellarModel):
    """Explicit risk inputs for one moment. ``None`` means unknown, never zero."""

    daily: DailyRiskState | None = None
    cooldowns: tuple[CooldownState, ...] | None = None
    event_restriction: EventRestrictionState | None = None
    metadata: InstrumentRiskMetadata | None = None
    requested_volume: PositiveDecimal | None = None
    conversions: tuple[ConversionRate, ...] = ()

    @model_validator(mode="after")
    def _one_instrument(self) -> OperatorRiskInputs:
        instruments = {x.instrument for x in (self.event_restriction, self.metadata)
                       if x is not None}
        if len(instruments) > 1:
            raise ValueError("operator inputs name more than one instrument")
        return self

    def identity(self) -> str:
        return content_hash(self.model_dump(mode="json"))
