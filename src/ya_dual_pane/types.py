from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DdsEnvelope:
    kind: str
    receiver: str
    sender: str
    body: Any


@dataclass(frozen=True, slots=True)
class AuthorityMeta:
    event_id: str
    origin_seq: int
    lease_epoch: int
    causal_id: str | None = None


@dataclass(frozen=True, slots=True)
class IngressEvent:
    wire: DdsEnvelope
    meta: AuthorityMeta


@dataclass(frozen=True, slots=True)
class OutcomeMeta:
    event_id: str
    origin_seq: int
    lease_epoch: int
    participant_id: str | None
    commit_seq: int | None
    causal_id: str | None
    decision: str


@dataclass(frozen=True, slots=True)
class Outcome:
    decision: str
    reason: str
    wire: DdsEnvelope
    meta: OutcomeMeta
    state: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "wire": {
                "kind": self.wire.kind,
                "receiver": self.wire.receiver,
                "sender": self.wire.sender,
                "body": self.wire.body,
            },
            "meta": {
                "event_id": self.meta.event_id,
                "origin_seq": self.meta.origin_seq,
                "lease_epoch": self.meta.lease_epoch,
                "participant_id": self.meta.participant_id,
                "commit_seq": self.meta.commit_seq,
                "causal_id": self.meta.causal_id,
                "decision": self.meta.decision,
            },
            "state": self.state,
        }


@dataclass(slots=True)
class CoordinatorState:
    lease_holder: str
    lease_epoch: int
    commit_seq: int = 0
    last_seq_by_participant: dict[str, int] = field(default_factory=dict)
    seen_event_ids: set[str] = field(default_factory=set)

    def snapshot(self) -> dict[str, Any]:
        return {
            "leaseHolder": self.lease_holder,
            "leaseEpoch": self.lease_epoch,
            "commitSeq": self.commit_seq,
        }
