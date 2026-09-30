"""Execution values are typed fields, never hidden in prose.

Every field of the proposal, decision, order and result contracts is inspected:
prices, volumes and ratios must be Decimal, and any text field must be an id,
a closed label or a bounded, non-decision field on an explicit allowlist.
"""

import typing
from decimal import Decimal
from enum import Enum

import pytest
from factories import make_intent, make_proposal
from pydantic import BaseModel, ValidationError
from stellar.schemas import (
    AdvisoryLevels,
    EntrySpec,
    ExecutionResult,
    OrderIntent,
    PriceLevel,
    RiskCheck,
    RiskDecision,
    TradeProposal,
)

pytestmark = pytest.mark.unit

EXECUTION_CONTRACTS = [TradeProposal, EntrySpec, PriceLevel, AdvisoryLevels, RiskDecision,
                       RiskCheck, OrderIntent, ExecutionResult]

NUMERIC_FIELDS = {
    "TradeProposal": {"size_factor", "reward_risk"},
    "EntrySpec": {"price", "zone_low", "zone_high"},
    "PriceLevel": {"price"},
    "AdvisoryLevels": {"entry", "stop"},
    "RiskDecision": {"volume", "risk_pct_equity"},
    "RiskCheck": {"value", "limit"},
    "OrderIntent": {"volume", "price", "stop_loss", "take_profit", "max_slippage"},
    "ExecutionResult": {"requested_volume", "filled_volume", "fill_price", "slippage"},
}

# Text fields that are allowed: ids (pattern-checked), hashes, labels (pattern-checked)
# and bounded fields that no decision reads.
ALLOWED_TEXT_FIELDS = {
    "TradeProposal": {"schema_version", "proposal_id", "run_id", "snapshot_id", "setup_id",
                      "profile", "report_hashes"},
    "PriceLevel": {"basis"},
    "RiskDecision": {"schema_version", "decision_id", "proposal_id", "run_id"},
    "OrderIntent": {"schema_version", "intent_id", "proposal_id", "decision_id",
                    "broker_symbol", "idempotency_key"},
    "ExecutionResult": {"schema_version", "order_id", "intent_id", "fill_id", "reason",
                        "broker_ticket"},
}


def _leaf_types(annotation):
    args = typing.get_args(annotation)
    if typing.get_origin(annotation) is typing.Annotated:
        return _leaf_types(args[0])
    if args:
        return {t for a in args for t in _leaf_types(a)}
    return {annotation}


@pytest.mark.parametrize("model", EXECUTION_CONTRACTS, ids=lambda m: m.__name__)
def test_numeric_execution_fields_are_decimal(model):
    for name in NUMERIC_FIELDS.get(model.__name__, set()):
        leaves = _leaf_types(model.model_fields[name].annotation) - {type(None)}
        assert leaves == {Decimal}, (model.__name__, name, leaves)


@pytest.mark.parametrize("model", EXECUTION_CONTRACTS, ids=lambda m: m.__name__)
def test_text_fields_are_on_the_allowlist(model):
    allowed = ALLOWED_TEXT_FIELDS.get(model.__name__, set())
    for name, field in model.model_fields.items():
        leaves = _leaf_types(field.annotation)
        if str in leaves and not any(isinstance(t, type) and issubclass(t, Enum) for t in leaves):
            assert name in allowed, f"{model.__name__}.{name} is free text"


def test_no_free_form_notes_field_can_carry_levels():
    for model in (TradeProposal, OrderIntent, RiskDecision, ExecutionResult):
        assert model.model_config["extra"] == "forbid"
        assert not {"notes", "comment", "text", "description"} & set(model.model_fields)
    with pytest.raises(ValidationError):
        make_intent(comment="sell 1 lot at 2400, stop 2412")


def test_levels_are_rejected_when_given_as_prose():
    for value in ("2400 or so", "market", "2,400.00"):
        with pytest.raises(ValidationError):
            make_proposal(stop_loss={"price": value, "basis": "x"})
    with pytest.raises(ValidationError):
        make_proposal(stop_loss={"price": "2412", "basis": "stop above 2412"})


def test_labels_are_machine_tokens_not_sentences():
    with pytest.raises(ValidationError):
        PriceLevel(price="1", basis="Stop at the swing high")
    assert issubclass(PriceLevel, BaseModel)
