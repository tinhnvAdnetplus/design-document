"""Private persistent tmux worker for fixed-reference supervised turns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections.abc import Mapping
from pathlib import Path


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


_REQUIRED = {
    "plan": {"summary", "steps", "acceptance_criteria", "risks"},
    "implement": {"summary", "tests", "commit"},
    "review": {"verdict", "summary", "findings"},
}


def _walk(value):
    yield value
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            yield from _walk(json.loads(value))
        except json.JSONDecodeError:
            return


def _valid(task: str, value: Mapping) -> bool:
    required = _REQUIRED.get(task)
    if required is None:
        return True
    if set(value) != required or not isinstance(value.get("summary"), str):
        return False
    arrays = {
        "plan": ("steps", "acceptance_criteria", "risks"),
        "implement": ("tests",),
        "review": ("findings",),
    }[task]
    if any(
        not isinstance(value.get(field), list)
        or not all(isinstance(item, str) for item in value[field])
        for field in arrays
    ):
        return False
    if task == "implement" and not re.fullmatch(r"[0-9a-f]{40}", str(value.get("commit", ""))):
        return False
    return task != "review" or value.get("verdict") in {"approve", "changes_requested"}


def _structured(output: str, task: str) -> dict | None:
    roots = []
    try:
        roots.append(json.loads(output.strip()))
    except json.JSONDecodeError:
        pass
    for line in output.splitlines():
        try:
            roots.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    required = _REQUIRED.get(task)
    for root in roots:
        for node in _walk(root):
            if isinstance(node, Mapping) and (required is None or required.issubset(node)):
                candidate = dict(node)
                if _valid(task, candidate):
                    return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spool", type=Path, required=True)
    parser.add_argument("--identity", required=True)
    args = parser.parse_args(argv)
    args.spool.mkdir(parents=True, exist_ok=True, mode=0o700)
    print(f"AI_RUNTIME_READY {args.identity}", flush=True)
    for line in sys.stdin:
        notice = line.strip()
        if notice == "TERMINATE":
            print("AI_RUNTIME_TERMINATED", flush=True)
            return 0
        match = re.fullmatch(r"TURN ([A-Za-z0-9][A-Za-z0-9._-]{0,127})", notice)
        if not match:
            print("AI_RUNTIME_NOTICE_REJECTED", flush=True)
            continue
        turn_id = match.group(1)
        request_path = args.spool / f"{turn_id}.request.json"
        response_path = args.spool / f"{turn_id}.response.json"
        if response_path.exists():
            print(f"AI_RUNTIME_TURN_PRESENT {turn_id}", flush=True)
            continue
        if not request_path.is_file():
            print(f"AI_RUNTIME_TURN_MISSING {turn_id}", flush=True)
            continue
        request = json.loads(request_path.read_text(encoding="utf-8"))
        started = time.perf_counter_ns()
        timed_out = False
        try:
            result = subprocess.run(
                request["command"],
                cwd=request["cwd"],
                text=True,
                capture_output=True,
                timeout=float(request["timeout_seconds"]) + 5,
                check=False,
            )
            stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            exit_code = None
        _write(response_path, {
            "turn_id": turn_id,
            "prompt_sha256": request["prompt_sha256"],
            "structured_result": _structured(stdout, str(request.get("task", ""))),
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            "stdout_bytes": len(stdout.encode("utf-8")),
            "stderr_bytes": len(stderr.encode("utf-8")),
            "diagnostic_redacted": (
                f"stderr_present bytes={len(stderr.encode('utf-8'))}" if stderr else ""
            ),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
        })
        print(f"AI_RUNTIME_TURN_COMPLETE {turn_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
