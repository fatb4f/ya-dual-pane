from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class PolicyError(ValueError):
    """Raised when runtime policy is malformed."""


@dataclass(frozen=True, slots=True)
class Participant:
    participant_id: str
    sender_ids: tuple[str, ...]
    roles: tuple[str, ...]
    placement: str


@dataclass(frozen=True, slots=True)
class LeasePolicy:
    holder: str
    epoch: int
    required_kinds: frozenset[str]


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    broadcast_receiver: str
    self_target_reject_kinds: frozenset[str]
    ignore_duplicate_event_ids: bool


@dataclass(frozen=True, slots=True)
class RuntimePolicy:
    participants: dict[str, Participant]
    sender_to_participant: dict[str, str]
    lease: LeasePolicy
    routing: RoutingPolicy

    def participant_for_sender(self, sender: str) -> str | None:
        return self.sender_to_participant.get(sender)



def load_policy(path: str | Path) -> RuntimePolicy:
    raw = json.loads(Path(path).read_text())

    participants_raw = raw.get("participants")
    if not isinstance(participants_raw, dict) or not participants_raw:
        raise PolicyError("participants must be a non-empty object")

    participants: dict[str, Participant] = {}
    sender_to_participant: dict[str, str] = {}
    for participant_id, spec in participants_raw.items():
        if not isinstance(spec, dict):
            raise PolicyError(f"participant {participant_id!r} must be an object")
        sender_ids = tuple(str(value) for value in spec.get("sender_ids", []))
        if not sender_ids:
            raise PolicyError(f"participant {participant_id!r} must define sender_ids")
        participant = Participant(
            participant_id=participant_id,
            sender_ids=sender_ids,
            roles=tuple(str(value) for value in spec.get("roles", [])),
            placement=str(spec.get("placement", "unknown")),
        )
        participants[participant_id] = participant
        for sender_id in sender_ids:
            if sender_id in sender_to_participant:
                raise PolicyError(f"duplicate sender id mapping: {sender_id!r}")
            sender_to_participant[sender_id] = participant_id

    lease_raw = raw.get("lease")
    if not isinstance(lease_raw, dict):
        raise PolicyError("lease must be an object")
    lease = LeasePolicy(
        holder=str(lease_raw["holder"]),
        epoch=int(lease_raw["epoch"]),
        required_kinds=frozenset(str(kind) for kind in lease_raw.get("required_kinds", [])),
    )
    if lease.holder not in participants:
        raise PolicyError(f"lease holder is not a declared participant: {lease.holder!r}")

    routing_raw = raw.get("routing")
    if not isinstance(routing_raw, dict):
        raise PolicyError("routing must be an object")
    routing = RoutingPolicy(
        broadcast_receiver=str(routing_raw.get("broadcast_receiver", "0")),
        self_target_reject_kinds=frozenset(
            str(kind) for kind in routing_raw.get("self_target_reject_kinds", [])
        ),
        ignore_duplicate_event_ids=bool(routing_raw.get("ignore_duplicate_event_ids", True)),
    )

    return RuntimePolicy(
        participants=participants,
        sender_to_participant=sender_to_participant,
        lease=lease,
        routing=routing,
    )
