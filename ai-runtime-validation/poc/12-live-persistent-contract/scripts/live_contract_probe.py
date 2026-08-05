#!/usr/bin/env python3
"""Bounded, redacted live probe of the persistent-adapter contract.

The probe runs the argv the installed adapters build today against a disposable
Git fixture, observes the declared readiness detectors on the runtime-private
tmux socket, and records only non-content evidence: digests, byte counts,
timings, booleans, and the single redacted pane line that satisfied a detector.

No raw prompt, pane capture, or model transcript is retained.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

POC_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = POC_ROOT.parents[1]
REPO_ROOT = VALIDATION_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_runtime.adapters.base import StructuredTask  # noqa: E402
from ai_runtime.adapters.cli import (  # noqa: E402
    ClaudeCLIAdapter,
    CodexCLIAdapter,
    _extract_structured,
    _validate_result,
)
from ai_runtime.runtime.feature_sessions import (  # noqa: E402
    StructuredTerminalEventChannel,
)
from ai_runtime.runtime.schemas import (  # noqa: E402
    IMPLEMENTATION_SCHEMA,
    PLAN_SCHEMA,
    REVIEW_SCHEMA,
)
from ai_runtime.runtime.sessions import (  # noqa: E402
    ForkCapability,
    ReadinessDetector,
    SessionError,
    SessionKind,
    SessionSpec,
    SessionSupervisor,
    TerminationBehavior,
    TransportMode,
    TrustPromptBehavior,
)

# Runtime-owned namespace for deriving a vendor session UUID from a runtime
# session identifier.  This is the Q2 candidate: the runtime assigns the vendor
# identifier instead of discovering it, so a fork/resume template stays
# renderable from data the runtime already owns.
VENDOR_SESSION_NAMESPACE = uuid.UUID("9f2c1d54-6b3a-5f7e-9c48-1a2b3c4d5e6f")

CLAUDE_MODEL = os.environ.get("PROBE_CLAUDE_MODEL", "haiku")
CODEX_MODEL = os.environ.get("PROBE_CODEX_MODEL", "gpt-5.4-mini")
MAX_LIVE_CALLS = int(os.environ.get("PROBE_MAX_LIVE_CALLS", "30"))
TURN_TIMEOUT = float(os.environ.get("PROBE_TURN_TIMEOUT_SECONDS", "180"))
READINESS_TIMEOUT = float(os.environ.get("PROBE_READINESS_TIMEOUT_SECONDS", "60"))

RECALL_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "properties": {"remembered": {"type": "string"}},
    "required": ["remembered"],
    "additionalProperties": False,
}

REQUIRED_KEYS = {
    StructuredTask.PLAN: {"summary", "steps", "acceptance_criteria", "risks"},
    StructuredTask.IMPLEMENT: {"summary", "tests", "commit"},
    StructuredTask.REVIEW: {"verdict", "summary", "findings"},
}


class BudgetExceeded(RuntimeError):
    """The bounded live-call quota for this increment is exhausted."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def file_evidence(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"present": False, "sha256": None, "bytes": None}
    raw = path.read_bytes()
    return {"present": True, "sha256": digest(raw), "bytes": len(raw)}


class Redactor:
    """Replace machine-identifying strings before anything is persisted."""

    def __init__(self) -> None:
        self._literals: dict[str, str] = {
            str(Path.home()): "$HOME",
            str(REPO_ROOT): "$REPO",
        }

    def add(self, value: str, label: str) -> None:
        if value:
            self._literals[value] = label

    def __call__(self, value: str, limit: int = 2_048) -> str:
        result = value
        for source, target in sorted(
            self._literals.items(), key=lambda item: len(item[0]), reverse=True
        ):
            result = result.replace(source, target)
        result = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", result
        )
        result = re.sub(
            r"(?i)(api[_-]?key|secret|token|authorization|bearer)(\s*[=:]\s*)\S+",
            r"\1\2<REDACTED>",
            result,
        )
        result = re.sub(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "<REDACTED_UUID>",
            result,
        )
        result = re.sub(r"\b[0-9a-fA-F]{32,64}\b", "<REDACTED_DIGEST>", result)
        return result[:limit]


class Budget:
    """Hard cap on authenticated model calls, logged as it is consumed."""

    def __init__(self, maximum: int):
        self.maximum = maximum
        self.calls: list[dict[str, Any]] = []

    def spend(self, cli: str, gate: str, tag: str) -> int:
        if len(self.calls) >= self.maximum:
            raise BudgetExceeded(
                f"live-call budget of {self.maximum} is exhausted; stop and ask the human"
            )
        index = len(self.calls) + 1
        self.calls.append({"index": index, "cli": cli, "gate": gate, "tag": tag, "at": utc_now()})
        print(f"[live-call {index}/{self.maximum}] {cli} {gate} {tag}", flush=True)
        return index

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {"total": len(self.calls)}
        for call in self.calls:
            counts[call["cli"]] = counts.get(call["cli"], 0) + 1
        return counts


@dataclasses.dataclass
class Invocation:
    argv: list[str]
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_ms: float

    def evidence(self, redact: Redactor, *, prompt_index: int | None = -1) -> dict[str, Any]:
        argv = [redact(part, 512) for part in self.argv]
        if prompt_index is not None:
            argv[prompt_index] = "<PROMPT_REDACTED>"
        return {
            "argv_redacted": argv,
            "argv_sha256": digest("\0".join(self.argv)),
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_ms": round(self.duration_ms, 3),
            "stdout_sha256": digest(self.stdout),
            "stderr_sha256": digest(self.stderr),
            "stdout_bytes": len(self.stdout.encode("utf-8")),
            "stderr_bytes": len(self.stderr.encode("utf-8")),
            "diagnostic_redacted": (
                "" if self.exit_code == 0 else redact(self.stderr or self.stdout, 512)
            ),
        }


def invoke(argv: Sequence[str], *, cwd: Path, timeout: float) -> Invocation:
    started = time.perf_counter_ns()
    try:
        # stdin=DEVNULL is required, not defensive: `codex exec` prints
        # "Reading additional input from stdin..." and blocks until EOF when it
        # inherits an open stdin, which a live probe run observed as a 210s
        # timeout rather than a turn.
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        stdout, stderr, exit_code, timed_out = (
            completed.stdout,
            completed.stderr,
            completed.returncode,
            False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code, timed_out = None, True
    return Invocation(
        argv=list(argv),
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=(time.perf_counter_ns() - started) / 1_000_000,
    )


def json_roots(output: str) -> Iterator[tuple[str, Any]]:
    stripped = output.strip()
    if stripped:
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            decoded = None
        if decoded is not None:
            yield "whole-stdout", decoded
    for index, line in enumerate(output.splitlines()):
        try:
            yield f"jsonl-line[{index}]", json.loads(line)
        except json.JSONDecodeError:
            continue


def walk_traced(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from walk_traced(child, (*path, f".{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_traced(child, (*path, f"[{index}]"))
    elif isinstance(value, str):
        candidate = value.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.IGNORECASE)
        step = "<json-string>"
        if fenced:
            candidate, step = fenced.group(1), "<code-fence>"
        if candidate.startswith(("{", "[")):
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                return
            yield from walk_traced(decoded, (*path, step))


def trace_structured(output: str, required: set[str]) -> dict[str, Any]:
    """Locate a required-key object and report how deeply it was buried.

    The runtime's `_extract_structured` digs through nesting, JSON-in-string, and
    code fences.  Recording which of those it needed is the difference between a
    stable vendor contract and a parser compensating for an unstable one.
    """
    root_shapes: list[str] = []
    for source, root in json_roots(output):
        if len(root_shapes) < 4:
            root_shapes.append(
                f"{source}:{sorted(root)}"
                if isinstance(root, Mapping)
                else f"{source}:{type(root).__name__}"
            )
        for path, node in walk_traced(root):
            if isinstance(node, Mapping) and required.issubset(node):
                return {
                    "found": True,
                    "source": source,
                    "path": "".join(path) or "<root>",
                    "depth": len(path),
                    "needed_json_string_decode": "<json-string>" in path,
                    "needed_code_fence_strip": "<code-fence>" in path,
                    "extra_keys": sorted(set(node) - required),
                    "root_shapes": root_shapes,
                }
    return {
        "found": False,
        "source": None,
        "path": None,
        "depth": None,
        "needed_json_string_decode": False,
        "needed_code_fence_strip": False,
        "extra_keys": [],
        "root_shapes": root_shapes,
    }


def find_value(output: str, keys: set[str]) -> str | None:
    for _source, root in json_roots(output):
        for _path, node in walk_traced(root):
            if isinstance(node, Mapping):
                for key in keys:
                    candidate = node.get(key)
                    if isinstance(candidate, str) and candidate:
                        return candidate
    return None


def find_usage(output: str) -> dict[str, Any] | None:
    fields = {
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "cached_input_tokens",
    }
    best: dict[str, Any] | None = None
    for _source, root in json_roots(output):
        for _path, node in walk_traced(root):
            if isinstance(node, Mapping) and fields & set(node):
                candidate = {
                    key: node[key]
                    for key in sorted(fields & set(node))
                    if isinstance(node[key], int)
                }
                if candidate and (best is None or len(candidate) > len(best)):
                    best = candidate
    return best


def find_cost(output: str) -> float | None:
    for _source, root in json_roots(output):
        for _path, node in walk_traced(root):
            if isinstance(node, Mapping):
                value = node.get("total_cost_usd")
                if isinstance(value, (int, float)):
                    return float(value)
    return None


# Bounded allowlist of session-shaped diagnostic lines.  A readiness failure has
# to report what the pane actually showed, or the detector can never be bound to
# reality.  A raw pane capture is still never retained: only lines matching these
# shapes, redacted, length-capped, and limited in number.
MARKER_PATTERNS = (
    r"(?i)do you trust",
    r"(?i)trust th(is|e) (files|folder|contents|directory)",
    r"(?i)^[0-9]?\s*[.)]?\s*(yes|no)\b",
    r"(?i)press (enter|esc|tab)",
    # The prompt glyph was anchored to end-of-line, which is the very assumption
    # the declared Claude detector got wrong, so the idle prompt line was never
    # captured and the detector could not be rebound from evidence.
    r"[❯>]",  # noqa: RUF001
    r"(?i)model:\s*\S+",
    r"(?i)welcome to",
    r"(?i)(error|not found|unknown|invalid|failed|no such)",
    r"(?i)(session|thread|conversation|fork|resume)",
    r"(?i)usage:",
    r"(?i)(for shortcuts|for help|esc to|ctrl\+|shift\+tab)",
    r"[╭╮╰╯]",
)


# Candidate readiness patterns evaluated against the live pane so a declaration
# change is bound to a recorded match rather than to a reading of the vendor's
# rendering.  Every candidate is also evaluated against the trust-dialog pane:
# one that matches there is unusable, because `_wait_ready` checks readiness on
# the same capture in which it just answered a trust prompt, and would report
# READY while the dialog is still up.
READY_PATTERN_TRIALS: dict[str, tuple[tuple[str, str], ...]] = {
    "claude": (
        ("declared_glyph_at_line_end", r"(?:^|\n).*?[❯>]\s*$"),  # noqa: RUF001
        ("glyph_line_start_any", r"^\s*[❯>](?:\s|$)"),  # noqa: RUF001
        ("glyph_not_numbered_option", r"^\s*[❯>]\s+(?!\d+\.)\S"),  # noqa: RUF001
        ("glyph_placeholder_hint", r"^\s*[❯>]\s+Try\s"),  # noqa: RUF001
        ("footer_shift_tab_cycle", r"(?i)\(shift\+tab to cycle\)"),
        ("footer_plan_mode_on", r"(?i)plan mode on"),
    ),
    "codex": (("declared_model_line", r"model:\s+(?!loading)\S+"),),
}


# Candidate trust patterns.  The declared one was never observed on Claude; it
# was carried into the declaration without evidence, which is what the first
# G2 iteration disproved.
TRUST_PATTERN_TRIALS: tuple[tuple[str, str], ...] = (
    ("declared_do_you_trust_the_contents", r"Do you trust the contents"),
    ("broad_do_you_trust", r"(?i)do you trust"),
    ("yes_i_trust_this_folder", r"Yes, I trust this folder"),
    ("numbered_first_option_yes", r"^\s*[❯>]?\s*1\.\s*Yes\b"),  # noqa: RUF001
)


# One-time interactive gates observed on the installed CLIs.  These are dismissed
# for the disposable fixture only, and every dismissal is recorded together with
# whether the adapter's declared trust pattern was able to see it.
INTERACTIVE_GATES = (
    ("claude_workspace_trust", r"(?i)yes, I trust this folder"),
    ("codex_startup_notice", r"(?i)press enter to continue"),
    ("generic_first_option", r"(?i)^\s*[❯>]?\s*1\.\s*(yes|proceed|allow|continue)"),  # noqa: RUF001
)


def candidate_markers(pane: str, redact: Redactor, limit: int = 16) -> list[str]:
    lines: list[str] = []
    for line in pane.splitlines():
        stripped = line.strip()
        if not stripped or len(lines) >= limit:
            continue
        if any(re.search(pattern, stripped) for pattern in MARKER_PATTERNS):
            candidate = redact(stripped, 200)
            if candidate not in lines:
                lines.append(candidate)
    return lines


def pattern_trials(
    pane: str, trials: Sequence[tuple[str, str]], redact: Redactor
) -> list[dict[str, Any]]:
    """Record which candidate patterns the live pane actually satisfies."""
    return [
        {
            "name": name,
            "pattern": pattern,
            "matched": bool(re.search(pattern, pane, re.MULTILINE)),
            "line_redacted": matched_line(pane, pattern, redact),
        }
        for name, pattern in trials
    ]


def matched_line(pane: str, pattern: str, redact: Redactor) -> str | None:
    for line in pane.splitlines():
        if re.search(pattern, line):
            return redact(line.strip(), 200)
    if re.search(pattern, pane, re.MULTILINE):
        return "<matched across lines; single-line capture unavailable>"
    return None


STABLE_PREFIX = "\n".join(
    f"fixture-fact {index:03d}: the disposable probe repository holds no project data, "
    "no credentials, and no history beyond its single seed commit."
    for index in range(1, 61)
)


class Probe:
    def __init__(self, *, run_id: str, live: bool, budget: Budget):
        self.run_id = run_id
        self.live = live
        self.budget = budget
        self.redact = Redactor()
        self.nonce = uuid.uuid4().hex
        self.results: dict[str, Any] = {}
        self.iterations: list[dict[str, Any]] = []
        self.residue: dict[str, Any] = {}
        self.claude_session_ids: dict[str, str] = {}
        self.codex_session_ids: dict[str, str] = {}
        self.started_epoch = time.time()

    # ---------------------------------------------------------------- fixture

    def build_fixture(self, root: Path) -> None:
        self.fixture = root
        self.repo = root / "repo"
        self.state_dir = root / "runtime-state"
        self.worktree_root = root / "worktrees"
        self.worktree = self.worktree_root / "probe"
        self.redact.add(str(root), "$FIXTURE")
        self.redact.add(self.nonce, "<REDACTED_NONCE>")
        for path in (self.repo, self.state_dir, self.worktree_root):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
        git = ["git", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            [*git, "config", "user.email", "probe@example.invalid"], cwd=self.repo, check=True
        )
        subprocess.run([*git, "config", "user.name", "Live Probe"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text(
            "# Disposable live-contract probe fixture\n\nNo project data and no secrets.\n",
            encoding="utf-8",
        )
        (self.repo / "src").mkdir(exist_ok=True)
        (self.repo / "src" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run([*git, "add", "-A"], cwd=self.repo, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "probe fixture"], cwd=self.repo, check=True)
        subprocess.run(
            [*git, "worktree", "add", "-q", "-b", "feature/probe", str(self.worktree)],
            cwd=self.repo,
            check=True,
        )
        self.git_base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        self.claude_project_slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.repo))
        self.claude_project_dir = Path.home() / ".claude" / "projects" / self.claude_project_slug
        self.claude_project_dir_existed = self.claude_project_dir.exists()

    def fixture_clean(self) -> bool:
        for path in (self.repo, self.worktree):
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                text=True,
                capture_output=True,
                check=False,
            )
            if status.returncode != 0 or status.stdout.strip():
                return False
        return True

    def failure_markers(
        self,
        supervisor: SessionSupervisor,
        session_id: str,
        detector: ReadinessDetector,
        *,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Report what the pane actually showed when a detector never matched."""
        record = supervisor.read(session_id)
        pane = supervisor._capture(record, detector.pane_lines) if record is not None else ""
        trials = READY_PATTERN_TRIALS.get(label or "", ())
        return {
            "candidate_markers_redacted": candidate_markers(pane, self.redact),
            "ready_pattern_trials": pattern_trials(pane, trials, self.redact) if trials else None,
            "ready_pattern_matched_pane": bool(
                re.search(
                    detector.ready_pattern.replace("{session_identity}", r"[0-9a-f]{32}"),
                    pane,
                    re.MULTILINE,
                )
            ),
            "trust_pattern_matched_pane": bool(
                detector.trust_pattern and re.search(detector.trust_pattern, pane, re.MULTILINE)
            ),
            "pane_bytes": len(pane.encode("utf-8")),
            "pane_sha256": digest(pane),
            "pane_dead": (
                supervisor._tmux(
                    ["display-message", "-p", "-t", f"{record.tmux_name}:0.0", "#{pane_dead}"]
                ).stdout.strip()
                if record is not None
                else None
            ),
        }

    def record_iteration(self, gate: str, outcome: str, correction: str) -> None:
        self.iterations.append(
            {"gate": gate, "outcome": outcome, "correction": correction, "at": utc_now()}
        )
        print(f"[iteration] {gate}: {outcome} -> {correction}", flush=True)

    # ------------------------------------------------------------- vendor ids

    def vendor_session_id(self, adapter: str, runtime_session_id: str) -> str:
        return str(
            uuid.uuid5(VENDOR_SESSION_NAMESPACE, f"{adapter}|{runtime_session_id}|{self.run_id}")
        )

    def claude_transcript(self, session_id: str) -> Path | None:
        candidate = self.claude_project_dir / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
        matches = sorted((Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"))
        return matches[0] if matches else None

    def codex_rollouts_since_start(self) -> list[Path]:
        sessions = Path.home() / ".codex" / "sessions"
        if not sessions.is_dir():
            return []
        return [
            path for path in sessions.rglob("*.jsonl") if path.stat().st_mtime >= self.started_epoch
        ]

    def codex_rollout(self, session_id: str) -> Path | None:
        for path in self.codex_rollouts_since_start():
            if session_id in path.name:
                return path
        return None

    # ------------------------------------------------------------------ gates

    def ensure_adapters(self) -> tuple[ClaudeCLIAdapter, CodexCLIAdapter]:
        """Bind the version-observed declarations any gate may need."""
        if not hasattr(self, "_adapters"):
            claude = ClaudeCLIAdapter(model=CLAUDE_MODEL)
            codex = CodexCLIAdapter(model=CODEX_MODEL)
            self.claude_version = claude.version
            self.codex_version = codex.version
            self.claude_declaration = claude.persistent_declaration
            self.codex_declaration = codex.persistent_declaration
            self._adapters = (claude, codex)
        return self._adapters

    def gate_1(self) -> None:
        """Live structured result under the exact adapter argv."""
        claude, codex = self.ensure_adapters()
        gate: dict[str, Any] = {"roles": {}}

        plans = [
            (
                claude,
                StructuredTask.PLAN,
                PLAN_SCHEMA,
                self.repo,
                "Plan one change to this disposable probe repository: add a module docstring to "
                "src/module.py. Return only the structured plan. Do not use tools and do not "
                "read or write files.",
            ),
            (
                claude,
                StructuredTask.REVIEW,
                REVIEW_SCHEMA,
                self.repo,
                'Review this proposed change to src/module.py: `+"""Probe module."""`. Return '
                'only the structured review. The verdict field must be exactly "approve" or '
                '"changes_requested". Do not use tools and do not read or write files.',
            ),
            (
                codex,
                StructuredTask.IMPLEMENT,
                IMPLEMENTATION_SCHEMA,
                self.worktree,
                "Remember this harmless probe nonce for later turns: "
                + self.nonce
                + ". Then, in this workspace only: append the line PROBE = 2 to src/module.py, "
                "stage it, and commit with message 'probe: append marker'. Return only the "
                "structured result. The commit field must be the exact 40-character object ID "
                "printed by `git rev-parse HEAD` after your commit.",
            ),
        ]

        for adapter, task, schema, cwd, prompt in plans:
            name = adapter.capability.name
            with tempfile.TemporaryDirectory(prefix="probe-schema-") as temporary:
                schema_path = Path(temporary) / f"{task}.schema.json"
                schema_json = json.dumps(schema, sort_keys=True, separators=(",", ":"))
                schema_path.write_text(schema_json + "\n", encoding="utf-8")
                argv = adapter._command(
                    task,
                    prompt=prompt,
                    cwd=cwd,
                    schema_path=schema_path,
                    schema_json=schema_json,
                    timeout_seconds=TURN_TIMEOUT,
                )
                self.budget.spend(name, "G1", f"{task}-direct")
                result = invoke(argv, cwd=cwd, timeout=TURN_TIMEOUT + 30)
            trace = trace_structured(result.stdout, REQUIRED_KEYS[task])
            validated = False
            validation_error = ""
            if trace["found"]:
                value = _extract_structured(result.stdout, task, REQUIRED_KEYS[task])
                if value is not None:
                    try:
                        _validate_result(task, value)
                        validated = True
                    except Exception as exc:  # AdapterError
                        validation_error = self.redact(str(exc), 256)
                else:
                    validation_error = "extract_structured returned no candidate"
            session_id = find_value(
                result.stdout, {"session_id", "sessionId", "conversation_id", "thread_id"}
            )
            if session_id:
                self.redact.add(session_id, "<REDACTED_UUID>")
                (self.claude_session_ids if name == "claude" else self.codex_session_ids)[
                    f"g1-{task}"
                ] = session_id
            gate["roles"][f"{name}-{task}"] = {
                **result.evidence(self.redact),
                "prompt_sha256": digest(prompt),
                "schema_channel": "inline_json" if name == "claude" else "schema_file",
                "structured_shape": trace,
                "validate_result_passed": validated,
                "validation_error_redacted": validation_error,
                "session_id_present": bool(session_id),
                "session_id_sha256": digest(session_id) if session_id else None,
                "usage": find_usage(result.stdout),
                "total_cost_usd": find_cost(result.stdout),
            }
            if not validated:
                self.record_iteration(
                    "G1",
                    f"{name} {task} produced no schema-valid structured result",
                    "kept as recorded negative evidence; see structured_shape for the observed shape",
                )

        gate["supervised_transport"] = self.gate_1_supervised(claude)
        gate["passed"] = all(role["validate_result_passed"] for role in gate["roles"].values())
        self.results["G1"] = gate

    def gate_1_supervised(self, claude: ClaudeCLIAdapter) -> dict[str, Any]:
        """One end-to-end turn through the real SessionSupervisor transport."""
        supervisor = SessionSupervisor(self.state_dir / "g1-supervised")
        claude.bind_supervisor(supervisor)
        prompt = (
            "Plan one change to this disposable probe repository: add a trailing newline to "
            "README.md. Return only the structured plan. Do not use tools."
        )
        record: dict[str, Any] = {
            "transport_mode": str(TransportMode.TMUX_SUPERVISED_NONINTERACTIVE_V1),
            "prompt_sha256": digest(prompt),
        }
        try:
            self.budget.spend("claude", "G1", "plan-supervised")
            result = claude.invoke(
                StructuredTask.PLAN,
                prompt=prompt,
                cwd=self.repo,
                schema=PLAN_SCHEMA,
                timeout_seconds=TURN_TIMEOUT,
            )
            record.update(
                {
                    "passed": True,
                    "result_fields": sorted(result.value),
                    "evidence_keys": sorted(result.evidence),
                    "exit_code": result.evidence.get("exit_code"),
                    "duration_ms": result.evidence.get("duration_ms"),
                    "stdout_bytes": result.evidence.get("stdout_bytes"),
                }
            )
            claude.acknowledge(result)
        except Exception as exc:
            record.update({"passed": False, "error_redacted": self.redact(str(exc), 512)})
            self.record_iteration(
                "G1",
                "supervised transport turn failed",
                "recorded as negative evidence; the direct argv result is reported separately",
            )
        finally:
            supervisor._tmux(["kill-server"])
        return record

    def clear_interactive_gates(
        self,
        supervisor: SessionSupervisor,
        *,
        label: str,
        launch_command: Sequence[str],
        cwd: Path,
        detector: ReadinessDetector,
    ) -> dict[str, Any]:
        """Dismiss one-time interactive gates for the disposable fixture only.

        `SessionSupervisor._wait_ready` can only act on a gate its declared
        `trust_pattern` matches.  Anything else — a differently worded trust
        dialog, a first-run notice — is invisible to it and simply times out.
        This throwaway session establishes the operational precondition and
        records, verbatim, every gate the declared pattern failed to see.
        """
        session = f"prewarm-{label}"
        evidence: dict[str, Any] = {
            "gates_dismissed": [],
            "declared_trust_pattern_matched": False,
            "ready_pattern_matched_after_clearing": False,
            "ready_line_redacted": None,
            "gate_lines_redacted": [],
            # Recorded on the pane that still shows a one-time gate, and again on
            # the settled pane after every known gate is cleared.  The first
            # proves a candidate readiness pattern cannot fire on a trust dialog;
            # the second binds the pattern that can replace the declared one.
            "trust_pane_trials": None,
            "settled_pane_trials": None,
        }
        ready_trials = READY_PATTERN_TRIALS.get(label, ())
        quiet_samples = 0
        supervisor._tmux(
            ["new-session", "-d", "-s", session, "-c", str(cwd), shlex.join(launch_command)],
            check=True,
        )
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                pane = supervisor._tmux(
                    ["capture-pane", "-p", "-S", f"-{detector.pane_lines}", "-t", f"{session}:0.0"]
                ).stdout
                if detector.trust_pattern and re.search(detector.trust_pattern, pane, re.MULTILINE):
                    evidence["declared_trust_pattern_matched"] = True
                expected = detector.ready_pattern.replace("{session_identity}", r"[0-9a-f]{32}")
                if re.search(expected, pane, re.MULTILINE):
                    evidence["ready_pattern_matched_after_clearing"] = True
                    evidence["ready_line_redacted"] = matched_line(pane, expected, self.redact)
                    break
                dismissed = False
                for name, pattern in INTERACTIVE_GATES:
                    if re.search(pattern, pane, re.MULTILINE) and name not in [
                        item["gate"] for item in evidence["gates_dismissed"]
                    ]:
                        line = matched_line(pane, pattern, self.redact)
                        if evidence["trust_pane_trials"] is None:
                            evidence["trust_pane_trials"] = {
                                "trust": pattern_trials(pane, TRUST_PATTERN_TRIALS, self.redact),
                                "ready": pattern_trials(pane, ready_trials, self.redact),
                            }
                        evidence["gates_dismissed"].append(
                            {
                                "gate": name,
                                "pattern": pattern,
                                "line_redacted": line,
                                "seen_by_declared_trust_pattern": bool(
                                    detector.trust_pattern
                                    and re.search(detector.trust_pattern, line or "")
                                ),
                            }
                        )
                        supervisor._tmux(["send-keys", "-t", f"{session}:0.0", "Enter"])
                        dismissed = True
                        quiet_samples = 0
                        time.sleep(4)
                        break
                if not dismissed:
                    evidence["gate_lines_redacted"] = candidate_markers(pane, self.redact, 8)
                    quiet_samples += 1
                    # Three gate-free samples means the launch has settled, so the
                    # pane can be trialled without waiting out the full deadline.
                    if quiet_samples >= 3:
                        evidence["settled_pane_trials"] = pattern_trials(
                            pane, ready_trials, self.redact
                        )
                        break
                    time.sleep(2)
        finally:
            supervisor._tmux(["kill-session", "-t", session])
        return evidence

    def gate_2(self) -> None:
        """Persistent root readiness, identity stability, and child survival."""
        self.ensure_adapters()
        gate: dict[str, Any] = {"adapters": {}}
        for name, declaration in (
            ("claude", self.claude_declaration),
            ("codex", self.codex_declaration),
        ):
            supervisor = SessionSupervisor(self.state_dir / f"g2-{name}")
            observed: dict[str, Any] = {
                "declared_root_launch_redacted": [
                    self.redact(part, 256) for part in declaration.root_launch_command
                ],
                "declared_ready_pattern": declaration.root_readiness.ready_pattern,
                "declared_trust_pattern": declaration.root_readiness.trust_pattern,
                "declared_trust_behavior": str(declaration.trust_prompt),
            }
            observed["interactive_gate_clearing"] = self.clear_interactive_gates(
                supervisor,
                label=name,
                launch_command=declaration.root_launch_command,
                cwd=self.repo,
                detector=declaration.root_readiness,
            )
            # Two variants.  The declared production path keeps
            # TrustPromptBehavior.REJECT, so a fresh fixture must fail closed at
            # a trust dialog: that is correct behaviour, recorded as such.  The
            # readiness measurement then runs on the disposable-authorized path.
            production = SessionSpec(
                session_id=f"{name}-root-declared",
                adapter=name,
                adapter_version=declaration.adapter_version,
                role="root",
                cwd=self.repo,
                launch_command=declaration.root_launch_command,
                readiness=declaration.root_readiness,
                trust_prompt=declaration.trust_prompt,
                termination=declaration.termination,
                transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
                session_kind=SessionKind.ROOT,
                policy_revision="live-persistent-contract-probe",
                capability_revision=declaration.declaration_revision,
                capability_sha256=declaration.digest,
                read_only=True,
            )
            try:
                declared_start = supervisor.start(production, readiness_timeout=READINESS_TIMEOUT)
                observed["declared_production_path"] = {
                    "ready": declared_start.ready,
                    "state": str(declared_start.state),
                    "fail_closed": False,
                }
            except SessionError as exc:
                observed["declared_production_path"] = {
                    "ready": False,
                    "fail_closed": True,
                    "error_redacted": self.redact(str(exc), 256),
                    **self.failure_markers(
                        supervisor, production.session_id, declaration.root_readiness, label=name
                    ),
                }

            spec = SessionSpec(
                session_id=f"{name}-root",
                adapter=name,
                adapter_version=declaration.adapter_version,
                role="root",
                cwd=self.repo,
                launch_command=declaration.root_launch_command,
                readiness=declaration.root_readiness,
                trust_prompt=TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY,
                termination=declaration.termination,
                transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
                session_kind=SessionKind.ROOT,
                disposable=True,
                policy_revision="live-persistent-contract-probe",
                capability_revision=declaration.declaration_revision,
                capability_sha256=declaration.digest,
                read_only=True,
            )
            try:
                start = supervisor.start(spec, readiness_timeout=READINESS_TIMEOUT)
                record = supervisor.read(spec.session_id)
                assert record is not None
                pane = supervisor._capture(record, declaration.root_readiness.pane_lines)
                observed.update(
                    {
                        "readiness_reached": start.ready,
                        "state": str(start.state),
                        "readiness_line_redacted": matched_line(
                            pane, declaration.root_readiness.ready_pattern, self.redact
                        ),
                        "trust_line_redacted": (
                            matched_line(
                                pane, declaration.root_readiness.trust_pattern, self.redact
                            )
                            if declaration.root_readiness.trust_pattern
                            else None
                        ),
                        "trust_prompt_observed": bool(
                            declaration.root_readiness.trust_pattern
                            and re.search(
                                declaration.root_readiness.trust_pattern, pane, re.MULTILINE
                            )
                        ),
                        "pane_bytes": start.pane_bytes,
                        "ready_pattern_trials": pattern_trials(
                            pane, READY_PATTERN_TRIALS.get(name, ()), self.redact
                        ),
                    }
                )
                stability = []
                for _ in range(6):
                    time.sleep(2)
                    again = supervisor.observe(spec)
                    stability.append(
                        {
                            "ready": again.ready,
                            "state": str(again.state),
                            "identity_stable": supervisor._identity_matches(record),
                        }
                    )
                observed["identity_observation_window"] = {
                    "samples": len(stability),
                    "window_seconds": 12,
                    "all_ready": all(item["ready"] for item in stability),
                    "all_identity_stable": all(item["identity_stable"] for item in stability),
                    "states": sorted({item["state"] for item in stability}),
                }
                observed["child_termination"] = self.child_survival(supervisor, spec)
                observed["passed"] = bool(
                    start.ready
                    and observed["identity_observation_window"]["all_ready"]
                    and observed["identity_observation_window"]["all_identity_stable"]
                    and observed["child_termination"]["root_survived"]
                )
            except SessionError as exc:
                observed.update(
                    {
                        "readiness_reached": False,
                        "passed": False,
                        "error_redacted": self.redact(str(exc), 512),
                        **self.failure_markers(
                            supervisor, spec.session_id, declaration.root_readiness, label=name
                        ),
                    }
                )
                self.record_iteration(
                    "G2",
                    f"{name} root did not reach declared readiness",
                    "recorded verbatim readiness/trust markers for detector binding",
                )
            finally:
                supervisor._tmux(["kill-server"])
            gate["adapters"][name] = observed
        gate["passed"] = all(item.get("passed") for item in gate["adapters"].values())
        self.results["G2"] = gate

    def child_survival(self, supervisor: SessionSupervisor, root: SessionSpec) -> dict[str, Any]:
        """A child session terminating must not disturb the root."""
        worker = REPO_ROOT / "src" / "ai_runtime" / "runtime" / "_terminal_event_worker.py"
        child = SessionSpec(
            session_id=f"{root.adapter}-feature-probe-child-1",
            adapter=root.adapter,
            adapter_version=root.adapter_version,
            role="reviewer",
            cwd=self.repo,
            launch_command=(
                sys.executable,
                str(worker),
                "--state-dir",
                str(self.state_dir / f"g2-{root.adapter}"),
                "--session-id",
                f"{root.adapter}-feature-probe-child-1",
                "--identity",
                "{session_identity}",
            ),
            readiness=ReadinessDetector(r"^AI_RUNTIME_EVENT_READY {session_identity}$"),
            trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
            transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
            feature_id="probe",
            fork=ForkCapability.SYNTHETIC,
            session_kind=SessionKind.FEATURE,
            parent_root_id=root.session_id,
            fork_mode="synthetic",
            policy_revision=root.policy_revision,
            git_base=self.git_base,
            capability_revision=root.capability_revision,
            capability_sha256=root.capability_sha256,
            read_only=True,
        )
        started = supervisor.start(child, readiness_timeout=30)
        supervisor.terminate(child.session_id, grace_seconds=3)
        after = supervisor.observe(root)
        return {
            "child_kind": "runtime_event_worker",
            "child_ready": started.ready,
            "child_terminated": True,
            "root_survived": after.ready and after.live,
            "root_state_after": str(after.state),
        }

    def claude_print(
        self,
        *,
        gate: str,
        tag: str,
        prompt: str,
        session_id: str | None = None,
        resume: str | None = None,
        fork: bool = False,
        schema: Mapping[str, Any] | None = None,
    ) -> tuple[Invocation, dict[str, Any]]:
        argv = [
            shutil.which("claude") or "claude",
            "--print",
            "--permission-mode",
            "plan",
            "--disable-slash-commands",
            "--output-format",
            "json",
            "--model",
            CLAUDE_MODEL,
        ]
        if schema is not None:
            argv.extend(
                ["--json-schema", json.dumps(schema, sort_keys=True, separators=(",", ":"))]
            )
        if session_id is not None:
            argv.extend(["--session-id", session_id])
        if resume is not None:
            argv.extend(["--resume", resume])
        if fork:
            argv.append("--fork-session")
        argv.append(prompt)
        self.budget.spend("claude", gate, tag)
        result = invoke(argv, cwd=self.repo, timeout=TURN_TIMEOUT + 30)
        returned = find_value(result.stdout, {"session_id", "sessionId"})
        if returned:
            self.redact.add(returned, "<REDACTED_UUID>")
        evidence = {
            **result.evidence(self.redact),
            "prompt_sha256": digest(prompt),
            "requested_session_id_sha256": digest(session_id) if session_id else None,
            "resumed_session_id_sha256": digest(resume) if resume else None,
            "fork_session_flag": fork,
            "returned_session_id_sha256": digest(returned) if returned else None,
            "usage": find_usage(result.stdout),
            "total_cost_usd": find_cost(result.stdout),
        }
        return result, evidence

    def gate_3_4_6_claude(self) -> None:
        """Claude native fork, resume, and prompt-cache measurement."""
        self.ensure_adapters()
        root_runtime_id = "claude-root"
        root_uuid = self.vendor_session_id("claude", root_runtime_id)
        fresh_uuid = self.vendor_session_id("claude", "claude-fresh-baseline")
        self.redact.add(root_uuid, "<REDACTED_UUID>")
        self.redact.add(fresh_uuid, "<REDACTED_UUID>")
        downstream = (
            "Reply with exactly this token and nothing else: DOWNSTREAM_OK. "
            "Do not use tools and do not read or write files."
        )
        seed = (
            "AI-RUNTIME PROBE ROOT ORIENTATION v1\n"
            + STABLE_PREFIX
            + "\nRemember this harmless probe nonce for later turns: "
            + self.nonce
            + ".\nReply with exactly this token and nothing else: ROOT_READY. "
            "Do not use tools and do not read or write files."
        )
        gate3: dict[str, Any] = {
            "runtime_assigned_root_uuid": True,
            "root_uuid_sha256": digest(root_uuid),
            "vendor_uuid_derivation": "uuid5(runtime_namespace, adapter|runtime_session_id|run_id)",
        }
        gate4: dict[str, Any] = {}
        cache: dict[str, Any] = {"turns": {}}

        seed_result, seed_evidence = self.claude_print(
            gate="G3", tag="root-seed", prompt=seed, session_id=root_uuid
        )
        gate3["root_seed"] = seed_evidence
        cache["turns"]["root_seed"] = {
            "usage": seed_evidence["usage"],
            "total_cost_usd": seed_evidence["total_cost_usd"],
        }
        transcript = self.claude_transcript(root_uuid)
        gate3["root_transcript_before_fork"] = file_evidence(transcript)
        if seed_result.exit_code != 0 or transcript is None:
            gate3["passed"] = False
            gate3["blocked_reason"] = "root seed turn did not establish a resumable session"
            self.record_iteration(
                "G3",
                "root seed turn failed or left no resumable transcript",
                "native fork cannot be evaluated without a live root; kept as negative evidence",
            )
            self.results["G3"] = gate3
            self.results["G4"] = {"passed": False, "blocked_reason": "no root session"}
            self.results["G6"] = cache
            return

        forks: dict[str, Any] = {}
        for label in ("fork_a", "fork_b"):
            _result, evidence = self.claude_print(
                gate="G3", tag=label, prompt=downstream, resume=root_uuid, fork=True
            )
            after = file_evidence(transcript)
            evidence["root_transcript_after"] = after
            evidence["root_unmutated"] = (
                after["sha256"] == gate3["root_transcript_before_fork"]["sha256"]
            )
            evidence["child_session_distinct_from_root"] = evidence[
                "returned_session_id_sha256"
            ] is not None and evidence["returned_session_id_sha256"] != digest(root_uuid)
            child_id = find_value(_result.stdout, {"session_id", "sessionId"})
            if child_id:
                self.claude_session_ids[label] = child_id
                evidence["child_transcript"] = file_evidence(self.claude_transcript(child_id))
            forks[label] = evidence
            cache["turns"][label] = {
                "usage": evidence["usage"],
                "total_cost_usd": evidence["total_cost_usd"],
            }
        gate3["forks"] = forks
        gate3["children_distinct_from_each_other"] = (
            forks["fork_a"]["returned_session_id_sha256"]
            != forks["fork_b"]["returned_session_id_sha256"]
        )
        gate3["passed"] = bool(
            all(item["child_session_distinct_from_root"] for item in forks.values())
            and all(item["root_unmutated"] for item in forks.values())
            and gate3["children_distinct_from_each_other"]
        )

        _fresh, fresh_evidence = self.claude_print(
            gate="G6", tag="fresh-baseline", prompt=downstream, session_id=fresh_uuid
        )
        cache["turns"]["fresh_baseline"] = {
            "usage": fresh_evidence["usage"],
            "total_cost_usd": fresh_evidence["total_cost_usd"],
        }
        cache["fresh_baseline"] = fresh_evidence

        child_id = self.claude_session_ids.get("fork_a")
        if child_id:
            recall_result, recall_evidence = self.claude_print(
                gate="G4",
                tag="resume-fork-child",
                prompt=(
                    "Return only JSON with the field remembered set to the probe nonce I asked "
                    'you to remember earlier. If you do not have it, set it to "unknown". '
                    "Do not use tools."
                ),
                resume=child_id,
                schema=RECALL_SCHEMA,
            )
            recalled = None
            for _source, root in json_roots(recall_result.stdout):
                for _path, node in walk_traced(root):
                    if isinstance(node, Mapping) and isinstance(node.get("remembered"), str):
                        recalled = node["remembered"]
                        break
                if recalled:
                    break
            recall_evidence.update(
                {
                    "nonce_sha256": digest(self.nonce),
                    "recall_matched_nonce": recalled == self.nonce,
                    "recall_present": recalled is not None,
                }
            )
            gate4 = {
                "claude": recall_evidence,
                "resumed_target": "forked child session",
                "inherited_root_context": recall_evidence["recall_matched_nonce"],
            }
            if not recall_evidence["recall_matched_nonce"]:
                self.record_iteration(
                    "G4",
                    "Claude resume did not recall the root nonce through the forked child",
                    "recorded as negative evidence; resume stays fail-closed",
                )
        else:
            gate4 = {"claude": {"passed": False}, "blocked_reason": "no forked child session id"}
        gate4["passed"] = bool(gate4.get("inherited_root_context"))

        cache["measurable"] = any(
            isinstance(turn.get("usage"), dict) and turn["usage"]
            for turn in cache["turns"].values()
        )
        cache["comparison"] = self.cache_comparison(cache["turns"])
        self.results["G3"] = gate3
        self.results["G4"] = gate4
        self.results["G6"] = cache

    @staticmethod
    def cache_comparison(turns: Mapping[str, Any]) -> dict[str, Any]:
        def read(label: str, field: str) -> int | None:
            usage = turns.get(label, {}).get("usage")
            return usage.get(field) if isinstance(usage, dict) else None

        fresh_read = read("fresh_baseline", "cache_read_input_tokens")
        fork_read = read("fork_a", "cache_read_input_tokens")
        return {
            "downstream_prompt_identical": True,
            "fresh_cache_read_input_tokens": fresh_read,
            "forked_cache_read_input_tokens": fork_read,
            "forked_minus_fresh_cache_read": (
                fork_read - fresh_read
                if isinstance(fork_read, int) and isinstance(fresh_read, int)
                else None
            ),
            "fresh_cache_creation_input_tokens": read(
                "fresh_baseline", "cache_creation_input_tokens"
            ),
            "forked_cache_creation_input_tokens": read("fork_a", "cache_creation_input_tokens"),
            "second_fork_cache_read_input_tokens": read("fork_b", "cache_read_input_tokens"),
            "note": (
                "The Claude Code system prompt is part of every prefix, so a fresh turn also "
                "reports cache activity. Only the delta above is attributable to the forked "
                "conversation prefix."
            ),
        }

    def gate_q1_codex(self) -> None:
        """Does `codex fork` compose with `codex exec`?"""
        self.ensure_adapters()
        parent = self.codex_session_ids.get(f"g1-{StructuredTask.IMPLEMENT}")
        seeded = None
        if parent is None:
            argv = [
                shutil.which("codex") or "codex",
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "--cd",
                str(self.worktree),
                "--config",
                'model_reasoning_effort="low"',
                "--model",
                CODEX_MODEL,
                "exec",
                "--ignore-rules",
                "--json",
                "Remember this harmless probe nonce for later turns: "
                + self.nonce
                + ". Reply with exactly: SEEDED. Do not read or write files.",
            ]
            self.budget.spend("codex", "Q1", "parent-seed")
            seeded = invoke(argv, cwd=self.worktree, timeout=TURN_TIMEOUT + 30)
            parent = find_value(seeded.stdout, {"thread_id", "session_id", "conversation_id"})
            if parent:
                self.redact.add(parent, "<REDACTED_UUID>")
                self.codex_session_ids["q1-seed"] = parent
        gate: dict[str, Any] = {
            "parent_session_from": "codex exec --json structured output",
            "parent_session_present": bool(parent),
            "parent_seeded_in_this_gate": seeded is not None,
        }
        if seeded is not None:
            gate["parent_seed"] = seeded.evidence(self.redact)
        if not parent:
            gate.update(
                {
                    "passed": False,
                    "answer": "INCONCLUSIVE: codex exec did not expose a session identifier",
                }
            )
            self.results["Q1"] = gate
            self.results["G3_codex"] = {"passed": False, "blocked_reason": "no parent session id"}
            self.results["G4_codex"] = {"passed": False, "blocked_reason": "no parent session id"}
            return
        parent_rollout = self.codex_rollout(parent)
        gate["parent_rollout_before_fork"] = file_evidence(parent_rollout)
        before = {path.name for path in self.codex_rollouts_since_start()}

        supervisor = SessionSupervisor(self.state_dir / "q1-codex")
        fork_argv = [
            shutil.which("codex") or "codex",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--cd",
            str(self.worktree),
            "--no-alt-screen",
            "--model",
            CODEX_MODEL,
            "fork",
            parent,
        ]
        gate["fork_argv_redacted"] = [self.redact(part, 256) for part in fork_argv]
        gate["interactive_gate_clearing"] = self.clear_interactive_gates(
            supervisor,
            label="codex-fork",
            launch_command=fork_argv,
            cwd=self.worktree,
            detector=self.codex_declaration.root_readiness,
        )
        # Re-snapshot: the prewarm session forks the parent as well and leaves its
        # own rollout behind.  Counting it as "new" was a probe defect, not a
        # vendor limitation, and it made a working fork look undiscoverable.
        before = {path.name for path in self.codex_rollouts_since_start()}
        gate["rollout_snapshot_taken_after_gate_clearing"] = True
        spec = SessionSpec(
            session_id="codex-fork-probe",
            adapter="codex",
            adapter_version=self.codex_version,
            role="implementer",
            cwd=self.worktree,
            launch_command=tuple(fork_argv),
            readiness=self.codex_declaration.root_readiness,
            trust_prompt=TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY,
            transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
            disposable=True,
            policy_revision="live-persistent-contract-probe",
            capability_revision=self.codex_declaration.declaration_revision,
            capability_sha256=self.codex_declaration.digest,
        )
        forked: str | None = None
        try:
            observation = supervisor.start(spec, readiness_timeout=READINESS_TIMEOUT)
            gate["fork_tui_ready"] = observation.ready
            time.sleep(5)
            candidates = sorted({path.name for path in self.codex_rollouts_since_start()} - before)
            gate["new_rollout_count"] = len(candidates)
            uuid_pattern = re.compile(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
            )
            fresh_paths = sorted(
                (path for path in self.codex_rollouts_since_start() if path.name in candidates),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            found = [
                match.group(0)
                for path in fresh_paths
                if (match := uuid_pattern.search(path.name)) and match.group(0) != parent
            ]
            gate["forked_candidate_count"] = len(found)
            if found:
                forked = found[0]
                self.redact.add(forked, "<REDACTED_UUID>")
                self.codex_session_ids["fork"] = forked
            gate["forked_session_discovered"] = forked is not None
            gate["forked_session_sha256"] = digest(forked) if forked else None
        except SessionError as exc:
            gate["fork_tui_ready"] = False
            gate["error_redacted"] = self.redact(str(exc), 512)
            gate.update(
                self.failure_markers(
                    supervisor, spec.session_id, self.codex_declaration.root_readiness
                )
            )
            self.record_iteration(
                "Q1",
                "codex fork TUI did not reach the declared readiness marker",
                "recorded as negative evidence; no synthetic path was relabelled as native",
            )
        finally:
            supervisor._tmux(["kill-server"])

        if forked is None:
            gate.update(
                {
                    "passed": False,
                    "answer": (
                        "NO: codex fork produced no discoverable non-interactive session, so "
                        "codex exec cannot drive a forked session under this transport"
                    ),
                }
            )
            self.results["Q1"] = gate
            self.results["G3_codex"] = {"passed": False, "blocked_reason": gate["answer"]}
            self.results["G4_codex"] = {"passed": False, "blocked_reason": gate["answer"]}
            return

        argv = [
            shutil.which("codex") or "codex",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--cd",
            str(self.worktree),
            "--config",
            'model_reasoning_effort="low"',
            "--model",
            CODEX_MODEL,
            "exec",
            "resume",
            "--ignore-rules",
            "--json",
            forked,
            "Return only the probe nonce I asked you to remember earlier, with no other text. "
            'If you do not have it, return exactly "unknown".',
        ]
        self.budget.spend("codex", "Q1", "exec-resume-forked")
        result = invoke(argv, cwd=self.worktree, timeout=TURN_TIMEOUT + 30)
        composed = result.exit_code == 0
        recalled = self.nonce in result.stdout
        gate.update(
            {
                **result.evidence(self.redact),
                "exec_resume_argv_redacted": [self.redact(part, 256) for part in argv[:-1]]
                + ["<PROMPT_REDACTED>"],
                "exec_resume_succeeded": composed,
                "nonce_recalled": recalled,
                "nonce_sha256": digest(self.nonce),
                "parent_rollout_after_fork": file_evidence(parent_rollout),
                "passed": composed and recalled,
                "answer": (
                    "YES: codex exec resume drove a session created by codex fork"
                    if composed and recalled
                    else "NO: codex exec resume did not drive the forked session with inherited context"
                ),
            }
        )
        gate["parent_unmutated"] = (
            gate["parent_rollout_after_fork"]["sha256"]
            == gate["parent_rollout_before_fork"]["sha256"]
        )
        if not gate["passed"]:
            self.record_iteration(
                "Q1",
                "codex exec resume on a forked session did not inherit the nonce",
                "recorded as the finding; Codex native fork stays fail-closed",
            )
        self.results["Q1"] = gate
        self.results["G3_codex"] = {
            "passed": bool(gate["passed"] and gate["parent_unmutated"]),
            "fork_mode": "native",
            "parent_unmutated": gate["parent_unmutated"],
        }
        self.results["G4_codex"] = {
            "passed": bool(gate["passed"]),
            "resume_surface": "codex exec resume <session_id>",
        }

    def gate_5(self) -> None:
        """Structured terminal events with the live CLI as the event client."""
        self.ensure_adapters()
        root_uuid = self.vendor_session_id("claude", "claude-root")
        session_id = "claude-feature-probe-reviewer-1"
        supervisor = SessionSupervisor(self.state_dir / "g5-claude")
        channel = StructuredTerminalEventChannel(supervisor.state_dir)
        inbox = supervisor.state_dir / "terminal-events" / session_id / "inbox"
        outbox = supervisor.state_dir / "terminal-events" / session_id / "outbox"
        declared = r"^AI_RUNTIME_EVENT_READY {session_identity}$"
        relaxed = r"AI_RUNTIME_EVENT_READY {session_identity}"
        bootstrap = (
            "AI-RUNTIME EVENT CLIENT PROTOCOL v1. You are a runtime event client for a "
            "disposable probe. Follow this protocol exactly and do nothing else.\n"
            f"INBOX directory: {inbox}\n"
            f"OUTBOX directory: {outbox}\n"
            "Step 1 now: reply with exactly one line and no other text:\n"
            "AI_RUNTIME_EVENT_READY {session_identity}\n"
            'Step 2 later: when a message is exactly "EVENT <ref>", read INBOX/<ref>.json and '
            "write OUTBOX/<ref>.json containing exactly this object: "
            '{"reference_id": "<ref>", "session_id": "' + session_id + '", "intent_sha256": '
            '<the intent_sha256 value from the inbox file>, "event": <the packet.structured_event '
            "object from the inbox file>}. Then reply with exactly: AI_RUNTIME_EVENT_WRITTEN <ref>. "
            "Never print file contents and never modify the inbox."
        )
        gate: dict[str, Any] = {
            "declared_ready_pattern": declared,
            "relaxed_ready_pattern": relaxed,
            "bootstrap_prompt_sha256": digest(bootstrap),
        }
        gate["interactive_gate_clearing"] = self.clear_interactive_gates(
            supervisor,
            label="claude-feature",
            launch_command=self.claude_declaration.root_launch_command,
            cwd=self.repo,
            detector=self.claude_declaration.root_readiness,
        )
        if self.claude_transcript(root_uuid) is None:
            _seed, seed_evidence = self.claude_print(
                gate="G5",
                tag="root-seed",
                prompt=(
                    "AI-RUNTIME PROBE ROOT ORIENTATION v1\n"
                    + STABLE_PREFIX
                    + "\nReply with exactly this token and nothing else: ROOT_READY. "
                    "Do not use tools and do not read or write files."
                ),
                session_id=root_uuid,
            )
            gate["root_seeded_in_this_gate"] = True
            gate["root_seed"] = seed_evidence
        gate["root_transcript"] = file_evidence(self.claude_transcript(root_uuid))
        launch = (
            shutil.which("claude") or "claude",
            "--permission-mode",
            "acceptEdits",
            "--disable-slash-commands",
            "--model",
            CLAUDE_MODEL,
            "--add-dir",
            str(supervisor.state_dir),
            "--resume",
            root_uuid,
            "--fork-session",
            bootstrap,
        )
        gate["feature_launch_redacted"] = [self.redact(part, 256) for part in launch[:-1]] + [
            "<BOOTSTRAP_REDACTED>"
        ]
        spec = SessionSpec(
            session_id=session_id,
            adapter="claude",
            adapter_version=self.claude_version,
            role="reviewer",
            cwd=self.repo,
            launch_command=launch,
            readiness=ReadinessDetector(relaxed, pane_lines=80),
            trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
            transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
            feature_id="probe",
            fork=ForkCapability.NATIVE,
            session_kind=SessionKind.FEATURE,
            parent_root_id="claude-root",
            fork_mode="native",
            policy_revision="live-persistent-contract-probe",
            git_base=self.git_base,
            capability_revision=self.claude_declaration.declaration_revision,
            capability_sha256=self.claude_declaration.digest,
            read_only=True,
            termination=TerminationBehavior.GRACEFUL_THEN_KILL,
        )
        try:
            self.budget.spend("claude", "G5", "feature-bootstrap")
            observation = supervisor.start(spec, readiness_timeout=max(READINESS_TIMEOUT, 120))
            record = supervisor.read(session_id)
            assert record is not None
            pane = supervisor._capture(record, 80)
            identity = None
            match = re.search(r"AI_RUNTIME_EVENT_READY\s+([0-9a-f]{32})", pane)
            if match:
                identity = match.group(1)
                self.redact.add(identity, "<REDACTED_IDENTITY>")
            gate.update(
                {
                    "feature_session_ready": observation.ready,
                    "relaxed_detector_matched": True,
                    "declared_detector_would_match": bool(
                        identity
                        and re.search(
                            declared.replace("{session_identity}", re.escape(identity)),
                            pane,
                            re.MULTILINE,
                        )
                    ),
                    "identity_line_redacted": (
                        matched_line(pane, r"AI_RUNTIME_EVENT_READY", self.redact)
                    ),
                }
            )
        except SessionError as exc:
            gate.update(
                {
                    "feature_session_ready": False,
                    "relaxed_detector_matched": False,
                    "declared_detector_would_match": False,
                    "error_redacted": self.redact(str(exc), 512),
                    "passed": False,
                    **self.failure_markers(
                        supervisor, session_id, ReadinessDetector(relaxed, pane_lines=80)
                    ),
                }
            )
            self.record_iteration(
                "G5",
                "Claude feature session never printed the identity handshake line",
                "recorded as negative evidence; structured terminal events stay fail-closed",
            )
            supervisor._tmux(["kill-server"])
            self.results["G5"] = gate
            return

        structured_event = {
            "event_id": f"probe-{uuid.uuid4().hex[:16]}",
            "type": "probe.terminal_event",
            "payload": {"probe": "ack"},
        }
        intent = channel.persist_intent(
            session_id=session_id,
            event_reference="probe-reference-v1",
            packet={"structured_event": structured_event},
        )
        notice = channel.notification(intent.reference_id)
        gate.update(
            {
                "send_keys_payload": notice,
                "send_keys_is_fixed_form": bool(re.fullmatch(r"EVENT ref-[0-9a-f]{32}", notice)),
                "send_keys_carries_no_prompt_path_or_schema": not any(
                    marker in notice
                    for marker in (
                        str(self.fixture),
                        str(Path.home()),
                        str(supervisor.state_dir),
                        "schema",
                        "PROTOCOL",
                        self.nonce,
                    )
                ),
                "intent_sha256_recorded": True,
                "packet_sha256": intent.packet_sha256,
            }
        )
        record = supervisor.read(session_id)
        assert record is not None
        self.budget.spend("claude", "G5", "event-reference-delivery")
        supervisor._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "-l", notice], check=True)
        supervisor._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "Enter"], check=True)
        channel.mark_notified(intent)

        def validator(event: Mapping[str, Any]) -> None:
            if event.get("event_id") != structured_event["event_id"]:
                raise ValueError("event identity does not match the delivered packet")
            if event.get("type") != structured_event["type"]:
                raise ValueError("event type does not match the delivered packet")

        collected = None
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline and collected is None:
            time.sleep(3)
            try:
                collected = channel.collect(intent, validator=validator)
            except SessionError as exc:
                gate["collect_error_redacted"] = self.redact(str(exc), 256)
                break
        gate["structured_event_returned"] = collected is not None
        if collected is not None:
            gate["result_evidence"] = {
                key: value
                for key, value in collected.evidence.items()
                if key
                in {
                    "intent_sha256",
                    "packet_sha256",
                    "result_sha256",
                    "result_bytes",
                    "structured_terminal_channel",
                    "raw_output_retained",
                }
            }
            gate["identity_correlated"] = (
                collected.session_id == session_id
                and collected.event.get("event_id") == structured_event["event_id"]
            )
            channel.acknowledge(intent, accepted_event_id=structured_event["event_id"])
            gate["durable_ack_written"] = True
        else:
            gate["identity_correlated"] = False
            gate["durable_ack_written"] = False
            self.record_iteration(
                "G5",
                "no structured event reached the runtime outbox within the bounded window",
                "recorded as negative evidence; the channel stays fail-closed for this adapter",
            )
        supervisor.terminate(session_id, grace_seconds=3)
        gate["cleanup"] = channel.cleanup_session(session_id)
        supervisor._tmux(["kill-server"])
        gate["passed"] = bool(
            gate.get("structured_event_returned")
            and gate.get("identity_correlated")
            and gate.get("send_keys_is_fixed_form")
            and gate.get("declared_detector_would_match")
        )
        self.results["G5"] = gate

    # ----------------------------------------------------------------- teardown

    def cleanup_probe_sessions(self) -> None:
        removed_claude = 0
        if self.claude_project_dir.exists() and not self.claude_project_dir_existed:
            for path in sorted(self.claude_project_dir.rglob("*")):
                if path.is_file():
                    removed_claude += 1
            shutil.rmtree(self.claude_project_dir, ignore_errors=True)
        known = set(self.codex_session_ids.values())
        removed_codex = 0
        for path in self.codex_rollouts_since_start():
            if any(session in path.name for session in known):
                path.unlink(missing_ok=True)
                removed_codex += 1
        self.residue = {
            "claude_project_dir_created_by_probe": not self.claude_project_dir_existed,
            "claude_transcript_files_removed": removed_claude,
            "codex_rollout_files_removed": removed_codex,
            "codex_known_session_count": len(known),
            "retained_workspace_trust_entry": (
                "Claude records fixture-path workspace trust outside the fixture; the path is "
                "deleted with the fixture and no probe content remains."
            ),
        }


def build_report(probe: Probe, *, live: bool, revision: str, branch: str) -> dict[str, Any]:
    gates = {
        key: bool(value.get("passed"))
        for key, value in probe.results.items()
        if isinstance(value, dict) and "passed" in value
    }
    return {
        "format": "ai-runtime-evidence/v2",
        "format_version": 2,
        "subject": "live-persistent-adapter-contract",
        "run_id": probe.run_id,
        "captured_at": utc_now(),
        "tested_revision": revision,
        "branch": branch,
        "mode": "live" if live else "discovery-only",
        "models": {"claude": CLAUDE_MODEL, "codex": CODEX_MODEL, "codex_reasoning_effort": "low"},
        "limits": {
            "max_live_calls": probe.budget.maximum,
            "turn_timeout_seconds": TURN_TIMEOUT,
            "readiness_timeout_seconds": READINESS_TIMEOUT,
        },
        "live_calls": probe.budget.counts,
        "live_call_log": probe.budget.calls,
        "adapter_versions": {
            "claude": getattr(probe, "claude_version", None),
            "codex": getattr(probe, "codex_version", None),
        },
        "gates": probe.results,
        "gate_summary": gates,
        "iterations": probe.iterations,
        "fixture": {
            "layout": ["repo/", "runtime-state/", "worktrees/probe/"],
            "disposable": True,
            "clean_after_probe": probe.fixture_clean() if live else None,
            "git_base_sha256": digest(getattr(probe, "git_base", "")),
        },
        "session_residue": probe.residue,
        "privacy_contract": {
            "raw_prompt_retained": False,
            "raw_pane_capture_retained": False,
            "raw_stdout_retained": False,
            "raw_model_transcript_retained": False,
            # Stated as what is actually retained.  The earlier wording described
            # only the readiness line and understated the diagnostic allowlist,
            # which retains up to 16 redacted lines when a detector fails.
            "retained_pane_data": (
                "redacted detector-matching and allowlisted diagnostic lines only, "
                "<=200 chars each, <=16 lines per session"
            ),
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(artifact_dir: Path) -> str:
    lines = [
        f"{digest(path.read_bytes())}  {path.relative_to(artifact_dir)}"
        for path in sorted(
            item
            for item in artifact_dir.rglob("*")
            if item.is_file() and item.name != "manifest.sha256"
        )
    ]
    manifest = artifact_dir / "manifest.sha256"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return digest(manifest.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="run bounded authenticated model calls")
    mode.add_argument(
        "--discovery-only", action="store_true", help="exercise the harness without a model call"
    )
    parser.add_argument(
        "--gates",
        default="G1,G2,G3,G4,G5,G6,Q1",
        help="comma-separated gate selection (default: all)",
    )
    args = parser.parse_args()
    selected = {item.strip().upper() for item in args.gates.split(",") if item.strip()}

    run_id = (
        dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:6]}"
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    budget = Budget(MAX_LIVE_CALLS)
    probe = Probe(run_id=run_id, live=args.live, budget=budget)
    artifact_dir = POC_ROOT / "artifacts" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    failure: str | None = None

    with tempfile.TemporaryDirectory(prefix="airv-live-persistent-") as temporary:
        probe.build_fixture(Path(temporary))
        try:
            if args.live:
                if "G1" in selected:
                    probe.gate_1()
                if "G2" in selected:
                    probe.gate_2()
                if {"G3", "G4", "G6"} & selected:
                    probe.gate_3_4_6_claude()
                if "Q1" in selected:
                    probe.gate_q1_codex()
                if "G5" in selected:
                    probe.gate_5()
            else:
                probe.results["harness"] = {
                    "fixture_built": True,
                    "fixture_clean": probe.fixture_clean(),
                    "runtime_imports": True,
                    "passed": True,
                }
        except BudgetExceeded as exc:
            failure = str(exc)
            print(f"[stop] {exc}", file=sys.stderr)
        finally:
            if args.live:
                probe.cleanup_probe_sessions()

        report = build_report(probe, live=args.live, revision=revision, branch=branch)

    report["budget_exhausted"] = failure
    payload = json.dumps(report, sort_keys=True)
    report["privacy_checks"] = {
        "home_path_absent": str(Path.home()) not in payload,
        "repository_path_absent": str(REPO_ROOT) not in payload,
        "nonce_absent": probe.nonce not in payload,
        "fixture_email_absent": "probe@example.invalid" not in payload,
        "raw_stdout_field_absent": '"stdout"' not in payload and '"stderr"' not in payload,
        "raw_pane_field_absent": '"pane_capture"' not in payload,
    }
    required = {"G1", "G2", "G3", "G4", "G5", "G6", "Q1"} & selected
    achieved = {key for key, value in report["gate_summary"].items() if value}
    if args.discovery_only:
        report["decision"] = "DISCOVERY_ONLY"
    elif failure:
        report["decision"] = "BUDGET_STOPPED"
    elif not all(report["privacy_checks"].values()):
        report["decision"] = "BLOCKED_PRIVACY"
    elif achieved >= required:
        report["decision"] = "LIVE_CONTRACT_ESTABLISHED"
    elif achieved:
        report["decision"] = "PARTIAL_CONTRACT_ESTABLISHED"
    else:
        report["decision"] = "LIVE_CONTRACT_NOT_ESTABLISHED"

    write_json(artifact_dir / "live-contract-evidence.json", report)
    write_json(artifact_dir / "portable-git-evidence.json", [])
    write_json(
        artifact_dir / "revision-evidence.json",
        {
            "base_revision": revision,
            "tested_revision": revision,
            "branch": branch,
            "run_id": run_id,
            "decision": report["decision"],
            "live_calls": report["live_calls"],
        },
    )
    provenance = write_manifest(artifact_dir)
    print(f"Decision: {report['decision']}")
    print(f"Live calls: {report['live_calls']}")
    print(f"Evidence: {artifact_dir}")
    print(f"validation_provenance_sha256 (sha256 of manifest.sha256): {provenance}")
    return 0 if report["decision"] in {"LIVE_CONTRACT_ESTABLISHED", "DISCOVERY_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
