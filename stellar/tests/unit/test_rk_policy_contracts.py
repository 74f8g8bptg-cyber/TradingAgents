"""Risk policy, context/state contracts and the additive Phase 1 extensions."""

from decimal import Decimal

import pytest
from factories import make_decision, provenance
from pydantic import ValidationError
from risk_helpers import AS_OF, TEST_POLICY, context, engine
from stellar.config import IMPLEMENTED_FEATURES, FeatureGate, StellarConfig
from stellar.risk import (
    MANDATORY_CONTROLS,
    AccountRiskState,
    ControlState,
    InstrumentRiskMetadata,
    PolicyRejected,
    RiskEngine,
    RiskPolicy,
)
from stellar.schemas.risk import CheckStatus, RiskCheck, RiskDecision
from stellar.telemetry import EVENT_TYPES
from stellar.telemetry.catalogue import REQUIRED_PAYLOAD_KEYS

pytestmark = pytest.mark.unit

# --- policy ------------------------------------------------------------------------


def test_default_policy_configures_no_threshold():
    p = RiskPolicy()
    for name in ("max_risk_per_trade", "max_open_positions", "max_pending_orders",
                 "max_instrument_exposure", "correlated_exposure", "max_daily_loss",
                 "max_drawdown", "max_spread", "max_quote_age_seconds", "max_slippage",
                 "cooldowns", "event_restrictions", "max_position_volume"):
        assert getattr(p, name).state is ControlState.UNSET, name
    assert not p.allow_proxy_market_data and not p.overweight_allowed
    assert not p.size_to_max_risk and not p.test_only
    assert p.missing_input_outcome == "FAIL"


def test_a_limit_is_given_exactly_when_enabled():
    with pytest.raises(ValidationError, match="exactly when"):
        RiskPolicy.model_validate({"max_drawdown": {"state": "ENABLED"}})
    with pytest.raises(ValidationError, match="exactly when"):
        RiskPolicy.model_validate({"max_drawdown": {"state": "UNSET", "limit": "0.1"}})
    with pytest.raises(ValidationError):
        RiskPolicy.model_validate({"max_drawdown": {"state": "ENABLED", "limit": "1.5"}})
    with pytest.raises(ValidationError):
        RiskPolicy.model_validate({"max_drawdown": {"state": "ENABLED", "limit": 0.1}})  # float
    with pytest.raises(ValidationError, match="only when"):
        RiskPolicy.model_validate({"max_spread": {"state": "UNSET", "limits": {"XAUUSD": "1"}}})


@pytest.mark.parametrize("name", MANDATORY_CONTROLS)
def test_mandatory_controls_cannot_be_disabled(name):
    with pytest.raises(ValidationError, match="mandatory"):
        RiskPolicy.model_validate({name: {"state": "DISABLED"}})


def test_formula_sizing_needs_a_configured_risk_limit():
    with pytest.raises(ValidationError, match="size_to_max_risk"):
        RiskPolicy(size_to_max_risk=True)


def test_correlation_clusters_are_configuration_only():
    with pytest.raises(ValidationError, match="clusters"):
        RiskPolicy.model_validate({"correlated_exposure": {"state": "ENABLED", "limit": "0.1"}})
    with pytest.raises(ValidationError, match="two distinct"):
        RiskPolicy.model_validate({"correlated_exposure": {
            "state": "ENABLED", "clusters": [["XAUUSD"]], "limit": "0.1"}})


def test_policy_hash_is_stable_and_content_sensitive():
    assert TEST_POLICY.policy_hash() == RiskPolicy.model_validate(
        TEST_POLICY.model_dump()).policy_hash()
    assert TEST_POLICY.policy_hash() != RiskPolicy().policy_hash()


def test_test_only_policy_is_refused_for_real_decisions():
    with pytest.raises(PolicyRejected):
        RiskEngine(TEST_POLICY)
    assert engine().policy.test_only


def test_risk_engine_gate_is_implemented_but_trading_still_not_permitted():
    assert {FeatureGate.MARKET_DATA, FeatureGate.RISK_ENGINE} <= IMPLEMENTED_FEATURES
    config = StellarConfig.model_validate({"features": {"risk_engine": True,
                                                        "market_data": True}})
    assert config.trading_permitted()[0] is False


# --- context / state ------------------------------------------------------------------


def test_context_distinguishes_unknown_from_empty_book():
    assert context().positions == ()
    assert context(positions=None).positions is None


def test_execution_mode_input_cannot_open_the_demo_gate():
    with pytest.raises(ValidationError):
        context(execution={"mode": "DEMO", "demo_gate_open": True})


def test_state_contracts_reject_invented_or_inconsistent_values():
    with pytest.raises(ValidationError):
        AccountRiskState(currency="USD", equity="1000", peak_equity="900", as_of=AS_OF,
                         source="test_fixture")
    with pytest.raises(ValidationError):
        InstrumentRiskMetadata(instrument="XAUUSD", account_currency="USD",
                               value_per_price_unit_per_lot="100", lot_step="0.01",
                               min_volume="1", max_volume="0.5", source="test_fixture")
    with pytest.raises(ValidationError):
        AccountRiskState(currency="USD", equity="1000", as_of=AS_OF, source="guess")


# --- additive Phase 1 extensions --------------------------------------------------------


def test_phase1_risk_checks_and_decisions_remain_valid():
    assert RiskCheck(rule="max_spread", passed=False).blocks
    assert make_decision().outcome == "APPROVED"


def test_status_checks_never_turn_not_configured_into_a_pass():
    with pytest.raises(ValidationError, match="passed is true exactly"):
        RiskCheck(rule="max_spread", passed=True, status="NOT_CONFIGURED", blocking=True)
    unset = RiskCheck(rule="max_spread", passed=False, status="NOT_CONFIGURED", blocking=True)
    disabled = RiskCheck(rule="max_spread", passed=False, status="NOT_CONFIGURED",
                         blocking=False)
    assert unset.blocks and not disabled.blocks and not disabled.passed
    with pytest.raises(ValidationError, match="always block"):
        RiskCheck(rule="max_spread", passed=False, status="FAIL", blocking=False)
    with pytest.raises(ValidationError, match="cannot block"):
        RiskCheck(rule="max_spread", passed=True, status="PASS", blocking=True)


def test_decision_outcome_must_follow_status_precedence():
    fail = {"rule": "max_spread", "passed": False, "status": "FAIL", "blocking": True}
    review = {"rule": "cooldown", "passed": False, "status": "REVIEW", "blocking": True}
    base = {"decision_id": "dec_x", "proposal_id": "prop_01", "instrument": "XAUUSD",
            "decided_at": AS_OF, "provenance": provenance("risk_engine")}
    with pytest.raises(ValidationError, match="FAIL check makes"):
        RiskDecision.model_validate({**base, "outcome": "REVIEW", "checks": [fail, review],
                                     "reasons": ["max_spread", "cooldown"]})
    with pytest.raises(ValidationError, match="needs a FAIL"):
        RiskDecision.model_validate({**base, "outcome": "REJECTED", "checks": [review],
                                     "reasons": ["cooldown"]})
    ok = RiskDecision.model_validate({**base, "outcome": "REVIEW", "checks": [review],
                                      "reasons": ["cooldown"]})
    assert ok.outcome == "REVIEW"


def test_review_outcome_has_a_canonical_event():
    assert "risk.review.requested" in EVENT_TYPES
    assert REQUIRED_PAYLOAD_KEYS["risk.review.requested"] == {"proposal_id", "decision_id",
                                                              "reasons"}


def test_check_status_values():
    assert {s.value for s in CheckStatus} == {"PASS", "FAIL", "REVIEW", "NOT_APPLICABLE",
                                              "NOT_CONFIGURED"}
    assert Decimal("0.01") == TEST_POLICY.max_risk_per_trade.limit
