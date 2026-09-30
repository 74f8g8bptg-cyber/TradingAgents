"""Shared building blocks for Stellar contracts.

Rules every contract follows:

- **Closed and immutable.** Unknown fields are rejected (a mistyped field is an
  error, not a silently ignored value) and records cannot be mutated after
  construction.
- **Versioned and additive.** Every record carries ``schema_version``; new
  fields within major version 1 are optional with defaults, so old records stay
  valid. A record from another major version is rejected.
- **Typed numbers.** Prices, volumes and ratios are ``Decimal``. Floats, booleans,
  NaN and infinity are rejected, so no execution value is rounded through a
  float or hidden in text.
- **UTC timestamps.** Naive timestamps are rejected; aware ones are converted to
  UTC.
- **Prefixed ids.** Ids carry the prefix of their record kind (``stellar.ids``).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from stellar.ids import ID_TOKEN, ULID_PATTERN, IdKind

SCHEMA_VERSION = "1.0"


class StellarModel(BaseModel):
    """Base for every Stellar contract: closed, immutable, validated defaults."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


# ---------------------------------------------------------------- numbers ---


def strict_number(value: Any) -> Any:
    if isinstance(value, bool):
        raise ValueError("a boolean is not a number")
    if isinstance(value, float):
        raise ValueError("floats are not accepted; pass a Decimal, an int or a numeric string")
    return value


Price = Annotated[Decimal, BeforeValidator(strict_number), Field(gt=0, allow_inf_nan=False)]
"""A strictly positive, finite price."""

PositiveDecimal = Annotated[
    Decimal, BeforeValidator(strict_number), Field(gt=0, allow_inf_nan=False)
]
"""A strictly positive, finite quantity (for example a volume in lots)."""

NonNegativeDecimal = Annotated[
    Decimal, BeforeValidator(strict_number), Field(ge=0, allow_inf_nan=False)
]
"""A finite quantity that may be zero."""

FiniteDecimal = Annotated[Decimal, BeforeValidator(strict_number), Field(allow_inf_nan=False)]
"""Any finite decimal (may be negative, for example a slippage or a check value)."""

UnitInterval = Annotated[
    Decimal, BeforeValidator(strict_number), Field(ge=0, le=1, allow_inf_nan=False)
]
"""A finite decimal in [0, 1]."""


# ------------------------------------------------------------------ time ----


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_to_utc)]


# ------------------------------------------------------------------ text ----

TechnicalId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{1,63}$")]
"""A technical agent id (``risk_engine``). Never a persona or display name."""

Label = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
"""A short machine label (rule ids, reasons, bases). Not free text."""

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

SchemaVersion = Annotated[str, StringConstraints(pattern=r"^1\.[0-9]+$")]

Ulid = Annotated[str, StringConstraints(pattern=ULID_PATTERN.pattern)]

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]

ProfileId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_\-]{0,63}$")]
"""A timeframe profile id (Foundation §7). No profile is chosen yet (D-7)."""

ShortText = Annotated[str, StringConstraints(min_length=1, max_length=500)]
"""Bounded human-readable text. Never read by a decision or an order."""


def _id(kind: IdKind) -> Any:
    return Annotated[str, StringConstraints(pattern=rf"^{kind.value}_{ID_TOKEN}$")]


ResearchItemId = _id(IdKind.RESEARCH_ITEM)
ClaimId = _id(IdKind.CLAIM)
ClaimValidationId = _id(IdKind.CLAIM_VALIDATION)
ResearchSnapshotId = _id(IdKind.RESEARCH_SNAPSHOT)
SnapshotId = _id(IdKind.SNAPSHOT)
SetupId = _id(IdKind.SETUP)
AnalysisId = _id(IdKind.ANALYSIS)
RunId = _id(IdKind.RUN)
ProposalId = _id(IdKind.PROPOSAL)
DecisionId = _id(IdKind.DECISION)
IntentId = _id(IdKind.INTENT)
OrderId = _id(IdKind.ORDER)
FillId = _id(IdKind.FILL)
TradeId = _id(IdKind.TRADE)
PositionId = _id(IdKind.POSITION)

_ANY_RECORD_ID = re.compile(
    rf"^(?:{'|'.join(k.value for k in IdKind)})_{ID_TOKEN}$"
)


def is_record_id(value: str) -> bool:
    """True when ``value`` is an id of any known record kind."""
    return bool(_ANY_RECORD_ID.match(value))


# ------------------------------------------------------------- vocabulary ---


class InstrumentId(StrEnum):
    """Canonical Stellar instrument ids (Foundation §4.2)."""

    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    USDJPY = "USDJPY"
    NAS100 = "NAS100"


INSTRUMENT_DISPLAY_NAMES: dict[InstrumentId, str] = {
    InstrumentId.XAUUSD: "XAU/USD",
    InstrumentId.EURUSD: "EUR/USD",
    InstrumentId.USDJPY: "USD/JPY",
    InstrumentId.NAS100: "NAS100",
}


class AssetClass(StrEnum):
    METAL = "metal"
    FX = "fx"
    INDEX_CFD = "index_cfd"


class Direction(StrEnum):
    """Direction of a Setup or TradeProposal (Foundation §4.12)."""

    LONG = "LONG"
    SHORT = "SHORT"


class OrderSide(StrEnum):
    """Side of an OrderIntent (Foundation §4.14)."""

    BUY = "BUY"
    SELL = "SELL"


SIDE_FOR_DIRECTION: dict[Direction, OrderSide] = {
    Direction.LONG: OrderSide.BUY,
    Direction.SHORT: OrderSide.SELL,
}


class Provenance(StellarModel):
    """Who produced a record, under which configuration, from which inputs."""

    produced_by: TechnicalId
    config_hash: Sha256Hex
    input_ids: tuple[str, ...] = ()

    @field_validator("input_ids")
    @classmethod
    def _inputs_are_record_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [v for v in value if not is_record_id(v)]
        if bad:
            raise ValueError(f"input ids must be Stellar record ids: {bad}")
        if len(set(value)) != len(value):
            raise ValueError("input ids must be unique")
        return value
