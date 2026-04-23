from __future__ import annotations

import io
import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ya_dual_pane.bridge import YaziBridge
from ya_dual_pane.bridge import ingress_json
from ya_dual_pane.bridge import session_from_policy
from ya_dual_pane.policy import load_policy
from ya_dual_pane.transport import run_stream


class BridgeCoordinatorSmokeTests(unittest.TestCase):
    def test_bridge_output_matches_coordinator_commit(self) -> None:
        policy = load_policy(PROJECT_ROOT / "profiles" / "dev.cue")
        bridge = YaziBridge(session_from_policy(policy, sender="100"))
        event = bridge.reveal_in_peer("/tmp/a")
        stream = io.StringIO(f"{ingress_json(event)}\n")
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = run_stream(str(PROJECT_ROOT / "profiles" / "dev.cue"), stdin=stream, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn('"decision": "commit"', stdout.getvalue())
        self.assertIn('"reveal_in_peer"', stdout.getvalue())
        self.assertIn('"error": null', stdout.getvalue())

    def test_copy_to_peer_matches_coordinator_commit(self) -> None:
        policy = load_policy(PROJECT_ROOT / "profiles" / "dev.cue")
        bridge = YaziBridge(session_from_policy(policy, sender="100"))
        event = bridge.copy_to_peer(["/tmp/a", "/tmp/b"], destination="/dst")
        stream = io.StringIO(f"{ingress_json(event)}\n")
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = run_stream(str(PROJECT_ROOT / "profiles" / "dev.cue"), stdin=stream, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn('"decision": "commit"', stdout.getvalue())
        self.assertIn('"copy_to_peer"', stdout.getvalue())
        self.assertIn('"/dst"', stdout.getvalue())

    def test_move_to_peer_matches_coordinator_commit(self) -> None:
        policy = load_policy(PROJECT_ROOT / "profiles" / "dev.cue")
        bridge = YaziBridge(session_from_policy(policy, sender="100"))
        event = bridge.move_to_peer(["/tmp/a"], destination="/dst")
        stream = io.StringIO(f"{ingress_json(event)}\n")
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = run_stream(str(PROJECT_ROOT / "profiles" / "dev.cue"), stdin=stream, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn('"decision": "commit"', stdout.getvalue())
        self.assertIn('"move_to_peer"', stdout.getvalue())
        self.assertIn('"/dst"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
