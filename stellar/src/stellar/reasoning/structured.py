"""Structured LLM calls: schema-validated output, explicit retries, a full call record.

``call_structured`` sends one request and accepts the answer only if all of these hold:
1. it is exactly one JSON object;
2. it validates against the role's closed schema (unknown fields, unknown enum values and
   wrong types are rejected, not coerced; numbers parse as Decimal);
3. every evidence id it cites was offered in this call (no invented evidence).

Failures are typed (``FailureKind``):
- ``PROVIDER_UNAVAILABLE``, ``TIMEOUT`` and ``MALFORMED_OUTPUT`` may be retried, up to
  ``max_attempts``;
- ``UNSUPPORTED_MODEL`` is not retried.

There is no fallback to prose and no silent default: a failed call returns no output.

The ``AgentCallRecord`` is the call's provenance:
- role, prompt version and template hash, model, schema, ``as_of`` and the input fingerprint;
- attempts, the hashes of every raw response, the output hash;
- usage summed over attempts: ``None`` whenever a provider did not report it.

No prompt text, secret or raw response body is stored in the record.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, ValidationError

from stellar.reasoning.prompts import PromptTemplate
from stellar.reasoning.provider import (
    RETRYABLE,
    FailureKind,
    LlmRequest,
    LlmUsage,
    ModelSpec,
    ProviderFailure,
    ReasoningProvider,
    UntrustedBlock,
)
from stellar.schemas.common import Label, RunId, Sha256Hex, StellarModel, TechnicalId, UtcDatetime
from stellar.serialization import canonical_json, content_hash, sha256_hex


class CallStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentCallRecord(StellarModel):
    run_id: RunId | None = None
    role: TechnicalId
    prompt_version: Label
    prompt_hash: Sha256Hex
    input_fingerprint: Sha256Hex
    model: ModelSpec
    schema_name: Label
    schema_version: Label
    as_of: UtcDatetime
    status: CallStatus
    failure: FailureKind | None = None
    failure_detail: Label | None = None
    attempts: int = Field(ge=0)
    response_hashes: tuple[Sha256Hex, ...] = ()
    output_hash: Sha256Hex | None = None
    usage: LlmUsage = LlmUsage()


def fingerprint(template: PromptTemplate, model: ModelSpec, as_of: datetime, trusted: Any,
                untrusted: Sequence[UntrustedBlock]) -> str:
    """The exact identity of a call: same fingerprint → the same question to the same model."""
    return content_hash({"role": template.role, "template": template.template_hash(),
                         "model": model.model_dump(mode="json"), "as_of": as_of.isoformat(),
                         "trusted": trusted,
                         "untrusted": [b.model_dump(mode="json") for b in untrusted]})


def _sum(values):
    values = list(values)
    return None if not values or any(v is None for v in values) else sum(values)


def _parse(text: str, schema: type[StellarModel], allowed: set[str]) -> tuple[Any, str | None]:
    try:
        data = json.loads(text.strip(), parse_float=Decimal)
    except json.JSONDecodeError:
        return None, "not_json"
    if not isinstance(data, dict):
        return None, "not_an_object"
    try:
        output = schema.model_validate(data)
    except ValidationError:
        return None, "schema_mismatch"
    unknown = output.cited_evidence_ids() - allowed  # type: ignore[attr-defined]
    if unknown:
        return None, "unknown_evidence_id"
    return output, None


def call_structured(provider: ReasoningProvider, template: PromptTemplate, *, role: str,
                    model: ModelSpec, as_of: datetime, trusted: Any,
                    untrusted: Sequence[UntrustedBlock] = (), schema: type[StellarModel],
                    allowed_evidence: set[str], max_attempts: int, run_id: str | None = None,
                    timeout_seconds: int | None = None) -> tuple[Any, AgentCallRecord]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    fp = fingerprint(template, model, as_of, trusted, untrusted)
    base = {"run_id": run_id, "role": role, "prompt_version": template.version,
            "prompt_hash": template.template_hash(), "input_fingerprint": fp, "model": model,
            "schema_name": template.output_schema, "schema_version": template.output_schema_version,
            "as_of": as_of}
    if not provider.supports(model):
        return None, AgentCallRecord(**base, status=CallStatus.FAILED,
                                     failure=FailureKind.UNSUPPORTED_MODEL, attempts=0)
    request = LlmRequest(role=role, model=model, system=template.system,
                         task=canonical_json(trusted), untrusted=tuple(untrusted),
                         schema_name=template.output_schema,
                         schema_version=template.output_schema_version,
                         timeout_seconds=timeout_seconds)
    hashes: list[str] = []
    usages: list[LlmUsage] = []
    failure, detail = FailureKind.MALFORMED_OUTPUT, None
    for attempt in range(1, max_attempts + 1):
        try:
            response = provider.complete(request)
        except ProviderFailure as exc:
            failure, detail = exc.kind, None
            if exc.kind not in RETRYABLE:
                break
            continue
        hashes.append(sha256_hex(response.text))
        usages.append(response.usage)
        output, problem = _parse(response.text, schema, allowed_evidence)
        if output is not None:
            usage = _usage(usages)
            return output, AgentCallRecord(
                **base, status=CallStatus.COMPLETED, attempts=attempt,
                response_hashes=tuple(hashes),
                output_hash=content_hash(output.model_dump(mode="json")), usage=usage)
        failure, detail = FailureKind.MALFORMED_OUTPUT, problem
    return None, AgentCallRecord(**base, status=CallStatus.FAILED, failure=failure,
                                 failure_detail=detail, attempts=attempt,
                                 response_hashes=tuple(hashes), usage=_usage(usages))


def _usage(usages: Sequence[LlmUsage]) -> LlmUsage:
    currencies = {u.cost_currency for u in usages}
    return LlmUsage(input_tokens=_sum(u.input_tokens for u in usages),
                    output_tokens=_sum(u.output_tokens for u in usages),
                    cost=_sum(u.cost for u in usages) if len(currencies) == 1 else None,
                    cost_currency=currencies.pop() if len(currencies) == 1 else None,
                    latency_ms=_sum(u.latency_ms for u in usages))

