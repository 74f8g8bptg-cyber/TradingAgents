"""Research sources: the owner's allowlist with trust tiers (Foundation §4.29.2, D-13).

No provider is named here (D-1 … D-6 open). A source is described by what it is:
- **Tier 1, OFFICIAL:** central banks, statistics offices, government or exchange
  publications;
- **Tier 2, PROFESSIONAL:** established financial or news providers;
- **Tier 3, AGGREGATOR:** calendars and aggregators that republish;
- **Tier 4, COMMUNITY:** social and community sources.

**The allowlist is empty by default** (D-13 safe default: "empty allowlist → no research
accepted"). An item from a source that is not on it is rejected by V1.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import model_validator

from stellar.schemas.common import Label, ShortText, StellarModel
from stellar.schemas.research import ResearchRole
from stellar.serialization import content_hash


class SourceTier(IntEnum):
    OFFICIAL = 1
    PROFESSIONAL = 2
    AGGREGATOR = 3
    COMMUNITY = 4


class SourceType(StrEnum):
    OFFICIAL_PUBLICATION = "official_publication"
    ECONOMIC_CALENDAR = "economic_calendar"
    NEWS = "news"
    RATES_DATA = "rates_data"
    CORPORATE_FILING = "corporate_filing"
    SOCIAL = "social"


ROLE_SOURCE_TYPES: dict[ResearchRole, frozenset[SourceType]] = {
    ResearchRole.CENTRAL_BANK: frozenset({SourceType.OFFICIAL_PUBLICATION}),
    ResearchRole.ECONOMIC_DATA: frozenset({SourceType.ECONOMIC_CALENDAR,
                                           SourceType.OFFICIAL_PUBLICATION}),
    ResearchRole.MARKET_NEWS: frozenset({SourceType.NEWS, SourceType.SOCIAL}),
    ResearchRole.GEOPOLITICAL: frozenset({SourceType.NEWS, SourceType.OFFICIAL_PUBLICATION}),
    ResearchRole.RATES_BONDS: frozenset({SourceType.RATES_DATA,
                                         SourceType.OFFICIAL_PUBLICATION}),
    ResearchRole.CORPORATE_EARNINGS: frozenset({SourceType.CORPORATE_FILING, SourceType.NEWS}),
}
"""Source types a role may use (Foundation §4.29.1). V1 rejects a mismatch."""


class SourceRecord(StellarModel):
    source_id: Label
    name: ShortText
    publisher: ShortText
    tier: SourceTier
    source_type: SourceType
    primary: bool
    """True for the originator of the information (for example the central bank itself)."""


class SourceAllowlist(StellarModel):
    sources: tuple[SourceRecord, ...] = ()
    test_only: bool = False

    @model_validator(mode="after")
    def _unique(self) -> SourceAllowlist:
        ids = [s.source_id for s in self.sources]
        if len(set(ids)) != len(ids):
            raise ValueError("each source may be listed once")
        return self

    def get(self, source_id: str) -> SourceRecord | None:
        return next((s for s in self.sources if s.source_id == source_id), None)

    def allowlist_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))
