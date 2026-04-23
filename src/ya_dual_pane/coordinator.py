from __future__ import annotations

from dataclasses import asdict

from ya_dual_pane.policy import RuntimePolicy
from ya_dual_pane.types import AuthorityMeta, CoordinatorState, DdsEnvelope, IngressEvent, Outcome, OutcomeMeta


class Coordinator:
    def __init__(self, policy: RuntimePolicy) -> None:
        self.policy = policy
        self.state = CoordinatorState(
            lease_holder=policy.lease.holder,
            lease_epoch=policy.lease.epoch,
        )

    def adjudicate(self, event: IngressEvent) -> Outcome:
        wire = event.wire
        meta = event.meta
        participant_id = self.policy.participant_for_sender(wire.sender)

        if participant_id is None:
            return self._outcome(
                decision="reject",
                reason="unknown sender",
                wire=wire,
                meta=meta,
                participant_id=None,
                commit_seq=None,
            )

        if meta.event_id in self.state.seen_event_ids:
            decision = "ignore" if self.policy.routing.ignore_duplicate_event_ids else "reject"
            return self._outcome(
                decision=decision,
                reason="duplicate event_id",
                wire=wire,
                meta=meta,
                participant_id=participant_id,
                commit_seq=None,
            )

        if meta.lease_epoch != self.state.lease_epoch:
            return self._outcome(
                decision="reject",
                reason="lease epoch mismatch",
                wire=wire,
                meta=meta,
                participant_id=participant_id,
                commit_seq=None,
            )

        if wire.kind in self.policy.routing.self_target_reject_kinds:
            target_participant_id = self.policy.participant_for_address(wire.receiver)
            if (
                target_participant_id is not None and target_participant_id == participant_id
            ) or wire.receiver == wire.sender:
                return self._outcome(
                    decision="reject",
                    reason="self-targeted addressed operation",
                    wire=wire,
                    meta=meta,
                    participant_id=participant_id,
                    commit_seq=None,
                )

        if wire.kind in self.policy.lease.required_kinds and participant_id != self.state.lease_holder:
            return self._outcome(
                decision="reject",
                reason="sender is not current lease holder for lease-protected kind",
                wire=wire,
                meta=meta,
                participant_id=participant_id,
                commit_seq=None,
            )

        last_seq = self.state.last_seq_by_participant.get(participant_id, -1)
        if meta.origin_seq <= last_seq:
            return self._outcome(
                decision="reject",
                reason="stale or replayed origin_seq",
                wire=wire,
                meta=meta,
                participant_id=participant_id,
                commit_seq=None,
            )

        self.state.last_seq_by_participant[participant_id] = meta.origin_seq
        self.state.seen_event_ids.add(meta.event_id)
        self.state.commit_seq += 1

        return self._outcome(
            decision="commit",
            reason="accepted",
            wire=wire,
            meta=meta,
            participant_id=participant_id,
            commit_seq=self.state.commit_seq,
        )

    def _outcome(
        self,
        *,
        decision: str,
        reason: str,
        wire: DdsEnvelope,
        meta: AuthorityMeta,
        participant_id: str | None,
        commit_seq: int | None,
    ) -> Outcome:
        return Outcome(
            decision=decision,
            reason=reason,
            error=None,
            wire=wire,
            meta=OutcomeMeta(
                event_id=meta.event_id,
                origin_seq=meta.origin_seq,
                lease_epoch=meta.lease_epoch,
                participant_id=participant_id,
                commit_seq=commit_seq,
                causal_id=meta.causal_id,
                decision=decision,
            ),
            state=self.state.snapshot(),
        )
