from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from ya_dual_pane.coordinator import Coordinator
from ya_dual_pane.dds import DdsParseError, parse_wire_line, parse_wire_object
from ya_dual_pane.policy import PolicyError, load_policy
from ya_dual_pane.types import AuthorityMeta, IngressEvent


class InputError(ValueError):
    """Raised when a runtime input line is malformed."""


def parse_input_line(line: str) -> IngressEvent:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON input: {line!r}") from exc

    if not isinstance(payload, dict):
        raise InputError("input line must be a JSON object")

    if "wire" in payload:
        wire = parse_wire_object(payload["wire"])
    elif "wire_raw" in payload:
        wire = parse_wire_line(str(payload["wire_raw"]))
    else:
        raise InputError("input line must contain 'wire' or 'wire_raw'")

    meta_raw = payload.get("meta")
    if not isinstance(meta_raw, dict):
        raise InputError("input line must contain meta object")

    try:
        meta = AuthorityMeta(
            event_id=str(meta_raw["event_id"]),
            origin_seq=int(meta_raw["origin_seq"]),
            lease_epoch=int(meta_raw["lease_epoch"]),
            causal_id=(None if meta_raw.get("causal_id") is None else str(meta_raw["causal_id"])),
        )
    except KeyError as exc:
        raise InputError(f"missing meta field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise InputError("meta fields must be coercible to the required scalar types") from exc

    return IngressEvent(wire=wire, meta=meta)


def _error_outcome(*, lineno: int, exc: Exception) -> dict[str, Any]:
    return {
        "decision": "reject",
        "reason": f"input error on line {lineno}: {exc}",
        "error": str(exc),
        "wire": None,
        "meta": None,
        "state": None,
    }


def run_stream(
    policy_path: str,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    try:
        policy = load_policy(policy_path)
    except (OSError, PolicyError, json.JSONDecodeError) as exc:
        print(f"policy error: {exc}", file=stderr)
        return 2

    coordinator = Coordinator(policy)

    for lineno, raw_line in enumerate(stdin, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = parse_input_line(line)
            outcome = coordinator.adjudicate(event)
        except (InputError, DdsParseError) as exc:
            print(
                json.dumps(
                    _error_outcome(lineno=lineno, exc=exc),
                    sort_keys=True,
                ),
                file=stdout,
            )
            continue

        print(json.dumps(outcome.as_dict(), sort_keys=True), file=stdout)

    return 0
