"""Phase 7 typed failures, fail-closed configuration and reconciliation failures, on
synthetic labelled fixtures. Nothing here is a real market fact."""

import json

import pytest
from research_helpers import AS_OF, CB_DECISION, CPI_OFFICIAL
from runtime_helpers import (
    RUNTIME_CONFIG,
    M,
    Script,
    approved,
    request,
    run_to_proposal,
    runtime,
    source,
)
from stellar.journal import StellarJournal
from stellar.reasoning import FailureKind, ProviderFailure, ScriptedProvider
from stellar.runtime import (
    HealthStatus,
    RunStage,
    RunState,
    RuntimeConfigError,
    RuntimeFailure,
    health,
    reconcile,
)
from stellar.setups import SetupInputError
from stellar.technical import TechnicalInputError
from stellar.telemetry import new_event
from trader_helpers import SETUP_CONFIG, TraderScript

pytestmark = pytest.mark.unit


@pytest.fixture
def journal():
    with StellarJournal() as j:
        yield j


def stages(rt, record) -> list[str]:
    return [s.value for s in rt.ledger.checkpoints(record.run_id)]


def test_market_data_failure(journal):
    rt = runtime(journal, market=source(closes=[100, 101], end=AS_OF + 180 * M))
    record = rt.run(request())  # no bar closes at or before as_of
    assert record.state is RunState.FAILED
    assert record.failure is RuntimeFailure.MARKET_DATA_FAILED
    assert stages(rt, record) == ["MARKET_DATA"]
    assert journal.read(run_id=record.run_id)[-1].type == "run.failed"


def test_missing_quote_is_not_invented(journal):
    rt = runtime(journal, market=source(supports_quotes=False))
    record = run_to_proposal(rt)
    cp = rt.ledger.checkpoints(record.run_id)[RunStage.MARKET_DATA]
    assert cp.outputs["quote"] is None and cp.detail.startswith("quote_unavailable")
    assert record.state is RunState.SETUP_CANDIDATE
    assert record.failure is RuntimeFailure.PROPOSAL_FAILED and record.detail == "no_quote"
    assert journal.read(types=["order.created"]) == []


def test_technical_failure(journal, monkeypatch):
    def broken(*a, **k):
        raise TechnicalInputError("fixture: technical input refused")

    monkeypatch.setattr("stellar.runtime.orchestrator.analyse", broken)
    record = runtime(journal).run(request())
    assert record.state is RunState.FAILED and record.failure is RuntimeFailure.TECHNICAL_FAILED
    assert journal.read(types=["research.snapshot.created"]) == []


def test_research_failure_when_the_synthesis_fails(journal):
    down = [ProviderFailure(FailureKind.PROVIDER_UNAVAILABLE)] * 2
    rt = runtime(journal, provider=ScriptedProvider(Script(overrides={"research_manager": down})))
    record = rt.run(request())
    assert record.state is RunState.FAILED and record.failure is RuntimeFailure.RESEARCH_FAILED
    assert "research_manager" in record.detail
    assert RunStage.SETUP not in rt.ledger.checkpoints(record.run_id)


def test_research_failure_on_inconsistent_inputs(journal):
    req = request()
    wrong = req.model_copy(update={"collections": tuple(
        c.model_copy(update={"as_of": AS_OF - M}) for c in req.collections)})
    record = runtime(journal).run(wrong)
    assert record.state is RunState.FAILED and record.failure is RuntimeFailure.RESEARCH_FAILED


def test_setup_failure(journal, monkeypatch):
    rt = runtime(journal)

    def broken(*a, **k):
        raise SetupInputError("technical_not_reviewed", "fixture")

    monkeypatch.setattr(rt.desk, "run", broken)
    record = rt.run(request())
    assert record.state is RunState.FAILED and record.failure is RuntimeFailure.SETUP_FAILED


def test_trader_llm_inventing_a_price_is_a_setup_failure(journal):
    liar = TraderScript(targets=("PRIOR_SWING_TARGET",), extra={"entry_price": "121.5"})
    rt = runtime(journal, provider=ScriptedProvider(Script(trader=liar)))
    parked = rt.run(request())
    record = rt.run(request(approval=approved(rt, parked)))
    assert record.state is RunState.SETUP_CANDIDATE
    assert record.failure is RuntimeFailure.SETUP_FAILED
    assert "schema_mismatch" in record.detail
    assert journal.read(types=["trade.proposed"]) == []


def test_proposal_failure(journal):
    setup = SETUP_CONFIG.model_copy(update={"profile": None})
    rt = runtime(journal, setup_config=setup,
                 config=RUNTIME_CONFIG.model_copy(update={"profile": None}))
    record = run_to_proposal(rt)
    assert record.state is RunState.SETUP_CANDIDATE
    assert record.failure is RuntimeFailure.PROPOSAL_FAILED
    assert record.detail == "profile_not_configured"


def test_order_authorisation_failure_without_a_broker_symbol(journal):
    rt = runtime(journal, config=RUNTIME_CONFIG.model_copy(update={"broker_symbols": {}}))
    record = run_to_proposal(rt)
    assert record.state is RunState.FAILED
    assert record.failure is RuntimeFailure.ORDER_AUTHORISATION_FAILED
    assert journal.read(types=["order.created"]) == []


def test_instrument_not_enabled_is_refused_by_the_risk_engine(journal):
    rt = runtime(journal, config=RUNTIME_CONFIG.model_copy(update={"enabled_instruments": ()}))
    record = run_to_proposal(rt)
    assert record.state is RunState.REJECTED and "instrument" in record.detail


def test_runtime_configuration_fails_closed(journal):
    with pytest.raises(RuntimeConfigError):
        runtime(journal, config=RUNTIME_CONFIG.model_copy(update={"timeframe": None}))
    with pytest.raises(RuntimeConfigError):
        runtime(journal, config=RUNTIME_CONFIG.model_copy(update={"profile": "other_profile"}))


def test_production_defaults_trade_nothing(journal):
    """The unconfigured runtime, setup and research defaults cannot reach an order."""
    from stellar.pipeline import WorkflowConfig  # noqa: PLC0415
    from stellar.runtime import RuntimeConfig  # noqa: PLC0415
    from stellar.schemas.market import Timeframe  # noqa: PLC0415
    from stellar.setups import SetupConfig  # noqa: PLC0415

    rt = runtime(journal, config=RuntimeConfig(timeframe=Timeframe.H1),
                 setup_config=SetupConfig(), workflow=WorkflowConfig())
    record = rt.run(request())
    assert record.state in (RunState.NO_SETUP, RunState.SETUP_CANDIDATE)
    assert journal.read(types=["trade.proposed"]) == []
    assert journal.read(types=["agent.llm_call.started"]) == []  # LLM stays disabled
    assert health(rt, checked_at=AS_OF).status is HealthStatus.BLOCKED


# ------------------------------------------------------------------- reconciliation --


def forge(journal, event_type, payload, **kw):
    """Append a forged event (as a corrupt writer would) to test the reconciliation."""
    return journal.append(new_event(event_type, station_id="stellar-test", source="stellar.forged",
                                    payload=payload, ts=AS_OF + 30 * M, **kw))


def test_reconciliation_succeeds_on_a_clean_journal(journal):
    rt = runtime(journal)
    run_to_proposal(rt)
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    assert report.ok and report.runs_checked == 1 and report.orders_checked == 1


def test_reconciliation_detects_a_duplicate_fill_and_proposal(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt)
    fill = journal.read(types=["order.filled"])[0]
    forge(journal, "order.filled", json.loads(json.dumps(fill.payload)),
          correlation_id=fill.correlation_id)
    proposed = journal.read(types=["trade.proposed"])[0]
    forge(journal, "trade.proposed", json.loads(json.dumps(proposed.payload)))
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    codes = {i.code for i in report.issues}
    assert not report.ok and {"duplicate_fill", "duplicate_proposal"} <= codes
    assert health(rt, checked_at=AS_OF).status is HealthStatus.FAILED
    assert record.refs["order_id"] in {i.ref for i in report.issues}


def test_reconciliation_detects_a_run_pointing_at_a_missing_order(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt)
    from stellar.runtime import StageCheckpoint  # noqa: PLC0415

    rt.ledger.checkpoint(StageCheckpoint(
        run_id=record.run_id, stage=RunStage.PAPER_SUBMISSION, fingerprint="a" * 64,
        state=RunState.PAPER_SUBMITTED, refs={"order_id": "ord_missing"}), instrument="XAUUSD")
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    assert "missing_order" in {i.code for i in report.issues}


def test_reconciliation_detects_an_orphan_intent(journal):
    rt = runtime(journal)
    record = run_to_proposal(rt, request(items=(CB_DECISION, CPI_OFFICIAL)))
    run_id = record.run_id
    # a run that authorised an intent and then was closed without submitting it
    forged = rt.ledger.record(run_id)
    assert forged.refs.get("intent_id")
    from stellar.runtime.ledger import RunLedger  # noqa: PLC0415

    ledger = RunLedger(journal, station_id="stellar-test", clock=lambda: AS_OF)
    bad = "run_" + "b" * 40
    ledger.emit("run.started", bad, {"instrument": "XAUUSD", "timeframe": "H1",
                                     "profile": None, "as_of": AS_OF.isoformat(),
                                     "workflow_version": "v1_paper_1", "config_hashes": {},
                                     "operator": {}})
    for cp in rt.ledger.checkpoints(run_id).values():
        if cp.stage is RunStage.PAPER_SUBMISSION:
            continue
        ledger.checkpoint(cp.model_copy(update={"run_id": bad}), instrument="XAUUSD")
    ledger.emit("run.completed", bad, {"state": "BLOCKED", "failure": None, "detail": "forged",
                                       "refs": {}})
    report = reconcile(journal, account_id="paper_test", ledger=rt.ledger)
    assert ("orphan_intent", bad) in {(i.code, i.ref) for i in report.issues}
