"""CircuitBreakerState: state only, sticky trips, owner-only resets, event compatible."""

from datetime import timedelta

import pytest
from factories import T0, make_event
from pydantic import ValidationError
from stellar.risk import (
    BreakerStatus,
    BreakerTrip,
    CircuitBreakerState,
    OwnerReset,
    TripCause,
)

pytestmark = pytest.mark.unit


def trip(**overrides):
    data = {"cause": "risk_rule", "rule": "max_daily_loss", "value": "-3.2", "limit": "-3.0",
            "tripped_by": "risk_engine", "tripped_at": T0}
    data.update(overrides)
    return BreakerTrip.model_validate(data)


def test_default_state_is_armed_and_not_blocking():
    state = CircuitBreakerState(updated_at=T0)
    assert state.status is BreakerStatus.ARMED
    assert state.trip is None and not state.trading_blocked


def test_tripping_blocks_trading_and_is_sticky():
    state = CircuitBreakerState(updated_at=T0).tripped(trip())
    assert state.status is BreakerStatus.TRIPPED and state.trading_blocked
    again = state.tripped(trip(rule="max_drawdown", tripped_at=T0 + timedelta(minutes=5)))
    assert again == state  # the first trip is kept; nothing re-arms or replaces it


@pytest.mark.parametrize(
    "cause,tripped_by",
    [("reconciliation_mismatch", "execution_checker"), ("data_failure", "data_validator"),
     ("budget_exhaustion", "wellbeing_monitor"), ("owner", "owner")],
)
def test_any_documented_cause_can_trip(cause, tripped_by):
    state = CircuitBreakerState(updated_at=T0).tripped(
        trip(cause=cause, rule=None, value=None, limit=None, tripped_by=tripped_by))
    assert state.trip.cause == cause


def test_trip_validation():
    with pytest.raises(ValidationError, match="name its rule"):
        trip(rule=None)
    with pytest.raises(ValidationError, match="owner"):
        trip(cause="owner", rule=None, tripped_by="risk_engine")
    with pytest.raises(ValidationError, match="owner"):
        trip(tripped_by="owner")
    with pytest.raises(ValidationError):
        trip(value=1.5)
    with pytest.raises(ValidationError):
        trip(rule="felt_risky")


def test_state_consistency():
    with pytest.raises(ValidationError, match="records its trip"):
        CircuitBreakerState(status="TRIPPED", updated_at=T0)
    with pytest.raises(ValidationError, match="no active trip"):
        CircuitBreakerState(status="ARMED", trip=trip(), updated_at=T0)
    with pytest.raises(ValidationError, match="before the trip"):
        CircuitBreakerState(status="TRIPPED", trip=trip(), updated_at=T0 - timedelta(seconds=1))


def test_there_is_no_reset_or_rearm_operation():
    operations = {name for name in dir(CircuitBreakerState) if not name.startswith("_")}
    assert not {n for n in operations if "reset" in n or "arm" in n or "clear" in n}
    state = CircuitBreakerState(updated_at=T0).tripped(trip())
    with pytest.raises(ValidationError):
        state.status = BreakerStatus.ARMED


def test_a_recorded_reset_is_always_the_owners():
    reset = OwnerReset(by="owner", reason="Reviewed the daily loss", reset_at=T0)
    state = CircuitBreakerState(updated_at=T0, last_reset=reset)
    assert state.last_reset.by == "owner" and not state.trading_blocked
    for by in ("risk_engine", "supervisor", "ui", "scheduler"):
        with pytest.raises(ValidationError):
            OwnerReset(by=by, reason="auto", reset_at=T0)
    with pytest.raises(ValidationError):
        OwnerReset(by="owner", reason="", reset_at=T0)


def test_an_active_trip_cannot_predate_the_last_reset():
    reset = OwnerReset(by="owner", reason="ok", reset_at=T0 + timedelta(minutes=1))
    with pytest.raises(ValidationError, match="predate"):
        CircuitBreakerState(status="TRIPPED", trip=trip(), last_reset=reset,
                            updated_at=T0 + timedelta(minutes=2))


def test_trip_round_trips_through_the_tripped_event():
    original = trip()
    event = make_event(0, type="circuit_breaker.tripped", source="stellar.risk",
                       agent_id="risk_engine", ts=T0, payload=original.to_event_payload())
    rebuilt = BreakerTrip.from_event(event)
    assert rebuilt.model_copy(update={"event_id": None}) == original
    assert rebuilt.event_id == event.event_id


def test_non_rule_trip_uses_its_cause_as_the_event_rule():
    manual = trip(cause="owner", rule=None, value=None, limit=None, tripped_by="owner")
    payload = manual.to_event_payload()
    assert payload["rule"] == "owner"
    event = make_event(0, type="circuit_breaker.tripped", ts=T0, payload=payload)
    assert BreakerTrip.from_event(event).cause is TripCause.OWNER


def test_from_event_refuses_other_event_types():
    with pytest.raises(ValueError, match="circuit_breaker.tripped"):
        BreakerTrip.from_event(make_event(0))


def test_state_serializes_deterministically():
    state = CircuitBreakerState(updated_at=T0).tripped(trip())
    assert CircuitBreakerState.model_validate_json(state.model_dump_json()) == state
