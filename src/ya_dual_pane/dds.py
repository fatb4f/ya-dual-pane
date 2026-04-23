from __future__ import annotations

import json
from typing import Any

from ya_dual_pane.types import DdsEnvelope


class DdsParseError(ValueError):
    """Raised when a DDS wire payload cannot be parsed."""


def parse_wire_line(line: str) -> DdsEnvelope:
    """Parse a raw Yazi DDS stdout line.

    Yazi reports payloads as:
        kind,receiver,sender,{json body}

    We split on the first three commas only so that JSON commas stay intact.
    """

    parts = line.split(",", 3)
    if len(parts) != 4:
        raise DdsParseError(f"expected 4 DDS fields, got {len(parts)}: {line!r}")

    kind, receiver, sender, body_raw = parts
    try:
        body: Any = json.loads(body_raw)
    except json.JSONDecodeError as exc:
        raise DdsParseError(f"invalid DDS body JSON: {body_raw!r}") from exc

    return DdsEnvelope(kind=kind, receiver=receiver, sender=sender, body=body)


def parse_wire_object(obj: dict[str, Any]) -> DdsEnvelope:
    for field in ("kind", "receiver", "sender", "body"):
        if field not in obj:
            raise DdsParseError(f"missing wire field: {field}")
    return DdsEnvelope(
        kind=str(obj["kind"]),
        receiver=str(obj["receiver"]),
        sender=str(obj["sender"]),
        body=obj["body"],
    )
