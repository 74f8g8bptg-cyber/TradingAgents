"""Rule-by-rule behaviour and decision precedence. All data SYNTHETIC; limits TEST-ONLY."""

import itertools
import socket
from datetime import timedelta
from decimal import Decimal

import pytest
from factories import T0, make_proposal, proposal_data
from risk_helpers import AS_OF, TEST_POLICY, H, context, engine, market, policy, result
from stellar.marketdata import MappingKind, SubstitutionPolicy
from stellar.risk import (
    RULES,
    BreakerTrip,
    CircuitBreakerState,
    InvalidRiskInput,
    PendingOrderState,
    PositionState,
    RiskEngine,
    RiskEvaluation,
    RiskPolicy,
    RuleResult,
    decide,
)
from stellar.schemas.market import DataQualityFlag
from stellar.schemas.order import idempotency_key_for
from stellar.schemas.proposal import TradeProposal
from stellar.schemas.risk import CheckStatus, RiskOutcome, RiskRule

pytestmark = pytest.mark.unit


def run(p=None, **ctx):
    return engine(p).evaluate(context(**ctx))


def status(ev, check):
    return result(ev, check).status


# --- approval and the default policy ------------------------------------------------------


def test_valid_proposal_is_approved_under_an_explicit_test_policy():
    ev = run()
    assert ev.decision.outcome is RiskOutcome.APPROVED
    assert ev.decision.volume == Decimal("0.50")
    assert ev.decision.risk_pct_equity == Decimal("0.006")
    assert ev.decision.reasons == ()
    assert len(ev.results) == len(RULES)
    assert ev.decision.provenance.config_hash == TEST_POLICY.policy_hash()


def test_default_policy_never_approves_and_reports_not_configured_not_pass():
    ev = RiskEngine(RiskPolicy()).evaluate(context())
    assert ev.decision.outcome is RiskOutcome.REVIEW
    for check in ("max_risk_per_trade", "max_daily_loss", "max_spread", "open_positions",
                  "instrument_exposure", "cooldown", "event_restriction"):
        name = {"max_daily_loss": "daily_loss"}.get(check, check)
        r = result(ev, name)
        assert r.status is CheckStatus.NOT_CONFIGURED and r.blocking, name
        assert not r.to_check().passed
    assert RiskRule.MAX_RISK_PER_TRADE in ev.decision.reasons


def test_explicitly_disabled_controls_are_not_configured_but_do_not_block():
    p = policy(max_spread={"state": "DISABLED"}, cooldowns={"state": "DISABLED"})
    ev = run(p)
    for check in ("max_spread", "cooldown"):
        r = result(ev, check)
        assert (r.status, r.reason, r.blocking) == (CheckStatus.NOT_CONFIGURED,
                                                    "disabled_by_policy", False)
    assert ev.decision.outcome is RiskOutcome.APPROVED


def test_reward_risk_is_never_evaluated():
    r = result(run(), "min_reward_risk")
    assert (r.status, r.reason, r.blocking) == (CheckStatus.NOT_CONFIGURED,
                                                "reward_risk_method_undecided", False)


# --- structural rules ---------------------------------------------------------------------


def test_malformed_proposal_is_refused_before_any_rule_runs():
    bad = TradeProposal.model_construct(**{**make_proposal().model_dump(), "size_factor": 5})
    with pytest.raises(InvalidRiskInput):
        engine().evaluate(context().model_copy(update={"proposal": bad}))
    # A well-formed proposal records the schema check as passed.
    assert status(run(), "proposal_schema") is CheckStatus.PASS


def test_unsupported_instrument():
    ev = run(enabled_instruments=("EURUSD",))
    assert status(ev, "instrument_supported") is CheckStatus.FAIL
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_expired_and_future_proposals_are_rejected():
    ev = run(as_of=T0 + 2 * H)
    assert status(ev, "proposal_expiry") is CheckStatus.FAIL
    ev = run(as_of=T0 - timedelta(minutes=1))
    assert result(ev, "proposal_time").reason == "proposal_created_after_as_of"


@pytest.mark.parametrize("mode,reason", [("LIVE", "live_not_permitted"),
                                          ("DEMO", "demo_gate_closed")])
def test_live_is_blocked_and_demo_stays_gated(mode, reason):
    ev = run(execution={"mode": mode})
    r = result(ev, "execution_mode")
    assert (r.status, r.reason) == (CheckStatus.FAIL, reason)
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_tripped_breaker_rejects():
    trip = BreakerTrip(cause="owner", tripped_by="owner", tripped_at=T0 - H)
    tripped = CircuitBreakerState(updated_at=T0 - H).tripped(trip)
    ev = run(breaker=tripped)
    assert status(ev, "circuit_breaker") is CheckStatus.FAIL
    assert ev.decision.outcome is RiskOutcome.REJECTED
    assert ev.breaker_trip is None  # sticky: no second trip proposed


def test_overweight_waits_for_d9():
    ev = run(proposal=make_proposal(source_rating="Overweight", size_factor="0.5"))
    assert status(ev, "size_factor") is CheckStatus.REVIEW
    assert ev.decision.outcome is RiskOutcome.REVIEW
    allowed = run(policy(overweight_allowed=True),
                  proposal=make_proposal(source_rating="Overweight", size_factor="0.5"))
    assert status(allowed, "size_factor") is CheckStatus.PASS


def test_stop_through_the_current_market_is_rejected():
    snap, quote = market(bid="2411.80", ask="2412.10")
    ev = run(snapshot=snap, quote=quote)
    assert result(ev, "stop_loss").reason == "stop_through_current_market"


def test_stop_inside_the_broker_stops_level_is_rejected():
    meta = context().metadata.model_dump() | {"min_stop_distance": "15"}
    ev = run(metadata=meta)
    r = result(ev, "stop_loss")
    assert (r.reason, r.value, r.limit) == ("below_broker_stops_level", Decimal("12.00"),
                                            Decimal("15"))


def test_duplicate_order_is_rejected():
    key = idempotency_key_for("prop_01")
    ev = run(prior_idempotency_keys=(key,))
    assert status(ev, "duplicate_order") is CheckStatus.FAIL
    pending = PendingOrderState(instrument="XAUUSD", side="SELL", volume="0.5",
                                idempotency_key=key, open_risk="600", source="test_fixture")
    assert status(run(pending_orders=(pending,)), "duplicate_order") is CheckStatus.FAIL


# --- market data --------------------------------------------------------------------------


def test_missing_critical_market_data_follows_the_explicit_policy():
    ev = run(snapshot=None)
    assert result(ev, "market_data_present").reason == "missing_market_snapshot"
    assert ev.decision.outcome is RiskOutcome.REJECTED
    ev = run(policy(missing_input_outcome="REVIEW"), snapshot=None)
    assert ev.decision.outcome is RiskOutcome.REVIEW


def test_proxy_snapshot_is_refused_unless_authorised_and_proxy_quotes_never_used():
    snap, quote = market(kind=MappingKind.PROXY, symbol="GC=F")
    ev = run(snapshot=snap, quote=None)
    assert result(ev, "market_data_source").reason == "proxy_snapshot_not_authorised"
    allowed = run(policy(allow_proxy_market_data=True, max_spread={"state": "DISABLED"},
                         max_quote_age_seconds={"state": "DISABLED"}), snapshot=snap, quote=None)
    assert result(allowed, "market_data_source").reason == "proxy_allowed_for_analysis_only"
    with_quote = run(policy(allow_proxy_market_data=True), snapshot=snap, quote=quote)
    assert result(with_quote, "quote_integrity").reason == "proxy_quote_never_for_order_levels"
    assert with_quote.decision.outcome is RiskOutcome.REJECTED


def test_market_data_after_as_of_is_rejected():
    ev = run(as_of=AS_OF - timedelta(minutes=5))
    assert result(ev, "market_data_consistent").reason == "snapshot_after_as_of"
    assert result(ev, "quote_integrity").reason == "quote_after_as_of"
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_calendar_naive_signals_never_reject_or_trip():
    snap = context().snapshot
    flagged = snap.model_copy(update={"quality": snap.quality.model_copy(update={
        "flags": (DataQualityFlag.GAP_DETECTED, DataQualityFlag.PARTIAL_SERIES,
                  DataQualityFlag.STALE)})})
    ev = run(snapshot=flagged)
    r = result(ev, "market_data_quality")
    assert (r.status, r.reason) == (CheckStatus.NOT_APPLICABLE,
                                    "calendar_naive_signal_not_risk_evidence")
    assert ev.decision.outcome is RiskOutcome.APPROVED and ev.breaker_trip is None


def test_source_precision_loss_needs_review():
    snap = context().snapshot
    lossy = snap.model_copy(update={"quality": snap.quality.model_copy(update={
        "flags": (DataQualityFlag.SOURCE_PRECISION_LOSS,)})})
    assert run(snapshot=lossy).decision.outcome is RiskOutcome.REVIEW


# --- spread / quote age / slippage ---------------------------------------------------------


def test_configured_max_spread_pass_and_fail():
    r = result(run(), "max_spread")
    assert (r.status, r.value, r.limit) == (CheckStatus.PASS, Decimal("0.30"), Decimal("0.50"))
    snap, quote = market(bid="2399.40", ask="2400.10")
    wide = run(snapshot=snap, quote=quote)
    assert result(wide, "max_spread").reason == "spread_above_limit"


def test_missing_spread_data_is_never_fabricated():
    ev = run(quote=None)
    r = result(ev, "max_spread")
    assert r.reason == "missing_quote" and r.value is None
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_spread_limit_missing_for_the_instrument_is_not_configured():
    ev = run(policy(max_spread={"state": "ENABLED", "limits": {"EURUSD": "0.0002"}}))
    r = result(ev, "max_spread")
    assert (r.status, r.reason) == (CheckStatus.NOT_CONFIGURED,
                                    "limit_not_configured_for_instrument")
    assert ev.decision.outcome is RiskOutcome.REVIEW


def test_old_quote_needs_review_not_rejection():
    snap, quote = market(quote_ts=AS_OF - timedelta(minutes=5))
    ev = run(snapshot=snap, quote=quote)
    r = result(ev, "quote_age")
    assert (r.status, r.reason) == (CheckStatus.REVIEW, "quote_age_exceeds_limit_calendar_naive")
    assert ev.decision.outcome is RiskOutcome.REVIEW and ev.breaker_trip is None


def test_slippage_tolerance_must_be_configured():
    ev = run(policy(max_slippage={"state": "UNSET"}))
    assert status(ev, "slippage_tolerance") is CheckStatus.NOT_CONFIGURED
    assert ev.decision.outcome is RiskOutcome.REVIEW


# --- sizing ---------------------------------------------------------------------------------


def test_max_risk_per_trade_pass_and_fail():
    ev = run(requested_volume="0.90")  # 0.90 × 12 × 100 = 1080 USD = 1.08 %
    r = result(ev, "max_risk_per_trade")
    assert (r.status, r.value, r.limit) == (CheckStatus.FAIL, Decimal("0.0108"), Decimal("0.01"))
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_formula_sizing_rounds_down_to_the_lot_step():
    ev = run(policy(size_to_max_risk=True), requested_volume=None)
    # 100000 × 0.01 × 1 / (12 × 100) = 0.8333… → 0.83 lots
    assert ev.decision.volume == Decimal("0.83")
    assert ev.decision.risk_pct_equity == Decimal("0.00996")


def test_missing_sizing_inputs_are_never_guessed():
    for override, reason in (({"requested_volume": None}, "missing_requested_volume"),
                             ({"metadata": None}, "missing_instrument_metadata"),
                             ({"account": None}, "missing_account_state")):
        ev = run(**override)
        assert result(ev, "position_sizing").reason == reason, reason
        assert ev.decision.outcome is not RiskOutcome.APPROVED


def test_sizing_rejects_bad_volumes_and_currency_mismatch():
    assert result(run(requested_volume="0.505"), "position_sizing").reason == \
        "volume_not_multiple_of_lot_step"
    meta = context().metadata.model_dump()
    assert result(run(metadata=meta | {"min_volume": "1"}), "position_sizing").reason == \
        "below_min_volume"
    assert result(run(metadata=meta | {"max_volume": "0.1"}), "position_sizing").reason == \
        "above_broker_max_volume"
    assert result(run(metadata=meta | {"account_currency": "EUR"}), "position_sizing").reason \
        == "account_currency_mismatch"


def test_zone_entries_are_not_sized_by_an_invented_reference():
    zone = make_proposal(entry={"type": "limit", "zone_low": "2398.00", "zone_high": "2402.00"})
    ev = run(proposal=zone)
    assert result(ev, "position_sizing").reason == "entry_zone_sizing_reference_undecided"
    assert ev.decision.outcome is RiskOutcome.REVIEW


def test_max_position_volume():
    ev = run(policy(max_position_volume={"state": "ENABLED", "limits": {"XAUUSD": "0.25"}}))
    assert result(ev, "max_position_volume").reason == "volume_above_limit"


# --- book, exposure, daily loss, drawdown ---------------------------------------------------------


def _position(instrument="XAUUSD", risk="600"):
    return PositionState(instrument=instrument, side="SELL", volume="0.5", open_price="2400",
                         stop_loss="2412", open_risk=risk, source="test_fixture")


def test_open_position_and_pending_order_counts():
    three = tuple(_position(risk="1") for _ in range(3))
    assert result(run(positions=three), "open_positions").reason == "open_positions_at_limit"
    assert result(run(positions=None), "open_positions").reason == "missing_open_positions"


def test_instrument_exposure():
    assert status(run(positions=(_position(risk="1000"),)), "instrument_exposure") \
        is CheckStatus.PASS  # (1000 + 600) / 100000 = 1.6 %
    r = result(run(positions=(_position(risk="1500"),)), "instrument_exposure")
    assert (r.status, r.value) == (CheckStatus.FAIL, Decimal("0.021"))
    assert result(run(positions=(_position(risk=None),)), "instrument_exposure").reason == \
        "missing_open_risk"


def test_correlated_exposure_uses_configured_clusters_only():
    ev = run(positions=(_position("EURUSD", "1500"), _position("USDJPY", "1000")))
    r = result(ev, "correlated_exposure")
    assert (r.status, r.value) == (CheckStatus.FAIL, Decimal("0.031"))
    solo = run(policy(correlated_exposure={"state": "ENABLED", "clusters": [["EURUSD", "USDJPY"]],
                                           "limit": "0.03"}))
    assert result(solo, "correlated_exposure").reason == "instrument_in_no_cluster"


def test_daily_loss_pass_fail_and_breaker_trip():
    daily = context().daily.model_dump()
    ok = run(daily=daily | {"realised_pnl": "-2000"})
    assert status(ok, "daily_loss") is CheckStatus.PASS
    breach = run(daily=daily | {"realised_pnl": "-2500", "unrealised_pnl": "-500"})
    r = result(breach, "daily_loss")
    assert (r.status, r.value, r.trips_breaker) == (CheckStatus.FAIL, Decimal("0.03"), True)
    assert breach.breaker_trip.rule is RiskRule.MAX_DAILY_LOSS
    no_trip = run(policy(trip={"on_daily_loss_breach": False}),
                  daily=daily | {"realised_pnl": "-3000"})
    assert no_trip.decision.outcome is RiskOutcome.REJECTED and no_trip.breaker_trip is None
    missing = run(daily=daily | {"unrealised_pnl": None}, positions=(_position(),))
    assert result(missing, "daily_loss").reason == "missing_unrealised_pnl"


def test_drawdown_rule_and_trip():
    account = context().account.model_dump()
    ev = run(account=account | {"equity": "89000", "peak_equity": "100000"})
    r = result(ev, "drawdown")
    assert (r.status, r.value) == (CheckStatus.FAIL, Decimal("0.11"))
    assert ev.breaker_trip.rule is RiskRule.MAX_DRAWDOWN
    assert result(run(account=account | {"peak_equity": None}), "drawdown").reason == \
        "missing_peak_equity"


def test_a_plain_rejection_does_not_propose_a_breaker_trip():
    ev = run(requested_volume="0.90")
    assert ev.decision.outcome is RiskOutcome.REJECTED and ev.breaker_trip is None


# --- cooldowns and event restrictions ------------------------------------------------------------


def test_cooldowns():
    active = {"instrument": "XAUUSD", "until": AS_OF + H, "reason": "after_loss",
              "source": "test_fixture"}
    assert result(run(cooldowns=(active,)), "cooldown").reason == "cooldown_active"
    expired = active | {"until": AS_OF}
    assert status(run(cooldowns=(expired,)), "cooldown") is CheckStatus.PASS
    assert result(run(cooldowns=None), "cooldown").reason == "missing_cooldown_state"


def test_event_restrictions_are_consumed_not_invented():
    er = context().event_restriction.model_dump()
    assert result(run(event_restriction=er | {"restricted": True}), "event_restriction").reason \
        == "event_window_active"
    assert result(run(event_restriction=None), "event_restriction").reason == \
        "missing_event_restriction_state"
    assert result(run(event_restriction=er | {"evaluated_at": AS_OF + H}),
                  "event_restriction").reason == "restriction_after_as_of"


# --- precedence, determinism, replay ----------------------------------------------------------------


def _rr(status, blocking=None):
    return RuleResult(check="x", rule="cooldown", status=status, reason="r",
                      blocking=blocking if blocking is not None else status in {"FAIL", "REVIEW"})


def test_decision_precedence_is_exhaustive():
    options = [_rr("PASS"), _rr("NOT_APPLICABLE"), _rr("FAIL"), _rr("REVIEW"),
               _rr("NOT_CONFIGURED", True), _rr("NOT_CONFIGURED", False)]
    for n in range(0, 4):
        for combo in itertools.product(options, repeat=n):
            blocking = [r for r in combo if r.blocking]
            expected = (RiskOutcome.REJECTED if any(r.status is CheckStatus.FAIL for r in blocking)
                        else RiskOutcome.REVIEW if blocking else RiskOutcome.APPROVED)
            assert decide(list(combo)) is expected


def test_fail_beats_review_in_a_real_evaluation():
    ev = run(execution={"mode": "LIVE"}, proposal=make_proposal(source_rating="Overweight",
                                                                size_factor="0.5"))
    assert status(ev, "size_factor") is CheckStatus.REVIEW
    assert ev.decision.outcome is RiskOutcome.REJECTED
    assert {RiskRule.EXECUTION_MODE, RiskRule.SIZE_FACTOR} <= set(ev.decision.reasons)


def test_same_input_and_policy_give_the_same_evaluation():
    one, two = run(), run()
    assert one == two
    assert one.model_dump_json() == two.model_dump_json()
    assert one.decision.decision_id == two.decision.decision_id
    other = run(policy(version="test_policy_2"))
    assert other.decision.decision_id != one.decision.decision_id


def test_evaluation_replays_from_its_own_record():
    ev = run()
    stored = RiskEvaluation.model_validate_json(ev.model_dump_json())
    assert stored == ev
    assert engine(stored.policy).evaluate(stored.context) == ev


def test_a_tampered_evaluation_record_is_refused():
    data = run().model_dump()
    data["decision"]["outcome"] = "REVIEW"
    data["decision"]["volume"] = None
    data["decision"]["risk_pct_equity"] = None
    data["decision"]["reasons"] = ["cooldown"]
    with pytest.raises(ValueError):
        RiskEvaluation.model_validate(data)


def test_no_network_is_used(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert run().decision.outcome is RiskOutcome.APPROVED


def test_proposal_data_used_is_synthetic():
    assert proposal_data()["instrument"] == "XAUUSD"
    assert SubstitutionPolicy().allow_proxy is False
