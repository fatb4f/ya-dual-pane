from __future__ import annotations

import json
import os
import shlex
import subprocess
import uuid
import sys
from dataclasses import dataclass
from dataclasses import asdict
from pathlib import Path
from typing import Sequence


class LayoutError(RuntimeError):
    """Raised when kitty pane-mode orchestration fails."""


@dataclass(frozen=True, slots=True)
class KittySession:
    current_window_id: str
    group_id: str
    peer_window_id: str | None = None
    peer_command: tuple[str, ...] = ()


class KittyRemote:
    def __init__(self, remote_cmd: Sequence[str] | None = None) -> None:
        self.remote_cmd = tuple(remote_cmd or self._default_remote_cmd())

    @staticmethod
    def _default_remote_cmd() -> tuple[str, ...]:
        if shutil_which("kitten"):
            return ("kitten", "@")
        if shutil_which("kitty"):
            return ("kitty", "@")
        raise LayoutError("kitty remote-control command not found")

    def run(self, *args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (*self.remote_cmd, *args),
            check=True,
            capture_output=capture_output,
            text=True,
        )

    def launch_peer(self, peer_command: Sequence[str], *, cwd: str = "current") -> str:
        completed = self.run(
            "launch",
            "--type=window",
            "--location=vsplit",
            "--keep-focus",
            "--cwd",
            cwd,
            "--title",
            "ya-dual-pane peer",
            "--tab-title",
            "ya-dual-pane",
            *peer_command,
            capture_output=True,
        )
        window_id = completed.stdout.strip()
        if not window_id:
            raise LayoutError("kitty launch did not return a peer window id")
        return window_id

    def set_user_vars(self, *, match: str | None = None, **vars: str) -> None:
        args = ["set-user-vars"]
        if match is not None:
            args.extend(["--match", match])
        args.extend(f"{key}={value}" for key, value in vars.items())
        self.run(*args)

    def goto_layout(self, layout_name: str = "splits") -> None:
        self.run("goto-layout", layout_name)

    def focus_window(self, match: str) -> None:
        self.run("focus-window", "--match", match)

    def close_window(self, match: str) -> None:
        self.run("close-window", "--match", match)


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


class KittyPaneMode:
    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        remote: KittyRemote | None = None,
    ) -> None:
        self.state_path = Path(state_path) if state_path is not None else _default_state_path()
        self.remote = remote or KittyRemote()

    def enter(self, peer_command: Sequence[str] | None = None) -> KittySession:
        current_window_id = _require_current_window_id()
        session = self._load_current_session()
        if session is not None and current_window_id not in {
            session.current_window_id,
            session.peer_window_id,
        }:
            session = None

        peer_command_tuple = tuple(peer_command or _default_peer_command())

        if session is not None and session.peer_window_id:
            self._ensure_roles(session.current_window_id, session.peer_window_id, session.group_id)
            self._save_session(session)
            return session

        group_id = session.group_id if session is not None else uuid.uuid4().hex
        self.remote.goto_layout("splits")
        peer_window_id = self.remote.launch_peer(peer_command_tuple)
        self._ensure_roles(current_window_id, peer_window_id, group_id)
        session = KittySession(
            current_window_id=current_window_id,
            group_id=group_id,
            peer_window_id=peer_window_id,
            peer_command=peer_command_tuple,
        )
        self._save_session(session)
        return session

    def focus_peer(self) -> None:
        session = self._require_session()
        if not session.peer_window_id:
            raise LayoutError("peer window is not recorded for this session")
        self.remote.focus_window(f"id:{session.peer_window_id}")

    def close_peer(self) -> None:
        session = self._require_session()
        if not session.peer_window_id:
            return
        self.remote.close_window(f"id:{session.peer_window_id}")
        self._save_session(
            KittySession(
                current_window_id=session.current_window_id,
                group_id=session.group_id,
                peer_window_id=None,
                peer_command=session.peer_command,
            )
        )

    def status(self) -> KittySession | None:
        session = self._load_current_session()
        if session is None:
            return None
        if session.peer_window_id and not self._window_exists(session.peer_window_id):
            session = KittySession(
                current_window_id=session.current_window_id,
                group_id=session.group_id,
                peer_window_id=None,
                peer_command=session.peer_command,
            )
            self._save_session(session)
        return session

    def _require_session(self) -> KittySession:
        _require_current_window_id()
        session = self._load_current_session()
        if session is None:
            raise LayoutError("no dual-pane session recorded for this kitty window")
        return session

    def _ensure_roles(self, current_window_id: str, peer_window_id: str, group_id: str) -> None:
        self.remote.set_user_vars(
            match=f"id:{current_window_id}",
            ya_dual_pane_group=group_id,
            ya_dual_pane_role="primary",
        )
        self.remote.set_user_vars(
            match=f"id:{peer_window_id}",
            ya_dual_pane_group=group_id,
            ya_dual_pane_role="peer",
        )

    def _load_current_session(self) -> KittySession | None:
        current_window_id = _current_window_id()
        if current_window_id is None:
            return None
        sessions = self._load_state()
        raw = sessions.get(current_window_id)
        if not isinstance(raw, dict):
            raw = next(
                (
                    candidate
                    for candidate in sessions.values()
                    if isinstance(candidate, dict)
                    and current_window_id
                    in {
                        str(candidate.get("current_window_id", "")),
                        (None if candidate.get("peer_window_id") in (None, "") else str(candidate.get("peer_window_id"))),
                    }
                ),
                None,
            )
        if not isinstance(raw, dict):
            return None
        peer_command = raw.get("peer_command", [])
        if isinstance(peer_command, list):
            peer_command_tuple = tuple(str(value) for value in peer_command)
        else:
            peer_command_tuple = ()
        peer_window_id = raw.get("peer_window_id")
        return KittySession(
            current_window_id=str(raw.get("current_window_id", current_window_id)),
            group_id=str(raw.get("group_id", "")),
            peer_window_id=(None if peer_window_id in (None, "") else str(peer_window_id)),
            peer_command=peer_command_tuple,
        )

    def _save_session(self, session: KittySession) -> None:
        sessions = self._load_state()
        sessions[session.current_window_id] = {
            "current_window_id": session.current_window_id,
            "group_id": session.group_id,
            "peer_window_id": session.peer_window_id,
            "peer_command": list(session.peer_command),
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(sessions, sort_keys=True, indent=2))

    def _load_state(self) -> dict[str, object]:
        if not self.state_path.exists():
            return {}
        try:
            raw = json.loads(self.state_path.read_text())
        except json.JSONDecodeError as exc:
            raise LayoutError(f"invalid layout state file: {self.state_path}") from exc
        if not isinstance(raw, dict):
            raise LayoutError(f"layout state file must contain an object: {self.state_path}")
        return raw


def _default_state_path() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "ya-dual-pane" / "layout.json"


def _default_peer_command() -> list[str]:
    command = os.environ.get("YA_DUAL_PANE_PEER_COMMAND", "yazi")
    return shlex.split(command)


def _current_window_id() -> str | None:
    return os.environ.get("KITTY_WINDOW_ID")


def _require_current_window_id() -> str:
    window_id = _current_window_id()
    if window_id is None:
        raise LayoutError("KITTY_WINDOW_ID is required to enter or manage pane mode")
    return window_id


def build_parser() -> "argparse.ArgumentParser":
    import argparse

    parser = argparse.ArgumentParser(prog="ya-layout")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enter_parser = subparsers.add_parser("enter", help="Enter two-pane kitty mode")
    enter_parser.add_argument(
        "--peer-command",
        default=None,
        help="Command to launch in the peer pane (default: YA_DUAL_PANE_PEER_COMMAND or yazi)",
    )

    subparsers.add_parser("focus-peer", help="Focus the peer pane")
    subparsers.add_parser("close-peer", help="Close the peer pane")
    subparsers.add_parser("status", help="Print the recorded pane-mode status")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = KittyPaneMode()

    try:
        if args.command == "enter":
            peer_command = None if args.peer_command is None else shlex.split(args.peer_command)
            session = mode.enter(peer_command=peer_command)
            print(json.dumps(asdict(session), sort_keys=True))
            return 0
        if args.command == "focus-peer":
            mode.focus_peer()
            return 0
        if args.command == "close-peer":
            mode.close_peer()
            return 0
        if args.command == "status":
            session = mode.status()
            print(json.dumps(None if session is None else asdict(session), sort_keys=True))
            return 0
    except (LayoutError, subprocess.CalledProcessError) as exc:
        print(f"layout error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
