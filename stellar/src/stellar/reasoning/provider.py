"""The provider-independent LLM boundary (layer design principle 7: model-provider agnostic).

A ``ReasoningProvider`` turns one ``LlmRequest`` into one ``LlmResponse`` (text + usage), or
raises ``ProviderFailure`` with a typed kind. Nothing here names a vendor or opens a network
connection. A production adapter (for example over the upstream ``llm_clients`` layer, audit
§8) implements this protocol elsewhere; Phase 6 ships only the interface and a
deterministic ``ScriptedProvider`` for tests.

The request keeps **trusted** content (the role's system text and the typed task inputs)
apart from **untrusted** content (research excerpts, source text): the untrusted blocks are
data and are never merged into instructions (see ``prompts``).

Usage (tokens, cost, latency) is recorded when the provider reports it, and ``None``
otherwise. No price is invented.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import Field, StringConstraints

from stellar.schemas.common import CurrencyCode, Label, ShortText, StellarModel, TechnicalId


class FailureKind(StrEnum):
    LLM_DISABLED = "llm_disabled"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    MALFORMED_OUTPUT = "malformed_output"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VALIDATION_FAILURE = "validation_failure"
    STALE_EVIDENCE = "stale_evidence"
    CONTRADICTION_UNRESOLVED = "contradiction_unresolved"
    BUDGET_UNAVAILABLE = "budget_unavailable"
    BUDGET_EXHAUSTED = "budget_exhausted"
    UNSUPPORTED_MODEL = "unsupported_model"
    DEPENDENCY_FAILED = "dependency_failed"


RETRYABLE = frozenset({FailureKind.PROVIDER_UNAVAILABLE, FailureKind.TIMEOUT,
                       FailureKind.MALFORMED_OUTPUT})


class ProviderFailure(Exception):
    def __init__(self, kind: FailureKind, detail: str = "") -> None:
        self.kind = kind
        super().__init__(f"{kind.value}: {detail}" if detail else kind.value)


class ModelSpec(StellarModel):
    provider: Label
    model: ShortText
    version: ShortText | None = None


UntrustedText = Annotated[str, StringConstraints(max_length=8000)]


class UntrustedBlock(StellarModel):
    """Source content handed to a model as data. It carries no authority."""

    ref: ShortText
    content: UntrustedText


class LlmRequest(StellarModel):
    role: TechnicalId
    model: ModelSpec
    system: str
    task: str
    """Canonical JSON of the trusted, typed task inputs."""
    untrusted: tuple[UntrustedBlock, ...] = ()
    schema_name: Label
    schema_version: Label
    timeout_seconds: int | None = Field(default=None, ge=1)


class LlmUsage(StellarModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: CurrencyCode | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class LlmResponse(StellarModel):
    text: str
    usage: LlmUsage = LlmUsage()


class ReasoningProvider(Protocol):
    provider_id: str

    def supports(self, model: ModelSpec) -> bool: ...

    def complete(self, request: LlmRequest) -> LlmResponse: ...


Script = Callable[[LlmRequest], "str | LlmResponse | ProviderFailure"]


class ScriptedProvider:
    """A deterministic fake provider for tests: no network, no randomness.

    ``script`` maps a role's technical id to a list of replies consumed in order (a reply
    may be text, an ``LlmResponse`` or a ``ProviderFailure`` to raise), or is a callable
    of the request. Every request is kept in ``requests`` for inspection.
    """

    provider_id = "scripted"

    def __init__(self, script: dict[str, list] | Script, *,
                 models: frozenset[str] = frozenset({"scripted-model"})) -> None:
        self._script = script
        self._models = models
        self.requests: list[LlmRequest] = []

    def supports(self, model: ModelSpec) -> bool:
        return model.provider == self.provider_id and model.model in self._models

    def complete(self, request: LlmRequest) -> LlmResponse:
        self.requests.append(request)
        if callable(self._script):
            reply = self._script(request)
        else:
            queue = self._script.get(request.role)
            if not queue:
                raise ProviderFailure(FailureKind.PROVIDER_UNAVAILABLE, "no scripted reply")
            reply = queue.pop(0)
        if isinstance(reply, ProviderFailure):
            raise reply
        if isinstance(reply, LlmResponse):
            return reply
        return LlmResponse(text=reply, usage=LlmUsage(input_tokens=len(request.task),
                                                      output_tokens=len(reply)))
