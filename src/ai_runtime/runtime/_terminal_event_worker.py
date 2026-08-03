"""Private deterministic runtime client for immutable terminal-event references."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path


def _atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--identity", required=True)
    args = parser.parse_args(argv)
    session = args.state_dir / "terminal-events" / args.session_id
    inbox = session / "inbox"
    outbox = session / "outbox"
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    outbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    print(f"AI_RUNTIME_EVENT_READY {args.identity}", flush=True)
    for line in sys.stdin:
        notice = line.strip()
        if notice == "TERMINATE":
            return 0
        match = re.fullmatch(r"EVENT ([A-Za-z0-9][A-Za-z0-9._-]{0,127})", notice)
        if not match:
            continue
        reference = match.group(1)
        source = inbox / f"{reference}.json"
        target = outbox / f"{reference}.json"
        if target.exists() or not source.exists():
            continue
        intent = json.loads(source.read_text(encoding="utf-8"))
        packet = intent.get("packet")
        if not isinstance(packet, dict) or not isinstance(packet.get("structured_event"), dict):
            _atomic(
                target,
                {
                    "reference_id": reference,
                    "session_id": args.session_id,
                    "intent_sha256": intent.get("intent_sha256"),
                    "event": None,
                },
            )
            continue
        _atomic(
            target,
            {
                "reference_id": reference,
                "session_id": args.session_id,
                "intent_sha256": intent["intent_sha256"],
                "event": packet["structured_event"],
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
