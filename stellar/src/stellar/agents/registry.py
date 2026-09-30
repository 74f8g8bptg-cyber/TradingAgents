"""Agent identity registry (Foundation §4.20).

Technical identity only: stable ``technical_id`` values, roles, groups,
responsibilities and roster status. Visual personas are separate: a display name
is optional, set per installation, and never used as a key (visual plan §5,
VX-3). Nothing here runs an agent.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from stellar.schemas.common import ShortText, StellarModel, TechnicalId


class AgentGroup(StrEnum):
    RESEARCH = "research"
    RESEARCH_VALIDATION = "research_validation"
    MACRO_ANALYSIS = "macro_analysis"
    MARKET_ANALYSIS = "market_analysis"
    TECHNICAL = "technical"
    DEBATE = "debate"
    DECISION = "decision"
    PROPOSAL = "proposal"
    VALIDATION = "validation"
    RISK = "risk"
    EXECUTION_VALIDATION = "execution_validation"
    EXECUTION = "execution"
    REVIEW = "review"
    OPERATIONAL = "operational"


class AgentKind(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HYBRID = "hybrid"
    """Deterministic code plus an LLM step (e.g. retrieval + LLM extraction)."""


class AgentSource(StrEnum):
    STELLAR = "STELLAR"
    UPSTREAM = "UPSTREAM"


class LlmTier(StrEnum):
    QUICK = "quick"
    DEEP = "deep"
    CONFIGURABLE = "configurable"


class RosterStatus(StrEnum):
    """Foundation §5.2 / §5.3."""

    MINIMUM_V1 = "minimum_v1"
    DEFERRED = "deferred"
    DEMO_GATE = "demo_gate"
    """Joins only at the Phase 8 MT5 / Vantage demo gate (E2)."""


_DETERMINISTIC_GROUPS = frozenset(
    {AgentGroup.RISK, AgentGroup.EXECUTION, AgentGroup.EXECUTION_VALIDATION}
)
"""No LLM may sit in these groups (layer design §3.1; Foundation §8.4)."""

AgentCode = Annotated[str, StringConstraints(pattern=r"^[RVMSTUPELO][0-9]$")]


class AgentIdentity(StellarModel):
    code: AgentCode
    technical_id: TechnicalId
    role: ShortText
    group: AgentGroup
    responsibilities: tuple[ShortText, ...] = Field(min_length=1)
    kind: AgentKind
    source: AgentSource
    llm_tier: LlmTier | None = None
    roster_status: RosterStatus
    enabled: bool
    upstream_node: ShortText | None = None
    display_name: ShortText | None = None

    @model_validator(mode="after")
    def _consistent(self) -> AgentIdentity:
        if self.kind is AgentKind.DETERMINISTIC and self.llm_tier is not None:
            raise ValueError("a deterministic agent has no LLM tier")
        if self.source is AgentSource.UPSTREAM:
            if self.upstream_node is None or not self.code.startswith("U"):
                raise ValueError("an upstream agent has a U code and its upstream node name")
        elif self.upstream_node is not None:
            raise ValueError("only upstream agents map to an upstream node")
        if self.group in _DETERMINISTIC_GROUPS and self.kind is not AgentKind.DETERMINISTIC:
            raise ValueError("risk and execution agents are deterministic code")
        if self.enabled and self.roster_status is not RosterStatus.MINIMUM_V1:
            raise ValueError(
                f"{self.technical_id} is {self.roster_status.value} and cannot be enabled yet"
            )
        return self


class AgentRegistry:
    """An immutable, validated collection of agent identities."""

    def __init__(self, identities: Iterable[AgentIdentity]) -> None:
        agents = tuple(identities)
        for attr in ("technical_id", "code"):
            values = [getattr(a, attr) for a in agents]
            dupes = sorted({v for v in values if values.count(v) > 1})
            if dupes:
                raise ValueError(f"duplicate {attr}: {dupes}")
        nodes = [a.upstream_node for a in agents if a.upstream_node is not None]
        if len(set(nodes)) != len(nodes):
            raise ValueError("each upstream node maps to one agent")
        names = [a.display_name for a in agents if a.display_name is not None]
        if len(set(names)) != len(names):
            raise ValueError("display names must be unique")
        clashes = sorted(set(names) & {a.technical_id for a in agents})
        if clashes:
            raise ValueError(f"display names cannot reuse technical ids: {clashes}")
        self._agents = agents
        self._by_id = {a.technical_id: a for a in agents}
        self._by_code = {a.code: a for a in agents}

    def __len__(self) -> int:
        return len(self._agents)

    def __iter__(self) -> Iterator[AgentIdentity]:
        return iter(self._agents)

    def __contains__(self, technical_id: object) -> bool:
        return technical_id in self._by_id

    def get(self, technical_id: str) -> AgentIdentity:
        try:
            return self._by_id[technical_id]
        except KeyError:
            raise KeyError(f"unknown agent {technical_id!r}") from None

    def by_code(self, code: str) -> AgentIdentity:
        try:
            return self._by_code[code]
        except KeyError:
            raise KeyError(f"unknown agent code {code!r}") from None

    def by_upstream_node(self, node: str) -> AgentIdentity:
        for agent in self._agents:
            if agent.upstream_node == node:
                return agent
        raise KeyError(f"no agent maps to upstream node {node!r}")

    def in_group(self, group: AgentGroup) -> tuple[AgentIdentity, ...]:
        return tuple(a for a in self._agents if a.group is group)

    def enabled(self) -> tuple[AgentIdentity, ...]:
        return tuple(a for a in self._agents if a.enabled)

    def with_display_names(self, names: Mapping[str, str | None]) -> AgentRegistry:
        """A copy with persona display names applied (e.g. from a local, uncommitted file)."""
        unknown = sorted(set(names) - set(self._by_id))
        if unknown:
            raise KeyError(f"unknown agents: {unknown}")
        return AgentRegistry(
            AgentIdentity.model_validate(
                {**a.model_dump(), "display_name": names[a.technical_id]}
            )
            if a.technical_id in names
            else a
            for a in self._agents
        )

    def with_enabled(self, technical_id: str, enabled: bool) -> AgentRegistry:
        """A copy with one agent enabled or disabled (re-validated)."""
        target = self.get(technical_id)
        updated = AgentIdentity.model_validate({**target.model_dump(), "enabled": enabled})
        return AgentRegistry(updated if a is target else a for a in self._agents)
