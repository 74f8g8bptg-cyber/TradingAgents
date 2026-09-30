"""Research collection results: data, or an explicit absence. Never an invented filler.

A collector (R1–R6) returns a ``CollectionResult``:
- **OK** with items;
- **NO_DATA:** the source answered with nothing for the window;
- **UNAVAILABLE:** the source could not be reached or read.

No component asks an LLM to fill a missing result from memory. Model knowledge is not
a data source. An absent role is reported as missing coverage downstream.

Collectors themselves (retrieval from owner-supplied files or, later, providers) are
behind the ``ResearchCollector`` protocol. ``StaticCollector`` serves pre-built items (owner
files, tests).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import model_validator

from stellar.schemas.common import Label, StellarModel, UtcDatetime
from stellar.schemas.research import ResearchItem, ResearchRole


class CollectionStatus(StrEnum):
    OK = "OK"
    NO_DATA = "NO_DATA"
    UNAVAILABLE = "UNAVAILABLE"


class CollectionResult(StellarModel):
    role: ResearchRole
    as_of: UtcDatetime
    status: CollectionStatus
    items: tuple[ResearchItem, ...] = ()
    reason: Label | None = None

    @model_validator(mode="after")
    def _consistent(self) -> CollectionResult:
        if (self.status is CollectionStatus.OK) != bool(self.items):
            raise ValueError("OK carries items; NO_DATA and UNAVAILABLE carry none")
        if self.status is not CollectionStatus.OK and self.reason is None:
            raise ValueError("an absence states its reason")
        if any(i.role is not self.role for i in self.items):
            raise ValueError("a collector returns items of its own role only")
        return self


class ResearchCollector(Protocol):
    role: ResearchRole

    def collect(self, as_of: datetime) -> CollectionResult: ...


class StaticCollector:
    """Serves given items (for example owner-supplied files) for one role."""

    def __init__(self, role: ResearchRole, items: Sequence[ResearchItem] = (), *,
                 unavailable_reason: str | None = None) -> None:
        self.role = role
        self._items = tuple(items)
        self._unavailable = unavailable_reason

    def collect(self, as_of: datetime) -> CollectionResult:
        if self._unavailable is not None:
            return CollectionResult(role=self.role, as_of=as_of,
                                    status=CollectionStatus.UNAVAILABLE,
                                    reason=self._unavailable)
        if not self._items:
            return CollectionResult(role=self.role, as_of=as_of, status=CollectionStatus.NO_DATA,
                                    reason="no_items")
        return CollectionResult(role=self.role, as_of=as_of, status=CollectionStatus.OK,
                                items=self._items)
