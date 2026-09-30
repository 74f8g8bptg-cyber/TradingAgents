"""The execution abstraction (Foundation §4.16): the ``Broker`` interface.

``PaperBroker`` implements it now; a future ``Mt5BridgeClient`` (Phase 8, demo
only) will implement the same surface. Only the execution service holds a
``Broker``; no LLM agent can reach one.

Deviation from §4.16, recorded in the Phase 4 document: there is no ``quote()``.
The Paper Broker has no price source of its own and never creates a price;
market input is pushed in explicitly (``submit(..., market=)``, ``process``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from stellar.execution.models import ConversionRate, PaperAccountState, Position, TradeRecord
from stellar.execution.pricing import MarketInput
from stellar.risk.state import RiskContext
from stellar.schemas.execution import ExecutionResult
from stellar.schemas.market import Quote
from stellar.schemas.order import OrderIntent
from stellar.telemetry import StellarEvent


@runtime_checkable
class Broker(Protocol):
    def account(self) -> PaperAccountState: ...

    def positions(self) -> tuple[Position, ...]: ...

    def submit(self, intent: OrderIntent, context: RiskContext, *, as_of: datetime,
               market: MarketInput | None = None,
               conversions: Sequence[ConversionRate] = ()) -> ExecutionResult: ...

    def close(self, position_id: str, quote: Quote, *, as_of: datetime,
              conversions: Sequence[ConversionRate] = ()) -> TradeRecord: ...

    def cancel(self, order_id: str, *, as_of: datetime) -> ExecutionResult: ...

    def events(self) -> list[StellarEvent]: ...
