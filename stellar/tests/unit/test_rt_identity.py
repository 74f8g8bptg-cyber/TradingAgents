"""Phase 7 run identity, approval-source independence and the run checkpoint event, on
synthetic labelled fixtures. Nothing here is a real market fact or a real approval."""

import pytest
from research_helpers import AS_OF
from risk_helpers import TEST_POLICY
from runtime_helpers import (
    Clock,
    M,
    Script,
    approved,
    operator,
    quote,
    request,
    run_types,
    runtime,
    source,
)
from stellar.journal import StellarJournal
from stellar.proposals import Approval, ApprovalSource
from stellar.reasoning import ScriptedProvider, Stance
from stellar.risk import RiskPolicy
from stellar.runtime import (
    FutureRunError,
    RunStage,
    RunState,
    RuntimeFailure,
    StageCheckpoint,
    reconcile,
)
from stellar.schemas.common import SCHEMA_VERSION, Direction
from stellar.schemas.proposal import Rating
from stellar.telemetry.catalogue import REQUIRED_PAYLOAD_KEYS
from trader_helpers import LONG_CLOSES, SHORT_CLOSES

pytestmark = pytest.mark.unit


class Crash(Exception):
    pass


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


# ------------------------------------------------------------- approval source --


@pytest.mark.parametrize("source_", list(ApprovalSource))
def test_any_approval_producer_resumes_the_same_run(journal, source_):
    """The runtime consumes a typed Approval; it does not care who produced it."""
    rt = runtime(journal)
    parked = rt.run(request())
    assert parked.state is RunState.AWAITING_APPROVAL
    approval = approved(rt, parked, source=source_)
    approval = approval.model_copy(update={"reference": f"{source_.value}_decision_1"})
    resumed = rt.run(request(approval=approval))
    assert resumed.run_id == parked.run_id  # the same run, not a new one
    assert resumed.state is RunState.POSITION_OPEN
    kinds = run_types(journal, parked.run_id)
    assert kinds.count("run.started") == 1 and kinds.count("run.resumed") == 1
    journaled = journal.read(types=["decision.final.created"])[0]
    assert journaled.run_id == parked.run_id
    assert journaled.payload["source"] == source_.value
    assert journaled.payload["approval"]["reference"] == f"{source_.value}_decision_1"
    assert journaled.payload["setup_id"] == approval.setup_id


def test_without_an_approval_the_run_parks_and_does_nothing_more(journal):
    rt = runtime(journal)
    parked = rt.run(request())
    before = journal.last_seq()
    assert rt.run(request()) == parked and journal.last_seq() == before
    assert journal.read(types=["trade.proposed"]) == []


@pytest.mark.parametrize("change, detail", [
    ({"setup_id": "setup_0000000000000000000000000000000000000000"}, "approval_for_other_setup"),
    ({"direction": Direction.SHORT}, "approval_direction_mismatch"),
    ({"rating": Rating.SELL}, "rating_does_not_approve"),
    ({"rating": Rating.HOLD}, "rating_does_not_approve"),
    ({"rating": Rating.OVERWEIGHT}, "overweight_d9_unresolved"),
])
def test_a_wrong_approval_gives_no_proposal_and_no_execution(journal, change, detail):
    rt = runtime(journal)
    parked = rt.run(request())
    wrong = Approval.model_validate({**approved(rt, parked).model_dump(), **change})
    record = rt.run(request(approval=wrong))
    assert record.run_id == parked.run_id
    assert record.state is RunState.SETUP_CANDIDATE
    assert record.failure is RuntimeFailure.PROPOSAL_FAILED and record.detail == detail
    for kind in ("trade.proposed", "risk.check.started", "order.created"):
        assert journal.read(types=[kind]) == [], kind


# -------------------------------------------------------------- market identity --


def test_changed_market_data_identity_is_a_different_run(journal):
    base = runtime(journal).run(request())
    moved_quote = runtime(journal, market=source(quotes=(("122.1", "122.3", AS_OF),)))
    other_bars = runtime(journal, market=source(closes=LONG_CLOSES[:-1] + [122.5]))
    ids = {base.run_id, moved_quote.run(request()).run_id, other_bars.run(request()).run_id}
    assert len(ids) == 3


# ---------------------------------------- an approval is never execution authority --


def test_a_policy_change_after_approval_is_evaluated_afresh(journal):
    rt = runtime(journal)
    approval = approved(rt, rt.run(request()))
    stricter = RiskPolicy.model_validate({**TEST_POLICY.model_dump(),
                                          "max_spread": {"state": "UNSET"}})
    record = runtime(journal, policy=stricter).run(request(approval=approval))
    assert record.state is RunState.REVIEW_REQUIRED  # the same approval, a fresh evaluation
    assert journal.read(types=["order.created"]) == []


@pytest.mark.parametrize("later", [False, True])
def test_a_market_change_after_authorisation_never_executes_the_old_intent(journal, later):
    """A run authorises, then crashes before submitting. The market view changes (a new quote
    at the same moment, or a later moment): that is a new run. Phase 6b gives the setup no
    second proposal, and the old run, resumed, is superseded: its approval and intent never
    execute. Nothing trades until a new setup is proposed and evaluated under current inputs."""
    rt = runtime(journal)
    approval = approved(rt, rt.run(request()))
    first = runtime(journal)

    def crash(done):
        if done is RunStage.ORDER_AUTHORISATION:
            raise Crash(done)

    first._stage_done = crash
    with pytest.raises(Crash):
        first.run(request(approval=approval))
    old_run = first.ledger.run_ids()[0]
    at = AS_OF + M if later else AS_OF
    quotes = (("122.0", "122.2", AS_OF), ("122.1", "122.3", at)) if later else \
        (("122.1", "122.3", AS_OF),)
    moved = runtime(journal, market=source(quotes=quotes), clock=Clock(at))
    fresh = moved.run(request(approval=approval, as_of=at, op=operator(at)))
    assert fresh.run_id != old_run
    assert fresh.state is RunState.SETUP_CANDIDATE and "setup_already_proposed" in fresh.detail
    stale = runtime(journal, clock=Clock(at)).run(request(approval=approval))  # old data
    assert stale.run_id == old_run and stale.state is RunState.BLOCKED
    assert stale.failure is RuntimeFailure.STALE_CONTEXT
    assert stale.detail == f"superseded_by_{fresh.run_id}"
    assert journal.read(types=["order.created"]) == []


def test_an_unfinished_run_never_submits_after_the_paper_book_moved_on(journal):
    """Run B (a SHORT setup) authorises and crashes. The paper book then moves on: another
    setup's position opens and closes later. Resuming B cannot submit into that book."""
    down = {"specialist": Stance.SUPPORTS_DOWNSIDE, "research_manager": Stance.SUPPORTS_DOWNSIDE}
    short_market = source(SHORT_CLOSES, (("127.8", "128.0", AS_OF),))

    def short_rt(**kw):
        return runtime(journal, market=short_market,
                       provider=ScriptedProvider(Script(stances=down)), **kw)

    b_approval = approved(short_rt(), short_rt().run(request()))
    b = short_rt()

    def crash(done):
        if done is RunStage.ORDER_AUTHORISATION:
            raise Crash(done)

    b._stage_done = crash
    with pytest.raises(Crash):
        b.run(request(approval=b_approval))
    clock = Clock()
    a = runtime(journal, clock=clock)
    a_record = a.run(request(approval=approved(a, a.run(request()))))
    assert a_record.state is RunState.POSITION_OPEN
    clock.now = AS_OF + 10 * M
    a.close(a_record.run_id, quote("123.0", "123.2", AS_OF + 10 * M), as_of=AS_OF + 10 * M)
    resumed = short_rt(clock=clock).run(request(approval=b_approval))
    assert resumed.state is RunState.BLOCKED and resumed.failure is RuntimeFailure.STALE_CONTEXT
    assert resumed.detail == "paper_book_moved_past_as_of"
    assert len(journal.read(types=["order.created"])) == 1  # only A's


def test_a_run_for_a_future_moment_is_refused(journal):
    with pytest.raises(FutureRunError):
        runtime(journal).run(request(as_of=AS_OF + M, op=operator(AS_OF + M)))
    assert journal.read(types=["run.started"]) == []


def test_an_account_change_after_approval_blocks_the_old_evaluation(journal):
    """See test_rt_recovery.test_stale_risk_evaluation_is_never_authorised: another run
    changes the book after RISK; the resumed run ends BLOCKED / STALE_CONTEXT."""
    rt = runtime(journal)
    approval = approved(rt, rt.run(request()))
    first = runtime(journal)

    def crash(done):
        if done is RunStage.RISK:
            raise Crash(done)

    first._stage_done = crash
    with pytest.raises(Crash):
        first.run(request(approval=approval))
    runtime(journal).run(request(approval=approval, op=operator(volume="0.40")))
    resumed = runtime(journal).run(request(approval=approval))
    assert resumed.state is RunState.BLOCKED and resumed.failure is RuntimeFailure.STALE_CONTEXT


# ------------------------------------------------------------ run.stage.completed --


def test_stage_checkpoint_event_is_self_describing_and_versioned(journal):
    rt = runtime(journal)
    record = rt.run(request(approval=approved(rt, rt.run(request()))))
    events = journal.read(types=["run.stage.completed"], run_id=record.run_id)
    assert {e.payload["stage"] for e in events} == {s.value for s in RunStage}
    for e in events:
        assert e.schema_version == SCHEMA_VERSION and e.correlation_id == record.run_id
        assert REQUIRED_PAYLOAD_KEYS["run.stage.completed"] <= set(e.payload)
        assert len(e.payload["fingerprint"]) == 64 and e.source == "stellar.runtime"
    by_stage = {e.payload["stage"]: e.payload for e in events}
    assert by_stage["RISK"]["refs"]["risk_fingerprint"]
    assert by_stage["PROPOSAL"]["refs"]["proposal_id"] == record.refs["proposal_id"]
    assert by_stage["ORDER_AUTHORISATION"]["refs"]["intent_id"] == record.refs["intent_id"]


def test_a_checkpoint_copy_that_disagrees_with_the_domain_record_is_reported(journal):
    rt = runtime(journal)
    record = rt.run(request(approval=approved(rt, rt.run(request()))))
    cp = rt.ledger.checkpoints(record.run_id)[RunStage.PROPOSAL]
    forged = dict(cp.outputs["proposal"], valid_until="2099-01-01T00:00:00Z")
    rt.ledger.checkpoint(StageCheckpoint(
        run_id=record.run_id, stage=RunStage.PROPOSAL, fingerprint=cp.fingerprint,
        state=cp.state, refs=cp.refs, outputs={"proposal": forged}), instrument="XAUUSD")
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    assert ("checkpoint_mismatch", record.run_id) in {(i.code, i.ref) for i in report.issues}
