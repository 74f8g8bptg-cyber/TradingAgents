"""Canonical instruments, provider mappings, substitution policy and timeframes."""

from datetime import timedelta

import pytest
from pydantic import ValidationError
from stellar.config import StellarConfig
from stellar.marketdata import (
    DURATIONS,
    INSTRUMENTS,
    TRADINGAGENTS_YAHOO_REFERENCE,
    MappingKind,
    PrecisionSpec,
    ProviderSymbolMapping,
    SubstitutionPolicy,
    SymbolMap,
    duration,
    get_instrument,
    parse_timeframe,
)
from stellar.marketdata.timeframes import intervals_between
from stellar.schemas.common import InstrumentId
from stellar.schemas.market import Timeframe

pytestmark = pytest.mark.unit

# --- canonical instruments -----------------------------------------------------


def test_registry_holds_the_four_canonical_instruments():
    assert set(INSTRUMENTS) == set(InstrumentId)
    assert [INSTRUMENTS[i].display_name for i in InstrumentId] == [
        "XAU/USD", "EUR/USD", "USD/JPY", "NAS100"]
    assert get_instrument("XAUUSD").asset_class == "metal"
    assert get_instrument("NAS100").base_currency is None
    assert get_instrument("USDJPY").quote_currency == "JPY"


def test_registry_agrees_with_the_phase1_config_defaults():
    for record in StellarConfig().instruments:
        spec = INSTRUMENTS[record.instrument_id]
        assert (spec.display_name, spec.asset_class, spec.base_currency, spec.quote_currency) == (
            record.display_name, record.asset_class, record.base_currency, record.quote_currency)


@pytest.mark.parametrize("value", ["XAU/USD", "GC=F", "^NDX", "EURUSD=X", "gold", "BTCUSD"])
def test_provider_symbols_and_display_names_are_not_instrument_ids(value):
    with pytest.raises(KeyError, match="canonical"):
        get_instrument(value)


def test_runtime_metadata_is_unset_until_declared_and_never_changes_identity():
    spec = get_instrument("EURUSD")
    assert spec.precision.price_decimals is None and spec.precision.source == "unset"
    assert spec.contract.contract_size is None and spec.session.timezone is None
    updated = spec.with_runtime_metadata(precision=PrecisionSpec(price_decimals=5,
                                                                 source="broker"))
    assert updated.precision.price_decimals == 5
    assert updated.instrument_id == spec.instrument_id and updated.display_name == "EUR/USD"
    with pytest.raises(ValidationError):
        PrecisionSpec(price_decimals=5)  # a value needs a named source
    with pytest.raises(ValidationError, match="displayed as"):
        type(spec).model_validate({**spec.model_dump(), "display_name": "Euro"})


# --- mappings -------------------------------------------------------------------


def test_mapping_kinds_and_their_rules():
    exact = ProviderSymbolMapping(provider_id="p", instrument="EURUSD", kind="EXACT",
                                  provider_symbol="EURUSD")
    assert not exact.is_substitute
    with pytest.raises(ValidationError, match="describe"):
        ProviderSymbolMapping(provider_id="p", instrument="XAUUSD", kind="PROXY",
                              provider_symbol="GC=F")
    with pytest.raises(ValidationError, match="supported"):
        ProviderSymbolMapping(provider_id="p", instrument="XAUUSD", kind="UNSUPPORTED",
                              provider_symbol="GC=F")
    with pytest.raises(ValidationError, match="supported"):
        ProviderSymbolMapping(provider_id="p", instrument="XAUUSD", kind="EXACT")


def test_symbol_map_treats_undeclared_instruments_as_unsupported():
    symbols = SymbolMap("p", [ProviderSymbolMapping(provider_id="p", instrument="EURUSD",
                                                    kind="EXACT", provider_symbol="EURUSD")])
    assert symbols.get("NAS100").kind is MappingKind.UNSUPPORTED
    with pytest.raises(ValueError, match="twice"):
        SymbolMap("p", [symbols.get("EURUSD"), symbols.get("EURUSD")])
    with pytest.raises(ValueError, match="given to"):
        SymbolMap("q", symbols.mappings())


def test_substitution_policy_defaults_to_exact_only():
    policy = SubstitutionPolicy()
    assert policy.permits(MappingKind.EXACT)
    assert not policy.permits(MappingKind.PROXY)
    assert not policy.permits(MappingKind.DERIVED)
    assert not SubstitutionPolicy(allow_proxy=True, allow_derived=True).permits(
        MappingKind.UNSUPPORTED)


def test_tradingagents_reference_classifies_its_substitutions_as_proxies():
    ref = TRADINGAGENTS_YAHOO_REFERENCE
    assert (ref.get("XAUUSD").provider_symbol, ref.get("XAUUSD").kind) == ("GC=F", "PROXY")
    assert (ref.get("NAS100").provider_symbol, ref.get("NAS100").kind) == ("^NDX", "PROXY")
    assert ref.get("EURUSD").kind is MappingKind.EXACT


# --- timeframes ------------------------------------------------------------------


def test_every_timeframe_has_a_duration():
    assert set(DURATIONS) == set(Timeframe)
    assert duration(Timeframe.M1) == timedelta(minutes=1)
    assert duration(Timeframe.M15) == timedelta(minutes=15)
    assert duration(Timeframe.H4) == timedelta(hours=4)
    assert duration(Timeframe.D1) == timedelta(days=1)
    for required in ("M1", "M5", "M15", "H1", "H4", "D1"):
        assert required in Timeframe.__members__


@pytest.mark.parametrize("text,expected", [("H1", "H1"), ("h1", "H1"), ("1h", "H1"),
                                           ("m15", "M15"), ("15m", "M15"), ("4H", "H4"),
                                           ("1d", "D1"), (" D1 ", "D1")])
def test_timeframe_parsing(text, expected):
    assert parse_timeframe(text) is Timeframe(expected)


@pytest.mark.parametrize("text", ["2h", "H2", "hourly", "", "60"])
def test_unknown_timeframes_are_rejected(text):
    with pytest.raises(ValueError, match="unknown timeframe"):
        parse_timeframe(text)


def test_intervals_between():
    from datetime import UTC, datetime

    t = datetime(2030, 1, 1, tzinfo=UTC)
    assert intervals_between(t, t + timedelta(hours=3, minutes=30), Timeframe.H1) == 3
    assert intervals_between(t, t, Timeframe.H1) == 0
    assert intervals_between(t + timedelta(hours=1), t, Timeframe.H1) == 0
