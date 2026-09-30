"""Phase 6 pipeline re-run idempotency (the Phase 7 duplicate-suppression fix).

The fix only skips a *descriptive* event (``analysis.created``, ``debate.*``,
``decision.research_plan.created``) whose identical payload is already journaled for the same
research run id. LLM calls, checkpoints, fingerprints, results and the order of decisions are
unchanged. All fixtures are synthetic.
"""

import pytest
from research_helpers import CB_DECISION, CPI_OFFICIAL, NEWS, EvidenceScript, inputs, pipeline
from stellar.journal import StellarJournal
from stellar.pipeline.orchestrator import DESCRIPTIVE_EVENTS
from stellar.reasoning import FailureKind, ProviderFailure
from stellar.technical import analyse
from technical_helpers import TEST_CONFIG, response
from trader_helpers import LONG_CLOSES, bars_for

pytestmark = pytest.mark.unit

ANALYSIS = analyse(response(bars_for(LONG_CLOSES)), as_of=inputs().as_of, config=TEST_CONFIG)


def described(journal) -> list[tuple[str, str]]:
    return [(e.type, e.correlation_id) for e in journal.read(types=sorted(DESCRIPTIVE_EVENTS))]


def test_the_first_run_still_emits_every_descriptive_event():
    with StellarJournal() as j:
        pipe, _ = pipeline(j)
        support = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        kinds = [t for t, _ in described(j)]
        assert kinds.count("analysis.created") == 2  # macro + market view
        assert kinds.count("debate.started") == 1 and kinds.count("debate.completed") == 1
        assert kinds.count("debate.turn.completed") == 2
        assert kinds.count("decision.research_plan.created") == 1
        assert {c for _, c in described(j)} == {support.run_id}


def test_same_inputs_same_journal_repeat_nothing():
    with StellarJournal() as j:
        pipe, provider = pipeline(j)
        first = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        before, calls = j.read(), len(provider.requests)
        second = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        assert len(provider.requests) == calls  # no repeated LLM call
        assert j.read() == before  # no event at all, descriptive or otherwise
        assert second.run_id == first.run_id
        assert second.outputs_hash == first.outputs_hash  # same research / debate outcome
        for field in ("macro", "market_view", "bull_cases", "bear_cases", "challenge",
                      "quality", "synthesis", "final_stance", "evidence_pool_hash",
                      "research_snapshot_id"):
            assert getattr(second, field) == getattr(first, field), field
        assert [s.fingerprint for s in second.steps] == [s.fingerprint for s in first.steps]
        assert {s.status.value for s in second.steps if s.call is not None} == {"REUSED"}


def test_a_retried_failed_step_still_describes_its_new_result():
    """A step that failed is retried on the re-run (new work); only its new descriptive event
    appears, and the already-journaled ones are not repeated."""
    down = [ProviderFailure(FailureKind.PROVIDER_UNAVAILABLE)] * 2
    with StellarJournal() as j:
        pipe, provider = pipeline(j, script=EvidenceScript(overrides={"research_manager": down}))
        failed = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        assert failed.synthesis is None
        kinds_before = [t for t, _ in described(j)]
        assert "decision.research_plan.created" not in kinds_before
        calls = len(provider.requests)
        retried = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        assert retried.synthesis is not None
        assert len(provider.requests) == calls + 1  # only the failed step asks again
        kinds_after = [t for t, _ in described(j)]
        assert kinds_after.count("decision.research_plan.created") == 1
        for kind in ("analysis.created", "debate.started", "debate.completed"):
            assert kinds_after.count(kind) == kinds_before.count(kind), kind


def test_changed_inputs_do_new_work_and_describe_it():
    with StellarJournal() as j:
        pipe, provider = pipeline(j)
        first = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, technical=[ANALYSIS]))
        calls = len(provider.requests)
        changed = pipe.run(inputs(CB_DECISION, CPI_OFFICIAL, NEWS, technical=[ANALYSIS]))
        assert changed.run_id != first.run_id
        assert len(provider.requests) > calls  # the changed evidence is asked about
        by_run = {}
        for kind, run_id in described(j):
            by_run.setdefault(run_id, []).append(kind)
        assert sorted(by_run[changed.run_id]) == sorted(by_run[first.run_id])
