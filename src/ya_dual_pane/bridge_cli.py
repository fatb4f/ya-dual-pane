from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from ya_dual_pane.bridge import BridgeError
from ya_dual_pane.bridge import YaziBridge
from ya_dual_pane.bridge import ingress_json
from ya_dual_pane.bridge import session_from_policy
from ya_dual_pane.policy import PolicyError
from ya_dual_pane.policy import load_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ya-bridge")
    parser.add_argument("--policy", required=True, help="Path to the runtime policy file (.cue or .json)")
    parser.add_argument("--sender", required=True, help="Local DDS sender id for this participant")
    parser.add_argument(
        "--lease-epoch",
        type=int,
        default=None,
        help="Lease epoch to attach to outgoing ingress frames (default: policy lease epoch)",
    )
    parser.add_argument(
        "--origin-seq-start",
        type=int,
        default=1,
        help="First origin sequence number to assign",
    )
    parser.add_argument(
        "--event-id-prefix",
        default="evt-",
        help="Prefix for generated event ids",
    )
    parser.add_argument(
        "--causal-id-prefix",
        default=None,
        help="Optional prefix for generated causal ids",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("wrap", help="Wrap raw DDS stdout lines into coordinator ingress JSONL")

    reveal = subparsers.add_parser("reveal-in-peer", help="Build a reveal_in_peer ingress event")
    reveal.add_argument("--url", required=True)
    reveal.add_argument("--receiver", default=None)

    cd = subparsers.add_parser("cd-peer-here", help="Build a cd_peer_here ingress event")
    cd.add_argument("--cwd", required=True)
    cd.add_argument("--receiver", default=None)

    copy = subparsers.add_parser("copy-to-peer", help="Build a copy_to_peer ingress event")
    copy.add_argument("paths", nargs="+", help="Paths to copy to the peer")
    copy.add_argument("--destination", default=None)
    copy.add_argument("--receiver", default=None)

    move = subparsers.add_parser("move-to-peer", help="Build a move_to_peer ingress event")
    move.add_argument("paths", nargs="+", help="Paths to move to the peer")
    move.add_argument("--destination", default=None)
    move.add_argument("--receiver", default=None)

    hover = subparsers.add_parser("send-hovered-to-peer", help="Build a send_hovered_to_peer ingress event")
    hover.add_argument("--url", required=True)
    hover.add_argument("--receiver", default=None)

    selected = subparsers.add_parser("send-selected-to-peer", help="Build a send_selected_to_peer ingress event")
    selected.add_argument("--url", action="append", dest="urls", required=True)
    selected.add_argument("--receiver", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        policy = load_policy(args.policy)
        session = session_from_policy(
            policy,
            sender=args.sender,
            lease_epoch=args.lease_epoch,
            origin_seq=args.origin_seq_start,
            event_id_prefix=args.event_id_prefix,
            causal_id_prefix=args.causal_id_prefix,
        )
        bridge = YaziBridge(session)

        if args.command == "wrap":
            return _run_wrap(bridge)
        if args.command == "reveal-in-peer":
            print(
                ingress_json(bridge.reveal_in_peer(args.url, receiver=args.receiver)),
                file=sys.stdout,
            )
            return 0
        if args.command == "cd-peer-here":
            print(
                ingress_json(bridge.cd_peer_here(args.cwd, receiver=args.receiver)),
                file=sys.stdout,
            )
            return 0
        if args.command == "copy-to-peer":
            print(
                ingress_json(
                    bridge.copy_to_peer(args.paths, destination=args.destination, receiver=args.receiver)
                ),
                file=sys.stdout,
            )
            return 0
        if args.command == "move-to-peer":
            print(
                ingress_json(
                    bridge.move_to_peer(args.paths, destination=args.destination, receiver=args.receiver)
                ),
                file=sys.stdout,
            )
            return 0
        if args.command == "send-hovered-to-peer":
            print(
                ingress_json(bridge.send_hovered_to_peer(args.url, receiver=args.receiver)),
                file=sys.stdout,
            )
            return 0
        if args.command == "send-selected-to-peer":
            print(
                ingress_json(bridge.send_selected_to_peer(args.urls, receiver=args.receiver)),
                file=sys.stdout,
            )
            return 0
    except (BridgeError, PolicyError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"bridge error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2


def _run_wrap(bridge: YaziBridge, *, stdin: Iterable[str] = sys.stdin) -> int:
    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        event = bridge.wrap_wire_line(line)
        print(ingress_json(event), file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
