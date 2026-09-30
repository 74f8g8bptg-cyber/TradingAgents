"""The Stellar event envelope (layer design §4.2).

An event is immutable. ``seq`` is empty until the journal stores the event and
assigns the next sequence number; the stored copy carries it. Serialization is
canonical, so the same event always produces the same JSON and the same hash.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import Field, JsonValue, StringConstraints, field_validator, model_validator

from stellar.ids import new_ulid
from stellar.schemas.common import (
    SCHEMA_VERSION,
    InstrumentId,
    Label,
    RunId,
    SchemaVersion,
    StellarModel,
    TechnicalId,
    Ulid,
    UtcDatetime,
    is_record_id,
)
from stellar.serialization import canonical_json, sha256_hex
from stellar.telemetry.catalogue import EVENT_TYPES, REQUIRED_PAYLOAD_KEYS

StationId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9\-]{0,63}$")]
EventSource = Annotated[str, StringConstraints(pattern=r"^(?:upstream|stellar|mt5)\.[a-z_]+$")]

FORBIDDEN_PAYLOAD_KEYS = frozenset({
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "access_token",
    "refresh_token",
    "auth_token",
    "private_key",
    "credentials",
    "backend_url",
})
"""Keys that would leak a secret or a local endpoint (layer design §4.1)."""


def _check_payload(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_PAYLOAD_KEYS:
                raise ValueError(f"payload key {path}{key!r} is not allowed in events")
            _check_payload(item, f"{path}{key}.")
    elif isinstance(value, list):
        for item in value:
            _check_payload(item, path)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"payload value at {path or 'root'} is not finite")


class StellarEvent(StellarModel):
    event_id: Ulid
    schema_version: SchemaVersion = SCHEMA_VERSION
    type: str
    ts: UtcDatetime
    seq: Annotated[int, Field(ge=1)] | None = None
    run_id: RunId | None = None
    station_id: StationId
    source: EventSource
    agent_id: TechnicalId | None = None
    room: Label | None = None
    instrument: InstrumentId | None = None
    correlation_id: str | None = None
    payload: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _canonical_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(f"{value!r} is not a canonical Stellar event name")
        return value

    @field_validator("correlation_id")
    @classmethod
    def _correlation_is_record_id(cls, value: str | None) -> str | None:
        if value is not None and not is_record_id(value):
            raise ValueError("correlation_id must be a Stellar record id")
        return value

    @model_validator(mode="after")
    def _payload_rules(self) -> StellarEvent:
        _check_payload(self.payload, "")
        missing = REQUIRED_PAYLOAD_KEYS.get(self.type, frozenset()) - set(self.payload)
        if missing:
            raise ValueError(f"{self.type} payload is missing {sorted(missing)}")
        return self

    # ------------------------------------------------------------ helpers --

    def to_json(self) -> str:
        """Canonical JSON (sorted keys, no whitespace)."""
        return canonical_json(self.model_dump(mode="json"))

    @classmethod
    def from_json(cls, text: str) -> StellarEvent:
        return cls.model_validate_json(text)

    def content_key(self) -> str:
        """Hash of the event without its ``seq``: identical content, identical key."""
        body = self.model_dump(mode="json")
        body.pop("seq", None)
        return sha256_hex(canonical_json(body))

    def with_seq(self, seq: int) -> StellarEvent:
        return self.model_validate({**self.model_dump(), "seq": seq})


def new_event(
    event_type: str,
    *,
    station_id: str,
    source: str,
    payload: dict[str, Any] | None = None,
    ts: datetime | None = None,
    rng: random.Random | None = None,
    **fields: Any,
) -> StellarEvent:
    """Build a validated event with a fresh ULID. Pass ``ts``/``rng`` for reproducibility."""
    moment = ts if ts is not None else datetime.now(UTC)
    return StellarEvent(
        event_id=new_ulid(moment, rng),
        type=event_type,
        ts=moment,
        station_id=station_id,
        source=source,
        payload=payload or {},
        **fields,
    )
