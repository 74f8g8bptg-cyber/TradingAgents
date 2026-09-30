"""Stable identifiers.

Event ids are ULIDs (layer design §4.2): 26 Crockford base-32 characters,
sortable by creation time. Record ids are ``<prefix>_<token>``; the prefix names
the kind of record along the identity chain (Foundation §9.2), so an id pasted
into the wrong field is rejected instead of silently linking the wrong records.

Time and randomness are injectable so tests and replays are reproducible.
"""

from __future__ import annotations

import random
import re
import secrets
from datetime import UTC, datetime
from enum import StrEnum

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
ID_TOKEN = r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}"


class IdKind(StrEnum):
    """Record kinds along the identity chain and their id prefixes."""

    RESEARCH_ITEM = "ri"
    CLAIM = "clm"
    CLAIM_VALIDATION = "val"
    RESEARCH_SNAPSHOT = "rsnap"
    SNAPSHOT = "snap"
    SETUP = "setup"
    ANALYSIS = "an"
    RUN = "run"
    PROPOSAL = "prop"
    DECISION = "dec"
    INTENT = "int"
    ORDER = "ord"
    FILL = "fill"
    TRADE = "trade"
    REVIEW = "rev"
    SETTLEMENT = "stl"
    POSITION = "pos"  # Phase 4 addition: paper broker positions


def id_pattern(kind: IdKind) -> re.Pattern[str]:
    return re.compile(rf"^{kind.value}_{ID_TOKEN}$")


def new_ulid(now: datetime | None = None, rng: random.Random | None = None) -> str:
    """A ULID for ``now`` (UTC). Pass ``rng`` for reproducible ids in tests."""
    moment = now if now is not None else datetime.now(UTC)
    if moment.tzinfo is None:
        raise ValueError("ULID time must be timezone-aware")
    millis = int(moment.timestamp() * 1000)
    if not 0 <= millis < 2**48:
        raise ValueError("ULID time out of range")
    entropy = rng.getrandbits(80) if rng is not None else secrets.randbits(80)
    value = (millis << 80) | entropy
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_id(kind: IdKind, now: datetime | None = None, rng: random.Random | None = None) -> str:
    """A new record id such as ``prop_01J8Z6Q3T6V4Y1M2N3P4Q5R6S7``."""
    return f"{kind.value}_{new_ulid(now, rng)}"
