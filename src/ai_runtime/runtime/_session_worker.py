"""Private persistent tmux worker for fixed-reference supervised turns."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


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
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
        })
        print(f"AI_RUNTIME_TURN_COMPLETE {turn_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
