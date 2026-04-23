from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ya_dual_pane.dds import parse_wire_line
from ya_dual_pane.policy import RuntimePolicy
from ya_dual_pane.types import AuthorityMeta
from ya_dual_pane.types import DdsEnvelope
from ya_dual_pane.types import IngressEvent


class BridgeError(ValueError):
    """Raised when a bridge frame cannot be constructed."""


@dataclass(frozen=True, slots=True)
class BridgeSession:
    sender: str
    peer_sender: str
    lease_epoch: int
    origin_seq: int = 1
    event_id_prefix: str = "evt-"
    causal_id_prefix: str | None = None
    participant_id: str | None = None


def session_from_policy(
    policy: RuntimePolicy,
    *,
    sender: str,
    lease_epoch: int | None = None,
    origin_seq: int = 1,
    event_id_prefix: str = "evt-",
    causal_id_prefix: str | None = None,
) -> BridgeSession:
    peer_sender = policy.peer_sender_for_sender(sender)
    if peer_sender is None:
        raise BridgeError(f"unable to resolve peer sender for {sender!r}")
    participant_id = policy.participant_for_sender(sender)
    if participant_id is None:
        raise BridgeError(f"unknown sender for session: {sender!r}")
    return BridgeSession(
        sender=sender,
        peer_sender=peer_sender,
        lease_epoch=policy.lease.epoch if lease_epoch is None else lease_epoch,
        origin_seq=origin_seq,
        event_id_prefix=event_id_prefix,
        causal_id_prefix=causal_id_prefix,
        participant_id=participant_id,
    )


class YaziBridge:
    def __init__(self, session: BridgeSession) -> None:
        self.session = session
        self._next_origin_seq = session.origin_seq

    def wrap_wire_line(
        self,
        line: str,
        *,
        event_id: str | None = None,
        origin_seq: int | None = None,
        lease_epoch: int | None = None,
        causal_id: str | None = None,
    ) -> IngressEvent:
        wire = parse_wire_line(line)
        if wire.sender != self.session.sender:
            raise BridgeError(
                f"wire sender {wire.sender!r} does not match bridge sender {self.session.sender!r}"
            )
        return IngressEvent(
            wire=wire,
            meta=self._next_meta(
                event_id=event_id,
                origin_seq=origin_seq,
                lease_epoch=lease_epoch,
                causal_id=causal_id,
            ),
        )

    def build_operation(
        self,
        kind: str,
        body: Any,
        *,
        receiver: str | None = None,
        sender: str | None = None,
        event_id: str | None = None,
        origin_seq: int | None = None,
        lease_epoch: int | None = None,
        causal_id: str | None = None,
    ) -> IngressEvent:
        return IngressEvent(
            wire=DdsEnvelope(
                kind=kind,
                receiver=receiver or self.session.peer_sender,
                sender=sender or self.session.sender,
                body=body,
            ),
            meta=self._next_meta(
                event_id=event_id,
                origin_seq=origin_seq,
                lease_epoch=lease_epoch,
                causal_id=causal_id,
            ),
        )

    def reveal_in_peer(self, url: str, **kwargs: Any) -> IngressEvent:
        return self.build_operation("reveal_in_peer", {"url": url}, **kwargs)

    def cd_peer_here(self, cwd: str, **kwargs: Any) -> IngressEvent:
        return self.build_operation("cd_peer_here", {"cwd": cwd}, **kwargs)

    def copy_to_peer(
        self,
        paths: list[str] | tuple[str, ...],
        *,
        destination: str | None = None,
        **kwargs: Any,
    ) -> IngressEvent:
        body: dict[str, Any] = {"paths": list(paths)}
        if destination is not None:
            body["destination"] = destination
        return self.build_operation("copy_to_peer", body, **kwargs)

    def move_to_peer(
        self,
        paths: list[str] | tuple[str, ...],
        *,
        destination: str | None = None,
        **kwargs: Any,
    ) -> IngressEvent:
        body: dict[str, Any] = {"paths": list(paths)}
        if destination is not None:
            body["destination"] = destination
        return self.build_operation("move_to_peer", body, **kwargs)

    def send_hovered_to_peer(self, url: str, **kwargs: Any) -> IngressEvent:
        return self.build_operation("send_hovered_to_peer", {"url": url}, **kwargs)

    def send_selected_to_peer(self, urls: list[str] | tuple[str, ...], **kwargs: Any) -> IngressEvent:
        return self.build_operation("send_selected_to_peer", {"urls": list(urls)}, **kwargs)

    def _next_meta(
        self,
        *,
        event_id: str | None,
        origin_seq: int | None,
        lease_epoch: int | None,
        causal_id: str | None,
    ) -> AuthorityMeta:
        seq = self._reserve_origin_seq(origin_seq)
        return AuthorityMeta(
            event_id=event_id or f"{self.session.event_id_prefix}{seq}",
            origin_seq=seq,
            lease_epoch=self.session.lease_epoch if lease_epoch is None else lease_epoch,
            causal_id=causal_id
            if causal_id is not None
            else (
                None
                if self.session.causal_id_prefix is None
                else f"{self.session.causal_id_prefix}{seq}"
            ),
        )

    def _reserve_origin_seq(self, origin_seq: int | None) -> int:
        if origin_seq is None:
            seq = self._next_origin_seq
            self._next_origin_seq += 1
            return seq
        self._next_origin_seq = max(self._next_origin_seq, origin_seq + 1)
        return origin_seq


def ingress_as_dict(event: IngressEvent) -> dict[str, Any]:
    return {
        "wire": {
            "kind": event.wire.kind,
            "receiver": event.wire.receiver,
            "sender": event.wire.sender,
            "body": event.wire.body,
        },
        "meta": {
            "event_id": event.meta.event_id,
            "origin_seq": event.meta.origin_seq,
            "lease_epoch": event.meta.lease_epoch,
            "causal_id": event.meta.causal_id,
        },
    }


def ingress_json(event: IngressEvent) -> str:
    return json.dumps(ingress_as_dict(event), sort_keys=True)
