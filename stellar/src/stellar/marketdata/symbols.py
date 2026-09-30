"""Provider symbol mappings and substitution safety (Foundation §4.2).

A mapping says how a provider's symbol relates to a canonical instrument:

- ``EXACT``: the same instrument (possibly a different price side or source quality).
- ``PROXY``: a different instrument used in its place (a future for spot gold, a
  cash index for an index CFD). Analysis-only at best; never for order levels.
- ``DERIVED``: computed from other data (for example a synthetic cross).
- ``UNSUPPORTED``: the provider has nothing for this instrument.

Proxies and derived series are refused unless the consumer explicitly allows
them, and a permitted proxy is labelled on every bar. An unmapped instrument is
an error, never a guess.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import model_validator

from stellar.schemas.common import InstrumentId, Label, ShortText, StellarModel


class MappingKind(StrEnum):
    EXACT = "EXACT"
    PROXY = "PROXY"
    DERIVED = "DERIVED"
    UNSUPPORTED = "UNSUPPORTED"


class SubstitutionPolicy(StellarModel):
    """What a consumer accepts in place of the exact instrument. Default: nothing."""

    allow_proxy: bool = False
    allow_derived: bool = False

    def permits(self, kind: MappingKind) -> bool:
        if kind is MappingKind.EXACT:
            return True
        if kind is MappingKind.PROXY:
            return self.allow_proxy
        if kind is MappingKind.DERIVED:
            return self.allow_derived
        return False


class ProviderSymbolMapping(StellarModel):
    provider_id: Label
    instrument: InstrumentId
    kind: MappingKind
    provider_symbol: ShortText | None = None
    description: ShortText | None = None

    @model_validator(mode="after")
    def _symbol_matches_kind(self) -> ProviderSymbolMapping:
        if (self.kind is MappingKind.UNSUPPORTED) != (self.provider_symbol is None):
            raise ValueError("a provider symbol is given exactly when the mapping is supported")
        if self.kind in {MappingKind.PROXY, MappingKind.DERIVED} and self.description is None:
            raise ValueError("a proxy or derived mapping must describe what it really is")
        return self

    @property
    def is_substitute(self) -> bool:
        return self.kind in {MappingKind.PROXY, MappingKind.DERIVED}


class SymbolMap:
    """All mappings of one provider, keyed by canonical instrument."""

    def __init__(self, provider_id: str, mappings: Iterable[ProviderSymbolMapping]) -> None:
        by_instrument: dict[InstrumentId, ProviderSymbolMapping] = {}
        for mapping in mappings:
            if mapping.provider_id != provider_id:
                raise ValueError(f"mapping for {mapping.provider_id} given to {provider_id}")
            if mapping.instrument in by_instrument:
                raise ValueError(f"{mapping.instrument} is mapped twice for {provider_id}")
            by_instrument[mapping.instrument] = mapping
        self.provider_id = provider_id
        self._by_instrument = by_instrument

    def get(self, instrument: InstrumentId) -> ProviderSymbolMapping:
        """The declared mapping; an instrument the provider never declared is UNSUPPORTED."""
        return self._by_instrument.get(
            InstrumentId(instrument),
            ProviderSymbolMapping(provider_id=self.provider_id, instrument=instrument,
                                  kind=MappingKind.UNSUPPORTED),
        )

    def mappings(self) -> tuple[ProviderSymbolMapping, ...]:
        return tuple(self._by_instrument.values())


def _ta(instrument: InstrumentId, symbol: str, kind: MappingKind, description: str | None = None):
    return ProviderSymbolMapping(provider_id="tradingagents_yahoo", instrument=instrument,
                                 kind=kind, provider_symbol=symbol, description=description)


TRADINGAGENTS_YAHOO_REFERENCE = SymbolMap("tradingagents_yahoo", (
    _ta(InstrumentId.XAUUSD, "GC=F", MappingKind.PROXY,
        "COMEX gold futures (front month), not spot XAU/USD"),
    _ta(InstrumentId.NAS100, "^NDX", MappingKind.PROXY,
        "Nasdaq-100 cash index, not the NAS100 CFD; no overnight prices"),
    _ta(InstrumentId.EURUSD, "EURUSD=X", MappingKind.EXACT),
    _ta(InstrumentId.USDJPY, "USDJPY=X", MappingKind.EXACT),
))
"""Reference data only: how upstream TradingAgents' ``normalize_symbol`` resolves the
four instruments, classified by Stellar. No Yahoo provider exists in Stellar
(knowledge audit K5, §13); a future adapter must use this classification. A
contract test pins it against upstream."""
