"""Workflow configuration: which roles run, with which models, under which budget.

Routing is typed configuration, never model output: no LLM can add a role, enable a role or
change a permission.

**LLM enablement (D-11).**
- Budgets are required configuration. With ``llm_enabled = False`` (the default), every LLM
  role is SKIPPED (``llm_disabled``) and only the deterministic parts run (research
  validation, technical evidence, contradiction checks, evidence quality).
- Enabling LLM roles requires an explicit ``budget``. No spending limit is invented: the
  budget is a call count the owner sets (tests use labelled test values).

**Roles** (Phase 1 registry ids; nothing is renamed):
- V4 ``claim_classifier`` (only when some claims lack declared labels);
- M1 ``causal_macro_analyst``;
- the focus instrument's specialist (``specialist_xauusd`` … ``specialist_nas100``; only
  that one runs);
- U1 ``bull_researcher`` and U2 ``bear_researcher`` (``debate_rounds``);
- P2 ``contradiction_checker`` (deterministic);
- U3 ``research_manager``.

``optional_roles`` may fail without failing the run; ``disabled_roles`` (optional ones only)
are skipped.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from stellar.agents import default_registry
from stellar.reasoning.provider import ModelSpec
from stellar.schemas.common import InstrumentId, Label, StellarModel, TechnicalId
from stellar.schemas.research import ResearchRole
from stellar.serialization import content_hash

SPECIALISTS: dict[InstrumentId, str] = {
    InstrumentId.XAUUSD: "specialist_xauusd",
    InstrumentId.EURUSD: "specialist_eurusd",
    InstrumentId.USDJPY: "specialist_usdjpy",
    InstrumentId.NAS100: "specialist_nas100",
}
LLM_ROLES = ("claim_classifier", "causal_macro_analyst", *SPECIALISTS.values(),
             "bull_researcher", "bear_researcher", "research_manager")
DETERMINISTIC_ROLES = ("research_validation", "contradiction_checker")


class LlmBudget(StellarModel):
    max_calls_per_run: int = Field(ge=1)
    test_only: bool = False


class WorkflowConfig(StellarModel):
    version: Label = "unset"
    test_only: bool = False
    llm_enabled: bool = False
    budget: LlmBudget | None = None
    models: dict[TechnicalId, ModelSpec] = {}
    max_attempts: int = Field(default=1, ge=1, le=5)
    """Attempts per call (retries only for unavailable, timeout or malformed output)."""
    timeout_seconds: int | None = Field(default=None, ge=1)
    debate_rounds: int = Field(default=1, ge=1, le=5)
    optional_roles: tuple[TechnicalId, ...] = ()
    disabled_roles: tuple[TechnicalId, ...] = ()
    required_research_roles: tuple[ResearchRole, ...] = ()
    """Research roles whose absence is reported as missing evidence (coverage)."""

    @model_validator(mode="after")
    def _consistent(self) -> WorkflowConfig:
        known = {a.technical_id for a in default_registry()}
        for role in (*self.models, *self.optional_roles, *self.disabled_roles):
            if role not in known:
                raise ValueError(f"{role} is not a registered agent")
            if role not in LLM_ROLES:
                raise ValueError(f"{role} is not an LLM role of this pipeline")
        if not set(self.disabled_roles) <= set(self.optional_roles):
            raise ValueError("only optional roles can be disabled")
        if self.llm_enabled and self.budget is None:
            raise ValueError("LLM roles need an explicit budget (D-11)")
        return self

    def config_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
