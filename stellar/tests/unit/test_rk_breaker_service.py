"""Breaker persistence and owner-only reset, the risk service (idempotency, events), intents."""

from datetime import timedelta
from decimal import Decimal

import pytest
from factories import T0, make_proposal
from risk_helpers import AS_OF, H, context, engine, market, policy
from stellar.journal import StellarJournal
from stellar.owner import CONFIRMATION_PHRASE, ResetOutcome, owner_reset_breaker
from stellar.risk import (
    BreakerLedger,
    BreakerStatus,
    BreakerTrip,
    IntentRefused,
    ProposalConflictError,
    ReevaluationRequired,
    RiskService,
)
from stellar.schemas.order import idempotency_key_for
from stellar.schemas.risk import RiskOutcome
from stellar.telemetry import EVENT_TYPES, new_event
from stellar.validation import order_intent_problems

pytestmark = pytest.mark.unit
STATION = "stellar-test"


def clock():
    return AS_OF


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def trip(at=T0):
    return BreakerTrip(cause="risk_rule", rule="max_daily_loss", value="0.031", limit="0.03",
                       tripped_by="risk_engine", tripped_at=at)


def reset_kwargs(**overrides):
    kwargs = {"station_id": STATION, "interactive": True,
              "typed_confirmation": CONFIRMATION_PHRASE, "reason": "Reviewed the loss",
              "clock": lambda: AS_OF + H}
    kwargs.update(overrides)
    return kwargs


# --- breaker ledger -------------------------------------------------------------------------


def test_breaker_starts_armed_and_trips_are_sticky(journal):
    ledger = BreakerLedger(journal, station_id=STATION, clock=clock)
    assert ledger.state().status is BreakerStatus.ARMED
    first = ledger.trip(trip())
    assert first.status is BreakerStatus.TRIPPED
    again = ledger.trip(trip(T0 + H))
    assert again.trip == first.trip
    assert len(journal.read(types=["circuit_breaker.tripped"])) == 1


def test_trip_survives_a_restart(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        BreakerLedger(j, station_id=STATION, clock=clock).trip(trip())
    with StellarJournal(path) as j:  # "restart": nothing re-arms it
        assert BreakerLedger(j, station_id=STATION).state().status is BreakerStatus.TRIPPED


@pytest.mark.parametrize("source,payload", [
    ("stellar.risk", {"by": "owner", "reason": "auto"}),
    ("stellar.system", {"by": "owner", "reason": "timer"}),
    ("stellar.owner", {"by": "supervisor", "reason": "x"}),
    ("stellar.owner", {"by": "owner", "reason": "   "}),
])
def test_resets_from_anything_but_the_owner_command_are_ignored(journal, source, payload):
    ledger = BreakerLedger(journal, station_id=STATION, clock=clock)
    ledger.trip(trip())
    journal.append(new_event("circuit_breaker.reset", station_id=STATION, source=source,
                             payload=payload, ts=AS_OF))
    assert ledger.state().status is BreakerStatus.TRIPPED
    assert ledger.ignored_resets() == 1


def test_ledger_and_risk_package_offer_no_reset_operation():
    import stellar.risk as risk

    names = {n for obj in (BreakerLedger, RiskService, risk.CircuitBreakerState)
             for n in dir(obj) if not n.startswith("_")}
    assert not {n for n in names if "reset" in n or "rearm" in n or "clear" in n} - \
        {"ignored_resets"}


# --- owner reset command ----------------------------------------------------------------------


def test_owner_reset_rearms_only_with_every_safeguard(journal):
    BreakerLedger(journal, station_id=STATION, clock=clock).trip(trip())
    assert owner_reset_breaker(journal, **reset_kwargs()) is ResetOutcome.RESET
    state = BreakerLedger(journal, station_id=STATION).state()
    assert state.status is BreakerStatus.ARMED
    assert state.last_reset.by == "owner" and state.last_reset.reason == "Reviewed the loss"


@pytest.mark.parametrize("overrides,outcome", [
    ({"interactive": False}, ResetOutcome.REFUSED_NOT_INTERACTIVE),
    ({"typed_confirmation": "yes"}, ResetOutcome.REFUSED_CONFIRMATION),
    ({"reason": "  "}, ResetOutcome.REFUSED_NO_REASON),
])
def test_owner_reset_refusals_are_journaled(journal, overrides, outcome):
    BreakerLedger(journal, station_id=STATION, clock=clock).trip(trip())
    assert owner_reset_breaker(journal, **reset_kwargs(**overrides)) is outcome
    assert BreakerLedger(journal, station_id=STATION).state().status is BreakerStatus.TRIPPED
    refused = journal.read(types=["circuit_breaker.reset_refused"])
    assert len(refused) == 1 and refused[0].payload["source"] == "owner_command"


def test_owner_reset_of_an_armed_breaker_is_refused(journal):
    assert owner_reset_breaker(journal, **reset_kwargs()) is ResetOutcome.REFUSED_NOT_TRIPPED
    assert journal.read(types=["circuit_breaker.reset"]) == []


def test_owner_cli_refuses_without_a_terminal(tmp_path, capsys):
    from stellar.owner.__main__ import main

    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        BreakerLedger(j, station_id=STATION, clock=clock).trip(trip())
    assert main(["reset-breaker", "--journal", str(path), "--station-id", STATION]) == 1
    assert "REFUSED_NOT_INTERACTIVE" in capsys.readouterr().out
    with StellarJournal(path) as j:
        assert BreakerLedger(j, station_id=STATION).state().status is BreakerStatus.TRIPPED


# --- risk service ---------------------------------------------------------------------------------


def service(journal, p=None):
    return RiskService(engine(p), journal, station_id=STATION, clock=clock)


def test_service_journals_canonical_events_with_reason_codes(journal):
    ev = service(journal).evaluate(context())
    types = [e.type for e in journal.read()]
    assert types[0] == "risk.check.started" and types[-1] == "risk.approved"
    assert types.count("risk.check.completed") == len(ev.results)
    assert set(types) <= EVENT_TYPES
    final = journal.read(types=["risk.approved"])[0]
    assert final.correlation_id == "prop_01" and final.agent_id == "risk_engine"
    assert final.payload["decision_id"] == ev.decision.decision_id
    assert final.payload["volume"] == "0.50"
    completed = journal.read(types=["risk.check.completed"])
    assert {e.payload["status"] for e in completed} >= {"PASS", "NOT_CONFIGURED"}


@pytest.mark.parametrize("ctx,event", [
    ({"execution": {"mode": "LIVE"}}, "risk.rejected"),
    ({"proposal": make_proposal(source_rating="Overweight", size_factor="0.5")},
     "risk.review.requested"),
])
def test_rejections_and_reviews_have_their_events(journal, ctx, event):
    ev = service(journal).evaluate(context(**ctx))
    final = journal.read(types=[event])
    assert len(final) == 1
    assert final[0].payload["reasons"] == [r.value for r in ev.decision.reasons]
    if event == "risk.rejected":
        assert final[0].payload["shadow_tracked"] is True


def test_service_takes_the_breaker_state_from_the_journal(journal):
    BreakerLedger(journal, station_id=STATION, clock=clock).trip(trip())
    ev = service(journal).evaluate(context())  # context claims ARMED
    assert ev.breaker_status is BreakerStatus.TRIPPED
    assert ev.decision.outcome is RiskOutcome.REJECTED


def test_systemic_breach_trips_the_breaker_but_a_rejection_does_not(journal):
    svc = service(journal)
    svc.evaluate(context(requested_volume="0.90"))  # plain rejection
    assert svc.breaker.state().status is BreakerStatus.ARMED
    daily = context().daily.model_dump() | {"realised_pnl": "-3000"}
    svc.evaluate(context(proposal=make_proposal(proposal_id="prop_02"), daily=daily))
    state = svc.breaker.state()
    assert state.status is BreakerStatus.TRIPPED and state.trip.rule == "max_daily_loss"
    later = svc.evaluate(context(proposal=make_proposal(proposal_id="prop_03")))
    assert later.decision.outcome is RiskOutcome.REJECTED


def test_identical_evaluation_is_idempotent(journal):
    svc = service(journal)
    first = svc.evaluate(context())
    count = len(journal.read())
    again = svc.evaluate(context())  # same proposal, context, policy and breaker
    assert again == first and again.fingerprint == first.fingerprint
    assert len(journal.read()) == count  # no duplicate events
    assert svc.evaluations_for("prop_01") == (first,)


def test_changed_context_is_a_new_evaluation_not_the_old_decision(journal):
    svc = service(journal)
    first = svc.evaluate(context())
    second = svc.evaluate(context(requested_volume="0.90", as_of=AS_OF + timedelta(minutes=1)))
    assert second.fingerprint != first.fingerprint
    assert second.decision.decision_id != first.decision.decision_id
    assert second.decision.outcome is RiskOutcome.REJECTED
    assert svc.evaluations_for("prop_01") == (first, second)
    assert svc.latest_evaluation("prop_01") == second


def test_fingerprint_covers_every_risk_input():
    eng = engine()
    base = eng.fingerprint(context())
    snap, wide_quote = market(bid="2399.70")
    changed = [
        context(as_of=AS_OF + timedelta(seconds=1)),
        context(breaker={"status": "TRIPPED", "updated_at": T0,
                         "trip": trip().model_dump()}),
        context(account={**context().account.model_dump(), "equity": "99000"}),
        context(daily={**context().daily.model_dump(), "realised_pnl": "-500"}),
        context(quote=wide_quote),
        context(metadata={**context().metadata.model_dump(), "lot_step": "0.10"}),
        context(execution={"mode": "LIVE"}),
    ]
    prints = {eng.fingerprint(c) for c in changed}
    assert base not in prints and len(prints) == len(changed)
    assert engine(policy(version="test_policy_2")).fingerprint(context()) != base
    assert eng.evaluate(context()).fingerprint == base


def test_same_proposal_id_with_different_content_is_refused(journal):
    svc = service(journal)
    svc.evaluate(context())
    count = len(journal.read())
    with pytest.raises(ProposalConflictError):
        svc.evaluate(context(proposal=make_proposal(stop_loss={"price": "2413.00",
                                                               "basis": "structure_high"})))
    assert len(journal.read()) == count


def test_prior_decisions_survive_a_restart(tmp_path):
    path = tmp_path / "journal.sqlite3"
    with StellarJournal(path) as j:
        first = service(j).evaluate(context())
        count = len(j.read())
    with StellarJournal(path) as j:
        assert service(j).evaluate(context()) == first
        assert len(j.read()) == count


def test_journaled_evaluation_replays_identically(journal):
    ev = service(journal).evaluate(context())
    stored = service(journal).latest_evaluation("prop_01")
    assert stored == ev
    assert engine(stored.policy).evaluate(stored.context) == ev


def test_replay_reproduces_the_evaluation_history(journal):
    svc = service(journal)
    svc.evaluate(context())
    svc.evaluate(context(daily={**context().daily.model_dump(), "realised_pnl": "-500"}))
    svc.evaluate(context(requested_volume="0.90"))
    history = svc.evaluations_for("prop_01")
    assert len(history) == 3 and len({h.fingerprint for h in history}) == 3
    finals = [e for e in journal.read() if e.type in {"risk.approved", "risk.rejected"}]
    assert [e.payload["fingerprint"] for e in finals] == [h.fingerprint for h in history]
    for stored in history:  # each entry is re-derived byte for byte from its own inputs
        assert engine(stored.policy).evaluate(stored.context) == stored


def test_evaluation_with_a_forged_fingerprint_is_invalid():
    data = engine().evaluate(context()).model_dump(mode="json")
    with pytest.raises(ValueError, match="fingerprint"):
        type(engine().evaluate(context())).model_validate({**data, "fingerprint": "0" * 64})


# --- order intents (current authorisation) --------------------------------------------------------


def intent_kwargs(**kw):
    kwargs = {"intent_id": "int_01", "broker_symbol": "XAUUSD", "created_at": AS_OF,
              "expires_at": AS_OF + timedelta(minutes=20)}
    kwargs.update(kw)
    return kwargs


def test_intent_only_from_an_approved_paper_evaluation(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    intent = svc.authorize_intent(approved, context(), **intent_kwargs(
        take_profit=Decimal("2376.00")))
    assert intent.volume == Decimal("0.50") and intent.max_slippage == Decimal("0.30")
    assert intent.decision_id == approved.decision.decision_id
    assert intent.idempotency_key == idempotency_key_for("prop_01")
    assert order_intent_problems(intent, approved.context.proposal, approved.decision) == []
    live = context(proposal=make_proposal(proposal_id="prop_10"), execution={"mode": "LIVE"})
    review = context(proposal=make_proposal(proposal_id="prop_11", source_rating="Overweight",
                                            size_factor="0.5"))
    for current in (live, review):  # REJECTED and REVIEW, both journaled and current
        with pytest.raises(IntentRefused):
            svc.authorize_intent(svc.evaluate(current), current, **intent_kwargs())


def test_intent_needs_a_configured_slippage_tolerance(journal):
    svc = service(journal, policy(max_slippage={"state": "DISABLED"}))
    ev = svc.evaluate(context())
    assert ev.decision.outcome is RiskOutcome.APPROVED
    with pytest.raises(IntentRefused, match="slippage"):
        svc.authorize_intent(ev, context(), **intent_kwargs())


def test_intent_cannot_carry_levels_other_than_the_proposal(journal):
    svc = service(journal)
    with pytest.raises(ValueError):
        svc.authorize_intent(svc.evaluate(context()), context(),
                             **intent_kwargs(take_profit=Decimal("2380.00")))


def test_no_public_intent_builder_bypasses_the_service():
    import stellar.risk as risk

    assert not any("intent" in n.lower() for n in risk.__all__
                   if n not in {"IntentRefused"})


def test_unjournaled_evaluation_cannot_authorise(journal):
    svc = service(journal)
    offline = engine().evaluate(context())  # never journaled
    with pytest.raises(ReevaluationRequired):
        svc.authorize_intent(offline, context(), **intent_kwargs())


def test_newly_tripped_breaker_blocks_an_old_approval(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    assert approved.decision.outcome is RiskOutcome.APPROVED
    svc.breaker.trip(trip())
    with pytest.raises(IntentRefused, match="TRIPPED"):
        svc.authorize_intent(approved, context(), **intent_kwargs())
    again = svc.evaluate(context())  # a new evaluation under the tripped breaker
    assert again.fingerprint != approved.fingerprint
    assert again.decision.outcome is RiskOutcome.REJECTED
    with pytest.raises(IntentRefused):
        svc.authorize_intent(again, context(), **intent_kwargs())
    with pytest.raises(IntentRefused):
        svc.authorize_intent(approved, context(), **intent_kwargs())


def test_changed_daily_pnl_requires_reevaluation(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    now = context(daily={**context().daily.model_dump(), "realised_pnl": "-500"})
    with pytest.raises(ReevaluationRequired):
        svc.authorize_intent(approved, now, **intent_kwargs())
    current = svc.evaluate(now)
    assert current.fingerprint != approved.fingerprint
    assert svc.authorize_intent(current, now, **intent_kwargs()).decision_id == \
        current.decision.decision_id
    with pytest.raises(ReevaluationRequired):  # the old approval stays superseded
        svc.authorize_intent(approved, context(), **intent_kwargs())


def test_changed_quote_spread_requires_reevaluation(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    _, wider = market(bid="2399.70")  # spread 0.40, still inside the test limit
    now = context(quote=wider)
    with pytest.raises(ReevaluationRequired):
        svc.authorize_intent(approved, now, **intent_kwargs())
    current = svc.evaluate(now)
    assert current.decision.outcome is RiskOutcome.APPROVED
    assert svc.authorize_intent(current, now, **intent_kwargs())


def test_changed_policy_requires_reevaluation(journal):
    approved = service(journal).evaluate(context())
    new_policy = policy(version="test_policy_2", max_spread={
        "state": "ENABLED", "limits": {"XAUUSD": "0.60"}})
    svc2 = service(journal, new_policy)
    with pytest.raises(ReevaluationRequired, match="policy"):
        svc2.authorize_intent(approved, context(), **intent_kwargs())
    current = svc2.evaluate(context())  # same proposal and context, new policy hash
    assert current.policy_hash != approved.policy_hash
    assert current.fingerprint != approved.fingerprint
    assert svc2.evaluations_for("prop_01") == (approved, current)
    assert svc2.authorize_intent(current, context(), **intent_kwargs())


def test_old_decision_remains_immutable_in_the_journal(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    snapshot = [(e.seq, e.type, e.payload) for e in journal.read()]
    svc.evaluate(context(daily={**context().daily.model_dump(), "realised_pnl": "-500"}))
    svc.breaker.trip(trip())
    svc.evaluate(context())
    after = [(e.seq, e.type, e.payload) for e in journal.read()]
    assert after[:len(snapshot)] == snapshot  # append-only: nothing earlier changed
    assert svc.evaluations_for("prop_01")[0] == approved
    assert journal.read(types=["risk.approved"])[0].payload["evaluation"] == \
        approved.model_dump(mode="json")


def test_returning_to_an_earlier_context_is_journaled_again(journal):
    svc = service(journal)
    first = svc.evaluate(context())
    svc.evaluate(context(requested_volume="0.90"))
    back = svc.evaluate(context())  # identical inputs to the first, but not the latest
    assert back == first and len(svc.evaluations_for("prop_01")) == 3
    assert svc.authorize_intent(back, context(), **intent_kwargs())


# --- execution-time confirmation (Phase 4, additive) -----------------------------------------------


def test_confirm_intent_accepts_only_the_current_authorised_intent(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    intent = svc.authorize_intent(approved, context(), **intent_kwargs())
    assert svc.confirm_intent(intent, context()) == approved
    tampered = intent.model_copy(update={"volume": Decimal("0.40")})
    with pytest.raises(IntentRefused):
        svc.confirm_intent(tampered, context())
    later = context(daily={**context().daily.model_dump(), "realised_pnl": "-500"})
    with pytest.raises(ReevaluationRequired):
        svc.confirm_intent(intent, later)
    svc.evaluate(later)  # supersedes the approval the intent came from
    with pytest.raises(ReevaluationRequired):
        svc.confirm_intent(intent, context())


def test_confirm_intent_refuses_under_a_tripped_breaker(journal):
    svc = service(journal)
    approved = svc.evaluate(context())
    intent = svc.authorize_intent(approved, context(), **intent_kwargs())
    svc.breaker.trip(trip())
    with pytest.raises(IntentRefused, match="TRIPPED"):
        svc.confirm_intent(intent, context())
