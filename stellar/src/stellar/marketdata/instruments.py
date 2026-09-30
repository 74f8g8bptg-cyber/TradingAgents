"""Canonical Stellar instruments (Foundation §4.2–4.6).

An instrument's identity is Stellar's: its id, display name, asset class and
currencies. Provider symbols live in ``stellar.marketdata.symbols`` and never
redefine it (XAU/USD is not ``GC=F``; NAS100 is not ``^NDX``).

Precision, contract and session details come from the broker or provider at
runtime (Foundation §6: "all execution values come from the broker"). They are
placeholders here, unset by default, and filled with ``with_runtime_metadata``.
No value is invented.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from stellar.schemas.common import (
    INSTRUMENT_DISPLAY_NAMES,
    AssetClass,
    CurrencyCode,
    InstrumentId,
    PositiveDecimal,
    ShortText,
    StellarModel,
)

MetadataSource = Literal["unset", "broker", "provider", "owner"]


class PrecisionSpec(StellarModel):
    """Price precision. ``None`` until a broker or provider declares it."""

    price_decimals: int | None = Field(default=None, ge=0, le=12)
    source: MetadataSource = "unset"

    @model_validator(mode="after")
    def _source_when_set(self) -> PrecisionSpec:
        if (self.price_decimals is None) != (self.source == "unset"):
            raise ValueError("price_decimals is set exactly when its source is named")
        return self


class ContractSpec(StellarModel):
    """Quantity / contract metadata placeholder, filled from the broker (Phase 4 / 8)."""

    contract_size: PositiveDecimal | None = None
    tick_size: PositiveDecimal | None = None
    lot_step: PositiveDecimal | None = None
    min_volume: PositiveDecimal | None = None
    max_volume: PositiveDecimal | None = None
    source: MetadataSource = "unset"


class SessionSpec(StellarModel):
    """Timezone / session placeholder. Session calendars are not implemented in Phase 2."""

    timezone: ShortText | None = None
    calendar_id: ShortText | None = None
    source: MetadataSource = "unset"


class InstrumentSpec(StellarModel):
    instrument_id: InstrumentId
    display_name: str
    asset_class: AssetClass
    base_currency: CurrencyCode | None = None
    quote_currency: CurrencyCode
    precision: PrecisionSpec = PrecisionSpec()
    contract: ContractSpec = ContractSpec()
    session: SessionSpec = SessionSpec()

    @model_validator(mode="after")
    def _display_name_is_canonical(self) -> InstrumentSpec:
        expected = INSTRUMENT_DISPLAY_NAMES[self.instrument_id]
        if self.display_name != expected:
            raise ValueError(f"{self.instrument_id} is displayed as {expected!r}")
        return self

    def with_runtime_metadata(
        self,
        *,
        precision: PrecisionSpec | None = None,
        contract: ContractSpec | None = None,
        session: SessionSpec | None = None,
    ) -> InstrumentSpec:
        """A copy with broker/provider metadata applied; identity is unchanged."""
        data = self.model_dump()
        if precision is not None:
            data["precision"] = precision.model_dump()
        if contract is not None:
            data["contract"] = contract.model_dump()
        if session is not None:
            data["session"] = session.model_dump()
        return InstrumentSpec.model_validate(data)


INSTRUMENTS: dict[InstrumentId, InstrumentSpec] = {
    InstrumentId.XAUUSD: InstrumentSpec(
        instrument_id=InstrumentId.XAUUSD, display_name="XAU/USD", asset_class=AssetClass.METAL,
        base_currency="XAU", quote_currency="USD"),
    InstrumentId.EURUSD: InstrumentSpec(
        instrument_id=InstrumentId.EURUSD, display_name="EUR/USD", asset_class=AssetClass.FX,
        base_currency="EUR", quote_currency="USD"),
    InstrumentId.USDJPY: InstrumentSpec(
        instrument_id=InstrumentId.USDJPY, display_name="USD/JPY", asset_class=AssetClass.FX,
        base_currency="USD", quote_currency="JPY"),
    InstrumentId.NAS100: InstrumentSpec(
        instrument_id=InstrumentId.NAS100, display_name="NAS100",
        asset_class=AssetClass.INDEX_CFD, base_currency=None, quote_currency="USD"),
}


def _check_registry() -> None:
    if set(INSTRUMENTS) != set(InstrumentId):  # pragma: no cover - guarded by tests
        raise RuntimeError("every canonical instrument needs exactly one InstrumentSpec")


_check_registry()


def get_instrument(value: InstrumentId | str) -> InstrumentSpec:
    """The canonical spec for a canonical id. Display names and provider symbols are refused."""
    try:
        return INSTRUMENTS[InstrumentId(value)]
    except ValueError:
        raise KeyError(
            f"{value!r} is not a canonical Stellar instrument id "
            f"({[i.value for i in InstrumentId]}); provider symbols are never accepted here"
        ) from None
