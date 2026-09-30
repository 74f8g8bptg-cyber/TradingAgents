"""Deterministic serialization shared by events, the journal and config hashing.

The same object always serializes to the same bytes: keys sorted, no
insignificant whitespace, no NaN or infinity. Decimals travel as strings (via
pydantic's JSON mode), so no value is ever rounded through a float.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible data (or a pydantic model) canonically."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(text: str) -> str:
    """Hex SHA-256 of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(value: Any) -> str:
    """Hash of the canonical JSON form of ``value``."""
    return sha256_hex(canonical_json(value))
