"""The U4 Trader's structured output, prompt and configuration.

The Trader interprets a READY_FOR_PROPOSAL setup and **selects** among the setup's own
evidence-derived options. It cannot create a level:
- ``TraderSelectionOutput`` has **no numeric field**. Entry, stop and targets are option ids;
  a price, size, percentage or pip value in the reply is an unknown field and the whole reply
  is rejected (the schema is closed);
- every option id and evidence id it cites must have been offered in the call;
- ``direction`` is LONG / SHORT / NONE and must equal the setup's direction. "BUY", "SELL",
  "Hold" or any other word is not a direction and is rejected;
- ``rationale`` and ``risks`` are narrative. Nothing reads a number from them.

Upstream reuse (audit K51 / L4): only the *concept* of a Trader transaction view is reused.
Upstream's ``TraderProposal`` levels are floats parsed from rendered text; Stellar parses no
numeric level from any text, so ``llm_levels_advisory`` stays empty.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stellar.pipeline.config import LlmBudget
from stellar.reasoning.contracts import EvidenceRef, ModelConfidence, Refs, Text
from stellar.reasoning.prompts import PromptTemplate
from stellar.reasoning.provider import ModelSpec
from stellar.schemas.common import Label, SetupId, StellarModel
from stellar.serialization import content_hash
from stellar.setups.models import SetupDirection

TRADER_ROLE = "trader"
PROMPT_VERSION = "p6b_1"
SCHEMA_VERSION = "s6b_1"


class TraderDecision(StrEnum):
    SELECT = "SELECT"
    DECLINE = "DECLINE"


class TraderSelectionOutput(StellarModel):
    setup_id: SetupId
    direction: SetupDirection
    decision: TraderDecision
    entry_option_id: EvidenceRef | None = None
    stop_option_id: EvidenceRef | None = None
    target_option_ids: tuple[EvidenceRef, ...] = Field(default=(), max_length=16)
    evidence_ids: Refs = ()
    rationale: Text
    risks: tuple[Text, ...] = ()
    self_reported_confidence: ModelConfidence | None = None
    """Metadata only. Never evidence quality, never a threshold."""

    @model_validator(mode="after")
    def _consistent(self) -> TraderSelectionOutput:
        chosen = (self.entry_option_id, self.stop_option_id, *self.target_option_ids)
        if self.decision is TraderDecision.SELECT:
            if self.entry_option_id is None or self.stop_option_id is None or \
                    not self.target_option_ids:
                raise ValueError("SELECT names an entry, a stop and at least one target")
        elif any(x is not None for x in chosen):
            raise ValueError("DECLINE selects nothing")
        if len(set(self.target_option_ids)) != len(self.target_option_ids):
            raise ValueError("target options must not repeat")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence ids must not repeat")
        return self

    def cited_evidence_ids(self) -> set[str]:
        return {x for x in (self.entry_option_id, self.stop_option_id, *self.target_option_ids,
                            *self.evidence_ids) if x is not None}


TRADER_TEMPLATE = PromptTemplate(
    role=TRADER_ROLE, version=PROMPT_VERSION, output_schema="trader_selection",
    output_schema_version=SCHEMA_VERSION,
    charter="Review one deterministic setup and the research decision support. Either SELECT "
            "one entry option, one stop option and one or more target options, citing only the "
            "option ids given, or DECLINE. You cannot create, move or state a price, level, "
            "size or order; options are the only levels. Repeat the setup's direction exactly "
            "(LONG or SHORT). Explain the choice and its risks in words.")


class TraderConfig(StellarModel):
    """U4 routing. LLM use is off by default and needs an explicit budget and model (D-11)."""

    version: Label = "unset"
    test_only: bool = False
    llm_enabled: bool = False
    budget: LlmBudget | None = None
    model: ModelSpec | None = None
    max_attempts: int = Field(default=1, ge=1, le=5)
    timeout_seconds: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _consistent(self) -> TraderConfig:
        if self.llm_enabled and (self.budget is None or self.model is None):
            raise ValueError("the Trader LLM needs an explicit budget and model (D-11)")
        return self

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
