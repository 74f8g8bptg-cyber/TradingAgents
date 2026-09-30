"""Research snapshots (Foundation §4.29.5): what the research looked like at ``as_of``.

A snapshot records:
- every collection result per role (OK, NO_DATA or UNAVAILABLE) and every item collected;
- every claim validation and every claim assessment;
- the allowlist and validation-config hashes.

Its id and hash are derived from that content, so the same research at the same ``as_of``
is the same snapshot, and a decision cycle can be replayed against it.

Items published after ``as_of`` are kept in the record (as FUTURE rejections) for audit, but
no rejected claim ever reaches analysis. Claim ids must be unique across the snapshot, since
they are the evidence ids analysis cites.

``publish_snapshot`` journals the existing events:
- ``research.item.collected`` per item;
- ``research.item.accepted`` or ``research.item.rejected`` per item (accepted when at least
  one claim was accepted);
- ``research.snapshot.created``.

No new event name is used.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import model_validator

from stellar.journal import StellarJournal
from stellar.research.collect import CollectionResult, CollectionStatus
from stellar.research.corroboration import ClaimAssessment
from stellar.schemas.common import ResearchSnapshotId, Sha256Hex, StellarModel, UtcDatetime
from stellar.schemas.research import ClaimValidation, ResearchItem, ResearchRole, ValidationStatus
from stellar.serialization import content_hash
from stellar.telemetry import EventBus, StellarEvent, new_event


class ResearchSnapshot(StellarModel):
    research_snapshot_id: ResearchSnapshotId
    as_of: UtcDatetime
    collections: tuple[CollectionResult, ...]
    validations: tuple[ClaimValidation, ...]
    assessments: tuple[ClaimAssessment, ...]
    allowlist_hash: Sha256Hex
    validation_config_hash: Sha256Hex
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def _consistent(self) -> ResearchSnapshot:
        claim_ids = [c.claim_id for i in self.items for c in i.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError("claim ids must be unique across a research snapshot")
        if any(c.as_of != self.as_of for c in self.collections):
            raise ValueError("every collection must be for the snapshot's as_of")
        return self

    @property
    def items(self) -> tuple[ResearchItem, ...]:
        return tuple(i for c in self.collections for i in c.items)

    def contributed_roles(self) -> tuple[ResearchRole, ...]:
        accepted_items = {v.item_id for v in self.validations
                          if v.status is ValidationStatus.ACCEPTED}
        return tuple(sorted({i.role for i in self.items if i.item_id in accepted_items},
                            key=lambda r: r.value))

    def missing_roles(self, required: Sequence[ResearchRole]) -> tuple[ResearchRole, ...]:
        have = set(self.contributed_roles())
        return tuple(r for r in required if r not in have)


def build_snapshot(collections: Sequence[CollectionResult], validations: Sequence[ClaimValidation],
                   assessments: Sequence[ClaimAssessment], *, as_of: datetime,
                   allowlist_hash: str, validation_config_hash: str) -> ResearchSnapshot:
    body = {"as_of": as_of, "collections": tuple(sorted(collections, key=lambda c: c.role.value)),
            "validations": tuple(validations), "assessments": tuple(assessments),
            "allowlist_hash": allowlist_hash, "validation_config_hash": validation_config_hash}
    draft = ResearchSnapshot.model_validate({**body, "research_snapshot_id": "rsnap_pending",
                                             "content_hash": "0" * 64})
    digest = content_hash(draft.model_dump(mode="json", exclude={"research_snapshot_id",
                                                                 "content_hash"}))
    return draft.model_copy(update={"research_snapshot_id": f"rsnap_{digest[:40]}",
                                    "content_hash": digest})


def publish_snapshot(journal: StellarJournal, snapshot: ResearchSnapshot, *, station_id: str,
                     ts: datetime) -> list[StellarEvent]:
    bus = EventBus(journal)
    events = []

    def emit(event_type: str, payload: dict, correlation: str) -> None:
        stored = bus.publish(new_event(event_type, station_id=station_id,
                                       source="stellar.research", ts=ts,
                                       correlation_id=correlation, payload=payload))
        if stored is not None:
            events.append(stored)

    accepted = {v.item_id for v in snapshot.validations if v.status is ValidationStatus.ACCEPTED}
    for item in snapshot.items:
        emit("research.item.collected", {"item_id": item.item_id, "role": item.role.value,
                                         "source_id": item.source_id,
                                         "published_at": item.published_at.isoformat(),
                                         "content_hash": item.content_hash,
                                         "item": item.model_dump(mode="json")}, item.item_id)
        reasons = sorted({c.reason for v in snapshot.validations if v.item_id == item.item_id
                          for c in v.checks if c.reason is not None})
        emit("research.item.accepted" if item.item_id in accepted else "research.item.rejected",
             {"item_id": item.item_id, "reasons": reasons,
              "research_snapshot_id": snapshot.research_snapshot_id}, item.item_id)
    emit("research.snapshot.created", {
        "research_snapshot_id": snapshot.research_snapshot_id,
        "content_hash": snapshot.content_hash, "as_of": snapshot.as_of.isoformat(),
        "collections": {c.role.value: c.status.value for c in snapshot.collections},
        "absent_roles": sorted(c.role.value for c in snapshot.collections
                               if c.status is not CollectionStatus.OK)},
        snapshot.research_snapshot_id)
    return events
