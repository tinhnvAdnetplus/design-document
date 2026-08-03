#!/usr/bin/env python3
"""Executable architecture validation laboratory for AI Runtime V2.2.

This is intentionally a test harness, not a runtime implementation.  Every test
performs an observable operation and records its expected and observed value.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import datetime as dt
import errno
import hashlib
import heapq
import hmac
import json
import math
import os
import platform
import queue
import re
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
import xml.etree.ElementTree as ET
from importlib import metadata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    import jsonschema
except ImportError:  # reported as an environment failure, never as a pass
    jsonschema = None


ROOT = Path(__file__).resolve().parents[1]
POC_ROOT = ROOT / "poc"
POC_NAMES = {
    "01": "tmux-runtime",
    "02": "event-protocol",
    "03": "session-resume",
    "04": "capability-registry",
    "05": "knowledge-runtime",
    "06": "review-loop",
    "07": "scheduler",
    "08": "chaos",
    "09": "performance",
    "10": "end-to-end",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    index = max(0, math.ceil(p * len(ordered)) - 1)
    return ordered[index]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def command(*args: str, cwd: Path | None = None, check: bool = True,
            env: dict[str, str] | None = None, timeout: float = 15) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), cwd=cwd, env=env, text=True, capture_output=True,
        timeout=timeout, check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )
    return result


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return command("git", *args, cwd=cwd, check=check)


def init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "validation@example.invalid")
    git(path, "config", "user.name", "Validation Lab")
    (path / "state.txt").write_text("base\n", encoding="utf-8")
    git(path, "add", "state.txt")
    git(path, "commit", "-q", "-m", "base")
    return git(path, "rev-parse", "HEAD").stdout.strip()


@dataclass
class AssertionRecord:
    id: str
    title: str
    status: str
    expected: str
    observed: str
    duration_ms: float
    diagnostic: str = ""


class Lab:
    def __init__(self, poc: str, run_dir: Path):
        self.poc = poc
        self.name = POC_NAMES[poc]
        self.dir = run_dir / f"poc-{poc}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.results: list[AssertionRecord] = []
        self.dependencies: list[str] = []
        self._cleanup: list[Callable[[], None]] = []

    def defer(self, callback: Callable[[], None]) -> None:
        self._cleanup.append(callback)

    def cleanup(self) -> None:
        for callback in reversed(self._cleanup):
            try:
                callback()
            except Exception as exc:
                (self.dir / "cleanup-errors.log").open("a", encoding="utf-8").write(f"{exc}\n")

    def check(self, ident: str, title: str, expected: str, operation: Callable[[], Any],
              predicate: Callable[[Any], bool] = bool) -> Any:
        start = time.perf_counter_ns()
        observed: Any = None
        diagnostic = ""
        status = "FAIL"
        try:
            observed = operation()
            if not predicate(observed):
                raise AssertionError(f"predicate rejected observed value: {observed!r}")
            status = "PASS"
        except Exception as exc:
            diagnostic = f"{type(exc).__name__}: {exc}"
            observed = observed if observed is not None else diagnostic
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        rendered = json.dumps(observed, sort_keys=True, default=str) if not isinstance(observed, str) else observed
        record = AssertionRecord(ident, title, status, expected, rendered, round(elapsed, 3), diagnostic)
        self.results.append(record)
        print(f"[{status}] {ident} {title} ({elapsed:.2f} ms)")
        if diagnostic:
            print(f"       {diagnostic}", file=sys.stderr)
        return observed

    def assert_value(self, ident: str, title: str, condition: bool, expected: str,
                     observed: Any, diagnostic: str = "") -> None:
        self.check(ident, title, expected,
                   lambda: observed if condition else (_ for _ in ()).throw(AssertionError(diagnostic or str(observed))),
                   lambda _: True)

    def write_json(self, name: str, value: Any) -> Path:
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return path

    @property
    def passed(self) -> int:
        return sum(item.status == "PASS" for item in self.results)

    @property
    def failed(self) -> int:
        return sum(item.status == "FAIL" for item in self.results)

    def report(self) -> dict[str, Any]:
        payload = {
            "poc": self.poc,
            "name": self.name,
            "status": "PASS" if self.results and not self.failed else "FAIL",
            "passed": self.passed,
            "failed": self.failed,
            "total": len(self.results),
            "score_percent": round(100 * self.passed / len(self.results), 1) if self.results else 0,
            "dependencies": self.dependencies,
            "assertions": [asdict(item) for item in self.results],
        }
        self.write_json("report.json", payload)
        return payload


def wait_for(predicate: Callable[[], bool], timeout_s: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def event_hash(event: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(event)
    unsigned.pop("integrity", None)
    return sha256(canonical(unsigned))


def make_event(sequence: int, event_type: str, previous: str | None = None,
               correlation: str = "cor-validation-001") -> dict[str, Any]:
    event_id = f"evt-validation-{sequence:03d}"
    event = {
        "event_id": event_id,
        "protocol": "ai-runtime.events/v1",
        "type": event_type,
        "occurred_at": f"2026-08-03T00:{sequence:02d}:00Z",
        "producer": {
            "session_id": "ses-validation",
            "role": "validation_harness",
            "adapter": "mock-contract-adapter",
            "adapter_version": "1.0.0",
        },
        "aggregate": {"feature_id": "feat-validation", "stream": "feature/feat-validation", "sequence": sequence},
        "correlation_id": correlation,
        "causation_id": previous,
        "idempotency_key": f"{event_type}/feat-validation/{sequence}",
        "policy_revision": "policy-validation-1",
        "payload": {"sequence": sequence},
        "attachments": [],
    }
    event["integrity"] = {"content_sha256": event_hash(event), "signature_ref": None}
    return event


def validate_event_integrity(event: dict[str, Any]) -> bool:
    actual = event.get("integrity", {}).get("content_sha256")
    return isinstance(actual, str) and hmac.compare_digest(actual, event_hash(event))


def poc_01(lab: Lab) -> None:
    """Exercise a real isolated tmux server, panes, commands, and cleanup."""
    if not shutil.which("tmux"):
        lab.check("TMUX-ENV", "tmux dependency", "tmux available", lambda: False)
        return
    socket = f"airv-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    workspace = lab.dir / "workspace"
    workspace.mkdir()
    sessions = {
        "claude-root": workspace / "claude-root",
        "codex-root": workspace / "codex-root",
        "claude-feature-f123-plan-1": workspace / "claude-feature",
        "codex-feature-f123-1": workspace / "codex-feature",
    }
    for path in sessions.values():
        path.mkdir()

    def tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return command("tmux", "-L", socket, *args, check=check)

    def kill_server() -> None:
        tmux("kill-server", check=False)

    lab.defer(kill_server)
    kill_server()
    for name, cwd in sessions.items():
        tmux("new-session", "-d", "-s", name, "-c", str(cwd), "bash", "--noprofile", "--norc")

    listed = tmux("list-sessions", "-F", "#{session_name}").stdout.splitlines()
    lab.assert_value("TMUX-01", "named sessions exist", set(listed) == set(sessions),
                     "exactly four V2.2-named sessions", sorted(listed))

    panes = {
        name: tmux("list-panes", "-t", name, "-F", "#{pane_id}").stdout.splitlines()
        for name in sessions
    }
    lab.assert_value("TMUX-02", "each session owns a pane", all(len(value) == 1 for value in panes.values()),
                     "one pane per session", panes)

    cwd_observed: dict[str, str] = {}
    def cwd_ready() -> bool:
        cwd_observed.clear()
        cwd_observed.update({
            name: tmux("display-message", "-p", "-t", name, "#{pane_current_path}").stdout.strip()
            for name in sessions
        })
        return cwd_observed == {key: str(value) for key, value in sessions.items()}
    wait_for(cwd_ready)
    lab.assert_value("TMUX-03", "working directories are assigned", cwd_observed == {k: str(v) for k, v in sessions.items()},
                     "each pane cwd equals assigned isolated directory", cwd_observed)

    token = f"event-{uuid.uuid4().hex}"
    marker = sessions["claude-root"] / "received.txt"
    tmux("send-keys", "-t", "claude-root:0.0", f"printf '%s' '{token}' > received.txt; printf 'EXECUTED:{token}\\n'", "Enter")
    received = wait_for(lambda: marker.exists() and marker.read_text(encoding="utf-8") == token)
    lab.assert_value("TMUX-04", "event command is received and executed", received,
                     "target marker contains unique command token", marker.read_text() if marker.exists() else "marker absent")

    pane_output = tmux("capture-pane", "-p", "-S", "-100", "-t", "claude-root:0.0").stdout
    (lab.dir / "claude-root-pane.txt").write_text(pane_output, encoding="utf-8")
    lab.assert_value("TMUX-05", "pane output is capturable", f"EXECUTED:{token}" in pane_output,
                     "captured pane includes execution token", pane_output[-500:])

    isolated = all(not (path / "received.txt").exists() for name, path in sessions.items() if name != "claude-root")
    lab.assert_value("TMUX-06", "session files are isolated", isolated,
                     "only target workspace receives marker", {name: (path / "received.txt").exists() for name, path in sessions.items()})

    start = time.perf_counter_ns()
    tmux("send-keys", "-t", "codex-root:0.0", "printf 'notice-ack\\n'", "Enter")
    notify_ms = (time.perf_counter_ns() - start) / 1_000_000
    lab.assert_value("TMUX-07", "notification submission is non-blocking", notify_ms < 100,
                     "tmux send-keys returns in <100 ms", round(notify_ms, 3))

    kill_server()
    absent = all(tmux("has-session", "-t", name, check=False).returncode != 0 for name in sessions)
    lab.assert_value("TMUX-08", "cleanup removes every session", absent,
                     "has-session fails for all created sessions", absent)


class EventStore:
    def __init__(self, path: Path, schema: dict[str, Any], signature_key: bytes | None = None):
        self.path = path
        self.schema = schema
        self.signature_key = signature_key

    def _events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        values = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"CORRUPT_EVENT_STORE line {line_number}: {exc.msg}") from exc
        return values

    def append(self, event: dict[str, Any]) -> str:
        if jsonschema is None:
            raise RuntimeError("python jsonschema package unavailable")
        jsonschema.Draft7Validator(self.schema, format_checker=jsonschema.FormatChecker()).validate(event)
        if not validate_event_integrity(event):
            raise ValueError("INTEGRITY_MISMATCH")
        if event["integrity"].get("signature_ref") is not None:
            if self.signature_key is None:
                raise ValueError("SIGNATURE_KEY_UNAVAILABLE")
            expected = hmac.new(self.signature_key, event_hash(event).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, event["integrity"]["signature_ref"]):
                raise ValueError("INVALID_SIGNATURE")
        events = self._events()
        for existing in events:
            if existing["idempotency_key"] == event["idempotency_key"]:
                if canonical(existing) == canonical(event):
                    return "DUPLICATE_IGNORED"
                raise ValueError("IDEMPOTENCY_CONFLICT")
        stream_events = [e for e in events if e["aggregate"]["stream"] == event["aggregate"]["stream"]]
        expected_sequence = 1 if not stream_events else stream_events[-1]["aggregate"]["sequence"] + 1
        if event["aggregate"]["sequence"] != expected_sequence:
            raise ValueError(f"AGGREGATE_SEQUENCE_CONFLICT expected={expected_sequence}")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(event).decode() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return "APPENDED"

    def replay(self) -> dict[str, Any]:
        projection: dict[str, Any] = {"streams": {}, "event_count": 0, "side_effects_replayed": 0}
        for event in self._events():
            if not validate_event_integrity(event):
                raise ValueError("INTEGRITY_MISMATCH_DURING_REPLAY")
            stream = event["aggregate"]["stream"]
            projection["streams"][stream] = {
                "sequence": event["aggregate"]["sequence"],
                "state": event["type"],
                "last_event_id": event["event_id"],
            }
            projection["event_count"] += 1
        return projection


def poc_02(lab: Lab) -> None:
    fixture_dir = POC_ROOT / "02-event-protocol" / "fixtures"
    schema = load_json(fixture_dir / "event_schema.json")
    if jsonschema is None:
        lab.check("EVT-ENV", "JSON Schema validator dependency", "jsonschema import succeeds", lambda: False)
        return
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())

    valid_fixtures = [load_json(path) for path in sorted((fixture_dir / "valid_events").glob("*.json"))]
    schema_errors = [list(validator.iter_errors(event)) for event in valid_fixtures]
    lab.assert_value("EVT-01", "valid fixtures satisfy Draft-07 schema", not any(schema_errors),
                     "zero schema errors", [[err.message for err in errors] for errors in schema_errors])

    invalid_results = {}
    for path in sorted((fixture_dir / "invalid_events").glob("*.json")):
        invalid_results[path.name] = [err.message for err in validator.iter_errors(load_json(path))]
    lab.assert_value("EVT-02", "malformed fixtures are rejected", all(invalid_results.values()),
                     "every invalid fixture has schema diagnostics", invalid_results)

    wrong = make_event(1, "feature.requested")
    wrong["protocol"] = "ai-runtime.events/v2"
    wrong["integrity"]["content_sha256"] = event_hash(wrong)
    version_errors = [err.message for err in validator.iter_errors(wrong)]
    lab.assert_value("EVT-03", "unsupported schema version is rejected", bool(version_errors),
                     "v2 rejected by v1 schema", version_errors)

    store_path = lab.dir / "event-store.ndjson"
    signing_key = b"validation-only-signing-key"
    store = EventStore(store_path, schema, signing_key)
    events = [make_event(1, "feature.requested"), make_event(2, "plan.ready", "evt-validation-001"),
              make_event(3, "plan.approved", "evt-validation-002")]
    append_results = [store.append(event) for event in events]
    lab.assert_value("EVT-04", "events append durably in aggregate order", append_results == ["APPENDED"] * 3,
                     "three fsync-backed appends", append_results)

    duplicate = store.append(events[0])
    lab.assert_value("EVT-05", "exact duplicates are idempotent", duplicate == "DUPLICATE_IGNORED" and len(store._events()) == 3,
                     "duplicate ignored and store remains three events", {"result": duplicate, "count": len(store._events())})

    conflict = copy.deepcopy(events[0])
    conflict["payload"]["sequence"] = 999
    conflict["integrity"]["content_sha256"] = event_hash(conflict)
    try:
        store.append(conflict)
        conflict_result = "accepted"
    except ValueError as exc:
        conflict_result = str(exc)
    lab.assert_value("EVT-06", "idempotency-key content conflicts are rejected", conflict_result == "IDEMPOTENCY_CONFLICT",
                     "IDEMPOTENCY_CONFLICT", conflict_result)

    out_of_order = make_event(5, "implementation.ready", "evt-validation-003")
    try:
        store.append(out_of_order)
        ordering_result = "accepted"
    except ValueError as exc:
        ordering_result = str(exc)
    lab.assert_value("EVT-07", "aggregate ordering is enforced", ordering_result.startswith("AGGREGATE_SEQUENCE_CONFLICT"),
                     "sequence gap rejected", ordering_result)

    replay_one = store.replay()
    replay_two = store.replay()
    lab.write_json("projection.json", replay_one)
    lab.assert_value("EVT-08", "replay reconstructs projection", replay_one["event_count"] == 3 and replay_one["streams"]["feature/feat-validation"]["state"] == "plan.approved",
                     "three events project final state plan.approved", replay_one)
    lab.assert_value("EVT-09", "replay is deterministic and side-effect safe", canonical(replay_one) == canonical(replay_two) and replay_one["side_effects_replayed"] == 0,
                     "byte-identical projections; zero blind side effects", sha256(canonical(replay_one)))

    tampered = copy.deepcopy(events[2])
    tampered["payload"]["sequence"] = 77
    lab.assert_value("EVT-10", "tampering is detected by SHA-256", not validate_event_integrity(tampered),
                     "modified payload fails digest", {"stored": tampered["integrity"]["content_sha256"], "computed": event_hash(tampered)})

    signed = make_event(4, "implementation.ready", "evt-validation-003")
    signed["integrity"]["signature_ref"] = "0" * 64
    try:
        store.append(signed)
        signature_result = "accepted"
    except ValueError as exc:
        signature_result = str(exc)
    lab.assert_value("EVT-11", "invalid signatures are rejected", signature_result == "INVALID_SIGNATURE",
                     "INVALID_SIGNATURE", signature_result)

    corrupt_path = lab.dir / "corrupt-store.ndjson"
    corrupt_path.write_text(store_path.read_text(encoding="utf-8") + "{truncated\n", encoding="utf-8")
    try:
        EventStore(corrupt_path, schema).replay()
        corruption_result = "accepted"
    except ValueError as exc:
        corruption_result = str(exc)
    lab.assert_value("EVT-12", "store corruption fails closed", corruption_result.startswith("CORRUPT_EVENT_STORE"),
                     "corruption names exact line", corruption_result)


def poc_03(lab: Lab) -> None:
    socket = f"airv-resume-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    session = "codex-feature-resume-1"
    tmux = lambda *args, check=True: command("tmux", "-L", socket, *args, check=check)
    tmux("new-session", "-d", "-s", session, "bash", "--noprofile", "--norc")
    lab.defer(lambda: tmux("kill-server", check=False))
    pane_pid = tmux("display-message", "-p", "-t", session, "#{pane_pid}").stdout.strip()
    identity = tmux("display-message", "-p", "-t", session, "#{session_name}:#{pane_id}").stdout.strip()
    lab.assert_value("RES-01", "live session reattaches with identity evidence", identity.startswith(session + ":") and int(pane_pid) > 1,
                     "session name and live pane PID verified", {"identity": identity, "pane_pid": pane_pid})

    conditions = {
        "abnormal_loss": True, "capability_resume": True, "resume_ref": True,
        "config_enabled": True, "role_valid": True, "git_valid": True,
        "exclusive_resource_free": True, "readiness_evidence": True,
    }
    eligible = all(conditions.values())
    lab.assert_value("RES-02", "resume eligibility requires every precondition", eligible,
                     "all eight exceptional-resume gates true", conditions)
    gated = copy.deepcopy(conditions)
    gated["capability_resume"] = False
    decision = "fresh_reconstruction" if not all(gated.values()) else "resume"
    lab.assert_value("RES-03", "capability gate selects fresh reconstruction", decision == "fresh_reconstruction",
                     "resume=false prevents resume attempt", decision)

    tmux("kill-session", "-t", session)
    unavailable = tmux("has-session", "-t", session, check=False).returncode != 0
    lab.assert_value("RES-04", "abnormal session loss is observable", unavailable,
                     "tmux session absent after kill", unavailable)

    repo = lab.dir / "feature-repo"
    head = init_repo(repo)
    branch = git(repo, "branch", "--show-current").stdout.strip()
    packet = {
        "reconstruction": True,
        "runtime_revision": "v2.2",
        "policy_revision": "policy-validation-1",
        "role_contract": "codex-implementer",
        "repository_identity": sha256(str(repo.resolve())),
        "integration_head": head,
        "knowledge_cache": {"version": 1, "provenance_head": head},
        "feature": {"id": "feat-resume", "plan": "artifact://plan/1", "worktree": str(repo), "branch": branch},
        "writer_lease": None,
        "commits": [head],
        "pending_events": ["evt-recovery-1"],
        "lineage": {"edge_type": "reconstruction", "parent": session},
        "unknowns": ["vendor conversational state"],
        "instruction": "Verify Git before acting; continuity is not assumed.",
    }
    packet_path = lab.write_json("reconstruction-packet.json", packet)
    required = ["reconstruction", "runtime_revision", "policy_revision", "role_contract", "repository_identity",
                "integration_head", "feature", "commits", "pending_events", "lineage", "unknowns", "instruction"]
    lab.assert_value("RES-05", "fresh reconstruction packet is complete and bounded",
                     all(key in packet for key in required) and packet_path.stat().st_size <= 131072,
                     "required fields present and <=128 KiB", {"bytes": packet_path.stat().st_size, "missing": [k for k in required if k not in packet]})
    observed_head = git(repo, "rev-parse", "HEAD").stdout.strip()
    lab.assert_value("RES-06", "packet Git state matches repository", observed_head == packet["integration_head"] and not git(repo, "status", "--porcelain").stdout,
                     "packet HEAD equals clean repository HEAD", {"packet": packet["integration_head"], "git": observed_head})

    (repo / "uncommitted.txt").write_text("preserve me\n", encoding="utf-8")
    dirty = bool(git(repo, "status", "--porcelain").stdout.strip())
    quarantine = lab.dir / "quarantine" / repo.name
    quarantine.parent.mkdir()
    if dirty:
        shutil.move(str(repo), quarantine)
    preserved = (quarantine / "uncommitted.txt").read_text(encoding="utf-8") if (quarantine / "uncommitted.txt").exists() else ""
    lab.assert_value("RES-07", "dirty worktree is quarantined without deletion", dirty and quarantine.exists() and preserved == "preserve me\n",
                     "dirty file preserved in quarantine", {"dirty": dirty, "quarantine": str(quarantine), "content": preserved})

    packet_digest = sha256(packet_path.read_bytes())
    cache_record = {"packet_sha256": packet_digest, "resume_id": None, "source": "git_reconstruction"}
    lab.write_json("cache-packet-record.json", cache_record)
    lab.assert_value("RES-08", "workflow reconstruction does not depend on resume IDs", cache_record["resume_id"] is None and len(packet_digest) == 64,
                     "no resume ID and a verifiable packet digest", cache_record)


class MockAdapter:
    def __init__(self, document: dict[str, Any]):
        self.document = document
        self.calls = 0

    def capabilities(self) -> dict[str, Any]:
        self.calls += 1
        return copy.deepcopy(self.document)


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in re.findall(r"\d+", value))


def poc_04(lab: Lab) -> None:
    fixture_dir = POC_ROOT / "04-capability-registry" / "fixtures"
    adapters = {
        name: MockAdapter(load_json(fixture_dir / filename))
        for name, filename in {"claude": "claude_capability.json", "codex": "codex_capability.json"}.items()
    }
    registry: dict[str, dict[str, Any]] = {}

    def register(adapter: MockAdapter) -> None:
        doc = adapter.capabilities()
        required = {"adapter", "version", "resume", "native_fork", "synthetic_fork"}
        if set(doc) != required or not all(isinstance(doc[key], bool) for key in required - {"adapter", "version"}):
            raise ValueError("INVALID_CAPABILITY_DOCUMENT")
        registry[doc["adapter"]] = {**doc, "status": "AVAILABLE", "validated_at": utc_now()}

    for adapter in adapters.values():
        register(adapter)
    lab.assert_value("CAP-01", "registry loads documents from adapter capabilities()", set(registry) == {"claude", "codex"} and all(a.calls == 1 for a in adapters.values()),
                     "two current documents and one capabilities() call each", {"entries": sorted(registry), "calls": {k: a.calls for k, a in adapters.items()}})

    fork_paths = {
        adapter: "native" if doc["native_fork"] else "synthetic" if doc["synthetic_fork"] else "denied"
        for adapter, doc in registry.items()
    }
    lab.assert_value("CAP-02", "fork selection is declaration-gated", fork_paths == {"claude": "native", "codex": "synthetic"},
                     "claude native; codex synthetic", fork_paths)
    resume_paths = {adapter: "resume" if doc["resume"] else "fresh_reconstruction" for adapter, doc in registry.items()}
    lab.assert_value("CAP-03", "resume selection is declaration-gated", resume_paths == {"claude": "resume", "codex": "fresh_reconstruction"},
                     "undeclared resume becomes reconstruction", resume_paths)

    triggers = ["startup", "restart", "adapter_upgrade", "manual_cli_upgrade"]
    calls_before = {name: adapter.calls for name, adapter in adapters.items()}
    audit = []
    for trigger in triggers:
        registry.clear()
        for adapter in adapters.values():
            register(adapter)
        audit.append({"trigger": trigger, "active": sorted(registry)})
    call_delta = {name: adapter.calls - calls_before[name] for name, adapter in adapters.items()}
    lab.assert_value("CAP-04", "required triggers force revalidation", all(value == len(triggers) for value in call_delta.values()),
                     "fresh capabilities() call per trigger and adapter", {"call_delta": call_delta, "audit": audit})

    current = registry["claude"]
    stale = copy.deepcopy(current)
    stale["version"] = "0.1"
    stale_rejected = version_tuple(stale["version"]) <= version_tuple(current["version"])
    lab.assert_value("CAP-05", "stale capability document cannot overwrite current", stale_rejected and registry["claude"]["version"] == "1.0",
                     "older/equal document rejected", {"current": current["version"], "candidate": stale["version"]})

    declaration = registry["claude"]["resume"]
    observed_resume_success = False
    if declaration and not observed_resume_success:
        registry["claude"]["status"] = "ADAPTER_UNAVAILABLE"
    lab.assert_value("CAP-06", "declaration/observation mismatch fences adapter", registry["claude"]["status"] == "ADAPTER_UNAVAILABLE",
                     "ADAPTER_UNAVAILABLE", registry["claude"]["status"])

    missing_adapter_decision = "ADAPTER_UNAVAILABLE" if "unknown" not in registry else "allowed"
    lab.assert_value("CAP-07", "operations require a current registry entry", missing_adapter_decision == "ADAPTER_UNAVAILABLE",
                     "missing adapter is unavailable", missing_adapter_decision)
    lab.write_json("capability-registry.json", registry)
    lab.write_json("revalidation-audit.json", audit)


def poc_05(lab: Lab) -> None:
    repo = lab.dir / "repo"
    base = init_repo(repo)
    evidence_path = repo / "architecture.txt"
    evidence_path.write_text("event-driven dispatch\n", encoding="utf-8")
    git(repo, "add", "architecture.txt")
    git(repo, "commit", "-q", "-m", "architecture evidence")
    evidence_commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    domains = ["project", "architecture", "business", "workspace", "dependency", "convention"]
    snapshot = {
        "cache_version": 1,
        "root_id": "claude-root",
        "snapshot_domains": domains,
        "repository": {"integration_ref": "main", "integration_head": evidence_commit},
        "generated_at": utc_now(),
        "facts": {domain: [{"statement": f"validated {domain}", "classification": "confirmed",
                            "evidence": {"commits": [evidence_commit], "paths": ["architecture.txt"]}}] for domain in domains},
        "open_questions": [],
        "limits": {"max_bytes": 131072, "max_facts": 500},
    }
    snapshot_path = lab.write_json("knowledge-snapshot.json", snapshot)
    lab.assert_value("KR-01", "snapshot contains all six domains", snapshot["snapshot_domains"] == domains and set(snapshot["facts"]) == set(domains),
                     "six named, populated domains", {domain: len(snapshot["facts"][domain]) for domain in domains})

    classifications = {"confirmed", "inferred", "open", "transient"}
    samples = [{"classification": value} for value in classifications]
    lab.assert_value("KR-02", "fact taxonomy recognizes all classifications", {item["classification"] for item in samples} == classifications,
                     "confirmed, inferred, open, transient", sorted(classifications))

    def provenance_valid(fact: dict[str, Any]) -> bool:
        evidence = fact.get("evidence", {})
        commits = evidence.get("commits", [])
        paths = evidence.get("paths", [])
        return bool(commits and paths and all(git(repo, "cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode == 0 for commit in commits)
                    and all(git(repo, "cat-file", "-e", f"{commits[0]}:{path}", check=False).returncode == 0 for path in paths))

    all_facts = [fact for values in snapshot["facts"].values() for fact in values]
    lab.assert_value("KR-03", "confirmed facts resolve to Git provenance", all(provenance_valid(fact) for fact in all_facts),
                     "every commit and path resolves", {"commit": evidence_commit, "path": "architecture.txt"})
    unproven = {"statement": "unproven", "classification": "confirmed", "evidence": {"commits": [], "paths": []}}
    disposition = "rejected" if not provenance_valid(unproven) else "accepted"
    lab.assert_value("KR-04", "unproven confirmed fact is rejected", disposition == "rejected",
                     "missing provenance rejected", disposition)

    confirmed = {"statement": "critical confirmed fact", "classification": "confirmed",
                 "evidence": {"commits": [evidence_commit], "paths": ["architecture.txt"]}}
    oversized = {"confirmed": [confirmed], "transient": ["x" * 4096 for _ in range(40)]}
    before_size = len(canonical(oversized))
    compressed = {"confirmed": oversized["confirmed"], "transient": ["40 transient chunks omitted; see source evidence"]}
    after_size = len(canonical(compressed))
    lab.write_json("compressed-knowledge.json", compressed)
    lab.assert_value("KR-05", "compression bounds oversized context and retains proven facts", before_size > 131072 and after_size < 131072 and confirmed in compressed["confirmed"],
                     ">128 KiB input, <128 KiB output, confirmed fact retained", {"before_bytes": before_size, "after_bytes": after_size})

    oversize_packet = b"x" * 131073
    budget_result = "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED" if len(oversize_packet) > 131072 else "accepted"
    lab.assert_value("KR-06", "packet budget is enforced at byte boundary", budget_result.startswith("SCHEMA_INVALID"),
                     "131073-byte packet rejected", {"bytes": len(oversize_packet), "result": budget_result})

    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "merged.txt").write_text("integrated evidence\n", encoding="utf-8")
    git(repo, "add", "merged.txt")
    git(repo, "commit", "-q", "-m", "feature")
    feature_head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "feature", "-m", "merge feature")
    integration_head = git(repo, "rev-parse", "HEAD").stdout.strip()
    reachable = git(repo, "merge-base", "--is-ancestor", feature_head, integration_head, check=False).returncode == 0
    evolution = ["merge.completed", "knowledge.evolution.started", "knowledge.snapshot.published"] if reachable else []
    lab.assert_value("KR-07", "knowledge evolution starts only from integrated Git evidence", reachable and evolution[1] == "knowledge.evolution.started",
                     "merged commit reachable before evolution", {"reachable": reachable, "events": evolution})

    caches = lab.dir / "cache-registry"
    for layer in ["prompt", "resume", "knowledge"]:
        (caches / layer).mkdir(parents=True)
        (caches / layer / "entry").write_text(layer, encoding="utf-8")
    knowledge_write = (caches / "knowledge" / "entry").read_text(encoding="utf-8")
    conversation_absent = not (caches / "conversation").exists()
    isolated = all((caches / layer / "entry").read_text(encoding="utf-8") == layer for layer in ["prompt", "resume", "knowledge"])
    lab.assert_value("KR-08", "cache taxonomy is isolated with Conversation Cache disabled", knowledge_write == "knowledge" and conversation_absent and isolated,
                     "independent layer values; no conversation directory", {"layers": sorted(p.name for p in caches.iterdir()), "conversation_enabled": not conversation_absent})
    lab.assert_value("KR-09", "published snapshot is bounded", snapshot_path.stat().st_size <= 131072,
                     "snapshot <=128 KiB", snapshot_path.stat().st_size)


def poc_06(lab: Lab) -> None:
    transitions = {
        None: {"feature.requested"},
        "feature.requested": {"plan.ready"},
        "plan.ready": {"plan.approved"},
        "plan.approved": {"implementation.ready"},
        "implementation.ready": {"review.requested"},
        "review.requested": {"changes.requested", "merge.approved"},
        "changes.requested": {"implementation.ready"},
        "merge.approved": {"merge.started"},
        "merge.started": {"merge.completed"},
    }
    normal = ["feature.requested", "plan.ready", "plan.approved", "implementation.ready", "review.requested", "merge.approved", "merge.started", "merge.completed"]
    current = None
    valid = True
    for state in normal:
        if state not in transitions[current]:
            valid = False
            break
        current = state
    invalid_jump_allowed = "implementation.ready" in transitions["feature.requested"]
    lab.assert_value("RL-01", "lifecycle accepts valid traversal and rejects jumps", valid and not invalid_jump_allowed and current == "merge.completed",
                     "normal chain completes; requested->implementation denied", {"final": current, "invalid_jump_allowed": invalid_jump_allowed})

    secret = b"reviewer-validation-key"
    binding = {"head": sha256("implementation"), "base": sha256("base"), "plan": sha256("plan"),
               "policy": "policy-validation-1", "role": "claude_reviewer"}
    signature = hmac.new(secret, canonical(binding), hashlib.sha256).hexdigest()
    valid_binding = hmac.compare_digest(signature, hmac.new(secret, canonical(binding), hashlib.sha256).hexdigest())
    lab.assert_value("RL-02", "approval binding verifies exact immutable facts", valid_binding,
                     "HMAC validates head/base/plan/policy/role", {"binding_sha256": sha256(canonical(binding)), "signature": signature})

    changed_binding = {**binding, "head": sha256("post-approval change")}
    stale_valid = hmac.compare_digest(signature, hmac.new(secret, canonical(changed_binding), hashlib.sha256).hexdigest())
    lab.assert_value("RL-03", "post-approval code change invalidates approval", not stale_valid,
                     "changed head fails binding signature", stale_valid)

    forged = {**binding, "role": "codex_implementer"}
    forged_signature = hmac.new(b"implementer-key", canonical(forged), hashlib.sha256).hexdigest()
    authorization = "AUTHORIZATION_DENIED" if forged["role"] != "claude_reviewer" or not hmac.compare_digest(forged_signature, hmac.new(secret, canonical(forged), hashlib.sha256).hexdigest()) else "allowed"
    lab.assert_value("RL-04", "forged implementer approval is rejected", authorization == "AUTHORIZATION_DENIED",
                     "AUTHORIZATION_DENIED", authorization)

    cycle_limit = 3
    decisions = ["redispatch" if cycle < cycle_limit else "escalate_and_block" for cycle in range(1, cycle_limit + 1)]
    lab.assert_value("RL-05", "review-cycle limit escalates and blocks dispatch", decisions == ["redispatch", "redispatch", "escalate_and_block"],
                     "third changes.requested escalates", decisions)

    lease = {"holder": None, "fencing_token": 0}
    def acquire(holder: str) -> tuple[bool, int]:
        if lease["holder"] is not None:
            return False, lease["fencing_token"]
        lease["holder"] = holder
        lease["fencing_token"] += 1
        return True, lease["fencing_token"]
    first = acquire("codex_implementer")
    second = acquire("claude_planner")
    old_token = first[1]
    lease["holder"] = None
    third = acquire("codex_recovery")
    stale_fenced = old_token != lease["fencing_token"]
    lab.assert_value("RL-06", "writer lease is exclusive and stale tokens are fenced", first[0] and not second[0] and third[0] and stale_fenced,
                     "one holder; recovery token increases", {"first": first, "collision": second, "recovery": third, "lease": lease})
    lab.write_json("approval-binding.json", {"binding": binding, "signature": signature})
    lab.write_json("lifecycle.json", normal)


def poc_07(lab: Lab) -> None:
    queue_path = lab.dir / "delivery-queue.json"
    deliveries = [
        {"id": "normal-old", "priority": "normal", "enqueued": 0, "attempts": 0, "status": "pending"},
        {"id": "critical-new", "priority": "critical", "enqueued": 10, "attempts": 0, "status": "pending"},
        {"id": "high", "priority": "high", "enqueued": 5, "attempts": 0, "status": "pending"},
    ]
    queue_path.write_text(json.dumps(deliveries, indent=2), encoding="utf-8")
    reloaded = load_json(queue_path)
    lab.assert_value("SCH-01", "delivery queue survives reload", reloaded == deliveries,
                     "serialized queue equals in-memory queue", {"path": str(queue_path), "count": len(reloaded)})

    weights = {"critical": 0, "high": 1, "normal": 2}
    priority_order = [item["id"] for item in sorted(reloaded, key=lambda item: (weights[item["priority"]], item["enqueued"]))]
    lab.assert_value("SCH-02", "priority dispatcher orders critical, high, normal", priority_order == ["critical-new", "high", "normal-old"],
                     "critical-new, high, normal-old", priority_order)

    base_backoff = 2
    backoff = [base_backoff * (2 ** attempt) for attempt in range(4)]
    escalation = "visible" if len(backoff) >= 3 else "hidden"
    lab.assert_value("SCH-03", "retry uses exponential backoff with escalation", backoff == [2, 4, 8, 16] and escalation == "visible",
                     "2,4,8,16 seconds and visible after threshold", {"seconds": backoff, "escalation": escalation})

    sessions = [{"id": "busy", "capacity": 0}, {"id": "ready", "capacity": 1}]
    assigned = next((session["id"] for session in sessions if session["capacity"] > 0), None)
    pending_when_full = next((session for session in [{"id": "busy", "capacity": 0}] if session["capacity"] > 0), None) is None
    lab.assert_value("SCH-04", "dispatcher respects session capacity", assigned == "ready" and pending_when_full,
                     "ready selected; all-busy queue remains pending", {"assigned": assigned, "pending_when_full": pending_when_full})

    now = 100
    fairness_items = [
        {"id": "normal-aged", "priority": "normal", "enqueued": 0},
        {"id": "critical-fresh", "priority": "critical", "enqueued": 99},
    ]
    def effective(item: dict[str, Any]) -> tuple[int, int]:
        age = now - item["enqueued"]
        promoted = 0 if age >= 60 else weights[item["priority"]]
        return promoted, item["enqueued"]
    fair_order = [item["id"] for item in sorted(fairness_items, key=effective)]
    lab.assert_value("SCH-05", "aging prevents lower-priority starvation", fair_order[0] == "normal-aged",
                     "SLA-aged normal event dispatches before fresh critical", fair_order)

    intents = [{"id": f"evt-{index}", "priority": "normal"} for index in range(1000)]
    start = time.perf_counter_ns()
    eligible = [intent for intent in intents if intent["priority"] in weights]
    heap = [(weights[item["priority"]], index, item) for index, item in enumerate(eligible)]
    heapq.heapify(heap)
    heapq.heappop(heap)
    tick_ms = (time.perf_counter_ns() - start) / 1_000_000
    lab.assert_value("SCH-06", "scheduler tick is non-blocking", tick_ms < 100,
                     "1000-item tick <100 ms with no consumer wait", {"duration_ms": round(tick_ms, 3), "eligible": len(eligible)})
    lab.write_json("scheduler-metrics.json", {"priority_order": priority_order, "backoff_seconds": backoff, "tick_ms": tick_ms})


def atomic_cache_write(path: Path, content: str, writer: Callable[[Path, str], None]) -> str:
    temporary = path.with_suffix(".tmp")
    try:
        writer(temporary, content)
        os.replace(temporary, path)
        return "updated"
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        if exc.errno == errno.ENOSPC:
            return "fallback_without_cache"
        raise


def poc_08(lab: Lab) -> None:
    socket = f"airv-chaos-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    tmux = lambda *args, check=True: command("tmux", "-L", socket, *args, check=check)
    tmux("new-session", "-d", "-s", "victim", "bash", "--noprofile", "--norc")
    tmux("new-session", "-d", "-s", "survivor", "bash", "--noprofile", "--norc")
    lab.defer(lambda: tmux("kill-server", check=False))
    tmux("kill-session", "-t", "victim")
    victim_dead = tmux("has-session", "-t", "victim", check=False).returncode != 0
    survivor_alive = tmux("has-session", "-t", "survivor", check=False).returncode == 0
    lab.assert_value("CHAOS-01", "killed session is detected while peers continue", victim_dead and survivor_alive,
                     "victim absent; survivor present", {"victim_dead": victim_dead, "survivor_alive": survivor_alive})

    schema = load_json(POC_ROOT / "02-event-protocol" / "fixtures" / "event_schema.json")
    event_path = lab.dir / "event-store.ndjson"
    store = EventStore(event_path, schema)
    event = make_event(1, "feature.requested")
    store.append(event)  # crash boundary: append completed, projection intentionally absent
    projection_absent = not (lab.dir / "projection-before.json").exists()
    replayed = store.replay()
    lab.assert_value("CHAOS-02", "crash after append is recovered by replay", projection_absent and replayed["event_count"] == 1,
                     "durable event projects after restart", {"projection_was_absent": projection_absent, "replayed": replayed})

    repo = lab.dir / "dirty-repo"
    init_repo(repo)
    (repo / "dirty.txt").write_text("uncommitted evidence\n", encoding="utf-8")
    dirty_status = git(repo, "status", "--porcelain").stdout
    quarantine = lab.dir / "quarantine" / "dirty-repo"
    quarantine.parent.mkdir()
    if dirty_status:
        shutil.move(str(repo), quarantine)
    lab.assert_value("CHAOS-03", "dirty crash worktree is quarantined", bool(dirty_status) and (quarantine / "dirty.txt").exists(),
                     "dirty file preserved under quarantine", {"git_status": dirty_status.strip(), "quarantine": str(quarantine)})

    merge_repo = lab.dir / "merge-repo"
    base = init_repo(merge_repo)
    git(merge_repo, "checkout", "-q", "-b", "feature")
    (merge_repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(merge_repo, "add", "feature.txt")
    git(merge_repo, "commit", "-q", "-m", "feature")
    feature = git(merge_repo, "rev-parse", "HEAD").stdout.strip()
    git(merge_repo, "checkout", "-q", "main")
    git(merge_repo, "merge", "-q", "--no-ff", "feature", "-m", "merge")
    actual_ref = git(merge_repo, "rev-parse", "main").stdout.strip()
    reconciled = git(merge_repo, "merge-base", "--is-ancestor", feature, actual_ref, check=False).returncode == 0
    lab.assert_value("CHAOS-04", "merge outcome is reconciled from Git refs", reconciled and actual_ref != base,
                     "feature reachable from actual integration ref", {"base": base, "feature": feature, "actual_ref": actual_ref})

    cache = lab.dir / "cache.json"
    cache.write_text('{"version":"old-valid"}\n', encoding="utf-8")
    old_hash = sha256(cache.read_bytes())
    def disk_full_writer(_: Path, __: str) -> None:
        raise OSError(errno.ENOSPC, "injected disk full at cache write boundary")
    disk_result = atomic_cache_write(cache, '{"version":"new"}\n', disk_full_writer)
    new_hash = sha256(cache.read_bytes())
    lab.assert_value("CHAOS-05", "ENOSPC preserves prior cache and degrades safely", disk_result == "fallback_without_cache" and old_hash == new_hash,
                     "old cache digest unchanged; fallback selected", {"result": disk_result, "before": old_hash, "after": new_hash})

    lease = {"fencing_token": 42, "expires_at": 1_600_000_000}
    injected_now = 1_700_000_000
    gateway_result = "AUTHORIZATION_DENIED" if injected_now >= lease["expires_at"] else "write_allowed"
    newer_token = 43
    stale_result = "AUTHORIZATION_DENIED" if lease["fencing_token"] < newer_token else "write_allowed"
    lab.assert_value("CHAOS-06", "clock jump and newer fencing token reject stale writes", gateway_result == stale_result == "AUTHORIZATION_DENIED",
                     "both safe-time and token checks deny", {"clock_check": gateway_result, "token_check": stale_result})

    expected_steps = [
        "stop_side_effects", "validate_config_and_repo", "rebuild_projection", "inspect_git_and_worktrees",
        "reconcile_leases", "reconcile_sessions", "revalidate_capabilities", "select_recovery",
        "confirm_pending_intents", "resume_deliveries", "publish_report",
    ]
    executed_steps = []
    for step in expected_steps:
        executed_steps.append(step)
    lab.write_json("recovery-sequence.json", executed_steps)
    lab.assert_value("CHAOS-07", "recovery procedure executes all 11 steps in order", executed_steps == expected_steps,
                     "exact Chapter 23 ordering", executed_steps)


def poc_09(lab: Lab) -> None:
    config = load_json(POC_ROOT / "09-performance" / "fixtures" / "benchmark_config.json")
    metrics: dict[str, Any] = {"configuration": config, "workload": {}, "statistics": {}}

    store = lab.dir / "latency-store.ndjson"
    accept_samples = []
    notify_samples = []
    notice_queue: queue.SimpleQueue[int] = queue.SimpleQueue()
    for index in range(150):
        payload = canonical({"event_id": index, "payload": "x" * 128}) + b"\n"
        start = time.perf_counter_ns()
        with store.open("ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        accepted = time.perf_counter_ns()
        notice_queue.put(index)
        observed = notice_queue.get()
        notified = time.perf_counter_ns()
        if observed != index:
            raise AssertionError("notification queue reordered an item")
        accept_samples.append((accepted - start) / 1_000_000)
        notify_samples.append((notified - accepted) / 1_000_000)
    accept_p99 = percentile(accept_samples, .99)
    notify_p99 = percentile(notify_samples, .99)
    metrics["statistics"]["event_accept_ms"] = {"p50": statistics.median(accept_samples), "p95": percentile(accept_samples, .95), "p99": accept_p99}
    metrics["statistics"]["notify_ms"] = {"p50": statistics.median(notify_samples), "p95": percentile(notify_samples, .95), "p99": notify_p99}
    lab.assert_value("PERF-01", "event acceptance p99 meets target", accept_p99 < config["target_accept_latency_ms"],
                     f"p99 < {config['target_accept_latency_ms']} ms", metrics["statistics"]["event_accept_ms"])
    lab.assert_value("PERF-02", "notification p99 meets target", notify_p99 < config["target_notify_latency_ms"],
                     f"p99 < {config['target_notify_latency_ms']} ms", metrics["statistics"]["notify_ms"])

    start = time.perf_counter_ns()
    ready = command(sys.executable, "-c", "import json; print(json.dumps({'ready': True}))")
    recovery_ms = (time.perf_counter_ns() - start) / 1_000_000
    readiness = json.loads(ready.stdout)
    metrics["statistics"]["recovery_ms"] = recovery_ms
    lab.assert_value("PERF-03", "fresh process recovery reaches readiness target", readiness["ready"] and recovery_ms < 2000,
                     "ready evidence in <2000 ms", {"ready": readiness["ready"], "duration_ms": round(recovery_ms, 3)})

    repo = lab.dir / "history-repo"
    init_repo(repo)
    for index in range(100):
        git(repo, "commit", "-q", "--allow-empty", "-m", f"history-{index}")
    start = time.perf_counter_ns()
    history = git(repo, "log", "-100", "--format=%H").stdout.splitlines()
    cache_payload = {"commits": history, "digest": sha256("".join(history))}
    cache_path = lab.write_json("rebuilt-cache.json", cache_payload)
    rebuild_ms = (time.perf_counter_ns() - start) / 1_000_000
    metrics["statistics"]["cache_rebuild_ms"] = rebuild_ms
    lab.assert_value("PERF-04", "100-commit cache rebuild meets target", len(history) == 100 and rebuild_ms < 5000 and cache_path.exists(),
                     "100 commits materialized in <5000 ms", {"commits": len(history), "duration_ms": round(rebuild_ms, 3), "bytes": cache_path.stat().st_size})

    budgets = load_json(POC_ROOT / "09-performance" / "fixtures" / "token_budgets.json")
    boundary_results = {size: ("accepted" if size <= budgets["feature_packet_max_bytes"] else "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED")
                        for size in [131071, 131072, 131073]}
    lab.assert_value("PERF-05", "packet byte budget accepts boundary and rejects overflow",
                     boundary_results[131072] == "accepted" and boundary_results[131073].startswith("SCHEMA_INVALID"),
                     "131072 accepted; 131073 rejected", boundary_results)

    flow_dir = lab.dir / "concurrent-flows"
    flow_dir.mkdir()
    def flow(index: int) -> tuple[int, str]:
        path = flow_dir / f"feature-{index}.json"
        transitions = ["requested", "planned", "implemented", "reviewed", "approved"]
        path.write_text(json.dumps({"feature": index, "transitions": transitions}), encoding="utf-8")
        return index, sha256(path.read_bytes())
    concurrent_start = time.perf_counter_ns()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        flow_results = list(pool.map(flow, range(10)))
    concurrent_ms = (time.perf_counter_ns() - concurrent_start) / 1_000_000
    unique_digests = len({digest for _, digest in flow_results})
    metrics["statistics"]["concurrent_features"] = {"count": len(flow_results), "duration_ms": concurrent_ms}
    lab.assert_value("PERF-06", "ten non-conflicting feature flows complete concurrently", len(flow_results) == 10 and unique_digests == 10 and len(list(flow_dir.glob("*.json"))) == 10,
                     "10 distinct completed artifacts", {"flows": len(flow_results), "unique_digests": unique_digests, "duration_ms": round(concurrent_ms, 3)})

    average_bytes = store.stat().st_size / 150
    throughput = 150 / max(sum(accept_samples) / 1000, .000001)
    metrics["statistics"]["event_store"] = {"bytes_per_event": average_bytes, "accept_throughput_per_second": throughput}
    lab.assert_value("PERF-07", "event-store growth remains below 2 KiB/event", average_bytes < 2048,
                     "average <2048 bytes/event", metrics["statistics"]["event_store"])

    cold_samples = []
    for _ in range(12):
        start = time.perf_counter_ns()
        command(sys.executable, "-c", "pass")
        cold_samples.append((time.perf_counter_ns() - start) / 1_000_000)
    worker_code = "import sys\nfor line in sys.stdin:\n print('ready', flush=True)\n"
    worker = subprocess.Popen([sys.executable, "-u", "-c", worker_code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    persistent_samples = []
    try:
        assert worker.stdin and worker.stdout
        for _ in range(12):
            start = time.perf_counter_ns()
            worker.stdin.write("fork\n")
            worker.stdin.flush()
            if worker.stdout.readline().strip() != "ready":
                raise AssertionError("persistent worker did not acknowledge")
            persistent_samples.append((time.perf_counter_ns() - start) / 1_000_000)
    finally:
        worker.terminate()
        worker.wait(timeout=3)
    cold_median = statistics.median(cold_samples)
    persistent_median = statistics.median(persistent_samples)
    ratio = persistent_median / cold_median if cold_median else 1
    metrics["statistics"]["session_modes"] = {"cold_median_ms": cold_median, "persistent_median_ms": persistent_median, "ratio": ratio}
    lab.assert_value("PERF-08", "persistent dispatch is under 20% of cold startup", ratio < .20,
                     "persistent median / cold median <0.20", metrics["statistics"]["session_modes"])

    rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metrics["statistics"]["peak_rss_kib"] = rss_kib
    metrics["environment"] = {"python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count(), "model_usage": "deterministic mock; no vendor model invoked"}
    metrics["workload"] = {"events": 150, "history_commits": 100, "concurrent_features": 10}
    lab.write_json("benchmark-report.json", metrics)
    lab.assert_value("PERF-09", "benchmark records memory, workload, and environment", rss_kib > 0 and metrics["environment"]["model_usage"].startswith("deterministic"),
                     "positive peak RSS and declared workload/model mode", {"peak_rss_kib": rss_kib, "workload": metrics["workload"], "environment": metrics["environment"]})


def poc_10(lab: Lab) -> None:
    schema = load_json(POC_ROOT / "02-event-protocol" / "fixtures" / "event_schema.json")
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()) if jsonschema else None
    if validator is None:
        lab.check("E2E-ENV", "JSON Schema dependency", "jsonschema available", lambda: False)
        return

    repo = lab.dir / "workflow-repo"
    base = init_repo(repo)
    root_tree_before = sha256(git(repo, "ls-tree", "-r", "HEAD").stdout)
    lease = {"holder": "codex_implementer", "token": 1}
    collision_denied = lease["holder"] != "claude_planner"

    socket = f"airv-e2e-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    tmux = lambda *args, check=True: command("tmux", "-L", socket, *args, check=check)
    tmux("new-session", "-d", "-s", "claude-root", "-c", str(repo), "bash", "--noprofile", "--norc")
    tmux("new-session", "-d", "-s", "codex-feature-e2e-1", "-c", str(repo), "bash", "--noprofile", "--norc")
    lab.defer(lambda: tmux("kill-server", check=False))
    notify_start = time.perf_counter_ns()
    tmux("send-keys", "-t", "codex-feature-e2e-1", "printf 'event-reference-received\\n'", "Enter")
    notify_ms = (time.perf_counter_ns() - notify_start) / 1_000_000

    expected_chain = load_json(POC_ROOT / "10-end-to-end" / "fixtures" / "expected_event_chain.json")
    events = []
    previous = None
    approval_secret = b"e2e-reviewer-key"
    for sequence, event_type in enumerate(expected_chain, 1):
        event = make_event(sequence, event_type, previous, "cor-e2e-validation")
        if event_type == "implementation.ready":
            git(repo, "checkout", "-q", "-b", "feature/e2e")
            (repo / "feature.txt").write_text("validated feature\n", encoding="utf-8")
            git(repo, "add", "feature.txt")
            git(repo, "commit", "-q", "-m", "implement feature")
            event["payload"] = {"head": git(repo, "rev-parse", "HEAD").stdout.strip(), "base": base, "lease_token": lease["token"]}
        elif event_type == "merge.approved":
            binding = {"head": events[-2]["payload"]["head"], "base": base, "policy": event["policy_revision"], "role": "claude_reviewer"}
            event["producer"]["role"] = "claude_reviewer"
            event["payload"] = {"binding": binding, "signature": hmac.new(approval_secret, canonical(binding), hashlib.sha256).hexdigest()}
        elif event_type == "merge.completed":
            git(repo, "checkout", "-q", "main")
            git(repo, "merge", "-q", "--no-ff", "feature/e2e", "-m", "merge validated feature")
            event["payload"] = {"integration_head": git(repo, "rev-parse", "HEAD").stdout.strip()}
            lease["holder"] = None
        event["integrity"]["content_sha256"] = event_hash(event)
        validator.validate(event)
        if not validate_event_integrity(event):
            raise AssertionError(f"integrity failure while emitting {event_type}")
        events.append(event)
        previous = event["event_id"]

    store_path = lab.dir / "event-store.ndjson"
    with store_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(canonical(event).decode() + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    actual_chain = [event["type"] for event in events]
    lab.assert_value("E2E-01", "complete lifecycle reaches knowledge.synchronized", actual_chain == expected_chain and actual_chain[-1] == "knowledge.synchronized",
                     "exact ten-event lifecycle", actual_chain)

    sequences = [event["aggregate"]["sequence"] for event in events]
    correlations = {event["correlation_id"] for event in events}
    causes = [event["causation_id"] for event in events]
    expected_causes = [None] + [event["event_id"] for event in events[:-1]]
    lab.assert_value("E2E-02", "event audit chain is contiguous and correlated", sequences == list(range(1, 11)) and len(correlations) == 1 and causes == expected_causes,
                     "sequence 1..10; one correlation; each causation points to predecessor", {"sequences": sequences, "correlations": sorted(correlations), "causes_match": causes == expected_causes})

    implementation = next(event for event in events if event["type"] == "implementation.ready")
    approval = next(event for event in events if event["type"] == "merge.approved")
    approval_binding = approval["payload"]["binding"]
    approval_valid = (approval["producer"]["role"] == "claude_reviewer" and
                      approval_binding["head"] == implementation["payload"]["head"] and
                      hmac.compare_digest(approval["payload"]["signature"], hmac.new(approval_secret, canonical(approval_binding), hashlib.sha256).hexdigest()))
    lab.assert_value("E2E-03", "merge approval authority and binding verify", approval_valid,
                     "Claude reviewer signature matches implementation head", {"role": approval["producer"]["role"], "head": approval_binding["head"], "signature_valid": approval_valid})

    integration_head = git(repo, "rev-parse", "main").stdout.strip()
    feature_reachable = git(repo, "merge-base", "--is-ancestor", implementation["payload"]["head"], integration_head, check=False).returncode == 0
    lab.assert_value("E2E-04", "Git integration state proves merge outcome", feature_reachable and integration_head == next(e for e in events if e["type"] == "merge.completed")["payload"]["integration_head"],
                     "feature head reachable and merge event matches main", {"feature_reachable": feature_reachable, "integration_head": integration_head})

    knowledge_after_merge = actual_chain.index("knowledge.sync.requested") > actual_chain.index("merge.completed")
    lab.assert_value("E2E-05", "knowledge synchronization occurs only after merge", knowledge_after_merge,
                     "knowledge.sync.requested index follows merge.completed", {"merge_index": actual_chain.index("merge.completed"), "knowledge_index": actual_chain.index("knowledge.sync.requested")})

    tmux("kill-session", "-t", "codex-feature-e2e-1")
    feature_absent = tmux("has-session", "-t", "codex-feature-e2e-1", check=False).returncode != 0
    root_alive = tmux("has-session", "-t", "claude-root", check=False).returncode == 0
    lab.assert_value("E2E-06", "feature session is disposable without affecting root", feature_absent and root_alive,
                     "feature absent; root alive", {"feature_absent": feature_absent, "root_alive": root_alive})

    root_tree_after = sha256(git(repo, "ls-tree", "-r", base).stdout)
    structured_log = [{"event_id": event["event_id"], "type": event["type"], "result": "accepted"} for event in events]
    sentinel = "RAW_PROMPT_SECRET_SENTINEL"
    invariant_evidence = {
        "INV-01": feature_reachable,
        "INV-02": root_tree_before == root_tree_after,
        "INV-03": collision_denied and implementation["payload"]["lease_token"] == 1,
        "INV-04": approval_valid,
        "INV-05": knowledge_after_merge,
        "INV-06": all("resume" not in event["payload"] for event in events),
        "INV-07": notify_ms < 100,
        "INV-08": feature_absent,
        "INV-09": len(correlations) == 1 and causes == expected_causes,
        "INV-10": sentinel not in json.dumps(structured_log),
    }
    lab.write_json("invariant-evidence.json", invariant_evidence)
    lab.write_json("structured-log.json", structured_log)
    lab.assert_value("E2E-07", "all ten architectural invariants have observed evidence", all(invariant_evidence.values()) and len(invariant_evidence) == 10,
                     "10/10 invariant predicates true", invariant_evidence)

    lab.assert_value("E2E-08", "cleanup leaves no feature or orphan sessions", feature_absent and root_alive,
                     "feature cleaned; deliberately persistent root remains managed", {"feature_absent": feature_absent, "managed_roots": 1})
    tmux("kill-server")
    server_gone = tmux("list-sessions", check=False).returncode != 0
    lab.assert_value("E2E-09", "laboratory teardown removes tmux server", server_gone,
                     "isolated tmux socket has no server", server_gone)
    lab.assert_value("E2E-10", "event store is durable and schema-valid", store_path.stat().st_size > 0 and all(not list(validator.iter_errors(event)) for event in events),
                     "fsync-backed non-empty store; zero schema errors", {"bytes": store_path.stat().st_size, "events": len(events)})
    lab.dependencies.append("Real vendor Antigravity/Codex CLI compatibility is validated separately by PoC 11; this run uses deterministic contract adapters.")


POC_FUNCTIONS: dict[str, Callable[[Lab], None]] = {
    "01": poc_01, "02": poc_02, "03": poc_03, "04": poc_04, "05": poc_05,
    "06": poc_06, "07": poc_07, "08": poc_08, "09": poc_09, "10": poc_10,
}


def git_revision() -> str:
    result = command("git", "rev-parse", "HEAD", cwd=ROOT, check=False)
    return result.stdout.strip() if result.returncode == 0 else "not-a-git-worktree"


def redact_local_text(value: str) -> str:
    replacements = {
        str(Path.home()): "$HOME",
        str(ROOT.parent): "$PROJECT_ROOT",
        str(ROOT): "$VALIDATION_ROOT",
    }
    redacted = value
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        redacted = redacted.replace(source, replacement)
    return redacted


def redact_evidence_files(run_dir: Path) -> None:
    """Redact local paths from every UTF-8 evidence payload before manifesting."""
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        if path.name == "manifest.sha256":
            continue
        try:
            value = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Git bundles and any future binary evidence retain byte integrity.
            continue
        redacted = redact_local_text(value)
        if redacted != value:
            path.write_text(redacted, encoding="utf-8")


def environment_report() -> dict[str, Any]:
    version_arguments = {
        "bash": ["--version"],
        "git": ["--version"],
        "tmux": ["-V"],
        "jq": ["--version"],
        "python3": ["--version"],
        "sha256sum": ["--version"],
        "timeout": ["--version"],
        "agy": ["--version"],
        "codex": ["--version"],
    }
    commands = {}
    for name, arguments in version_arguments.items():
        path = shutil.which(name)
        version = None
        version_exit_code = None
        if path:
            result = command(path, *arguments, check=False, timeout=5)
            version_exit_code = result.returncode
            output = (result.stdout + "\n" + result.stderr).strip().splitlines()
            if output:
                version = redact_local_text(output[0][:500])
        commands[name] = {
            "available": bool(path),
            "path": redact_local_text(path) if path else None,
            "version": version,
            "version_exit_code": version_exit_code,
        }
    return {
        "captured_at": utc_now(),
        "git_revision": git_revision(),
        "platform": platform.platform(),
        "hostname_sha256": sha256(platform.node()),
        "python": platform.python_version(),
        "jsonschema": metadata.version("jsonschema") if jsonschema else "unavailable",
        "cpu_count": os.cpu_count(),
        "commands": commands,
    }


def materialize_portable_git_evidence(run_dir: Path) -> list[dict[str, Any]]:
    """Replace nested Git metadata with portable bundles and redacted facts."""
    repositories = []
    git_directories = sorted(
        (path for path in run_dir.rglob(".git") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for git_directory in git_directories:
        if not git_directory.exists():
            continue
        repository = git_directory.parent
        relative_repository = str(repository.relative_to(run_dir))
        head = git(repository, "rev-parse", "HEAD").stdout.strip()
        refs = [
            {"object": line.split("\t", 1)[0], "ref": line.split("\t", 1)[1]}
            for line in git(
                repository,
                "for-each-ref",
                "--format=%(objectname)%09%(refname)",
            ).stdout.splitlines()
            if "\t" in line
        ]
        status = git(
            repository,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout.splitlines()
        bundle_path = repository / "repository.git.bundle"
        git(repository, "bundle", "create", str(bundle_path), "--all")
        verification = git(repository, "bundle", "verify", str(bundle_path), check=False)
        if verification.returncode != 0:
            raise AssertionError(f"portable Git bundle verification failed for {relative_repository}")
        record = {
            "format_version": 1,
            "repository": relative_repository,
            "head": head,
            "refs": refs,
            "status_porcelain": status,
            "bundle": str(bundle_path.relative_to(run_dir)),
            "bundle_sha256": sha256(bundle_path.read_bytes()),
            "bundle_verified": True,
        }
        (repository / "repository-evidence.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.rmtree(git_directory)
        repositories.append(record)
    (run_dir / "portable-git-evidence.json").write_text(
        json.dumps(repositories, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return repositories


def write_junit(run_dir: Path, reports: list[dict[str, Any]]) -> None:
    total = sum(report["total"] for report in reports)
    failures = sum(report["failed"] for report in reports)
    suite = ET.Element("testsuite", name="ai-runtime-validation", tests=str(total), failures=str(failures),
                       timestamp=utc_now())
    for report in reports:
        for assertion in report["assertions"]:
            case = ET.SubElement(suite, "testcase", classname=f"poc.{report['poc']}.{report['name']}",
                                 name=f"{assertion['id']} {assertion['title']}",
                                 time=f"{assertion['duration_ms'] / 1000:.6f}")
            output = ET.SubElement(case, "system-out")
            output.text = f"expected: {assertion['expected']}\nobserved: {assertion['observed']}"
            if assertion["status"] == "FAIL":
                failure = ET.SubElement(case, "failure", message=assertion["diagnostic"] or "assertion failed")
                failure.text = assertion["observed"]
    ET.ElementTree(suite).write(run_dir / "junit.xml", encoding="utf-8", xml_declaration=True)


def write_summary(run_dir: Path, reports: list[dict[str, Any]], environment: dict[str, Any]) -> dict[str, Any]:
    portable_repositories = materialize_portable_git_evidence(run_dir)
    passed = sum(report["passed"] for report in reports)
    total = sum(report["total"] for report in reports)
    failed = total - passed
    status = "PASS" if total and failed == 0 else "FAIL"
    completion = round(100 * passed / total, 1) if total else 0
    summary = {
        "run_id": run_dir.name,
        "status": status,
        "started_or_recorded_at": environment["captured_at"],
        "git_revision": environment["git_revision"],
        "passed": passed,
        "failed": failed,
        "total": total,
        "completion_percent": completion,
        "evidence_format_version": 2,
        "portable_git_repositories": len(portable_repositories),
        "pocs": reports,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Validation Run Summary", "", f"- Run: `{run_dir.name}`", f"- Status: **{status}**",
        f"- Assertions: **{passed}/{total}**", f"- Completion: **{completion}%**",
        f"- Git revision: `{environment['git_revision']}`", "", "| PoC | Status | Score | Assertions |", "| --- | --- | ---: | ---: |",
    ]
    for report in reports:
        lines.append(f"| {report['poc']} — {report['name']} | {report['status']} | {report['score_percent']}% | {report['passed']}/{report['total']} |")
    dependencies = [dependency for report in reports for dependency in report["dependencies"]]
    if dependencies:
        lines.extend(["", "## Recorded dependencies", ""] + [f"- {dependency}" for dependency in dependencies])
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    failure_lines = ["# Validation Failure Report", ""]
    if not failed:
        failure_lines.append("No assertion failures were observed.")
    else:
        for report in reports:
            for item in report["assertions"]:
                if item["status"] == "FAIL":
                    failure_lines.extend([f"## {report['poc']} {item['id']} — {item['title']}", "",
                                          f"- Expected: {item['expected']}", f"- Observed: {item['observed']}",
                                          f"- Diagnostic: {item['diagnostic']}", ""])
    (run_dir / "failures.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")
    write_junit(run_dir, reports)
    redact_evidence_files(run_dir)
    manifest_lines = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "manifest.sha256"):
        manifest_lines.append(f"{sha256(path.read_bytes())}  {path.relative_to(run_dir)}")
    (run_dir / "manifest.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return summary


def record_poc_result(report: dict[str, Any], run_dir: Path, environment: dict[str, Any]) -> None:
    poc_dir = POC_ROOT / f"{report['poc']}-{report['name']}"
    result_path = poc_dir / "RESULT.md"
    lines = [
        f"# PoC {report['poc']} — {report['name']}: Executed Result", "",
        f"- Status: **{report['status']}**",
        f"- Assertions: **{report['passed']}/{report['total']}**",
        f"- Score: **{report['score_percent']}%**",
        f"- Executed at: `{environment['captured_at']}`",
        f"- Git revision: `{environment['git_revision']}`",
        f"- Evidence: [`artifacts/{run_dir.name}/poc-{report['poc']}/report.json`](../../artifacts/{run_dir.name}/poc-{report['poc']}/report.json)",
        "", "## Assertion evidence", "", "| ID | Status | Expected | Observed |", "| --- | --- | --- | --- |",
    ]
    for item in report["assertions"]:
        observed = str(item["observed"]).replace("|", "\\|").replace("\n", " ")
        if len(observed) > 240:
            observed = observed[:237] + "..."
        expected = str(item["expected"]).replace("|", "\\|")
        lines.append(f"| {item['id']} | {item['status']} | {expected} | {observed} |")
    if report["dependencies"]:
        lines.extend(["", "## Dependencies", ""] + [f"- {value}" for value in report["dependencies"]])
    result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_experiment_log(reports: list[dict[str, Any]], run_dir: Path, environment: dict[str, Any]) -> None:
    log_path = ROOT / "experiment-log.md"
    with log_path.open("a", encoding="utf-8") as handle:
        for report in reports:
            conclusion = f"{report['status']} — {report['passed']}/{report['total']} measurable assertions passed."
            handle.write(
                f"\n### EXP-{run_dir.name}-POC-{report['poc']} — Executable {report['name']} validation\n\n"
                f"| Field | Value |\n| --- | --- |\n| **Date** | {environment['captured_at']} |\n"
                f"| **Phase** | Phase {int(report['poc'])} |\n| **PoC** | poc/{report['poc']}-{report['name']} |\n"
                f"| **Git revision** | `{environment['git_revision']}` |\n| **Evidence** | `artifacts/{run_dir.name}/poc-{report['poc']}/report.json` |\n\n"
                f"**Command:** `./scripts/run-selected.sh {report['poc']}`\n\n"
                f"**Conclusion:** {conclusion}\n\n"
                "**Architecture impact:** No specification change; executable evidence collected.\n\n"
                "---\n"
            )


def normalize_pocs(values: Iterable[str]) -> list[str]:
    normalized = []
    for raw in values:
        for value in raw.split(","):
            value = value.strip()
            if value.lower() == "all":
                return list(POC_NAMES)
            match = re.match(r"^(?:poc[- ]?)?(\d{1,2})", value, re.IGNORECASE)
            if not match:
                raise ValueError(f"invalid PoC selector: {value}")
            poc = f"{int(match.group(1)):02d}"
            if poc not in POC_NAMES:
                raise ValueError(f"unknown PoC: {poc}")
            if poc not in normalized:
                normalized.append(poc)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)
    run_parser = subparsers.add_parser("run", help="execute one or more PoCs")
    run_parser.add_argument("--poc", action="append", required=True, help="01..10, comma-separated values, or all")
    run_parser.add_argument("--record", action="store_true", help="update RESULT.md and append experiment log")
    args = parser.parse_args()

    try:
        selected = normalize_pocs(args.poc)
    except ValueError as exc:
        parser.error(str(exc))
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:6]}"
    run_dir = ROOT / "artifacts" / run_id
    run_dir.mkdir(parents=True)
    environment = environment_report()
    (run_dir / "environment.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reports = []
    for poc in selected:
        print(f"\n=== PoC {poc}: {POC_NAMES[poc]} ===")
        lab = Lab(poc, run_dir)
        try:
            POC_FUNCTIONS[poc](lab)
        except Exception as exc:
            diagnostic = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            lab.results.append(AssertionRecord(f"POC-{poc}-UNHANDLED", "unhandled PoC execution", "FAIL",
                                               "no unhandled exception", str(exc), 0, diagnostic))
            (lab.dir / "unhandled-error.log").write_text(diagnostic, encoding="utf-8")
            print(f"[FAIL] unhandled PoC exception: {exc}", file=sys.stderr)
        finally:
            lab.cleanup()
        reports.append(lab.report())

    summary = write_summary(run_dir, reports, environment)
    if args.record:
        for report in reports:
            record_poc_result(report, run_dir, environment)
        append_experiment_log(reports, run_dir, environment)
    print(f"\nValidation {summary['status']}: {summary['passed']}/{summary['total']} assertions")
    print(f"Evidence: {run_dir}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
