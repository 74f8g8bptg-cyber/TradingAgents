"""Paper Broker state is a fold over the journal; nothing else is authoritative.

Every broker event carries the complete new record (order, position or trade), so
reconstruction is a plain upsert in journal order. ``order.filled`` also carries the
position it opens and ``trade.closed`` the closed position, so each transition is
complete in one event even if a later event of the same call was never written. The same journal always
gives the same state; the broker keeps no hidden in-memory state between calls.
Derived figures (balance, equity, peak equity, open risk) are recomputed from
the records after each event. ``account.snapshot.created`` is derived output and
is never read back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from stellar.execution.config import PaperBrokerConfig
from stellar.execution.models import (
    WORKING_ORDER_STATUSES,
    PaperAccountState,
    PaperOrder,
    PaperOrderStatus,
    PaperStats,
    PnlStatus,
    Position,
    TradeRecord,
)
from stellar.execution.pnl import risk_at_stop
from stellar.journal import StellarJournal
from stellar.telemetry import StellarEvent

BROKER_SOURCE = "stellar.paper_broker"
BROKER_EVENT_TYPES = (
    "account.opened",
    "order.preflight.failed",
    "order.created",
    "order.filled",
    "order.rejected",
    "order.cancelled",
    "order.expired",
    "position.opened",
    "position.updated",
    "trade.closed",
)
_ORDER_EVENTS = {"order.preflight.failed", "order.created", "order.filled", "order.rejected",
                 "order.cancelled", "order.expired"}


class BrokerJournalError(RuntimeError):
    """The journal's broker history is inconsistent; the broker refuses to run on it."""


@dataclass
class Book:
    account_id: str
    config: PaperBrokerConfig | None = None
    orders: dict[str, PaperOrder] = field(default_factory=dict)
    positions: dict[str, Position] = field(default_factory=dict)
    trades: dict[str, TradeRecord] = field(default_factory=dict)
    peak_equity: Decimal | None = None
    version: int = 0
    seq: int = 0
    as_of: datetime | None = None

    # ------------------------------------------------------------------ fold --

    def apply(self, event: StellarEvent) -> None:
        payload = event.payload
        if event.type == "account.opened":
            if self.config is not None:
                raise BrokerJournalError(f"account {self.account_id} is opened twice")
            self.config = PaperBrokerConfig.model_validate(payload["config"])
            self.peak_equity = self.config.starting_balance
        elif self.config is None:
            raise BrokerJournalError(f"{event.type} before account {self.account_id} opened")
        elif event.type in _ORDER_EVENTS:
            order = PaperOrder.model_validate(payload["order"])
            self.orders[order.order_id] = order
            if "position" in payload:  # order.filled carries the position it opens
                position = Position.model_validate(payload["position"])
                self.positions[position.position_id] = position
        elif event.type in {"position.opened", "position.updated"}:
            position = Position.model_validate(payload["position"])
            if event.type == "position.updated" and position.position_id not in self.positions:
                raise BrokerJournalError(f"update of unknown position {position.position_id}")
            self.positions[position.position_id] = position
        elif event.type == "trade.closed":
            trade = TradeRecord.model_validate(payload["trade"])
            if self.positions.pop(trade.position_id, None) is None:
                raise BrokerJournalError(f"close of unknown position {trade.position_id}")
            self.trades[trade.trade_id] = trade
        self.version += 1
        self.seq = event.seq or self.seq
        self.as_of = event.ts if self.as_of is None else max(self.as_of, event.ts)
        equity = self.equity()
        if equity is not None and (self.peak_equity is None or equity > self.peak_equity):
            self.peak_equity = equity

    # --------------------------------------------------------------- derived --

    @property
    def opened(self) -> bool:
        return self.config is not None

    def realised(self) -> Decimal | None:
        amounts = [t.realised.amount for t in self.trades.values()]
        return None if None in amounts else sum(amounts, Decimal(0))

    def balance(self) -> Decimal | None:
        realised = self.realised()
        return None if realised is None or self.config is None else \
            self.config.starting_balance + realised

    def unrealised(self) -> Decimal | None:
        amounts = [p.unrealised.amount if p.unrealised is not None else None
                   for p in self.positions.values()]
        return None if None in amounts else sum(amounts, Decimal(0))

    def equity(self) -> Decimal | None:
        balance, unrealised = self.balance(), self.unrealised()
        return None if balance is None or unrealised is None else balance + unrealised

    def open_risk(self) -> Decimal | None:
        assert self.config is not None
        risks = [risk_at_stop(entry=p.entry_price, stop=p.stop_loss, volume=p.volume,
                              economics=self.config.economics_for(p.instrument),
                              account_currency=self.config.account_currency)
                 for p in self.positions.values()]
        return None if None in risks else sum(risks, Decimal(0))

    def working(self) -> list[PaperOrder]:
        """PENDING and BLOCKED orders, oldest first."""
        return sorted((o for o in self.orders.values() if o.status in WORKING_ORDER_STATUSES),
                      key=lambda o: (o.created_at, o.order_id))

    def open_positions(self) -> list[Position]:
        return sorted(self.positions.values(), key=lambda p: (p.opened_at, p.position_id))

    def accepted_order_for_key(self, key: str) -> PaperOrder | None:
        return next((o for o in self.orders.values() if o.intent.idempotency_key == key
                     and o.status is not PaperOrderStatus.PREFLIGHT_FAILED), None)

    def state(self) -> PaperAccountState:
        if self.config is None:
            raise BrokerJournalError(f"account {self.account_id} is not opened")
        trades = sorted(self.trades.values(), key=lambda t: (t.closed_at, t.trade_id))
        positions = self.open_positions()
        return PaperAccountState(
            account_id=self.account_id,
            currency=self.config.account_currency,
            starting_balance=self.config.starting_balance,
            balance=self.balance(),
            realised_pnl=self.realised(),
            unrealised_pnl=self.unrealised(),
            equity=self.equity(),
            peak_equity=self.peak_equity,
            unsettled_trade_ids=tuple(t.trade_id for t in trades
                                      if t.realised.status is not PnlStatus.KNOWN),
            unvalued_position_ids=tuple(
                p.position_id for p in positions
                if p.unrealised is None or p.unrealised.status is not PnlStatus.KNOWN),
            open_positions=tuple(positions),
            pending_orders=tuple(self.working()),
            closed_trades=tuple(trades),
            open_risk=self.open_risk(),
            version=self.version,
            seq=self.seq,
            as_of=self.as_of,
            config_hash=self.config.config_hash(),
        )

    def stats(self) -> PaperStats:
        orders = list(self.orders.values())

        def count(status: PaperOrderStatus) -> int:
            return sum(o.status is status for o in orders)

        preflight = count(PaperOrderStatus.PREFLIGHT_FAILED)
        return PaperStats(
            submitted=len(orders), preflight_failed=preflight, accepted=len(orders) - preflight,
            pending=count(PaperOrderStatus.PENDING), blocked=count(PaperOrderStatus.BLOCKED),
            filled=count(PaperOrderStatus.FILLED),
            rejected=count(PaperOrderStatus.REJECTED), cancelled=count(PaperOrderStatus.CANCELLED),
            expired=count(PaperOrderStatus.EXPIRED), open_positions=len(self.positions),
            closed_trades=len(self.trades))


def broker_events(journal: StellarJournal, account_id: str) -> list[StellarEvent]:
    return [e for e in journal.read(types=BROKER_EVENT_TYPES)
            if e.source == BROKER_SOURCE and e.payload.get("account_id") == account_id]


def load_book(journal: StellarJournal, account_id: str) -> Book:
    """Reconstruct one paper account from the journal."""
    book = Book(account_id)
    for event in broker_events(journal, account_id):
        book.apply(event)
    return book
