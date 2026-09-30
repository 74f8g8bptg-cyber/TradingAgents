"""Deterministic PAPER reconciliation: journal ↔ runs ↔ paper orders, positions, trades, account.

Every check reads the journal (directly or through the Phase 4 book, itself folded from the
journal). Nothing is repaired or rewritten: problems are reported as typed issues.

| Code | Problem |
|---|---|
| JOURNAL_INTEGRITY | a sequence gap or a body-hash failure (``StellarJournal.verify``) |
| FILLED_WITHOUT_POSITION | a FILLED order with no open position and no closed trade |
| DUPLICATE_FILL | more than one entry fill (``order.filled``) for one order |
| CLOSED_POSITION_STILL_OPEN | a position is both closed (a trade) and open |
| DUPLICATE_ORDER | more than one accepted order for one proposal (idempotency key) |
| DUPLICATE_PROPOSAL | ``trade.proposed`` journaled twice for one proposal id |
| BALANCE_MISMATCH | starting balance + known realised P&L ≠ the account balance |
| MISSING_ORDER | a run references an order the book does not hold |
| RUN_ORDER_MISMATCH | a run's position / trade references disagree with the book |
| ORPHAN_INTENT | a finished run holds an authorised intent that was never submitted |
| STAGE_ORDER_VIOLATION | a run's stage checkpoints are out of order or skip a stage |
| CHECKPOINT_MISMATCH | a run checkpoint's copy of a domain record (the proposal, the intent) differs from the domain record itself (``trade.proposed``, the broker's order) |

Balance is checked only when every closed trade's P&L is KNOWN; otherwise the unsettled
trades are listed (``unsettled_trade_ids``), never valued.
"""

from __future__ import annotations

from collections import Counter

from stellar.execution.models import PaperOrderStatus, PnlStatus, order_id_for, trade_id_for
from stellar.execution.state import load_book
from stellar.journal import StellarJournal
from stellar.journal.store import JournalIntegrityError
from stellar.runtime.ledger import RunLedger
from stellar.runtime.models import STAGE_ORDER, TERMINAL_STATES, RunStage
from stellar.schemas.common import Label, ShortText, StellarModel


class ReconciliationIssue(StellarModel):
    code: Label
    ref: ShortText | None = None
    detail: ShortText | None = None


class ReconciliationReport(StellarModel):
    ok: bool
    issues: tuple[ReconciliationIssue, ...] = ()
    events_checked: int
    runs_checked: int
    orders_checked: int
    trades_checked: int
    unsettled_trade_ids: tuple[str, ...] = ()


def reconcile(journal: StellarJournal, *, account_id: str,
              ledger: RunLedger | None = None) -> ReconciliationReport:
    issues: list[ReconciliationIssue] = []

    def issue(code: str, ref: str | None = None, detail: str | None = None) -> None:
        issues.append(ReconciliationIssue(code=code, ref=ref, detail=detail))

    try:
        events = journal.verify()
    except JournalIntegrityError as exc:
        return ReconciliationReport(ok=False, issues=(ReconciliationIssue(
            code="journal_integrity", detail=str(exc)[:500]),), events_checked=0,
            runs_checked=0, orders_checked=0, trades_checked=0)

    book = load_book(journal, account_id)
    state = book.state()
    open_ids = {p.position_id for p in state.open_positions}
    closed = {t.position_id: t for t in state.closed_trades}

    # orders, fills, positions -------------------------------------------------------------
    fills = Counter(e.payload.get("order_id") for e in journal.read(types=["order.filled"]))
    for order_id, count in sorted(fills.items()):
        if count > 1:
            issue("duplicate_fill", order_id, f"{count} entry fills")
    accepted = Counter(o.intent.idempotency_key for o in book.orders.values()
                       if o.status is not PaperOrderStatus.PREFLIGHT_FAILED)
    for key, count in sorted(accepted.items()):
        if count > 1:
            issue("duplicate_order", key, f"{count} accepted orders for one proposal")
    for order in sorted(book.orders.values(), key=lambda o: o.order_id):
        if order.status is PaperOrderStatus.FILLED and (
                order.position_id is None or (order.position_id not in open_ids
                                              and order.position_id not in closed)):
            issue("filled_without_position", order.order_id)
    for position_id in sorted(open_ids & set(closed)):
        issue("closed_position_still_open", position_id)
    proposals = journal.read(types=["trade.proposed"])
    proposed = Counter(e.payload.get("proposal_id") for e in proposals)
    for proposal_id, count in sorted(proposed.items()):
        if count > 1:
            issue("duplicate_proposal", proposal_id, f"journaled {count} times")

    # account balance ------------------------------------------------------------------------
    unsettled = tuple(sorted(t.trade_id for t in state.closed_trades
                             if t.realised.status is not PnlStatus.KNOWN))
    if not unsettled and state.balance is not None:
        known = sum((t.realised.amount for t in state.closed_trades), start=0)
        if state.starting_balance + known != state.balance:
            issue("balance_mismatch", account_id,
                  f"{state.starting_balance} + {known} != {state.balance}")

    # runs -----------------------------------------------------------------------------------
    runs = 0
    if ledger is not None:
        for run_id in ledger.run_ids():
            runs += 1
            record = ledger.record(run_id)
            assert record is not None
            cps = ledger.checkpoints(run_id)
            present = [s for s in STAGE_ORDER if s in cps]
            if present != list(STAGE_ORDER[:len(present)]):
                issue("stage_order_violation", run_id, ",".join(s.value for s in present))
            order_id = record.refs.get("order_id")
            if order_id is not None:
                order = book.orders.get(order_id)
                if order is None:
                    issue("missing_order", run_id, order_id)
                elif order.position_id is not None:
                    trade_ref = record.refs.get("trade_id")
                    if trade_ref is not None and trade_ref != trade_id_for(order.position_id):
                        issue("run_order_mismatch", run_id, "trade_id")
            proposal_cp = cps.get(RunStage.PROPOSAL)
            if proposal_cp is not None:
                copy = proposal_cp.outputs.get("proposal")
                journaled = [e.payload.get("proposal") for e in proposals
                             if e.payload.get("proposal_id") == proposal_cp.refs.get("proposal_id")]
                if not journaled or any(j != copy for j in journaled):
                    issue("checkpoint_mismatch", run_id, "proposal")
            auth_cp = cps.get(RunStage.ORDER_AUTHORISATION)
            if auth_cp is not None and auth_cp.outputs.get("intent") is not None:
                intent_id = auth_cp.outputs["intent"]["intent_id"]
                order = book.orders.get(order_id_for(intent_id))
                if order is not None and \
                        order.intent.model_dump(mode="json") != auth_cp.outputs["intent"]:
                    issue("checkpoint_mismatch", run_id, "intent")
            if RunStage.ORDER_AUTHORISATION in cps and RunStage.PAPER_SUBMISSION not in cps \
                    and record.state in TERMINAL_STATES and \
                    cps[RunStage.ORDER_AUTHORISATION].state.value == "ORDER_AUTHORISED":
                issue("orphan_intent", run_id, record.refs.get("intent_id"))

    return ReconciliationReport(
        ok=not issues, issues=tuple(issues), events_checked=events, runs_checked=runs,
        orders_checked=len(book.orders), trades_checked=len(state.closed_trades),
        unsettled_trade_ids=unsettled)
