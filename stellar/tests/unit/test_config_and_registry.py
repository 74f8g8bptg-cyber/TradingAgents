"""Configuration validation and the agent registry."""

import pytest
from pydantic import ValidationError
from stellar.agents import (
    ARCHITECTURAL_ROSTER,
    AgentGroup,
    AgentIdentity,
    AgentKind,
    AgentRegistry,
    RosterStatus,
    default_registry,
)
from stellar.config import (
    IMPLEMENTED_FEATURES,
    ConfigError,
    ExecutionMode,
    FeatureGate,
    StellarConfig,
    load_config,
    parse_config,
)

pytestmark = pytest.mark.unit

# --- configuration -----------------------------------------------------------


def test_defaults_are_explicit_and_safe():
    config = load_config()
    assert config.execution.mode is ExecutionMode.PAPER
    assert config.environment == "development"
    assert [i.display_name for i in config.instruments] == ["XAU/USD", "EUR/USD", "USD/JPY",
                                                            "NAS100"]
    assert not any(config.features.enabled(g) for g in FeatureGate)
    permitted, reasons = config.trading_permitted()
    assert permitted is False and "risk_configuration_not_defined" in reasons


def test_live_can_never_be_selected():
    with pytest.raises(ConfigError, match="LIVE"):
        parse_config({"execution": {"mode": "LIVE"}})
    with pytest.raises(ValidationError, match="LIVE"):
        StellarConfig(execution={"mode": ExecutionMode.LIVE})


def test_demo_is_refused_before_the_demo_gate():
    with pytest.raises(ConfigError, match="demo gate"):
        parse_config({"execution": {"mode": "DEMO"}})


@pytest.mark.parametrize("mode", ["live", "Paper", "REAL", "", None])
def test_invalid_execution_modes_are_rejected(mode):
    with pytest.raises(ConfigError):
        parse_config({"execution": {"mode": mode}})


@pytest.mark.parametrize(
    "gate", [g.value for g in FeatureGate if g not in IMPLEMENTED_FEATURES]
)
def test_unimplemented_features_cannot_be_enabled(gate):
    with pytest.raises(ConfigError, match="not implemented"):
        parse_config({"features": {gate: True}})


def test_only_market_data_is_implemented_after_phase_2():
    assert {FeatureGate.MARKET_DATA} == IMPLEMENTED_FEATURES
    config = parse_config({"features": {"market_data": True}})
    assert config.features.enabled(FeatureGate.MARKET_DATA)
    # Enabling market data does not permit trading.
    assert config.trading_permitted()[0] is False


def test_market_data_staleness_threshold_is_unset_by_default():
    assert StellarConfig().market_data.max_staleness_intervals is None
    assert parse_config({"market_data": {"max_staleness_intervals": 3}}).market_data \
        .max_staleness_intervals == 3
    for bad in (0, -1, "three"):
        with pytest.raises(ConfigError):
            parse_config({"market_data": {"max_staleness_intervals": bad}})


def test_config_rejects_unknown_keys_duplicates_and_bad_instruments():
    with pytest.raises(ConfigError):
        parse_config({"risk": {"max_risk_per_trade_pct": 1}})
    xau = StellarConfig().instruments[0].model_dump()
    with pytest.raises(ConfigError, match="once"):
        parse_config({"instruments": [xau, xau]})
    with pytest.raises(ConfigError, match="displayed as"):
        parse_config({"instruments": [{**xau, "display_name": "Gold"}]})
    with pytest.raises(ConfigError, match="at least one"):
        parse_config({"instruments": [{**xau, "enabled": False}]})
    with pytest.raises(ConfigError):
        parse_config({"instruments": [{**xau, "instrument_id": "BTCUSD"}]})


def test_config_loads_from_toml_and_hash_is_stable(tmp_path):
    path = tmp_path / "stellar.toml"
    path.write_text(
        'environment = "test"\nstation_id = "stellar-test"\n'
        '[execution]\nmode = "PAPER"\n[journal]\npath = "/tmp/j.sqlite3"\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.environment == "test" and config.station_id == "stellar-test"
    assert config.config_hash() == load_config(path).config_hash()
    assert config.config_hash() != StellarConfig().config_hash()
    assert config.instrument("NAS100").asset_class == "index_cfd"
    with pytest.raises(KeyError):
        StellarConfig(instruments=[config.instruments[0]]).instrument("EURUSD")


def test_unreadable_or_invalid_files_raise(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.toml")
    bad = tmp_path / "bad.toml"
    bad.write_text("execution = [", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_config_is_immutable():
    config = StellarConfig()
    with pytest.raises(ValidationError):
        config.execution.mode = ExecutionMode.LIVE


# --- registry ---------------------------------------------------------------


def test_registry_holds_the_whole_architectural_roster():
    registry = default_registry()
    assert len(registry) == 41 == len(ARCHITECTURAL_ROSTER)
    prefixes = {"R": 6, "V": 4, "M": 1, "S": 4, "T": 8, "U": 8, "P": 4, "E": 2, "L": 2, "O": 2}
    for prefix, count in prefixes.items():
        assert sum(a.code.startswith(prefix) for a in registry) == count


def test_roster_status_and_enabled_flags_follow_the_foundation_plan():
    registry = default_registry()
    deferred = {a.code for a in registry if a.roster_status is RosterStatus.DEFERRED}
    assert deferred == {"R3", "R4", "R5", "R6"}
    assert registry.by_code("E2").roster_status is RosterStatus.DEMO_GATE
    assert {a.code for a in registry if not a.enabled} == deferred | {"E2"}
    with pytest.raises(ValidationError, match="cannot be enabled"):
        registry.with_enabled("mt5_execution", True)
    assert not registry.with_enabled("supervisor", False).get("supervisor").enabled


def test_lookup_by_id_code_group_and_upstream_node():
    registry = default_registry()
    assert registry.get("risk_engine").code == "P3"
    assert registry.by_code("T5").technical_id == "price_action"
    assert registry.by_upstream_node("Aggressive Analyst").technical_id == "risk_aggressive"
    assert {a.code for a in registry.in_group(AgentGroup.RESEARCH_VALIDATION)} == {
        "V1", "V2", "V3", "V4"}
    assert "risk_engine" in registry and "Captain" not in registry
    with pytest.raises(KeyError):
        registry.get("unknown_agent")


def test_risk_and_execution_agents_are_deterministic():
    for agent in default_registry():
        if agent.group in {AgentGroup.RISK, AgentGroup.EXECUTION,
                           AgentGroup.EXECUTION_VALIDATION}:
            assert agent.kind is AgentKind.DETERMINISTIC, agent.code
    data = default_registry().get("risk_engine").model_dump()
    with pytest.raises(ValidationError, match="deterministic"):
        AgentIdentity.model_validate({**data, "kind": "llm", "llm_tier": "deep"})


def test_technical_ids_are_not_display_names():
    registry = default_registry()
    assert all(a.display_name is None for a in registry)
    named = registry.with_display_names({"portfolio_manager": "Captain Example"})
    assert named.get("portfolio_manager").display_name == "Captain Example"
    assert named.get("portfolio_manager").technical_id == "portfolio_manager"
    with pytest.raises(ValidationError):
        AgentIdentity.model_validate({**registry.get("trader").model_dump(),
                                      "technical_id": "Lt. Example"})
    with pytest.raises(ValueError, match="unique"):
        registry.with_display_names({"trader": "Same", "supervisor": "Same"})
    with pytest.raises(ValueError, match="reuse technical ids"):
        registry.with_display_names({"trader": "supervisor"})
    with pytest.raises(KeyError):
        registry.with_display_names({"nobody": "X"})


def test_registry_rejects_duplicates():
    agents = list(ARCHITECTURAL_ROSTER)
    with pytest.raises(ValueError, match="duplicate technical_id"):
        AgentRegistry([*agents, agents[0]])
