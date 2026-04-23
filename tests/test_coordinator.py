from __future__ import annotations

import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ya_dual_pane.coordinator import Coordinator
from ya_dual_pane.policy import load_policy
from ya_dual_pane.dds import parse_wire_line
from ya_dual_pane.transport import _error_outcome
from ya_dual_pane.transport import parse_input_line


class CoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_policy(PROJECT_ROOT / "profiles" / "dev.cue")

    def setUp(self) -> None:
        self.coordinator = Coordinator(self.policy)

    def test_accepts_valid_event_from_lease_holder(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":1}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "commit")
        self.assertEqual(outcome.reason, "accepted")
        self.assertIsNone(outcome.error)
        self.assertEqual(outcome.meta.participant_id, "yazi.primary")
        self.assertEqual(outcome.meta.commit_seq, 1)

    def test_rejects_unknown_sender(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"999","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":1}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "unknown sender")

    def test_ignores_duplicate_event_id(self) -> None:
        first = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":1}}'
        )
        second = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/b"}},"meta":{"event_id":"evt-1","origin_seq":2,"lease_epoch":1}}'
        )
        self.coordinator.adjudicate(first)
        outcome = self.coordinator.adjudicate(second)
        self.assertEqual(outcome.decision, "ignore")
        self.assertEqual(outcome.reason, "duplicate event_id")

    def test_rejects_lease_holder_violation(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"200","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-2","origin_seq":1,"lease_epoch":1}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(
            outcome.reason,
            "sender is not current lease holder for lease-protected kind",
        )

    def test_rejects_epoch_mismatch(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":2}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "lease epoch mismatch")

    def test_rejects_future_lease_epoch(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":1,"lease_epoch":99}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "lease epoch mismatch")

    def test_rejects_replayed_sequence(self) -> None:
        first = parse_input_line(
            '{"wire":{"kind":"hover","receiver":"0","sender":"100","body":{"tab":0,"url":"/tmp/a"}},"meta":{"event_id":"evt-1","origin_seq":2,"lease_epoch":1}}'
        )
        second = parse_input_line(
            '{"wire":{"kind":"rename","receiver":"0","sender":"100","body":{"tab":0,"from":"/tmp/a","to":"/tmp/b"}},"meta":{"event_id":"evt-2","origin_seq":2,"lease_epoch":1}}'
        )
        self.coordinator.adjudicate(first)
        outcome = self.coordinator.adjudicate(second)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "stale or replayed origin_seq")

    def test_rejects_self_targeted_addressed_operation(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"reveal_in_peer","receiver":"100","sender":"100","body":{"url":"/tmp/a"}},"meta":{"event_id":"evt-3","origin_seq":3,"lease_epoch":1}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "self-targeted addressed operation")

    def test_rejects_self_targeted_addressed_operation_via_participant_id(self) -> None:
        event = parse_input_line(
            '{"wire":{"kind":"reveal_in_peer","receiver":"yazi.primary","sender":"100","body":{"url":"/tmp/a"}},"meta":{"event_id":"evt-4","origin_seq":4,"lease_epoch":1}}'
        )
        outcome = self.coordinator.adjudicate(event)
        self.assertEqual(outcome.decision, "reject")
        self.assertEqual(outcome.reason, "self-targeted addressed operation")

    def test_parses_raw_string_dds_body(self) -> None:
        envelope = parse_wire_line("hover,0,100,not-json")
        self.assertEqual(envelope.kind, "hover")
        self.assertEqual(envelope.receiver, "0")
        self.assertEqual(envelope.sender, "100")
        self.assertEqual(envelope.body, "not-json")

    def test_error_outcome_has_uniform_shape(self) -> None:
        outcome = _error_outcome(lineno=3, exc=ValueError("boom"))
        self.assertIn("wire", outcome)
        self.assertIn("meta", outcome)
        self.assertIn("state", outcome)
        self.assertIn("error", outcome)
        self.assertIsNone(outcome["wire"])
        self.assertIsNone(outcome["meta"])
        self.assertIsNone(outcome["state"])
        self.assertEqual(outcome["error"], "boom")


if __name__ == "__main__":
    unittest.main()
