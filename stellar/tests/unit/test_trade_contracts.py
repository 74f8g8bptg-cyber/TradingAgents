"""TradeProposal, RiskDecision, OrderIntent and ExecutionResult rules."""

from datetime import timedelta
from decimal import Decimal

import pytest
from factories import (
    T0,
    make_decision,
    make_intent,
    make_proposal,
    make_result,
    provenance,
)
from pydantic import ValidationError
from stellar.schemas import TradeProposal, idempotency_key_for

pytestmark = pytest.mark.unit

LONG = {
    "direction": "LONG",
    "entry": {"type": "limit", "price": "1.1000"},
    "stop_loss": {"price": "1.0950", "basis": "swing_low"},
    "take_profits": [{"price": "1.1100", "basis": "range_high"},
                     {"price": "1.1150", "basis": "measured_move"}],
    "reward_risk": "2.0000",
    "instrument": "EURUSD",
}

# --- TradeProposal ------------------------------------------------------------


def test_long_and_short_proposals_with_typed_levels():
    short = make_proposal()
    assert short.stop_loss.price == Decimal("2412.00")
    assert short.take_profits[0].price == Decimal("2376.00")
    long = make_proposal(**LONG)
    assert long.reward_risk == Decimal("2")


@pytest.mark.parametrize("rating", ["Hold", "Underweight", "Sell", "REVIEW"])
def test_only_buy_or_overweight_ratings_produce_proposals(rating):
    with pytest.raises(ValidationError, match="never produces a proposal"):
        make_proposal(source_rating=rating)


def test_rating_values_are_validated_against_the_upstream_vocabulary():
    with pytest.raises(ValidationError):
        make_proposal(source_rating="Strong Buy")


def test_buy_is_taken_at_full_size_and_overweight_takes_a_factor():
    with pytest.raises(ValidationError, match="size factor 1"):
        make_proposal(size_factor="0.5")
    assert make_proposal(source_rating="Overweight", size_factor="0.5").size_factor == Decimal(
        "0.5"
    )
    for bad in ("0", "1.5", "-0.1"):
        with pytest.raises(ValidationError):
            make_proposal(source_rating="Overweight", size_factor=bad)


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"stop_loss": {"price": "2390.00", "basis": "x"}}, "stop-loss must be above"),
        ({"take_profits": [{"price": "2410.00", "basis": "x"}]}, "take-profit must be below"),
        ({"take_profits": []}, "at least 1"),
        ({"take_profits": [{"price": "2350.00", "basis": "far"},
                           {"price": "2376.00", "basis": "near"}]}, "nearest first"),
        ({"valid_until": T0}, "valid_until"),
        ({"entry": {"type": "limit"}}, "price or a zone"),
        ({"entry": {"type": "limit", "price": "2400", "zone_low": "2399",
                    "zone_high": "2401"}}, "not both"),
        ({"entry": {"type": "limit", "zone_low": "2401", "zone_high": "2399"}}, "zone_low"),
    ],
)
def test_malformed_proposals_are_rejected(overrides, message):
    with pytest.raises(ValidationError, match=message):
        make_proposal(**overrides)


def test_long_stop_must_be_below_the_entry():
    with pytest.raises(ValidationError, match="stop-loss must be below"):
        make_proposal(**{**LONG, "stop_loss": {"price": "1.1050", "basis": "x"}})


def test_zone_entries_check_levels_against_both_zone_edges():
    zone = {"type": "limit", "zone_low": "2398.00", "zone_high": "2402.00"}
    assert make_proposal(entry=zone).entry.bounds() == (Decimal("2398.00"), Decimal("2402.00"))
    with pytest.raises(ValidationError, match="stop-loss must be above"):
        make_proposal(entry=zone, stop_loss={"price": "2401.00", "basis": "x"})
    with pytest.raises(ValidationError, match="take-profit must be below"):
        make_proposal(entry=zone, take_profits=[{"price": "2399.00", "basis": "x"}])


def test_reward_risk_is_provisional_typed_and_never_recomputed():
    # No measurement method is decided, so the stated value is kept as given...
    assert make_proposal(reward_risk="3.0000").reward_risk == Decimal("3.0000")
    assert make_proposal(reward_risk=None).reward_risk is None
    # ...but it must still be a typed, finite, positive number.
    for bad in ("0", "-1", "NaN", 2.0, "two"):
        with pytest.raises(ValidationError):
            make_proposal(reward_risk=bad)
    description = TradeProposal.model_fields["reward_risk"].description
    assert "PROVISIONAL" in description and "No rule may use it" in description
    import stellar.schemas as schemas

    assert not hasattr(schemas, "compute_reward_risk")


def test_proposals_are_built_only_by_the_trade_proposal_builder():
    with pytest.raises(ValidationError, match="trade_proposal_builder"):
        make_proposal(provenance=provenance("trader"))


def test_trader_levels_stay_advisory_and_typed():
    proposal = make_proposal(llm_levels_advisory={"entry": "2401.00", "stop": None})
    assert proposal.llm_levels_advisory.entry == Decimal("2401.00")
    with pytest.raises(ValidationError):
        make_proposal(llm_levels_advisory={"entry": "around 2400"})


# --- RiskDecision -------------------------------------------------------------


def test_approved_decision_needs_checks_volume_and_no_reasons():
    assert make_decision().outcome == "APPROVED"
    with pytest.raises(ValidationError, match="record the checks"):
        make_decision(checks=[])
    with pytest.raises(ValidationError, match="volume"):
        make_decision(volume=None)
    with pytest.raises(ValidationError, match="failed checks"):
        make_decision(checks=[{"rule": "max_spread", "passed": False}], reasons=["max_spread"])


def test_rejected_and_review_decisions_need_reason_codes_and_no_volume():
    rejected = make_decision(outcome="REJECTED", reasons=["max_spread"], volume=None,
                             risk_pct_equity=None,
                             checks=[{"rule": "max_spread", "passed": False,
                                      "value": "0.9", "limit": "0.5"}])
    assert rejected.reasons == ("max_spread",)
    with pytest.raises(ValidationError, match="reason codes"):
        make_decision(outcome="REJECTED", volume=None)
    with pytest.raises(ValidationError, match="no volume"):
        make_decision(outcome="REVIEW", reasons=["owner_review_required"])
    review = make_decision(outcome="REVIEW", reasons=["owner_review_required"], volume=None)
    assert review.outcome == "REVIEW"


def test_every_failed_check_is_a_reason_and_reason_codes_are_closed():
    with pytest.raises(ValidationError, match="every failed check"):
        make_decision(outcome="REJECTED", volume=None, reasons=["cooldown"],
                      checks=[{"rule": "max_spread", "passed": False}])
    with pytest.raises(ValidationError):
        make_decision(outcome="REJECTED", volume=None, reasons=["looked risky"])


def test_decisions_are_made_only_by_the_risk_engine():
    with pytest.raises(ValidationError, match="risk_engine"):
        make_decision(provenance=provenance("portfolio_manager", "prop_01"))


# --- OrderIntent --------------------------------------------------------------


def test_intent_needs_references_stop_and_slippage():
    for missing in ("proposal_id", "decision_id", "stop_loss", "max_slippage",
                    "idempotency_key", "account_mode"):
        data = make_intent().model_dump()
        del data[missing]
        with pytest.raises(ValidationError):
            type(make_intent()).model_validate(data)


def test_intent_modes_are_paper_or_demo_only():
    with pytest.raises(ValidationError):
        make_intent(account_mode="LIVE")
    assert make_intent(account_mode="DEMO").account_mode == "DEMO"


def test_intent_idempotency_key_is_the_hash_of_the_proposal_id():
    assert make_intent().idempotency_key == idempotency_key_for("prop_01")
    with pytest.raises(ValidationError, match="idempotency_key"):
        make_intent(idempotency_key=idempotency_key_for("prop_02"))


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"stop_loss": "2390.00"}, "SELL stop-loss"),
        ({"take_profit": "2420.00"}, "SELL take-profit"),
        ({"price": None}, "limit order needs a price"),
        ({"volume": "0"}, "greater than 0"),
        ({"expires_at": T0}, "expires_at"),
        ({"provenance": provenance("paper_execution")}, "risk_engine"),
    ],
)
def test_malformed_intents_are_rejected(overrides, message):
    with pytest.raises(ValidationError, match=message):
        make_intent(**overrides)


def test_market_intent_without_price_still_checks_stop_against_target():
    intent = make_intent(order_type="market", price=None)
    assert intent.price is None
    with pytest.raises(ValidationError, match="take-profit"):
        make_intent(order_type="market", price=None, take_profit="2420.00")


# --- ExecutionResult ----------------------------------------------------------


def test_execution_lifecycle_statuses():
    assert make_result().status == "filled"
    partial = make_result(status="partially_filled", filled_volume="0.05")
    assert partial.filled_volume == Decimal("0.05")
    sent = make_result(status="sent", filled_volume="0", fill_id=None, fill_price=None,
                       slippage=None)
    assert sent.fill_price is None
    rejected = make_result(status="rejected", filled_volume="0", fill_id=None, fill_price=None,
                           slippage=None, reason="invalid_volume")
    assert rejected.reason == "invalid_volume"


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"filled_volume": "0.05"}, "whole requested volume"),
        ({"fill_price": None}, "fill_price"),
        ({"status": "partially_filled"}, "partial fill"),
        ({"status": "sent"}, "carries no fill"),
        ({"status": "rejected", "filled_volume": "0", "fill_id": None, "fill_price": None,
          "slippage": None}, "must give a reason"),
        ({"reason": "spread_too_wide"}, "no failure reason"),
        ({"status": "closed"}, "status"),
        ({"broker_ticket": "123"}, "broker ticket"),
        ({"provenance": provenance("risk_engine")}, "execution agents"),
        ({"provenance": provenance("mt5_execution")}, "demo accounts only"),
    ],
)
def test_malformed_execution_results_are_rejected(overrides, message):
    with pytest.raises(ValidationError, match=message):
        make_result(**overrides)


def test_result_timestamp_is_required():
    data = make_result().model_dump()
    data["ts"] = None
    with pytest.raises(ValidationError):
        type(make_result()).model_validate(data)
    assert make_result(ts=T0 + timedelta(minutes=5)).ts > T0
