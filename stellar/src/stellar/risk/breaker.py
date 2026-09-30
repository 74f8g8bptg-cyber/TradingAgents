"""``CircuitBreakerState``: the kill switch's state as a contract (Foundation §4.27, §8.3).

State only. This module holds no thresholds and evaluates no rule: deciding
*when* to trip belongs to the Risk Engine and the other tripping agents (Phase 3
onward). It also contains **no reset operation**. Only the owner may reset the
breaker, through the local owner command (Phase 3, ``circuit_breaker.reset``);
this contract can only *record* such a reset, and a recorded reset must name
the owner. Nothing here re-arms the breaker automatically, on a timer or on
restart.

- Tripping is sticky: tripping an already tripped breaker keeps the first trip.
- A trip converts to and from the ``circuit_breaker.tripped`` event payload
  (layer design §4.3: ``rule``, ``value``, ``limit``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import model_validator

from stellar.schemas.common import (
    SCHEMA_VERSION,
    FiniteDecimal,
    SchemaVersion,
    ShortText,
    StellarModel,
    TechnicalId,
    Ulid,
    UtcDatetime,
)
from stellar.schemas.risk import RiskRule

OWNER = "owner"


class BreakerStatus(StrEnum):
    ARMED = "ARMED"
    TRIPPED = "TRIPPED"


class TripCause(StrEnum):
    """What tripped the breaker (Foundation §4.27)."""

    RISK_RULE = "risk_rule"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    DATA_FAILURE = "data_failure"
    BUDGET_EXHAUSTION = "budget_exhaustion"
    OWNER = "owner"


class BreakerTrip(StellarModel):
    """One trip: its cause, the rule involved (if any), the values seen, who and when."""

    cause: TripCause
    rule: RiskRule | None = None
    value: FiniteDecimal | None = None
    limit: FiniteDecimal | None = None
    tripped_by: TechnicalId
    tripped_at: UtcDatetime
    event_id: Ulid | None = None

    @model_validator(mode="after")
    def _consistent(self) -> BreakerTrip:
        if self.cause is TripCause.RISK_RULE and self.rule is None:
            raise ValueError("a risk-rule trip must name its rule")
        if (self.cause is TripCause.OWNER) != (self.tripped_by == OWNER):
            raise ValueError("a manual trip is made by the owner, and only the owner is 'owner'")
        return self

    def to_event_payload(self) -> dict[str, Any]:
        """Payload for a ``circuit_breaker.tripped`` event."""
        return {
            "rule": self.rule.value if self.rule is not None else self.cause.value,
            "cause": self.cause.value,
            "value": None if self.value is None else str(self.value),
            "limit": None if self.limit is None else str(self.limit),
            "tripped_by": self.tripped_by,
        }

    @classmethod
    def from_event(cls, event: Any) -> BreakerTrip:
        """Rebuild the trip recorded by a ``circuit_breaker.tripped`` event (for replay)."""
        if event.type != "circuit_breaker.tripped":
            raise ValueError(f"expected circuit_breaker.tripped, got {event.type}")
        payload = event.payload
        cause = TripCause(payload.get("cause", TripCause.RISK_RULE.value))
        rule = payload.get("rule")
        known_rules = {r.value for r in RiskRule}
        return cls(
            cause=cause,
            rule=RiskRule(rule) if rule in known_rules else None,
            value=payload.get("value"),
            limit=payload.get("limit"),
            tripped_by=payload.get("tripped_by") or event.agent_id,
            tripped_at=event.ts,
            event_id=event.event_id,
        )


class OwnerReset(StellarModel):
    """A record of a reset made by the owner command. Always by the owner, with a reason."""

    by: Literal["owner"]
    reason: ShortText
    reset_at: UtcDatetime
    event_id: Ulid | None = None


class CircuitBreakerState(StellarModel):
    schema_version: SchemaVersion = SCHEMA_VERSION
    status: BreakerStatus = BreakerStatus.ARMED
    trip: BreakerTrip | None = None
    last_reset: OwnerReset | None = None
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def _consistent(self) -> CircuitBreakerState:
        if self.status is BreakerStatus.TRIPPED:
            if self.trip is None:
                raise ValueError("a tripped breaker records its trip")
            if self.trip.tripped_at > self.updated_at:
                raise ValueError("updated_at cannot be before the trip")
        elif self.trip is not None:
            raise ValueError("an armed breaker carries no active trip")
        if self.last_reset is not None:
            if self.last_reset.reset_at > self.updated_at:
                raise ValueError("updated_at cannot be before the last reset")
            if self.trip is not None and self.trip.tripped_at < self.last_reset.reset_at:
                raise ValueError("an active trip cannot predate the last reset")
        return self

    @property
    def trading_blocked(self) -> bool:
        return self.status is BreakerStatus.TRIPPED

    def tripped(self, trip: BreakerTrip) -> CircuitBreakerState:
        """The state after ``trip``. Sticky: an already tripped breaker keeps its first trip."""
        if self.status is BreakerStatus.TRIPPED:
            return self
        return CircuitBreakerState(
            status=BreakerStatus.TRIPPED,
            trip=trip,
            last_reset=self.last_reset,
            updated_at=max(self.updated_at, trip.tripped_at),
        )
