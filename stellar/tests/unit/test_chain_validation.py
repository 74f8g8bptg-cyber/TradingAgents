"""Cross-record checks along proposal → decision → intent → result."""

from datetime import timedelta

import pytest
from factories import T0, make_decision, make_intent, make_proposal, make_result
from stellar.validation import (
    ChainValidationError,
    order_intent_problems,
    validate_execution_result,
    validate_order_intent,
    validate_risk_decision,
)

pytestmark = pytest.mark.unit


def test_a_consistent_chain_validates():
    proposal, decision, intent = make_proposal(), make_decision(), make_intent()
    validate_risk_decision(decision, proposal)
    validate_order_intent(intent, proposal, decision)
    validate_execution_result(make_result(), intent)


@pytest.mark.parametrize(
    "decision_overrides",
    [
        {"outcome": "REJECTED", "reasons": ["max_spread"], "volume": None,
         "risk_pct_equity": None, "checks": [{"rule": "max_spread", "passed": False}]},
        {"outcome": "REVIEW", "reasons": ["owner_review_required"], "volume": None},
    ],
)
def test_no_intent_without_an_approved_decision(decision_overrides):
    decision = make_decision(**decision_overrides)
    with pytest.raises(ChainValidationError) as err:
        validate_order_intent(make_intent(), make_proposal(), decision)
    assert "decision_not_approved" in err.value.problems
    assert "volume_mismatch" in err.value.problems


@pytest.mark.parametrize(
    "intent_overrides,problem",
    [
        ({"proposal_id": "prop_02", "idempotency_key": None}, "proposal_id_mismatch"),
        ({"decision_id": "dec_02"}, "decision_id_mismatch"),
        ({"volume": "0.20"}, "volume_mismatch"),
        ({"stop_loss": "2413.00"}, "stop_loss_mismatch"),
        ({"take_profit": "2380.00"}, "take_profit_mismatch"),
        ({"order_type": "market"}, "order_type_mismatch"),
        ({"price": "2401.00", "stop_loss": "2412.00"}, "price_mismatch"),
        ({"expires_at": T0 + timedelta(hours=2)}, "expires_after_proposal"),
        ({"created_at": T0, "expires_at": T0 + timedelta(minutes=10)},
         "created_before_decision"),
        ({"instrument": "EURUSD"}, "instrument_mismatch"),
    ],
)
def test_intent_must_match_its_proposal_and_decision(intent_overrides, problem):
    from stellar.schemas import idempotency_key_for

    if intent_overrides.get("idempotency_key", "") is None:
        intent_overrides["idempotency_key"] = idempotency_key_for(intent_overrides["proposal_id"])
    intent = make_intent(**intent_overrides)
    assert problem in order_intent_problems(intent, make_proposal(), make_decision())


def test_side_must_follow_the_proposal_direction():
    intent = make_intent(side="BUY", price="2400.00", stop_loss="2390.00", take_profit="2410.00")
    problems = order_intent_problems(intent, make_proposal(), make_decision())
    assert "side_mismatch" in problems


def test_decision_must_belong_to_the_proposal():
    with pytest.raises(ChainValidationError, match="decision_proposal_mismatch"):
        validate_risk_decision(make_decision(proposal_id="prop_99"), make_proposal())
    with pytest.raises(ChainValidationError, match="decided_before_proposal"):
        validate_risk_decision(make_decision(decided_at=T0 - timedelta(seconds=1)),
                               make_proposal())


@pytest.mark.parametrize(
    "result_overrides,problem",
    [
        ({"intent_id": "int_02"}, "intent_id_mismatch"),
        ({"account_mode": "DEMO"}, "account_mode_mismatch"),
        ({"requested_volume": "0.20", "filled_volume": "0.20"}, "volume_mismatch"),
        ({"ts": T0}, "result_before_intent"),
    ],
)
def test_result_must_match_its_intent(result_overrides, problem):
    with pytest.raises(ChainValidationError) as err:
        validate_execution_result(make_result(**result_overrides), make_intent())
    assert problem in err.value.problems
