from __future__ import annotations

import json
import subprocess
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
    policy_path = Path(path)
    if policy_path.suffix == ".cue":
        raw = _load_policy_from_cue(policy_path)
    else:
        raw = json.loads(policy_path.read_text())

    participants, sender_to_participant = _load_participants(raw.get("participants"))
    lease = _load_lease(raw.get("lease"))
    if lease.holder not in participants:
        raise PolicyError(f"lease holder is not a declared participant: {lease.holder!r}")
    routing = _load_routing(raw.get("routing"))

    return RuntimePolicy(
        participants=participants,
        sender_to_participant=sender_to_participant,
        lease=lease,
        routing=routing,
    )


def _load_policy_from_cue(path: Path) -> dict:
    repo_root = _find_repo_root(path)
    cue_path = path.resolve().relative_to(repo_root.resolve())
    try:
        completed = subprocess.run(
            ["cue", "export", str(cue_path)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise PolicyError("cue executable is not available") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else exc.stdout.strip()
        raise PolicyError(f"cue export failed: {stderr}") from exc

    return json.loads(completed.stdout)


def _find_repo_root(path: Path) -> Path:
    for candidate in [path, *path.parents]:
        if (candidate / "cue.mod" / "module.cue").is_file():
            return candidate
    raise PolicyError(f"unable to locate repo root for CUE policy: {path}")


def _load_participants(participants_raw: object) -> tuple[dict[str, Participant], dict[str, str]]:
    participants: dict[str, Participant] = {}
    sender_to_participant: dict[str, str] = {}

    if isinstance(participants_raw, dict):
        if not participants_raw:
            raise PolicyError("participants must be a non-empty object")
        items = participants_raw.items()
        for participant_id, spec in items:
            if not isinstance(spec, dict):
                raise PolicyError(f"participant {participant_id!r} must be an object")
            sender_ids = tuple(
                str(value)
                for value in spec.get("sender_ids", spec.get("senderIds", []))
            )
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
        return participants, sender_to_participant

    if isinstance(participants_raw, list):
        if not participants_raw:
            raise PolicyError("participants must be a non-empty list")
        for spec in participants_raw:
            if not isinstance(spec, dict):
                raise PolicyError("each participant entry must be an object")
            participant_id = str(spec.get("id", spec.get("participant_id", "")))
            if not participant_id:
                raise PolicyError("participant entry must define id")
            sender_ids = tuple(
                str(value)
                for value in spec.get("senderIds", spec.get("sender_ids", []))
            )
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
        return participants, sender_to_participant

    raise PolicyError("participants must be an object or list")


def _load_lease(lease_raw: object) -> LeasePolicy:
    if not isinstance(lease_raw, dict):
        raise PolicyError("lease must be an object")
    holder = lease_raw.get("holder")
    epoch = lease_raw.get("epoch", lease_raw.get("leaseEpoch"))
    required_kinds = lease_raw.get("required_kinds", lease_raw.get("requiredKinds", []))
    lease = LeasePolicy(
        holder=str(holder),
        epoch=int(epoch),
        required_kinds=frozenset(str(kind) for kind in required_kinds),
    )
    return lease


def _load_routing(routing_raw: object) -> RoutingPolicy:
    if not isinstance(routing_raw, dict):
        raise PolicyError("routing must be an object")
    return RoutingPolicy(
        broadcast_receiver=str(
            routing_raw.get("broadcast_receiver", routing_raw.get("broadcastReceiver", "0"))
        ),
        self_target_reject_kinds=frozenset(
            str(kind)
            for kind in routing_raw.get(
                "self_target_reject_kinds", routing_raw.get("selfTargetRejectKinds", [])
            )
        ),
        ignore_duplicate_event_ids=bool(
            routing_raw.get(
                "ignore_duplicate_event_ids", routing_raw.get("ignoreDuplicateEventIds", True)
            )
        ),
    )
