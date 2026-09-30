"""Phase 6b trader desk: setup → U4 Trader selection → Trade Proposal, on synthetic evidence
with a deterministic scripted Trader. Nothing here is a real market fact or a real model.
"""

import json

import pytest
from pydantic import ValidationError
from research_helpers import AS_OF, STATION
from stellar.journal import StellarJournal
from stellar.pipeline.records import StepStatus
from stellar.proposals import ApprovalSource, ProposalFailure, SelectionSource
from stellar.reasoning import FailureKind, ProviderFailure, ScriptedProvider, Stance
from stellar.schemas.proposal import Rating
from stellar.setups import OptionKind, SetupDirection, SetupInputError, SetupState, SetupStatus
from stellar.trader import (
    DeskFailure,
    OutcomeKind,
    TraderConfig,
    TraderDesk,
    TraderInputs,
    TraderSelectionOutput,
)
from trader_helpers import (
    LONG_CLOSES,
    MARKET_ONLY,
    RANGE_CLOSES,
    SETUP_CONFIG,
    SINGLE_CLOSES,
    TRADER_CONFIG,
    H,
    TraderScript,
    approve_for,
    decision_support,
    decision_variant,
    market,
    owner_selection,
    reviewed,
    technical,
    trader_provider,
)

pytestmark = pytest.mark.unit

LONG_MARKET = market(LONG_CLOSES, bid="122.0", ask="122.2")
CRITICAL = ("risk.", "order.", "circuit_breaker.", "account.", "position.")


@pytest.fixture(scope="module")
def evidence():
    with StellarJournal() as j:
        analysis = technical(LONG_CLOSES)
        return analysis, decision_support(j, analysis)


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def desk(journal, *, script=None, provider=None, config=SETUP_CONFIG, trader=TRADER_CONFIG):
    provider = provider or trader_provider(script)
    return TraderDesk(journal=journal, setup_config=config, trader_config=trader,
                      provider=provider, station_id=STATION, clock=lambda: AS_OF), provider


_OWN = object()


def inputs(evidence, *, approval=_OWN, as_of=AS_OF, mkt=LONG_MARKET, **kw):
    analysis, decision = evidence
    decision = kw.pop("decision", decision)
    if approval is _OWN:
        approval = approve_for(analysis, decision)
    return TraderInputs(technical=analysis, decision=decision, market=mkt, as_of=as_of,
                        approval=approval, **kw)


def types(journal):
    return [e.type for e in journal.read()]


# --------------------------------------------------------------------- happy path --


def test_clean_long_through_the_trader_builds_one_proposal(journal, evidence):
    d, provider = desk(journal)
    out = d.run(inputs(evidence))
    assert out.kind is OutcomeKind.TRADE_PROPOSAL and out.failure is None
    assert out.setup.status is SetupStatus.READY_FOR_PROPOSAL
    assert out.selection.source is SelectionSource.TRADER
    assert out.trader_step.status is StepStatus.COMPLETED
    p = out.proposal
    assert p.direction.value == "LONG" and p.entry.price == LONG_MARKET.latest_quote.ask
    assert len(p.take_profits) == 2  # the Trader explicitly selected both targets (RK-9)
    assert out.lifecycle.state is SetupState.PROPOSED
    seen = types(journal)
    assert seen.count("trade.proposed") == 1 and seen.count("decision.trader_plan.created") == 1
    assert [e.payload["to"] for e in journal.read(types=["setup.state.changed"])] == [
        "ARMED", "PROPOSED"]
    proposed = journal.read(types=["trade.proposed"])[0]
    assert {"proposal_id", "setup_id", "instrument", "direction"} <= set(proposed.payload)
    assert proposed.payload["proposal_id"] == p.proposal_id
    assert not [t for t in seen if t.startswith(CRITICAL)]  # no risk, order or breaker event
    assert len(provider.requests) == 1


def test_trader_sees_options_but_its_task_offers_no_way_to_state_a_price(journal, evidence):
    d, provider = desk(journal)
    d.run(inputs(evidence))
    request = provider.requests[0]
    task = json.loads(request.task)
    assert {o["kind"] for o in task["options"]} == {k.value for k in OptionKind} - {"ATR_STOP"}
    assert "trader_selection" in request.system and "cannot create" in request.system
    assert request.untrusted == ()


def test_same_inputs_are_idempotent(journal, evidence):
    d, provider = desk(journal)
    first = d.run(inputs(evidence))
    before = len(journal.read())
    second = d.run(inputs(evidence))
    assert second.kind is OutcomeKind.TRADE_PROPOSAL and second.proposal == first.proposal
    assert len(journal.read()) == before  # nothing journaled twice
    assert len(provider.requests) == 1  # the Trader was not asked again


def test_checkpointed_trader_answer_is_reused_without_a_call(evidence):
    with StellarJournal() as j:
        d, provider = desk(j)
        d.run(inputs(evidence, approval=None))  # selection made, then APPROVAL_REQUIRED
        again = d.run(inputs(evidence))
    assert again.kind is OutcomeKind.TRADE_PROPOSAL
    assert again.trader_step.status is StepStatus.REUSED and len(provider.requests) == 1


def test_changed_evidence_after_a_proposal_gets_no_second_proposal(journal, evidence):
    d, _ = desk(journal)
    d.run(inputs(evidence))
    _, decision = evidence
    out = d.run(inputs(evidence, decision=decision_variant(decision, outputs_hash="5" * 64)))
    assert out.kind is OutcomeKind.SETUP_CANDIDATE
    assert out.failure is DeskFailure.SETUP_ALREADY_PROPOSED
    assert types(journal).count("trade.proposed") == 1


# ------------------------------------------------------------ deterministic modes --


def test_single_option_setup_needs_no_llm(journal, evidence):
    _, decision = evidence
    analysis = technical(SINGLE_CLOSES)
    d, provider = desk(journal, config=MARKET_ONLY, trader=TraderConfig())
    decision = reviewed(decision, analysis)
    out = d.run(TraderInputs(technical=analysis, decision=decision,
                             market=market(SINGLE_CLOSES, bid="120.8", ask="121.0"),
                             as_of=AS_OF,
                             approval=approve_for(analysis, decision, config=MARKET_ONLY)))
    assert out.kind is OutcomeKind.TRADE_PROPOSAL
    assert out.selection.source is SelectionSource.SINGLE_OPTION and provider.requests == []


def test_several_options_without_a_trader_require_a_selection(journal, evidence):
    d, provider = desk(journal, trader=TraderConfig())
    out = d.run(inputs(evidence))
    assert out.kind is OutcomeKind.SETUP_CANDIDATE
    assert out.failure is DeskFailure.SELECTION_REQUIRED and out.proposal is None
    assert provider.requests == [] and "trade.proposed" not in types(journal)


def test_owner_selection_wins_and_skips_the_trader(journal, evidence):
    d, provider = desk(journal)
    probe, _ = desk(StellarJournal(), trader=TraderConfig())
    setup = probe.run(inputs(evidence)).setup
    sel = owner_selection(setup, entry=OptionKind.LIMIT_AT_ZONE)
    out = d.run(inputs(evidence, owner_selection=sel))
    assert out.kind is OutcomeKind.TRADE_PROPOSAL and out.selection == sel
    assert out.proposal.entry.zone_low is not None and provider.requests == []
    with pytest.raises(ValueError):
        inputs(evidence, owner_selection=sel.model_copy(
            update={"source": SelectionSource.TRADER}))


# ----------------------------------------------------------- no setup / no approval --


def test_no_setup_calls_no_model_and_proposes_nothing(journal, evidence):
    _, decision = evidence
    analysis = technical(RANGE_CLOSES)
    d, provider = desk(journal)
    out = d.run(TraderInputs(technical=analysis, decision=reviewed(decision, analysis),
                             market=LONG_MARKET, as_of=AS_OF,
                             approval=approve_for(*evidence)))
    assert out.kind is OutcomeKind.NO_SETUP and out.setup.status is SetupStatus.NO_SETUP
    assert provider.requests == [] and "trade.proposed" not in types(journal)
    assert types(journal) == ["setup.state.changed"]


def test_conflicting_research_is_no_setup(journal, evidence):
    _, decision = evidence
    d, provider = desk(journal)
    out = d.run(inputs(evidence, decision=decision_variant(decision,
                                                           final_stance=Stance.MIXED)))
    assert out.kind is OutcomeKind.NO_SETUP
    assert out.setup.status is SetupStatus.CONFLICTING_EVIDENCE and provider.requests == []


@pytest.mark.parametrize("rating", [Rating.HOLD, Rating.REVIEW, Rating.SELL])
def test_hold_review_sell_give_no_proposal(journal, evidence, rating):
    d, _ = desk(journal)
    out = d.run(inputs(evidence, approval=approve_for(
        *evidence, rating=rating, source=ApprovalSource.PORTFOLIO_MANAGER)))
    assert out.kind is OutcomeKind.SETUP_CANDIDATE and out.proposal is None
    assert out.proposal_outcome.failure is ProposalFailure.RATING_DOES_NOT_APPROVE
    assert "trade.proposed" not in types(journal)


def test_expired_setup_goes_to_no_setup(journal, evidence):
    d, _ = desk(journal)
    ready = d.run(inputs(evidence, approval=None)).setup
    out = d.run(inputs(evidence, as_of=ready.valid_until,
                       mkt=market(LONG_CLOSES, bid="122.0", ask="122.2", end=AS_OF)))
    assert out.kind is OutcomeKind.NO_SETUP and out.setup.status is SetupStatus.EXPIRED
    assert out.lifecycle.state is SetupState.EXPIRED


# ------------------------------------------------------------ untrusted LLM output --


def _reply(**change):
    def script(request):
        task = json.loads(request.task)
        base = json.loads(TraderScript()(request))
        base.update({k: (v(task) if callable(v) else v) for k, v in change.items()})
        return json.dumps(base)
    return script


@pytest.mark.parametrize("change, detail", [
    ({"entry_price": "121.5"}, "schema_mismatch"),                    # invents a price field
    ({"stop_option_id": "opt_ffffffffffffffff"}, "unknown_evidence_id"),  # invents an option
    ({"evidence_ids": ["clm_invented"]}, "unknown_evidence_id"),      # invents evidence
    ({"direction": "BUY"}, "schema_mismatch"),                         # loose action word
    ({"direction": "SHORT"}, "direction_mismatch"),                    # typed, but wrong side
    ({"setup_id": "setup_other"}, "wrong_setup"),
    ({"stop_option_id": lambda t: next(o["option_id"] for o in t["options"]
                                       if o["role"] == "TARGET")}, "option_role_mismatch"),
])
def test_untrusted_trader_output_is_rejected(journal, evidence, change, detail):
    d, _ = desk(journal, provider=ScriptedProvider(_reply(**change)))
    out = d.run(inputs(evidence))
    assert out.kind is OutcomeKind.SETUP_CANDIDATE and out.proposal is None
    assert out.failure is DeskFailure.TRADER_FAILED and out.detail == detail
    assert out.trader_step.failure is FailureKind.MALFORMED_OUTPUT
    assert "trade.proposed" not in types(journal)
    assert "agent.task.failed" in types(journal)


def test_free_text_buy_or_sell_is_rejected(journal, evidence):
    script = TraderScript(overrides=["FINAL TRANSACTION PROPOSAL: **BUY** at 121.5, stop 109"])
    d, _ = desk(journal, script=script)
    out = d.run(inputs(evidence))
    assert out.failure is DeskFailure.TRADER_FAILED and out.detail == "not_json"
    assert out.proposal is None


def test_typed_long_direction_is_accepted(journal, evidence):
    d, _ = desk(journal, script=TraderScript(direction="LONG"))
    assert d.run(inputs(evidence)).kind is OutcomeKind.TRADE_PROPOSAL


def test_trader_decline_is_a_candidate_without_proposal(journal, evidence):
    d, _ = desk(journal, script=TraderScript(decision="DECLINE"))
    out = d.run(inputs(evidence))
    assert out.kind is OutcomeKind.SETUP_CANDIDATE and out.failure is DeskFailure.TRADER_DECLINED
    assert out.trader_output.decision.value == "DECLINE"


def test_provider_failure_is_typed(journal, evidence):
    script = TraderScript(overrides=[ProviderFailure(FailureKind.TIMEOUT)])
    d, _ = desk(journal, script=script)
    out = d.run(inputs(evidence))
    assert out.failure is DeskFailure.TRADER_FAILED
    assert out.trader_step.failure is FailureKind.TIMEOUT


def test_selection_schema_has_no_numeric_field_and_rejects_numbers():
    with pytest.raises(ValidationError):
        TraderSelectionOutput.model_validate({
            "setup_id": "setup_x", "direction": "LONG", "decision": "SELECT",
            "entry_option_id": "opt_0000000000000000", "stop_option_id": "opt_0000000000000001",
            "target_option_ids": ["opt_0000000000000002"], "rationale": "r",
            "stop_loss": "109"})
    with pytest.raises(ValidationError):  # SELECT without a target
        TraderSelectionOutput(setup_id="setup_x", direction=SetupDirection.LONG,
                              decision="SELECT", entry_option_id="opt_0000000000000000",
                              stop_option_id="opt_0000000000000001", rationale="r")


def test_enabled_trader_needs_budget_model_and_provider(journal):
    with pytest.raises(ValidationError):
        TraderConfig(llm_enabled=True)
    with pytest.raises(ValueError):
        TraderDesk(journal=journal, setup_config=SETUP_CONFIG, trader_config=TRADER_CONFIG,
                   provider=None, station_id=STATION)


# ------------------------------------------------------------------- point in time --


def test_future_research_is_refused_before_anything_is_journaled(journal, evidence):
    _, decision = evidence
    d, provider = desk(journal)
    with pytest.raises(SetupInputError):
        d.run(inputs(evidence, decision=decision_variant(decision, as_of=AS_OF + H)))
    assert journal.read() == [] and provider.requests == []


def test_a_crash_after_trade_proposed_does_not_propose_twice(journal, evidence, monkeypatch):
    d, _ = desk(journal)

    def crash(*a, **k):
        raise RuntimeError("simulated crash before the lifecycle event")

    monkeypatch.setattr(d.book, "mark_proposed", crash)
    with pytest.raises(RuntimeError):
        d.run(inputs(evidence))
    monkeypatch.undo()
    again = d.run(inputs(evidence))
    assert again.kind is OutcomeKind.TRADE_PROPOSAL
    assert again.lifecycle.state is SetupState.PROPOSED
    assert types(journal).count("trade.proposed") == 1

