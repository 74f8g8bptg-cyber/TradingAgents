"""Phase 7 restart / crash recovery, stale context, pending re-authorisation, breaker and
replay, on synthetic labelled fixtures. Nothing here is a real market fact."""

import pytest
from research_helpers import AS_OF
from runtime_helpers import (
    POINT_ZONES,
    Clock,
    M,
    Script,
    approved,
    m5,
    operator,
    quote,
    request,
    run_to_proposal,
    run_types,
    runtime,
    source,
)
from stellar.journal import StellarJournal
from stellar.reasoning import ScriptedProvider
from stellar.runtime import (
    HealthStatus,
    RunNotActive,
    RunStage,
    RunState,
    RuntimeFailure,
    StageCheckpoint,
    health,
    reconcile,
)
from trader_helpers import TraderScript

pytestmark = pytest.mark.unit

SIDE_EFFECTS = ("snapshot.created", "analysis.created", "research.snapshot.created",
                "debate.started", "debate.turn.completed", "debate.completed",
                "agent.llm_call.started", "decision.research_plan.created", "trade.proposed",
                "decision.final.created", "risk.check.started", "risk.approved", "order.created",
                "order.filled", "position.opened", "account.snapshot.created")


class Crash(Exception):
    pass


def counts(journal) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in journal.read():
        if e.type in SIDE_EFFECTS:
            out[e.type] = out.get(e.type, 0) + 1
    return out


@pytest.fixture(scope="module")
def reference():
    """An uninterrupted run with the approval supplied up front."""
    with StellarJournal() as j:
        rt = runtime(j)
        approval = approved(rt, rt.run(request()))
    with StellarJournal() as j:
        provider = ScriptedProvider(Script())
        rt = runtime(j, provider=provider)
        final = rt.run(request(approval=approval))
        return approval, final, counts(j), len(provider.requests)


# ------------------------------------------------------------ crash after a stage --


@pytest.mark.parametrize("stage", list(RunStage))
def test_restart_after_each_stage_resumes_to_the_same_state(reference, stage):
    approval, final, expected_counts, expected_calls = reference
    with StellarJournal() as j:
        provider = ScriptedProvider(Script())
        first = runtime(j, provider=provider)

        def crash(done):
            if done is stage:
                raise Crash(done)

        first._stage_done = crash
        with pytest.raises(Crash):
            first.run(request(approval=approval))
        restarted = runtime(j, provider=provider)  # new objects; the journal is all that is kept
        record = restarted.run(request(approval=approval))
        assert record.state is RunState.POSITION_OPEN
        assert record.refs == final.refs and record.run_id == final.run_id
        assert counts(j) == expected_counts  # no duplicate report, call, proposal, order, fill
        assert len(provider.requests) == expected_calls  # no LLM question asked twice
        if stage is not RunStage.PAPER_SUBMISSION:
            assert run_types(j, record.run_id).count("run.resumed") == 1
        assert reconcile(j, account_id="paper_test", ledger=restarted.ledger).ok


@pytest.mark.parametrize("stage", [RunStage.MARKET_DATA, RunStage.TECHNICAL, RunStage.RESEARCH,
                                   RunStage.RISK, RunStage.ORDER_AUTHORISATION,
                                   RunStage.PAPER_SUBMISSION])
def test_crash_between_side_effect_and_checkpoint_duplicates_nothing(reference, stage):
    """The stage's work is journaled, its checkpoint is not: the components' own
    idempotency (and report de-duplication here) keeps every side effect single."""
    approval, final, expected_counts, expected_calls = reference
    with StellarJournal() as j:
        provider = ScriptedProvider(Script())
        first = runtime(j, provider=provider)
        original = first.ledger.checkpoint

        def failing(cp, **kw):
            if cp.stage is stage:
                raise Crash(stage)
            return original(cp, **kw)

        first.ledger.checkpoint = failing
        with pytest.raises(Crash):
            first.run(request(approval=approval))
        record = runtime(j, provider=provider).run(request(approval=approval))
        assert record.state is RunState.POSITION_OPEN and record.refs == final.refs
        assert counts(j) == expected_counts
        assert len(provider.requests) == expected_calls


def test_restart_after_the_position_closed_is_stable():
    with StellarJournal() as j:
        rt = runtime(j)
        record = run_to_proposal(rt)
        rt.close(record.run_id, quote("123.0", "123.2", AS_OF + 5 * M), as_of=AS_OF + 5 * M)
        before = j.last_seq()
        again = runtime(j)
        assert again.status(record.run_id).state is RunState.COMPLETED
        assert again.run(request(approval=approved(again, record))).state is RunState.COMPLETED
        with pytest.raises(RunNotActive):
            again.close(record.run_id, quote("123.0", "123.2", AS_OF + 6 * M),
                        as_of=AS_OF + 6 * M)
        assert j.last_seq() == before and len(again.broker.trades()) == 1


def test_file_journal_replay_rebuilds_the_same_state(tmp_path):
    path = tmp_path / "stellar.db"
    with StellarJournal(path) as j:
        rt = runtime(j)
        record = run_to_proposal(rt)
        rt.advance(record.run_id, m5("124", "126.9", "123.8", "126.6", start=AS_OF, side="bid"),
                   as_of=AS_OF + 10 * M)
        live, events = rt.status(record.run_id), [(e.seq, e.type) for e in j.read()]
        balance = rt.broker.state().balance
    with StellarJournal(path) as j:  # a new process: only the file remains
        rt = runtime(j)
        assert rt.status(record.run_id) == live
        assert [(e.seq, e.type) for e in j.read()] == events
        assert rt.broker.state().balance == balance
        assert j.verify() == len(events)
        assert reconcile(j, account_id="paper_test", ledger=rt.ledger).ok


def test_a_conflicting_checkpoint_fails_closed(reference):
    approval = reference[0]
    with StellarJournal() as j:
        first = runtime(j)

        def crash(done):
            if done is RunStage.TECHNICAL:
                raise Crash(done)

        first._stage_done = crash
        with pytest.raises(Crash):
            first.run(request(approval=approval))
        run_id = first.ledger.run_ids()[0]
        # a checkpoint written under another technical engine / config for the same run
        first.ledger.checkpoint(StageCheckpoint(
            run_id=run_id, stage=RunStage.TECHNICAL, fingerprint="f" * 64,
            state=RunState.TECHNICAL_COMPLETE), instrument="XAUUSD")
        record = runtime(j).run(request(approval=approval))
        assert record.state is RunState.FAILED
        assert record.failure is RuntimeFailure.CHECKPOINT_CONFLICT
        assert j.read(types=["trade.proposed"]) == []


# ------------------------------------------------------------------ stale context --


def test_stale_risk_evaluation_is_never_authorised(reference):
    approval = reference[0]
    with StellarJournal() as j:
        first = runtime(j)

        def crash(done):
            if done is RunStage.RISK:
                raise Crash(done)

        first._stage_done = crash
        with pytest.raises(Crash):
            first.run(request(approval=approval))
        # meanwhile another run re-evaluates the same proposal and trades it
        other = runtime(j).run(request(approval=approval, op=operator(volume="0.40")))
        assert other.state is RunState.POSITION_OPEN
        resumed = runtime(j).run(request(approval=approval))
        assert resumed.state is RunState.BLOCKED
        assert resumed.failure is RuntimeFailure.STALE_CONTEXT
        assert len(j.read(types=["order.created"])) == 1  # one proposal, one order


def test_duplicate_submission_is_prevented_across_runs(reference):
    approval = reference[0]
    with StellarJournal() as j:
        rt = runtime(j)
        a = rt.run(request(approval=approval))
        b = rt.run(request(approval=approval, op=operator(volume="0.40")))
        assert a.state is RunState.POSITION_OPEN
        assert b.state in (RunState.REJECTED, RunState.BLOCKED)  # duplicate_order refusal
        assert len(j.read(types=["order.filled"])) == 1


# ------------------------------------------------------- pending / BLOCKED lifecycle --

LIMIT = Script(trader=TraderScript(entry="LIMIT_AT_ZONE", targets=("PRIOR_SWING_TARGET",)))
QUOTES = (("122.0", "122.2", AS_OF), ("115.3", "115.5", AS_OF + 25 * M))


def limit_runtime(journal, **kw):
    return runtime(journal, market=source(quotes=QUOTES), technical_config=POINT_ZONES,
                   provider=ScriptedProvider(LIMIT), **kw)


def test_pending_order_blocks_without_current_authorisation_then_fills_after_reauth():
    with StellarJournal() as j:
        clock = Clock()
        rt = limit_runtime(j, clock=clock)
        record = run_to_proposal(rt)
        assert record.state is RunState.PAPER_SUBMITTED
        order = rt.order(record.refs["order_id"])
        assert order.intent.order_type.value == "limit" and str(order.intent.price) == "115.5"
        # the limit is reached, but the submission authorisation is no longer current
        clock.now = AS_OF + 10 * M
        blocked = rt.advance(record.run_id, m5("116", "116.2", "115.4", "115.8", start=AS_OF),
                             as_of=AS_OF + 10 * M)
        assert blocked.state is RunState.ORDER_BLOCKED and not blocked.terminal
        assert blocked.failure is None and blocked.detail  # BLOCKED is not FAILED
        assert j.read(types=["order.filled"]) == []
        # a restart does not unblock it by itself
        assert runtime(j, market=source(quotes=QUOTES), technical_config=POINT_ZONES,
                       provider=ScriptedProvider(LIMIT), clock=clock).status(
            record.run_id).state is RunState.ORDER_BLOCKED
        # a fresh Phase 3 evaluation and authorisation at the new moment lets it fill
        clock.now = AS_OF + 25 * M
        filled = rt.advance(record.run_id, m5("115.9", "116.0", "115.3", "115.6",
                                              start=AS_OF + 20 * M), as_of=AS_OF + 25 * M,
                            reauthorise=True, operator=operator(AS_OF + 25 * M))
        assert filled.state is RunState.POSITION_OPEN
        order = rt.order(record.refs["order_id"])
        assert order.fill_authorisation.intent_id != order.intent.intent_id
        assert len(j.read(types=["risk.approved"])) == 2  # submission + re-authorisation
        assert reconcile(j, account_id="paper_test", ledger=rt.ledger).ok


def test_pending_order_can_be_cancelled_or_expire():
    with StellarJournal() as j:
        rt = limit_runtime(j)
        record = run_to_proposal(rt)
        cancelled = rt.cancel(record.run_id, as_of=AS_OF + 5 * M)
        assert cancelled.state is RunState.CANCELLED and cancelled.terminal
        assert run_types(j, record.run_id)[-1] == "run.completed"
        with pytest.raises(RunNotActive):
            rt.cancel(record.run_id, as_of=AS_OF + 6 * M)
    with StellarJournal() as j:
        rt = limit_runtime(j)
        record = run_to_proposal(rt)
        order = rt.order(record.refs["order_id"])
        late = order.intent.expires_at
        expired = rt.advance(record.run_id, m5("120", "121", "119", "120", start=late),
                             as_of=late + 5 * M)
        assert expired.state is RunState.EXPIRED


# ---------------------------------------------------------------- circuit breaker --


def test_breaker_trip_stops_a_pending_order_and_survives_restart():
    with StellarJournal() as j:
        clock = Clock()
        rt = limit_runtime(j, clock=clock)
        pending = run_to_proposal(rt)
        assert pending.state is RunState.PAPER_SUBMITTED
        # another run's risk evaluation breaches the daily-loss limit: Phase 3 trips
        loss = run_to_proposal(rt, request(op=operator(realised="-4000")))
        assert loss.state is RunState.REJECTED
        assert loss.failure is RuntimeFailure.CIRCUIT_BREAKER_TRIPPED
        assert rt.risk.breaker.state().status.value == "TRIPPED"
        # the pending order reaches its price: no re-authorisation passes, the broker cancels
        clock.now = AS_OF + 25 * M
        stopped = rt.advance(pending.run_id, m5("115.9", "116.0", "115.3", "115.6",
                                                start=AS_OF + 20 * M), as_of=AS_OF + 25 * M,
                             reauthorise=True, operator=operator(AS_OF + 25 * M))
        assert stopped.state is RunState.CANCELLED
        assert stopped.failure is RuntimeFailure.CIRCUIT_BREAKER_TRIPPED
        assert j.read(types=["order.filled"]) == []
        # restart: still TRIPPED; nothing re-arms it and a new run cannot trade
        again = limit_runtime(j, clock=clock)
        assert again.risk.breaker.state().status.value == "TRIPPED"
        assert j.read(types=["circuit_breaker.reset"]) == []
        assert health(again, checked_at=AS_OF + 25 * M).status is HealthStatus.BLOCKED
        blocked = run_to_proposal(again, request(op=operator(volume="0.30")))
        assert blocked.state is RunState.REJECTED
        assert blocked.failure is RuntimeFailure.CIRCUIT_BREAKER_TRIPPED
        assert not hasattr(again, "reset_breaker") and not hasattr(again, "reset")


def test_rerunning_the_same_research_run_describes_nothing_twice():
    """Phase 6 pipeline: the same run again reuses every step and re-emits no descriptive
    event (analysis / debate / research plan) that is already journaled."""
    from research_helpers import CB_DECISION, CPI_OFFICIAL, inputs, pipeline  # noqa: PLC0415
    from stellar.technical import analyse  # noqa: PLC0415
    from technical_helpers import TEST_CONFIG, response  # noqa: PLC0415
    from trader_helpers import LONG_CLOSES, bars_for  # noqa: PLC0415

    analysis = analyse(response(bars_for(LONG_CLOSES)), as_of=AS_OF, config=TEST_CONFIG)
    with StellarJournal() as j:
        pipe, provider = pipeline(j)
        first = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[analysis]))
        before, calls = j.last_seq(), len(provider.requests)
        second = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[analysis]))
        assert second.outputs_hash == first.outputs_hash
        assert j.last_seq() == before and len(provider.requests) == calls


def test_a_fresh_quote_alone_never_reauthorises_a_working_order():
    """Without ``reauthorise`` the runtime offers no authorisation, even at a moment when
    Phase 3 would approve: the order blocks instead of filling on its old approval."""
    fresh = (("122.0", "122.2", AS_OF), ("115.3", "115.5", AS_OF + 10 * M))
    with StellarJournal() as j:
        rt = runtime(j, market=source(quotes=fresh), technical_config=POINT_ZONES,
                     provider=ScriptedProvider(LIMIT))
        record = run_to_proposal(rt)
        blocked = rt.advance(record.run_id, m5("116", "116.2", "115.4", "115.8", start=AS_OF),
                             as_of=AS_OF + 10 * M, operator=operator(AS_OF + 10 * M))
        assert blocked.state is RunState.ORDER_BLOCKED
        assert len(j.read(types=["risk.approved"])) == 1  # nothing re-evaluated

