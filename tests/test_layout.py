from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest
from dataclasses import asdict
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ya_dual_pane.layout import KittyPaneMode
from ya_dual_pane.layout import KittySession


class FakeRemote:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.launch_id = "peer-window-2"

    def goto_layout(self, layout_name: str) -> None:
        self.calls.append(("goto_layout", layout_name))

    def launch_peer(self, peer_command, *, cwd: str = "current") -> str:
        self.calls.append(("launch_peer", tuple(peer_command), cwd))
        return self.launch_id

    def set_user_vars(self, *, match: str | None = None, **vars: str) -> None:
        self.calls.append(("set_user_vars", match, vars))

    def focus_window(self, match: str) -> None:
        self.calls.append(("focus_window", match))

    def close_window(self, match: str) -> None:
        self.calls.append(("close_window", match))


class LayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_path = pathlib.Path(self.tempdir.name) / "layout.json"
        self.remote = FakeRemote()

    def test_enter_creates_session_and_marks_roles(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "KITTY_WINDOW_ID": "primary-window-1",
                "YA_DUAL_PANE_PEER_COMMAND": "yazi",
            },
            clear=False,
        ):
            mode = KittyPaneMode(state_path=self.state_path, remote=self.remote)
            session = mode.enter()

        self.assertEqual(session, KittySession("primary-window-1", session.group_id, "peer-window-2", ("yazi",)))
        self.assertTrue(self.state_path.exists())
        recorded = json.loads(self.state_path.read_text())
        self.assertIn("primary-window-1", recorded)
        self.assertEqual(recorded["primary-window-1"]["peer_window_id"], "peer-window-2")
        self.assertEqual(
            self.remote.calls,
            [
                ("goto_layout", "splits"),
                ("launch_peer", ("yazi",), "current"),
                (
                    "set_user_vars",
                    "id:primary-window-1",
                    {"ya_dual_pane_group": session.group_id, "ya_dual_pane_role": "primary"},
                ),
                (
                    "set_user_vars",
                    "id:peer-window-2",
                    {"ya_dual_pane_group": session.group_id, "ya_dual_pane_role": "peer"},
                ),
            ],
        )

    def test_enter_reuses_recorded_peer(self) -> None:
        stored = KittySession("primary-window-1", "group-1", "peer-window-2", ("yazi",))
        self.state_path.write_text(json.dumps({"primary-window-1": asdict(stored)}))

        with mock.patch.dict(
            os.environ,
            {
                "KITTY_WINDOW_ID": "primary-window-1",
            },
            clear=False,
        ):
            mode = KittyPaneMode(state_path=self.state_path, remote=self.remote)
            session = mode.enter()

        self.assertEqual(session, stored)
        self.assertNotIn(("launch_peer", ("yazi",), "current"), self.remote.calls)

    def test_enter_from_peer_window_reuses_recorded_session(self) -> None:
        stored = KittySession("primary-window-1", "group-1", "peer-window-2", ("yazi",))
        self.state_path.write_text(json.dumps({"primary-window-1": asdict(stored)}))

        with mock.patch.dict(
            os.environ,
            {
                "KITTY_WINDOW_ID": "peer-window-2",
            },
            clear=False,
        ):
            mode = KittyPaneMode(state_path=self.state_path, remote=self.remote)
            session = mode.enter()

        self.assertEqual(session, stored)
        self.assertNotIn(("launch_peer", ("yazi",), "current"), self.remote.calls)

    def test_focus_and_close_peer_use_recorded_peer_window(self) -> None:
        stored = KittySession("primary-window-1", "group-1", "peer-window-2", ("yazi",))
        self.state_path.write_text(json.dumps({"primary-window-1": asdict(stored)}))

        with mock.patch.dict(
            os.environ,
            {
                "KITTY_WINDOW_ID": "primary-window-1",
            },
            clear=False,
        ):
            mode = KittyPaneMode(state_path=self.state_path, remote=self.remote)
            mode.focus_peer()
            mode.close_peer()

        self.assertIn(("focus_window", "id:peer-window-2"), self.remote.calls)
        self.assertIn(("close_window", "id:peer-window-2"), self.remote.calls)


if __name__ == "__main__":
    unittest.main()
