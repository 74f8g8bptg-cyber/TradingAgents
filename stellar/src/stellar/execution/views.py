"""Read models of the paper account for the Risk Engine's ``RiskContext`` (Phase 3 RK-11).

The dependency points one way: ``stellar.execution`` imports the Phase 3 state
types; ``stellar.risk`` never imports ``stellar.execution``. Figures that cannot be
known are ``None`` (the risk rules then report a missing input), never estimated.
"""

from __future__ import annotations

from datetime import datetime

from stellar.execution.models import PaperOrderStatus
from stellar.execution.pnl import risk_at_stop
from stellar.execution.state import Book
from stellar.risk.state import AccountRiskState, PendingOrderState, PositionState
from stellar.schemas.common import Sha256Hex, StellarModel


class PaperRiskInputs(StellarModel):
    account: AccountRiskState | None
    positions: tuple[PositionState, ...]
    pending_orders: tuple[PendingOrderState, ...]
    prior_idempotency_keys: tuple[Sha256Hex, ...]
    """Keys of every order the broker accepted (one accepted order per proposal)."""


def risk_inputs(book: Book, as_of: datetime, *,
                excluding_order_id: str | None = None) -> PaperRiskInputs:
    """The book as the Risk Engine sees it. ``excluding_order_id`` gives the book a working
    order fills *into*: everything except that order (re-authorising it must not count
    the order against itself, just as at its first submission)."""
    config = book.config
    assert config is not None
    currency = config.account_currency
    positions = tuple(
        PositionState(instrument=p.instrument, side=p.side, volume=p.volume,
                      open_price=p.entry_price, stop_loss=p.stop_loss,
                      open_risk=risk_at_stop(entry=p.entry_price, stop=p.stop_loss,
                                             volume=p.volume,
                                             economics=config.economics_for(p.instrument),
                                             account_currency=currency),
                      idempotency_key=p.idempotency_key, source="paper_broker")
        for p in book.open_positions())
    pending = tuple(
        PendingOrderState(instrument=o.intent.instrument, side=o.intent.side,
                          volume=o.intent.volume, idempotency_key=o.intent.idempotency_key,
                          open_risk=None if o.intent.price is None else risk_at_stop(
                              entry=o.intent.price, stop=o.intent.stop_loss,
                              volume=o.intent.volume,
                              economics=config.economics_for(o.intent.instrument),
                              account_currency=currency),
                          source="paper_broker")
        for o in book.working() if o.order_id != excluding_order_id)
    keys = tuple(sorted({o.intent.idempotency_key for o in book.orders.values()
                         if o.order_id != excluding_order_id
                         and o.status is not PaperOrderStatus.PREFLIGHT_FAILED}))
    equity, balance, peak = book.equity(), book.balance(), book.peak_equity
    account = None
    if equity is not None and equity > 0:
        account = AccountRiskState(
            currency=currency, equity=equity,
            balance=balance if balance is not None and balance > 0 else None,
            peak_equity=peak if peak is not None and peak >= equity else None,
            as_of=as_of, source="paper_broker")
    return PaperRiskInputs(account=account, positions=positions, pending_orders=pending,
                           prior_idempotency_keys=keys)
