#!/usr/bin/env python3
"""Bounded, redacted live integration probes for Antigravity and Codex CLIs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


POC_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = POC_ROOT.parents[1]
REPO_ROOT = VALIDATION_ROOT.parent
EVENT_SCHEMA = POC_ROOT / "fixtures" / "event_schema.json"
RESUME_SCHEMA = POC_ROOT / "fixtures" / "resume_schema.json"
MAX_CALLS_PER_CLI = 3


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def redact(value: str, temporary_root: Path | None = None) -> str:
    replacements = {
        str(Path.home()): "$HOME",
        str(REPO_ROOT): "$REPO",
    }
    if temporary_root is not None:
        replacements[str(temporary_root)] = "$FIXTURE"
    redacted = value
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        redacted = redacted.replace(source, target)
    redacted = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", redacted)
    redacted = re.sub(r"(?i)(api[_-]?key|token|authorization|bearer)(\s*[=:]\s*)\S+", r"\1\2<REDACTED>", redacted)
    redacted = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", "<REDACTED_UUID>", redacted)
    redacted = re.sub(r"\b[0-9a-fA-F]{32}\b", "<REDACTED_NONCE>", redacted)
    return redacted[:16_384]


def command_evidence(
    command: list[str],
    *,
    cwd: Path,
    timeout: float,
    temporary_root: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str] | None, dict[str, Any]]:
    started = time.perf_counter_ns()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        result = None
        timed_out = True
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code = None
    duration_ms = (time.perf_counter_ns() - started) / 1_000_000
    evidence = {
        "command": [redact(part, temporary_root) for part in command[:-1]] + ["<PROMPT_REDACTED>"],
        "prompt_sha256": digest(command[-1]),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": round(duration_ms, 3),
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "stdout_sha256": digest(stdout),
        "stderr_sha256": digest(stderr),
        "stdout_excerpt_redacted": redact(stdout, temporary_root),
        "stderr_excerpt_redacted": redact(stderr, temporary_root),
    }
    return result, evidence


def json_nodes(output: str) -> list[Any]:
    nodes: list[Any] = []
    stripped = output.strip()
    if stripped:
        try:
            nodes.append(json.loads(stripped))
        except json.JSONDecodeError:
            pass
    for line in output.splitlines():
        try:
            nodes.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for match in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL | re.IGNORECASE):
        try:
            nodes.append(json.loads(match))
        except json.JSONDecodeError:
            continue
    return nodes


def walk_json(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)
    elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            yield from walk_json(json.loads(value))
        except json.JSONDecodeError:
            return


def find_object(output: str, required_keys: set[str]) -> dict[str, Any] | None:
    for root in json_nodes(output):
        for value in walk_json(root):
            if isinstance(value, dict) and required_keys.issubset(value):
                return value
    return None


def find_session_id(output: str) -> str | None:
    keys = {"conversation_id", "conversationId", "session_id", "sessionId", "thread_id", "threadId"}
    for root in json_nodes(output):
        for value in walk_json(root):
            if isinstance(value, dict):
                for key in keys:
                    candidate = value.get(key)
                    if isinstance(candidate, str) and candidate:
                        return candidate
    return None


def schema_event_valid(value: dict[str, Any] | None) -> bool:
    return bool(
        value
        and isinstance(value.get("event_id"), str)
        and value.get("type") == "feature.requested"
        and value.get("payload") == {"probe": "ack"}
    )


def discovery(
    cli: str,
    help_arguments: list[str],
    temporary_root: Path,
    version_arguments: list[str] | None = None,
) -> dict[str, Any]:
    path = shutil.which(cli)
    if not path:
        return {"available": False, "path": None, "version": None, "capabilities": {}}
    version = subprocess.run(
        [path, *(version_arguments or ["--version"])],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    help_result = subprocess.run([path, *help_arguments], text=True, capture_output=True, timeout=10, check=False)
    help_text = help_result.stdout + "\n" + help_result.stderr
    lowered = help_text.lower()
    if cli == "agy":
        capabilities = {
            "resume_declared": "--conversation" in lowered or "--continue" in lowered,
            "native_fork_declared": "fork" in lowered,
            "synthetic_fork_declared": "--new-project" in lowered,
            "structured_output_declared": "--json-schema" in lowered and "stream-json" in lowered,
            "sandbox_declared": "--sandbox" in lowered,
        }
    elif cli == "codex":
        capabilities = {
            "resume_declared": "resume" in lowered,
            "native_fork_declared": "fork" in lowered,
            "synthetic_fork_declared": True,
            "structured_output_declared": "exec" in lowered,
            "sandbox_declared": "--sandbox" in lowered,
        }
    else:
        capabilities = {}
    return {
        "available": True,
        "path": redact(path, temporary_root),
        "version": redact((version.stdout + version.stderr).strip().splitlines()[0], temporary_root),
        "version_exit_code": version.returncode,
        "help_sha256": digest(help_text),
        "capabilities": capabilities,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(artifact_dir: Path) -> None:
    lines = []
    for path in sorted(item for item in artifact_dir.rglob("*") if item.is_file() and item.name != "manifest.sha256"):
        lines.append(f"{digest(path.read_bytes())}  {path.relative_to(artifact_dir)}")
    (artifact_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="run bounded authenticated model probes")
    mode.add_argument("--discovery-only", action="store_true", help="do not invoke a model")
    args = parser.parse_args()

    timeout = min(max(float(os.environ.get("CLI_PROBE_TIMEOUT_SECONDS", "60")), 5), 60)
    agy_model = os.environ.get("AGY_PROBE_MODEL", "gemini-3.6-flash-low")
    codex_model = os.environ.get("CODEX_PROBE_MODEL", "").strip()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:6]}"
    artifact_dir = POC_ROOT / "artifacts" / run_id
    artifact_dir.mkdir(parents=True)
    git_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    call_counts = {"agy": 0, "codex": 0}

    with tempfile.TemporaryDirectory(prefix="airv-cli-spike-") as temporary:
        fixture = Path(temporary)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=fixture, check=True)
        subprocess.run(["git", "config", "user.email", "probe@example.invalid"], cwd=fixture, check=True)
        subprocess.run(["git", "config", "user.name", "CLI Probe"], cwd=fixture, check=True)
        (fixture / "README.md").write_text("# Isolated CLI probe fixture\n\nNo project data or secrets.\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=fixture, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "probe fixture"], cwd=fixture, check=True)

        discovered = {
            "agy": discovery("agy", ["--help"], fixture),
            "codex": discovery("codex", ["--help"], fixture),
            "tmux": discovery("tmux", ["-V"], fixture, ["-V"]),
        }
        write_json(artifact_dir / "cli-discovery.json", discovered)

        results: dict[str, Any] = {
            "run_id": run_id,
            "captured_at": utc_now(),
            "git_revision": git_revision,
            "mode": "live" if args.live else "discovery-only",
            "limits": {"timeout_seconds": timeout, "max_calls_per_cli": MAX_CALLS_PER_CLI},
            "models": {"agy": agy_model, "codex": codex_model or "cli-default"},
            "discovery": discovered,
            "structured": {},
            "resume": {},
            "tmux": {},
        }

        if args.live and discovered["agy"]["available"] and discovered["codex"]["available"]:
            nonce = uuid.uuid4().hex
            event_prompt = (
                "Remember this harmless nonce for the next turn: " + nonce + ". "
                "Return only a JSON object with event_id='cli-probe', type='feature.requested', "
                "and payload={\"probe\":\"ack\"}. Do not use tools or inspect files."
            )

            agy_command = [
                "agy", "--print", "--sandbox", "--mode", "plan", "--disable-slash-commands",
                "--log-file", "/dev/null", "--model", agy_model, "--output-format", "json",
                "--json-schema", str(EVENT_SCHEMA), "--print-timeout", f"{int(timeout)}s", event_prompt,
            ]
            call_counts["agy"] += 1
            agy_result, agy_evidence = command_evidence(
                agy_command, cwd=fixture, timeout=timeout + 5, temporary_root=fixture
            )
            agy_output = agy_result.stdout if agy_result else ""
            agy_event = find_object(agy_output, {"event_id", "type", "payload"})
            agy_session = find_session_id(agy_output)
            agy_evidence.update({
                "schema_valid": schema_event_valid(agy_event),
                "session_id_present": bool(agy_session),
                "session_id_sha256": digest(agy_session) if agy_session else None,
            })
            results["structured"]["agy"] = agy_evidence

            codex_command = [
                "codex", "--sandbox", "read-only", "--ask-for-approval", "never", "--cd", str(fixture),
            ]
            if codex_model:
                codex_command.extend(["--model", codex_model])
            codex_command.extend([
                "exec", "--skip-git-repo-check", "--ignore-rules", "--json",
                "--output-schema", str(EVENT_SCHEMA), event_prompt,
            ])
            call_counts["codex"] += 1
            codex_result, codex_evidence = command_evidence(
                codex_command, cwd=fixture, timeout=timeout, temporary_root=fixture
            )
            codex_output = codex_result.stdout if codex_result else ""
            codex_event = find_object(codex_output, {"event_id", "type", "payload"})
            codex_session = find_session_id(codex_output)
            codex_evidence.update({
                "schema_valid": schema_event_valid(codex_event),
                "session_id_present": bool(codex_session),
                "session_id_sha256": digest(codex_session) if codex_session else None,
            })
            results["structured"]["codex"] = codex_evidence

            resume_prompt = "Return only JSON with remembered equal to the nonce I asked you to remember."
            if agy_session and call_counts["agy"] < MAX_CALLS_PER_CLI:
                agy_resume_command = [
                    "agy", "--print", "--sandbox", "--mode", "plan", "--disable-slash-commands",
                    "--log-file", "/dev/null", "--model", agy_model, "--output-format", "json",
                    "--json-schema", str(RESUME_SCHEMA), "--conversation", agy_session,
                    "--print-timeout", f"{int(timeout)}s", resume_prompt,
                ]
                call_counts["agy"] += 1
                resumed, evidence = command_evidence(
                    agy_resume_command, cwd=fixture, timeout=timeout + 5, temporary_root=fixture
                )
                remembered = find_object(resumed.stdout if resumed else "", {"remembered"})
                evidence["memory_match"] = bool(remembered and remembered.get("remembered") == nonce)
                results["resume"]["agy"] = evidence
            else:
                results["resume"]["agy"] = {"memory_match": False, "reason": "session_id_unavailable"}

            if codex_session and call_counts["codex"] < MAX_CALLS_PER_CLI:
                codex_resume_command = [
                    "codex", "--sandbox", "read-only", "--ask-for-approval", "never", "--cd", str(fixture),
                    "exec", "resume", "--ignore-rules", "--json", "--output-schema", str(RESUME_SCHEMA),
                    codex_session, resume_prompt,
                ]
                call_counts["codex"] += 1
                resumed, evidence = command_evidence(
                    codex_resume_command, cwd=fixture, timeout=timeout, temporary_root=fixture
                )
                remembered = find_object(resumed.stdout if resumed else "", {"remembered"})
                evidence["memory_match"] = bool(remembered and remembered.get("remembered") == nonce)
                results["resume"]["codex"] = evidence
            else:
                results["resume"]["codex"] = {"memory_match": False, "reason": "session_id_unavailable"}

            socket = f"airv-cli-{os.getpid()}-{uuid.uuid4().hex[:6]}"
            tmux = ["tmux", "-L", socket]
            agy_tmux_command = [
                "agy", "--sandbox", "--mode", "plan", "--disable-slash-commands", "--log-file", "/dev/null",
                "--model", agy_model, "--prompt-interactive",
                "Compute 193 plus 251. Respond with only the decimal result.",
            ]
            codex_tmux_command = [
                "codex", "--sandbox", "read-only", "--ask-for-approval", "never", "--cd", str(fixture),
                "--no-alt-screen",
            ]
            if codex_session:
                codex_tmux_command.extend([
                    "fork", codex_session, "Compute 173 plus 249. Respond with only the decimal result."
                ])
            else:
                codex_tmux_command.append("Compute 173 plus 249. Respond with only the decimal result.")
            call_counts["agy"] += 1
            call_counts["codex"] += 1
            tmux_started = time.perf_counter_ns()
            captures = {"agy": "", "codex": ""}
            detected = {"agy": False, "codex": False}
            try:
                subprocess.run(
                    [*tmux, "new-session", "-d", "-s", "agy-probe", "-c", str(fixture), shlex.join(agy_tmux_command)],
                    check=True, timeout=10,
                )
                subprocess.run([*tmux, "set-option", "-t", "agy-probe", "remain-on-exit", "on"], check=True)
                subprocess.run(
                    [*tmux, "new-session", "-d", "-s", "codex-probe", "-c", str(fixture), shlex.join(codex_tmux_command)],
                    check=True, timeout=10,
                )
                subprocess.run([*tmux, "set-option", "-t", "codex-probe", "remain-on-exit", "on"], check=True)
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline and not all(detected.values()):
                    for cli, session, marker in [
                        ("agy", "agy-probe", "444"),
                        ("codex", "codex-probe", "422"),
                    ]:
                        captured = subprocess.run(
                            [*tmux, "capture-pane", "-p", "-S", "-200", "-t", f"{session}:0.0"],
                            text=True, capture_output=True, check=False,
                        )
                        captures[cli] = captured.stdout + captured.stderr
                        detected[cli] = marker in captures[cli]
                    if not all(detected.values()):
                        time.sleep(1)
            finally:
                cleanup = subprocess.run([*tmux, "kill-server"], text=True, capture_output=True, check=False)
            tmux_duration = (time.perf_counter_ns() - tmux_started) / 1_000_000
            results["tmux"] = {
                cli: {
                    "response_detected": detected[cli],
                    "duration_ms": round(tmux_duration, 3),
                    "captured_output_bytes": len(captures[cli].encode("utf-8")),
                    "captured_output_sha256": digest(captures[cli]),
                    "launch_mode": "interactive" if cli == "agy" else (
                        "native_fork" if codex_session else "interactive"
                    ),
                }
                for cli in ("agy", "codex")
            }
            results["tmux"]["cleanup_exit_code"] = cleanup.returncode

        fixture_status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=fixture, text=True, capture_output=True, check=True
        ).stdout
        results["fixture_clean"] = not bool(fixture_status.strip())
        results["fixture_status_sha256"] = digest(fixture_status)
        results["call_counts"] = call_counts

        redaction_payload = json.dumps(results, sort_keys=True)
        results["redaction_checks"] = {
            "home_path_absent": str(Path.home()) not in redaction_payload,
            "fixture_path_absent": str(fixture) not in redaction_payload,
            "nonce_absent": not args.live or nonce not in redaction_payload,
            "email_absent": "probe@example.invalid" not in redaction_payload,
            "tmux_capture_not_retained": all(
                "captured_output_excerpt_redacted" not in results["tmux"].get(cli, {})
                for cli in ("agy", "codex")
            ),
        }

    available = all(results["discovery"].get(cli, {}).get("available") for cli in ("agy", "codex"))
    if args.discovery_only:
        decision = "INCONCLUSIVE"
    elif not available:
        decision = "INCONCLUSIVE"
    else:
        live_gates = [
            results["structured"].get(cli, {}).get("schema_valid", False) for cli in ("agy", "codex")
        ] + [
            results["resume"].get(cli, {}).get("memory_match", False) for cli in ("agy", "codex")
        ] + [
            results["tmux"].get(cli, {}).get("response_detected", False) for cli in ("agy", "codex")
        ] + [
            results["fixture_clean"],
            results["tmux"].get("cleanup_exit_code") == 0,
            all(results["redaction_checks"].values()),
        ]
        decision = "PHASE_3_APPROVED_WITH_ADAPTATIONS" if all(live_gates) else "PHASE_3_BLOCKED"
    results["decision"] = decision
    results["adaptations"] = [
        "Replace the Claude adapter with a version-bound Antigravity adapter for Phase 2C.",
        "Use synthetic Git-derived reconstruction because agy 1.1.10 exposes no native fork flag.",
        "Prefer JSON Schema output channels over terminal scraping for protocol events.",
    ]
    write_json(artifact_dir / "phase2c-decision-report.json", results)

    markdown = [
        "# Phase 2C Real CLI Decision", "",
        f"- Decision: **{decision}**",
        f"- Run: `{run_id}`",
        f"- Git revision: `{git_revision}`",
        f"- Calls: agy `{call_counts['agy']}/{MAX_CALLS_PER_CLI}`, Codex `{call_counts['codex']}/{MAX_CALLS_PER_CLI}`",
        "", "## Gates", "",
        "| Gate | Antigravity | Codex |", "| --- | --- | --- |",
        f"| Available | {discovered['agy']['available']} | {discovered['codex']['available']} |",
        f"| Structured event | {results['structured'].get('agy', {}).get('schema_valid', False)} | {results['structured'].get('codex', {}).get('schema_valid', False)} |",
        f"| Resume memory | {results['resume'].get('agy', {}).get('memory_match', False)} | {results['resume'].get('codex', {}).get('memory_match', False)} |",
        f"| tmux response | {results['tmux'].get('agy', {}).get('response_detected', False)} | {results['tmux'].get('codex', {}).get('response_detected', False)} |",
        "", "## Required adaptations", "",
    ] + [f"- {value}" for value in results["adaptations"]]
    (artifact_dir / "phase2c-decision-report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    write_manifest(artifact_dir)

    result_lines = [
        "# PoC 11 — Real CLI Integration Result", "",
        f"- Decision: **{decision}**",
        f"- Executed at: `{results['captured_at']}`",
        f"- Git revision: `{git_revision}`",
        f"- Evidence: [`artifacts/{run_id}/phase2c-decision-report.md`](artifacts/{run_id}/phase2c-decision-report.md)",
        "", "Raw CLI output was not retained; the evidence contains hashes and redacted excerpts.",
    ]
    (POC_ROOT / "RESULT.md").write_text("\n".join(result_lines) + "\n", encoding="utf-8")
    print(f"Decision: {decision}")
    print(f"Evidence: {artifact_dir}")
    return 0 if decision == "PHASE_3_APPROVED_WITH_ADAPTATIONS" or args.discovery_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
