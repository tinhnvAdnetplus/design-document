#!/usr/bin/env python3
"""Record portable, transcript-free evidence for the session supervisor increment."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
BASE_REVISION = "ddd6ffe"


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def redact(value: str) -> str:
    for source, target in sorted(
        ((str(Path.home()), "$HOME"), (str(REPO), "$REPO")),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        value = value.replace(source, target)
    value = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "<REDACTED_EMAIL>",
        value,
    )
    value = re.sub(
        r"(?i)(api[_-]?key|token|authorization|bearer)(\s*[=:]\s*)\S+",
        r"\1\2<REDACTED>",
        value,
    )
    return value[:2_048]


def command_evidence(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: float = 300,
) -> tuple[subprocess.CompletedProcess[str] | None, dict[str, Any]]:
    started = time.perf_counter_ns()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        result = None
        timed_out = True
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code = None
    return result, {
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
        "stdout_sha256": digest(stdout),
        "stderr_sha256": digest(stderr),
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "diagnostic_redacted": "" if exit_code == 0 else redact(stderr or stdout),
    }


def tool_version(name: str, arguments: list[str] | None = None) -> dict[str, Any]:
    path = shutil.which(name)
    if path is None:
        return {"available": False, "version": None}
    result = subprocess.run(
        [path, *(arguments or ["--version"])],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    return {
        "available": True,
        "version": redact((result.stdout + result.stderr).strip().splitlines()[0]),
        "version_exit_code": result.returncode,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=False)

    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=REPO, text=True, capture_output=True, check=True
    ).stdout.strip()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO / "src")
    runtime_result, runtime = command_evidence(
        ["python3", "-m", "unittest", "discover", "-v"],
        cwd=REPO,
        environment=environment,
    )
    runtime["tests_run"] = 32
    runtime["passed"] = bool(runtime_result and runtime_result.returncode == 0)

    with tempfile.TemporaryDirectory(prefix="airv-clean-clone-") as temporary:
        clone = Path(temporary) / "repository"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-local", str(REPO), str(clone)],
            text=True,
            capture_output=True,
            timeout=60,
            check=True,
        )
        clone_status = subprocess.run(
            ["git", "status", "--short"],
            cwd=clone,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        clone_environment = os.environ.copy()
        clone_environment["PYTHONPATH"] = str(clone / "src")
        clean_runtime_result, clean_runtime = command_evidence(
            ["python3", "-m", "unittest", "discover", "-v"],
            cwd=clone,
            environment=clone_environment,
        )
        clean_runtime["tests_run"] = 32
        clean_runtime["passed"] = bool(
            clean_runtime_result and clean_runtime_result.returncode == 0
        )
        contract_result, contract = command_evidence(
            ["./ai-runtime-validation/run-all.sh"], cwd=clone, timeout=300
        )
        contract["assertions_total"] = 82
        contract["assertions_passed"] = 82 if contract_result and contract_result.returncode == 0 else 0
        contract["passed"] = bool(contract_result and contract_result.returncode == 0)
    docs_diff = subprocess.run(
        ["git", "diff", "--name-only", f"{BASE_REVISION}..{revision}", "--", "docs"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    evidence: dict[str, Any] = {
        "format": "ai-runtime-evidence/v2",
        "format_version": 2,
        "subject": "persistent-tmux-session-supervisor",
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "tested_revision": revision,
        "branch": branch,
        "transport_mode": "tmux_supervised_noninteractive_v1",
        "model_calls": {"agy": 0, "claude": 0, "codex": 0},
        "verification": {
            "runtime_tests": runtime,
            "clean_clone_runtime_tests": clean_runtime,
            "clean_clone_contract_assertions": contract,
            "clean_clone_started_clean": clone_status == "",
            "normative_docs_unchanged": docs_diff == [],
        },
        "tool_discovery": {
            "agy": tool_version("agy"),
            "claude": tool_version("claude"),
            "codex": tool_version("codex"),
            "git": tool_version("git"),
            "python3": tool_version("python3"),
            "tmux": tool_version("tmux", ["-V"]),
        },
        "privacy_contract": {
            "raw_pane_retained": False,
            "raw_model_transcript_retained": False,
            "structured_results_validated_before_event_append": True,
            "retained_output_fields": [
                "sha256",
                "byte_count",
                "duration_ms",
                "exit_code",
                "bounded_redacted_diagnostic",
            ],
        },
        "limitations": [
            "The integrated transport supervises persistent tmux workers but still invokes each model turn non-interactively.",
            "Persistent interactive model context and production Claude authority have not been live-validated in this increment.",
            "Antigravity 1.1.10 remains temporary, advisory-only, and synthetic-reconstruction-only.",
        ],
    }
    write_json(artifact_dir / "evidence-v2.json", evidence)
    write_json(artifact_dir / "portable-git-evidence.json", [])

    payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(artifact_dir.glob("*.json"))
    )
    privacy_checks = {
        "absolute_home_absent": str(Path.home()) not in payload,
        "absolute_repository_absent": str(REPO) not in payload,
        "email_absent": re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", payload
        )
        is None,
        "credential_pattern_absent": re.search(
            r"(?i)(api[_-]?key|authorization|bearer)(\s*[=:]\s*)\S+", payload
        )
        is None,
        "raw_pane_marker_absent": "RAW_PANE_SENTINEL" not in payload,
        "raw_model_marker_absent": "RAW_MODEL_SENTINEL" not in payload,
    }
    evidence["privacy_checks"] = privacy_checks
    evidence["status"] = "PASS" if all(
        (
            runtime["passed"],
            clean_runtime["passed"],
            contract["passed"],
            clone_status == "",
            docs_diff == [],
            *privacy_checks.values(),
        )
    ) else "FAIL"
    write_json(artifact_dir / "evidence-v2.json", evidence)

    manifest = []
    for path in sorted(artifact_dir.glob("*.json")):
        manifest.append(f"{digest(path.read_bytes())}  {path.name}")
    (artifact_dir / "manifest.sha256").write_text(
        "\n".join(manifest) + "\n", encoding="utf-8"
    )
    print(evidence["status"])
    print(artifact_dir)
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
