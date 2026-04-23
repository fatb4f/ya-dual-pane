from __future__ import annotations

import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ya_dual_pane.bridge import BridgeError
from ya_dual_pane.bridge import BridgeSession
from ya_dual_pane.bridge import YaziBridge
from ya_dual_pane.bridge import session_from_policy
from ya_dual_pane.bridge_cli import build_parser
from ya_dual_pane.policy import load_policy


class BridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = YaziBridge(
            BridgeSession(
                sender="100",
                peer_sender="200",
                lease_epoch=1,
                origin_seq=7,
                event_id_prefix="evt-",
            )
        )

    def test_wraps_raw_dds_line_into_ingress_event(self) -> None:
        event = self.bridge.wrap_wire_line('hover,0,100,{"tab":0,"url":"/tmp/a"}')

        self.assertEqual(event.wire.kind, "hover")
        self.assertEqual(event.wire.receiver, "0")
        self.assertEqual(event.wire.sender, "100")
        self.assertEqual(event.wire.body, {"tab": 0, "url": "/tmp/a"})
        self.assertEqual(event.meta.event_id, "evt-7")
        self.assertEqual(event.meta.origin_seq, 7)
        self.assertEqual(event.meta.lease_epoch, 1)

    def test_session_from_policy_resolves_peer_sender(self) -> None:
        policy = load_policy(PROJECT_ROOT / "profiles" / "dev.cue")
        session = session_from_policy(policy, sender="100")

        self.assertEqual(session.sender, "100")
        self.assertEqual(session.peer_sender, "200")
        self.assertEqual(session.lease_epoch, 1)

    def test_wrap_rejects_mismatched_sender(self) -> None:
        with self.assertRaises(BridgeError):
            self.bridge.wrap_wire_line('hover,0,200,{"tab":0,"url":"/tmp/a"}')

    def test_reveal_in_peer_targets_peer_sender(self) -> None:
        event = self.bridge.reveal_in_peer("/tmp/a")

        self.assertEqual(event.wire.kind, "reveal_in_peer")
        self.assertEqual(event.wire.receiver, "200")
        self.assertEqual(event.wire.sender, "100")
        self.assertEqual(event.wire.body, {"url": "/tmp/a"})

    def test_copy_to_peer_encodes_paths_and_destination(self) -> None:
        event = self.bridge.copy_to_peer(["/tmp/a", "/tmp/b"], destination="/dst")

        self.assertEqual(event.wire.kind, "copy_to_peer")
        self.assertEqual(event.wire.receiver, "200")
        self.assertEqual(event.wire.body, {"paths": ["/tmp/a", "/tmp/b"], "destination": "/dst"})

    def test_move_to_peer_encodes_paths(self) -> None:
        event = self.bridge.move_to_peer(["/tmp/a"])

        self.assertEqual(event.wire.kind, "move_to_peer")
        self.assertEqual(event.wire.receiver, "200")
        self.assertEqual(event.wire.body, {"paths": ["/tmp/a"]})

    def test_send_selected_to_peer_uses_url_list(self) -> None:
        event = self.bridge.send_selected_to_peer(["/tmp/a", "/tmp/b"])

        self.assertEqual(event.wire.kind, "send_selected_to_peer")
        self.assertEqual(event.wire.receiver, "200")
        self.assertEqual(event.wire.body, {"urls": ["/tmp/a", "/tmp/b"]})

    def test_cli_accepts_positional_paths_for_copy_and_move(self) -> None:
        parser = build_parser()

        copy_args = parser.parse_args(
            [
                "--policy",
                str(PROJECT_ROOT / "profiles" / "dev.cue"),
                "--sender",
                "100",
                "copy-to-peer",
                "/tmp/a",
                "/tmp/b",
            ]
        )
        move_args = parser.parse_args(
            [
                "--policy",
                str(PROJECT_ROOT / "profiles" / "dev.cue"),
                "--sender",
                "100",
                "move-to-peer",
                "/tmp/a",
            ]
        )

        self.assertEqual(copy_args.paths, ["/tmp/a", "/tmp/b"])
        self.assertEqual(move_args.paths, ["/tmp/a"])


if __name__ == "__main__":
    unittest.main()
