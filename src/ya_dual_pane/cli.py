from __future__ import annotations

import argparse

from ya_dual_pane.transport import run_stream


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ya-coord")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the coordinator event loop on JSONL stdin")
    run_parser.add_argument("--policy", required=True, help="Path to the runtime policy file (.cue or .json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_stream(args.policy)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
