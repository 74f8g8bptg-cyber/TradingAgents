"""Central Stellar configuration (Foundation §4.26), Phase 1 sections only.

Typed and validated, immutable after load, hashed for provenance. Secrets never
live here; they come from the environment when a later phase needs them.

Safety rules enforced by validation:
- ``execution.mode`` defaults to PAPER. LIVE is reserved and always refused: it
  does not exist in V1 and needs a future implementation and owner approval
  (Foundation §8.1). DEMO is refused until the Phase 8 demo gate exists.
- A feature gate for a subsystem that is not implemented cannot be switched on.
- Trading is never permitted in Phase 1: no risk configuration or risk engine
  exists yet, so the answer fails closed (Foundation §4.26).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from stellar.schemas.common import (
    INSTRUMENT_DISPLAY_NAMES,
    AssetClass,
    CurrencyCode,
    InstrumentId,
    StellarModel,
)
from stellar.serialization import content_hash


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ExecutionMode(StrEnum):
    PAPER = "PAPER"
    DEMO = "DEMO"
    LIVE = "LIVE"
    """Reserved. Always refused by validation; see the module docstring."""


class FeatureGate(StrEnum):
    """Later subsystems. Each stays off until the phase that implements it."""

    MARKET_DATA = "market_data"  # Phase 2
    RISK_ENGINE = "risk_engine"  # Phase 3
    PAPER_BROKER = "paper_broker"  # Phase 4
    TECHNICAL_ANALYSIS = "technical_analysis"  # Phase 5
    RESEARCH_PIPELINE = "research_pipeline"  # Phase 6
    LLM_AGENTS = "llm_agents"  # Phase 6
    MT5_DEMO_BRIDGE = "mt5_demo_bridge"  # Phase 8
    VISUAL_API = "visual_api"  # Phase 9
    VISUAL_STATION = "visual_station"  # Phase 9


IMPLEMENTED_FEATURES: frozenset[FeatureGate] = frozenset(
    {FeatureGate.MARKET_DATA, FeatureGate.RISK_ENGINE, FeatureGate.PAPER_BROKER,
     FeatureGate.TECHNICAL_ANALYSIS, FeatureGate.RESEARCH_PIPELINE, FeatureGate.LLM_AGENTS}
)
"""Gates whose subsystem exists. Phase 2 adds market data, Phase 3 the risk engine,
Phase 4 the paper broker,
Phase 5 technical analysis,
Phase 6 the research pipeline and LLM agents (decision support only);
each later phase adds its gate. Enabling a gate never permits trading by itself."""


class InstrumentConfig(StellarModel):
    """One instrument record (Foundation §4.3–4.6). Broker values come at runtime, never here."""

    instrument_id: InstrumentId
    display_name: str
    asset_class: AssetClass
    base_currency: CurrencyCode | None = None
    quote_currency: CurrencyCode
    session_calendar_id: str | None = None
    analysis_only: bool = False
    enabled: bool = True

    @model_validator(mode="after")
    def _display_name_matches(self) -> InstrumentConfig:
        expected = INSTRUMENT_DISPLAY_NAMES[self.instrument_id]
        if self.display_name != expected:
            raise ValueError(f"{self.instrument_id} is displayed as {expected!r}")
        return self


DEFAULT_INSTRUMENTS: tuple[InstrumentConfig, ...] = (
    InstrumentConfig(instrument_id=InstrumentId.XAUUSD, display_name="XAU/USD",
                     asset_class=AssetClass.METAL, base_currency="XAU", quote_currency="USD"),
    InstrumentConfig(instrument_id=InstrumentId.EURUSD, display_name="EUR/USD",
                     asset_class=AssetClass.FX, base_currency="EUR", quote_currency="USD"),
    InstrumentConfig(instrument_id=InstrumentId.USDJPY, display_name="USD/JPY",
                     asset_class=AssetClass.FX, base_currency="USD", quote_currency="JPY"),
    InstrumentConfig(instrument_id=InstrumentId.NAS100, display_name="NAS100",
                     asset_class=AssetClass.INDEX_CFD, base_currency=None, quote_currency="USD"),
)


class ExecutionConfig(StellarModel):
    mode: ExecutionMode = ExecutionMode.PAPER

    @field_validator("mode")
    @classmethod
    def _mode_allowed(cls, value: ExecutionMode) -> ExecutionMode:
        if value is ExecutionMode.LIVE:
            raise ValueError(
                "LIVE execution does not exist in Stellar V1; it needs a future "
                "implementation and explicit owner approval"
            )
        if value is ExecutionMode.DEMO:
            raise ValueError("DEMO execution needs the Phase 8 demo gate, which is not implemented")
        return value


class FeatureGates(StellarModel):
    market_data: bool = False
    risk_engine: bool = False
    paper_broker: bool = False
    technical_analysis: bool = False
    research_pipeline: bool = False
    llm_agents: bool = False
    mt5_demo_bridge: bool = False
    visual_api: bool = False
    visual_station: bool = False

    @model_validator(mode="after")
    def _only_implemented(self) -> FeatureGates:
        blocked = sorted(
            gate.value
            for gate in FeatureGate
            if getattr(self, gate.value) and gate not in IMPLEMENTED_FEATURES
        )
        if blocked:
            raise ValueError(f"features not implemented yet cannot be enabled: {blocked}")
        return self

    def enabled(self, gate: FeatureGate) -> bool:
        return bool(getattr(self, gate.value))


class MarketDataConfig(StellarModel):
    """Phase 2 market-data settings. No staleness threshold is chosen by default."""

    max_staleness_intervals: int | None = Field(default=None, ge=1)
    """A series is STALE when its newest bar closed more than this many timeframe
    intervals before ``as_of``. ``None`` (default): freshness is reported as unknown."""


class JournalConfig(StellarModel):
    path: Path = Path("~/.stellar/journal.sqlite3")

    def resolved_path(self) -> Path:
        return self.path.expanduser()


class StellarConfig(StellarModel):
    environment: Environment = Environment.DEVELOPMENT
    station_id: str = Field(default="stellar-01", pattern=r"^[a-z0-9][a-z0-9\-]{0,63}$")
    execution: ExecutionConfig = ExecutionConfig()
    instruments: tuple[InstrumentConfig, ...] = DEFAULT_INSTRUMENTS
    features: FeatureGates = FeatureGates()
    market_data: MarketDataConfig = MarketDataConfig()
    journal: JournalConfig = JournalConfig()

    @field_validator("instruments")
    @classmethod
    def _instruments_valid(
        cls, value: tuple[InstrumentConfig, ...]
    ) -> tuple[InstrumentConfig, ...]:
        ids = [i.instrument_id for i in value]
        if len(set(ids)) != len(ids):
            raise ValueError("each instrument may be configured once")
        if not any(i.enabled for i in value):
            raise ValueError("at least one instrument must be enabled")
        return value

    def instrument(self, instrument_id: InstrumentId | str) -> InstrumentConfig:
        wanted = InstrumentId(instrument_id)
        for record in self.instruments:
            if record.instrument_id is wanted:
                return record
        raise KeyError(f"{wanted} is not configured")

    def config_hash(self) -> str:
        """SHA-256 of the canonical JSON form; recorded on every run and record."""
        return content_hash(self.model_dump(mode="json"))

    def trading_permitted(self) -> tuple[bool, tuple[str, ...]]:
        """Whether orders may be placed, with the reasons if not. Always refused in Phase 1."""
        reasons = []
        if not self.features.enabled(FeatureGate.RISK_ENGINE):
            reasons.append("risk_engine_not_enabled")
        reasons.append("risk_configuration_not_defined")
        if not self.features.enabled(FeatureGate.PAPER_BROKER):
            reasons.append("paper_broker_not_enabled")
        return False, tuple(reasons)
