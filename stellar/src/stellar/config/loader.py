"""Load Stellar configuration from a local TOML file (Foundation §4.26).

Loaded once at start; an invalid file raises ``ConfigError`` and nothing runs.
There is deliberately no environment-variable overlay for settings such as the
execution mode: the file is the single, hashable source.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from stellar.config.models import StellarConfig


class ConfigError(ValueError):
    """The configuration is missing, unreadable or invalid."""


def load_config(path: str | Path | None = None) -> StellarConfig:
    """Load and validate configuration; ``None`` returns the explicit defaults."""
    if path is None:
        return StellarConfig()
    source = Path(path)
    try:
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read Stellar config {source}: {exc}") from exc
    return parse_config(data)


def parse_config(data: dict) -> StellarConfig:
    try:
        return StellarConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid Stellar config: {exc}") from exc
