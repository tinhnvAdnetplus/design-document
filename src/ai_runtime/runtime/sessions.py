"""Durable tmux session supervision without transcript retention.

The supervisor owns terminal/process lifecycle only.  Git, workflow state, and
authority remain in their existing gateways.  Pane captures are used as
ephemeral observations and are never written to the session registry.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class SessionError(RuntimeError):
    """A terminal operation failed or its outcome is ambiguous."""


class SessionUnavailableError(SessionError):
    """The declared transport capability/readiness is unavailable."""


class SessionRecoveryRequiredError(SessionError):
    """Automatic continuation would risk duplicating or losing work."""


class SessionState(enum.StrEnum):
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    UNAVAILABLE = "UNAVAILABLE"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    DRAINING = "DRAINING"


class SessionKind(enum.StrEnum):
    LEGACY = "legacy"
    ROOT = "root"
    FEATURE = "feature"


class TrustPromptBehavior(enum.StrEnum):
    REJECT = "reject"
    ACCEPT_DISPOSABLE_ONLY = "accept_disposable_only"
    NOT_APPLICABLE = "not_applicable"


class StructuredOutputChannel(enum.StrEnum):
    JSON_STDOUT = "json_stdout"
    JSONL_STDOUT = "jsonl_stdout"
    RUNTIME_SPOOL = "runtime_spool"


class TerminationBehavior(enum.StrEnum):
    GRACEFUL_THEN_KILL = "graceful_then_kill"
    KILL_SESSION = "kill_session"


class ForkCapability(enum.StrEnum):
    NATIVE = "native"
    SYNTHETIC = "synthetic"
    NONE = "none"


class TransportMode(enum.StrEnum):
    TMUX_SUPERVISED_NONINTERACTIVE_V1 = "tmux_supervised_noninteractive_v1"
    TMUX_INTERACTIVE_V1 = "tmux_interactive_v1"


@dataclasses.dataclass(frozen=True, slots=True)
class ReadinessDetector:
    ready_pattern: str
    trust_pattern: str | None = None
    pane_lines: int = 80

    def __post_init__(self) -> None:
        re.compile(self.ready_pattern)
        if self.trust_pattern:
            re.compile(self.trust_pattern)
        if not 1 <= self.pane_lines <= 200:
            raise ValueError("pane_lines must be between 1 and 200")


@dataclasses.dataclass(frozen=True, slots=True)
class AdapterSessionContract:
    """Version-bound lifecycle declaration owned by an adapter."""

    launch_command: tuple[str, ...]
    readiness: ReadinessDetector
    trust_prompt: TrustPromptBehavior
    resume: bool
    fork: ForkCapability
    structured_output: StructuredOutputChannel
    termination: TerminationBehavior
    transport_mode: TransportMode = TransportMode.TMUX_SUPERVISED_NONINTERACTIVE_V1

    def __post_init__(self) -> None:
        if not self.launch_command or any(not isinstance(part, str) or not part for part in self.launch_command):
            raise ValueError("launch_command must contain non-empty arguments")


@dataclasses.dataclass(frozen=True, slots=True)
class SessionSpec:
    session_id: str
    adapter: str
    adapter_version: str
    role: str
    cwd: Path
    launch_command: tuple[str, ...]
    readiness: ReadinessDetector
    trust_prompt: TrustPromptBehavior = TrustPromptBehavior.REJECT
    termination: TerminationBehavior = TerminationBehavior.GRACEFUL_THEN_KILL
    transport_mode: TransportMode = TransportMode.TMUX_SUPERVISED_NONINTERACTIVE_V1
    disposable: bool = False
    feature_id: str | None = None
    resume: bool = False
    fork: ForkCapability = ForkCapability.NONE
    session_kind: SessionKind = SessionKind.LEGACY
    attempt: int = 1
    parent_root_id: str | None = None
    fork_mode: str | None = None
    policy_revision: str = "minimal-runtime-v1"
    git_base: str | None = None
    worktree_binding: str | None = None
    capability_revision: str = "legacy-session-contract"
    capability_sha256: str | None = None
    read_only: bool = False
    resume_reference_sha256: str | None = None
    reconstruction_sha256: str | None = None

    def __post_init__(self) -> None:
        _safe_identifier(self.session_id, "session_id", 128)
        _safe_identifier(self.adapter, "adapter", 48)
        _safe_identifier(self.role, "role", 64)
        if self.feature_id is not None:
            _safe_identifier(self.feature_id, "feature_id", 64)
        object.__setattr__(self, "cwd", Path(self.cwd).resolve())
        if not self.cwd.is_dir():
            raise ValueError(f"session cwd does not exist: {self.cwd}")
        if not self.launch_command:
            raise ValueError("launch_command cannot be empty")
        if self.attempt <= 0:
            raise ValueError("attempt must be positive")
        if self.parent_root_id is not None:
            _safe_identifier(self.parent_root_id, "parent_root_id", 128)
        if self.session_kind == SessionKind.ROOT:
            if self.feature_id is not None or self.parent_root_id is not None:
                raise ValueError("root sessions cannot have feature or parent-root identity")
            if not self.read_only or self.worktree_binding is not None:
                raise ValueError("root sessions must be read-only and cannot bind a worktree")
        if self.session_kind == SessionKind.FEATURE:
            if self.feature_id is None or self.parent_root_id is None or not self.fork_mode:
                raise ValueError("feature sessions require feature, parent root, and fork mode")
            if self.role == "implement" and self.worktree_binding is None:
                raise ValueError("implementer feature sessions require a worktree binding")
        for name, digest in (
            ("capability_sha256", self.capability_sha256),
            ("resume_reference_sha256", self.resume_reference_sha256),
            ("reconstruction_sha256", self.reconstruction_sha256),
        ):
            if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"{name} must be a SHA-256 digest")


@dataclasses.dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    tmux_name: str
    socket_name: str
    adapter: str
    adapter_version: str
    role: str
    feature_id: str | None
    cwd: str
    state: SessionState
    state_revision: int
    transport_mode: str
    launch_sha256: str
    identity_sha256: str
    created_at: str
    updated_at: str
    recovery_kind: str | None = None
    diagnostic: Mapping[str, Any] | None = None
    session_kind: str = "legacy"
    attempt: int = 1
    parent_root_id: str | None = None
    fork_mode: str | None = None
    policy_revision: str = "minimal-runtime-v1"
    git_base: str | None = None
    worktree_binding: str | None = None
    capability_revision: str = "legacy-session-contract"
    capability_sha256: str | None = None
    repository_identity_sha256: str | None = None
    read_only: bool = False
    resume_reference_sha256: str | None = None
    reconstruction_sha256: str | None = None
    cleanup_evidence: Mapping[str, Any] | None = None
    replaced_by: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class SessionObservation:
    session_id: str
    state: SessionState
    live: bool
    ready: bool
    pane_bytes: int
    pane_sha256: str
    duration_ms: float
    diagnostic: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class TurnRequest:
    turn_id: str
    command: tuple[str, ...]
    cwd: Path
    timeout_seconds: float
    prompt_sha256: str
    task: str

    def __post_init__(self) -> None:
        _safe_identifier(self.turn_id, "turn_id", 128)
        object.__setattr__(self, "cwd", Path(self.cwd).resolve())
        if not self.cwd.is_dir() or not self.command:
            raise ValueError("turn requires an existing cwd and command")
        if not 0 < self.timeout_seconds <= 300:
            raise ValueError("turn timeout must be between 0 and 300 seconds")
        if not re.fullmatch(r"[0-9a-f]{64}", self.prompt_sha256):
            raise ValueError("prompt_sha256 must be a SHA-256 digest")


@dataclasses.dataclass(frozen=True, slots=True)
class TurnObservation:
    session_id: str
    turn_id: str
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    evidence: Mapping[str, Any]


@dataclasses.dataclass(frozen=True, slots=True)
class ReconcileReport:
    live: tuple[str, ...]
    unavailable: tuple[str, ...]
    recovery_required: tuple[str, ...]
    acknowledged: tuple[str, ...]


_TRANSITIONS: dict[SessionState, frozenset[SessionState]] = {
    SessionState.STARTING: frozenset({SessionState.READY, SessionState.UNAVAILABLE, SessionState.RECOVERY_REQUIRED, SessionState.TERMINATING}),
    SessionState.READY: frozenset({SessionState.BUSY, SessionState.UNAVAILABLE, SessionState.RECOVERY_REQUIRED, SessionState.DRAINING, SessionState.TERMINATING}),
    SessionState.BUSY: frozenset({SessionState.READY, SessionState.UNAVAILABLE, SessionState.RECOVERY_REQUIRED, SessionState.DRAINING, SessionState.TERMINATING}),
    SessionState.UNAVAILABLE: frozenset({SessionState.STARTING, SessionState.RECOVERY_REQUIRED, SessionState.TERMINATING, SessionState.TERMINATED}),
    SessionState.DRAINING: frozenset({SessionState.TERMINATING, SessionState.RECOVERY_REQUIRED}),
    SessionState.TERMINATING: frozenset({SessionState.TERMINATED, SessionState.RECOVERY_REQUIRED}),
    SessionState.TERMINATED: frozenset(),
    SessionState.RECOVERY_REQUIRED: frozenset({SessionState.STARTING, SessionState.BUSY, SessionState.READY, SessionState.TERMINATING, SessionState.TERMINATED}),
}


def _safe_identifier(value: str, field: str, maximum: int) -> str:
    if not re.fullmatch(rf"[A-Za-z0-9][A-Za-z0-9._-]{{0,{maximum - 1}}}", value):
        raise ValueError(f"{field} must use 1-{maximum} generated-safe characters")
    return value


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _redact(value: str, cwd: Path | None = None) -> str:
    replacements = {str(Path.home()): "$HOME"}
    if cwd:
        replacements[str(cwd)] = "$WORKTREE"
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(source, target)
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", value)
    value = re.sub(r"(?i)(api[_-]?key|token|authorization|bearer)(\s*[=:]\s*)\S+", r"\1\2<REDACTED>", value)
    return value[:2_048]


def repository_identity_sha256(cwd: Path) -> str:
    """Return a stable local repository identity without persisting its path."""
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    identity = result.stdout.strip() if result.returncode == 0 else str(cwd.resolve())
    return _sha_text(str(Path(identity).resolve()))


class SessionSupervisor:
    """Own a dedicated tmux socket and durable lifecycle registry."""

    def __init__(self, state_dir: Path, *, socket_name: str | None = None, tmux_binary: str = "tmux"):
        self.state_dir = Path(state_dir).resolve()
        self.registry_dir = self.state_dir / "sessions"
        self.spool_dir = self.state_dir / "session-spool"
        self.registry_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.spool_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.tmux_path = shutil.which(tmux_binary)
        if self.tmux_path is None:
            raise SessionUnavailableError(f"tmux executable is unavailable: {tmux_binary}")
        derived = f"air-{os.getuid()}-{_sha_text(str(self.state_dir))[:12]}"
        self.socket_name = _safe_identifier(socket_name or derived, "socket_name", 64)

    def _tmux(self, arguments: Sequence[str], *, timeout: float = 10, check: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [self.tmux_path, "-L", self.socket_name, *arguments],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if check and result.returncode != 0:
            raise SessionError(f"tmux {' '.join(arguments[:2])} failed: {_redact(result.stderr or result.stdout)}")
        return result

    def _path(self, session_id: str) -> Path:
        return self.registry_dir / f"{_safe_identifier(session_id, 'session_id', 128)}.json"

    def _turn_dir(self, session_id: str) -> Path:
        path = self.spool_dir / _safe_identifier(session_id, "session_id", 128)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def read(self, session_id: str) -> SessionRecord | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        value["state"] = SessionState(value["state"])
        for field in dataclasses.fields(SessionRecord):
            if field.name not in value and field.default is not dataclasses.MISSING:
                value[field.name] = field.default
        return SessionRecord(**value)

    def records(self) -> list[SessionRecord]:
        return [record for path in sorted(self.registry_dir.glob("*.json")) if (record := self.read(path.stem)) is not None]

    def _write(self, record: SessionRecord) -> SessionRecord:
        target = self._path(record.session_id)
        temporary = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
        payload = dataclasses.asdict(record)
        payload["state"] = str(record.state)
        temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, target)
        return record

    def _transition(self, record: SessionRecord, state: SessionState, *, diagnostic: Mapping[str, Any] | None = None, recovery_kind: str | None = None) -> SessionRecord:
        if state != record.state and state not in _TRANSITIONS[record.state]:
            raise SessionError(f"invalid session transition {record.state} -> {state}")
        return self._write(dataclasses.replace(
            record,
            state=state,
            state_revision=record.state_revision + (state != record.state),
            updated_at=_utc_now(),
            diagnostic=diagnostic,
            recovery_kind=recovery_kind if recovery_kind is not None else record.recovery_kind,
        ))

    @staticmethod
    def _name(spec: SessionSpec) -> str:
        semantic = "-".join(part for part in (spec.adapter, spec.role, spec.feature_id) if part)
        semantic = re.sub(r"[^A-Za-z0-9_-]", "-", semantic)[:48].strip("-") or "session"
        return f"air-{semantic}-{_sha_text(spec.session_id)[:12]}"

    def start(self, spec: SessionSpec, *, readiness_timeout: float = 30) -> SessionObservation:
        existing = self.read(spec.session_id)
        launch_sha = _sha_text(_canonical(list(spec.launch_command)))
        repository_sha = repository_identity_sha256(spec.cwd)
        if existing is not None:
            binding = (
                existing.adapter == spec.adapter
                and existing.adapter_version == spec.adapter_version
                and existing.launch_sha256 == launch_sha
                and existing.role == spec.role
                and existing.feature_id == spec.feature_id
                and existing.cwd == str(spec.cwd)
                and existing.policy_revision == spec.policy_revision
                and existing.capability_revision == spec.capability_revision
                and existing.capability_sha256 == spec.capability_sha256
                and existing.repository_identity_sha256 == repository_sha
                and existing.parent_root_id == spec.parent_root_id
                and existing.fork_mode == spec.fork_mode
                and existing.worktree_binding == spec.worktree_binding
            )
            if not binding:
                self._transition(existing, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "session_binding_drift"})
                raise SessionRecoveryRequiredError("stale adapter version, repository, policy, capability, or launch binding")
            observation = self.observe(spec)
            existing = self.read(spec.session_id) or existing
            if observation.ready:
                return observation
            if self._live(existing):
                raise SessionRecoveryRequiredError(
                    "existing tmux identity is live but not safely reusable"
                )
            if existing.state not in {SessionState.UNAVAILABLE, SessionState.RECOVERY_REQUIRED}:
                raise SessionUnavailableError(f"existing session is not reusable: {observation.state}")
        identity = uuid.uuid4().hex
        now = _utc_now()
        record = SessionRecord(
            session_id=spec.session_id,
            tmux_name=self._name(spec),
            socket_name=self.socket_name,
            adapter=spec.adapter,
            adapter_version=spec.adapter_version,
            role=spec.role,
            feature_id=spec.feature_id,
            cwd=str(spec.cwd),
            state=SessionState.STARTING,
            state_revision=(existing.state_revision + 1 if existing else 1),
            transport_mode=str(spec.transport_mode),
            launch_sha256=launch_sha,
            identity_sha256=_sha_text(identity),
            created_at=existing.created_at if existing else now,
            updated_at=now,
            recovery_kind=existing.recovery_kind if existing else None,
            session_kind=str(spec.session_kind),
            attempt=spec.attempt,
            parent_root_id=spec.parent_root_id,
            fork_mode=spec.fork_mode,
            policy_revision=spec.policy_revision,
            git_base=spec.git_base,
            worktree_binding=spec.worktree_binding,
            capability_revision=spec.capability_revision,
            capability_sha256=spec.capability_sha256,
            repository_identity_sha256=repository_sha,
            read_only=spec.read_only,
            resume_reference_sha256=spec.resume_reference_sha256,
            reconstruction_sha256=spec.reconstruction_sha256,
        )
        self._write(record)
        command = tuple(part.replace("{session_identity}", identity) for part in spec.launch_command)
        result = self._tmux(
            ["new-session", "-d", "-s", record.tmux_name, "-c", str(spec.cwd), shlex.join(command)],
            check=False,
        )
        if result.returncode != 0:
            self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "launch_failed", "exit_code": result.returncode})
            raise SessionUnavailableError(f"tmux session launch failed: {_redact(result.stderr, spec.cwd)}")
        self._tmux(["set-option", "-t", record.tmux_name, "remain-on-exit", "on"], check=True)
        self._tmux(
            [
                "set-option",
                "-t",
                record.tmux_name,
                "@ai_runtime_identity_sha256",
                record.identity_sha256,
            ],
            check=True,
        )
        return self._wait_ready(spec, identity, readiness_timeout)

    def _capture(self, record: SessionRecord, lines: int) -> str:
        result = self._tmux(["capture-pane", "-p", "-S", f"-{lines}", "-t", f"{record.tmux_name}:0.0"])
        return result.stdout if result.returncode == 0 else ""

    def _live(self, record: SessionRecord) -> bool:
        return self._tmux(["has-session", "-t", record.tmux_name]).returncode == 0

    def _identity_matches(self, record: SessionRecord) -> bool:
        if not self._live(record):
            return False
        result = self._tmux(
            [
                "show-options",
                "-v",
                "-t",
                record.tmux_name,
                "@ai_runtime_identity_sha256",
            ]
        )
        return result.returncode == 0 and result.stdout.strip() == record.identity_sha256

    def _cwd_matches(self, record: SessionRecord) -> bool:
        if not self._live(record):
            return False
        result = self._tmux(
            ["display-message", "-p", "-t", f"{record.tmux_name}:0.0", "#{pane_current_path}"]
        )
        if result.returncode != 0:
            return False
        try:
            return Path(result.stdout.strip()).resolve() == Path(record.cwd).resolve()
        except OSError:
            return False

    def _wait_ready(self, spec: SessionSpec, identity: str, timeout: float) -> SessionObservation:
        deadline = time.monotonic() + min(max(timeout, 0.1), 120)
        trust_seen = False
        while time.monotonic() < deadline:
            record = self.read(spec.session_id)
            assert record is not None
            if not self._live(record):
                self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "process_exited_before_readiness"})
                raise SessionUnavailableError("session exited before readiness")
            if not self._identity_matches(record):
                self._transition(
                    record,
                    SessionState.RECOVERY_REQUIRED,
                    diagnostic={"reason": "stale_session_identity"},
                )
                raise SessionRecoveryRequiredError(
                    "tmux session identity does not match the registry"
                )
            pane = self._capture(record, spec.readiness.pane_lines)
            if spec.readiness.trust_pattern and re.search(spec.readiness.trust_pattern, pane, re.MULTILINE):
                trust_seen = True
                if spec.trust_prompt == TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY and spec.disposable:
                    self._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "Enter"], check=True)
                else:
                    self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "trust_prompt_blocked"})
                    raise SessionRecoveryRequiredError("trust prompt requires an authorized disposable fixture")
            expected = spec.readiness.ready_pattern.replace("{session_identity}", re.escape(identity))
            if re.search(expected, pane, re.MULTILINE):
                self._transition(record, SessionState.READY, diagnostic={"trust_prompt_seen": trust_seen})
                return self.observe(spec)
            time.sleep(0.05)
        record = self.read(spec.session_id)
        assert record is not None
        pane = self._capture(record, spec.readiness.pane_lines)
        self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "readiness_timeout", "pane_sha256": _sha_text(pane), "pane_bytes": len(pane.encode())})
        raise SessionRecoveryRequiredError("session readiness timed out")

    def observe(self, spec: SessionSpec) -> SessionObservation:
        started = time.perf_counter_ns()
        record = self.read(spec.session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        live = self._live(record)
        pane = self._capture(record, spec.readiness.pane_lines) if live else ""
        identity_matches = live and self._identity_matches(record)
        cwd_matches = live and self._cwd_matches(record)
        if live and (not identity_matches or not cwd_matches) and record.state not in {
            SessionState.TERMINATED,
            SessionState.TERMINATING,
            SessionState.RECOVERY_REQUIRED,
        }:
            record = self._transition(
                record,
                SessionState.RECOVERY_REQUIRED,
                diagnostic={"reason": "stale_session_identity" if not identity_matches else "session_cwd_mismatch"},
            )
        ready = identity_matches and cwd_matches and record.state in {
            SessionState.READY,
            SessionState.BUSY,
        }
        diagnostic = None
        if not live and record.state not in {SessionState.TERMINATED, SessionState.TERMINATING, SessionState.RECOVERY_REQUIRED}:
            record = self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "tmux_session_absent"})
            diagnostic = "tmux_session_absent"
        return SessionObservation(
            session_id=spec.session_id,
            state=record.state,
            live=live,
            ready=ready,
            pane_bytes=len(pane.encode("utf-8")),
            pane_sha256=_sha_text(pane),
            duration_ms=round((time.perf_counter_ns() - started) / 1_000_000, 3),
            diagnostic=diagnostic,
        )

    def send_turn(self, spec: SessionSpec, request: TurnRequest) -> TurnObservation:
        record = self.read(spec.session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        turn_dir = self._turn_dir(spec.session_id)
        request_path = turn_dir / f"{request.turn_id}.request.json"
        response_path = turn_dir / f"{request.turn_id}.response.json"
        if response_path.exists():
            self._sanitize_legacy_response(request_path, response_path)
            if record.state == SessionState.RECOVERY_REQUIRED:
                record = self._transition(record, SessionState.BUSY, recovery_kind="completed_turn_recovered")
            return self._read_turn(record, request, request_path, response_path, reconciled=True)
        if request.cwd != spec.cwd:
            self._transition(
                record,
                SessionState.RECOVERY_REQUIRED,
                diagnostic={"reason": "turn_cwd_outside_session_scope"},
            )
            raise SessionRecoveryRequiredError("turn cwd differs from the registered session scope")
        if (
            record.state != SessionState.READY
            or not self._live(record)
            or not self._identity_matches(record)
        ):
            if record.state not in {SessionState.UNAVAILABLE, SessionState.RECOVERY_REQUIRED}:
                self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "turn_without_ready_transport"})
            raise SessionUnavailableError("persistent transport is not ready; no fallback was attempted")
        payload = {
            "turn_id": request.turn_id,
            "command": list(request.command),
            "cwd": str(request.cwd),
            "timeout_seconds": request.timeout_seconds,
            "prompt_sha256": request.prompt_sha256,
            "task": request.task,
        }
        request_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        request_path.chmod(0o600)
        record = self._transition(record, SessionState.BUSY)
        fixed_notice = f"TURN {request.turn_id}"
        self._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "-l", fixed_notice], check=True)
        self._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "Enter"], check=True)
        deadline = time.monotonic() + request.timeout_seconds + 10
        while time.monotonic() < deadline:
            if response_path.exists():
                return self._read_turn(record, request, request_path, response_path, reconciled=False)
            if not self._live(record):
                request_path.unlink(missing_ok=True)
                self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "agent_died_during_turn"})
                raise SessionUnavailableError("agent session died during a turn")
            time.sleep(0.05)
        request_path.unlink(missing_ok=True)
        self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "turn_deadline_ambiguous"})
        raise SessionRecoveryRequiredError("turn exceeded its bounded deadline; outcome is ambiguous")

    def _read_turn(self, record: SessionRecord, request: TurnRequest, request_path: Path, response_path: Path, *, reconciled: bool) -> TurnObservation:
        value = json.loads(response_path.read_text(encoding="utf-8"))
        if value.get("turn_id") != request.turn_id or value.get("prompt_sha256") != request.prompt_sha256:
            self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "stale_turn_identity"})
            raise SessionRecoveryRequiredError("completed response has stale turn identity")
        request_path.unlink(missing_ok=True)
        # v1 responses are read for crash compatibility.  New workers persist
        # only a validated structured candidate and non-content output metrics.
        if "structured_result" in value:
            candidate = value.get("structured_result")
            stdout = json.dumps(candidate, sort_keys=True) if isinstance(candidate, Mapping) else ""
            stderr = ""
        else:
            stdout = str(value.get("stdout", ""))
            stderr = str(value.get("stderr", ""))
        evidence = {
            "transport_mode": record.transport_mode,
            "session_id": record.session_id,
            "turn_id": request.turn_id,
            "duration_ms": value.get("duration_ms"),
            "exit_code": value.get("exit_code"),
            "timed_out": bool(value.get("timed_out")),
            "stdout_sha256": value.get("stdout_sha256", _sha_text(stdout)),
            "stderr_sha256": value.get("stderr_sha256", _sha_text(stderr)),
            "stdout_bytes": value.get("stdout_bytes", len(stdout.encode("utf-8"))),
            "stderr_bytes": value.get("stderr_bytes", len(stderr.encode("utf-8"))),
            "prompt_sha256": request.prompt_sha256,
            "reconciled_completed_turn": reconciled,
            "diagnostic_redacted": str(value.get("diagnostic_redacted", ""))[:256],
        }
        return TurnObservation(record.session_id, request.turn_id, stdout, stderr, value.get("exit_code"), bool(value.get("timed_out")), evidence)

    @staticmethod
    def _sanitize_legacy_response(request_path: Path, response_path: Path) -> None:
        """Remove pre-increment raw output while preserving resumable structure/metrics."""
        value = json.loads(response_path.read_text(encoding="utf-8"))
        if "stdout" not in value and "stderr" not in value:
            return
        stdout = str(value.pop("stdout", ""))
        stderr = str(value.pop("stderr", ""))
        task = ""
        if request_path.exists():
            request = json.loads(request_path.read_text(encoding="utf-8"))
            task = str(request.get("task", ""))
        from ._session_worker import _structured

        value.update(
            {
                "structured_result": _structured(stdout, task),
                "stdout_sha256": _sha_text(stdout),
                "stderr_sha256": _sha_text(stderr),
                "stdout_bytes": len(stdout.encode("utf-8")),
                "stderr_bytes": len(stderr.encode("utf-8")),
                "diagnostic_redacted": (
                    f"stderr_present bytes={len(stderr.encode('utf-8'))}" if stderr else ""
                ),
            }
        )
        temporary = response_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, response_path)

    def acknowledge_turn(self, session_id: str, turn_id: str) -> None:
        record = self.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        turn_dir = self._turn_dir(session_id)
        (turn_dir / f"{turn_id}.request.json").unlink(missing_ok=True)
        (turn_dir / f"{turn_id}.response.json").unlink(missing_ok=True)
        if record.state in {SessionState.BUSY, SessionState.RECOVERY_REQUIRED}:
            self._transition(record, SessionState.READY, diagnostic={"turn_acknowledged_sha256": _sha_text(turn_id)})

    def reject_turn(
        self,
        session_id: str,
        turn_id: str,
        *,
        reason: str,
        evidence: Mapping[str, Any],
    ) -> None:
        """Forget invalid raw output while retaining bounded non-content evidence."""
        record = self.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        turn_dir = self._turn_dir(session_id)
        (turn_dir / f"{turn_id}.request.json").unlink(missing_ok=True)
        (turn_dir / f"{turn_id}.response.json").unlink(missing_ok=True)
        allowed = {
            key: value
            for key, value in evidence.items()
            if key
            in {
                "stdout_sha256",
                "stderr_sha256",
                "stdout_bytes",
                "stderr_bytes",
                "duration_ms",
                "exit_code",
                "timed_out",
                "diagnostic_redacted",
            }
        }
        self._transition(
            record,
            SessionState.RECOVERY_REQUIRED,
            diagnostic={"reason": reason[:128], **allowed},
        )

    def resume_or_reconstruct(self, spec: SessionSpec, *, worktree_clean: bool, resume_command: tuple[str, ...] | None = None, readiness_timeout: float = 30) -> SessionObservation:
        record = self.read(spec.session_id)
        if record is None:
            return self.start(spec, readiness_timeout=readiness_timeout)
        observation = self.observe(spec)
        record = self.read(spec.session_id) or record
        if observation.live and observation.ready:
            return observation
        if not worktree_clean:
            self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "dirty_worktree_preserved"})
            raise SessionRecoveryRequiredError("dirty worktree preserved; recovery requires maintainer action")
        if record.adapter_version != spec.adapter_version:
            self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "adapter_version_drift"})
            raise SessionRecoveryRequiredError("adapter version drift blocks recovery")
        kind = "resume" if spec.resume and resume_command else "synthetic_reconstruction"
        recovered_spec = dataclasses.replace(spec, launch_command=resume_command or spec.launch_command)
        recovered_launch_sha = _sha_text(
            _canonical(list(recovered_spec.launch_command))
        )
        if (
            recovered_launch_sha != record.launch_sha256
            or recovered_spec.fork_mode != record.fork_mode
            or recovered_spec.resume_reference_sha256 != record.resume_reference_sha256
            or recovered_spec.reconstruction_sha256 != record.reconstruction_sha256
        ):
            record = self._write(
                dataclasses.replace(
                    record,
                    launch_sha256=recovered_launch_sha,
                    fork_mode=recovered_spec.fork_mode,
                    resume_reference_sha256=recovered_spec.resume_reference_sha256,
                    reconstruction_sha256=recovered_spec.reconstruction_sha256,
                    updated_at=_utc_now(),
                    recovery_kind=kind,
                )
            )
        self._transition(record, SessionState.STARTING, recovery_kind=kind)
        return self.start(recovered_spec, readiness_timeout=readiness_timeout)

    def terminate(self, session_id: str, *, grace_seconds: float = 2) -> SessionRecord:
        record = self.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        if record.state == SessionState.TERMINATED:
            return record
        if record.state != SessionState.TERMINATING:
            record = self._transition(record, SessionState.TERMINATING)
        if self._live(record):
            self._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "-l", "TERMINATE"])
            self._tmux(["send-keys", "-t", f"{record.tmux_name}:0.0", "Enter"])
            deadline = time.monotonic() + max(0, grace_seconds)
            while time.monotonic() < deadline and self._live(record):
                time.sleep(0.05)
            if self._live(record):
                self._tmux(["kill-session", "-t", record.tmux_name])
        for path in self._turn_dir(session_id).glob("*"):
            path.unlink(missing_ok=True)
        absent = not self._live(record)
        record = self._transition(record, SessionState.TERMINATED, diagnostic={"terminal_absent": absent})
        return self._write(dataclasses.replace(
            record,
            cleanup_evidence={"terminal_absent": absent, "completed_at": _utc_now()},
        ))

    def drain(self, session_id: str) -> SessionRecord:
        """Fence new work before controlled root replacement."""
        record = self.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        if record.session_kind != str(SessionKind.ROOT):
            raise SessionError("only root sessions use controlled drain")
        if record.state == SessionState.DRAINING:
            return record
        if record.state not in {SessionState.READY, SessionState.BUSY}:
            raise SessionRecoveryRequiredError("root is not eligible for controlled drain")
        return self._transition(record, SessionState.DRAINING, diagnostic={"reason": "controlled_root_replacement"})

    def mark_replaced(self, session_id: str, replacement_session_id: str) -> SessionRecord:
        record = self.read(session_id)
        if record is None or record.state != SessionState.TERMINATED:
            raise SessionRecoveryRequiredError("root must be terminated before replacement is recorded")
        _safe_identifier(replacement_session_id, "replacement_session_id", 128)
        return self._write(dataclasses.replace(record, replaced_by=replacement_session_id, updated_at=_utc_now()))

    def reconcile(
        self,
        *,
        acknowledged_turn_ids: frozenset[str] = frozenset(),
        adapter_versions: Mapping[str, str] | None = None,
    ) -> ReconcileReport:
        live: list[str] = []
        unavailable: list[str] = []
        recovery: list[str] = []
        acknowledged: list[str] = []
        for record in self.records():
            if record.state == SessionState.TERMINATED:
                continue
            expected_version = (adapter_versions or {}).get(record.adapter)
            if expected_version is not None and expected_version != record.adapter_version:
                if record.state != SessionState.RECOVERY_REQUIRED:
                    record = self._transition(
                        record,
                        SessionState.RECOVERY_REQUIRED,
                        diagnostic={"reason": "adapter_version_drift_on_reconcile"},
                    )
                recovery.append(record.session_id)
                continue
            responses = list(self._turn_dir(record.session_id).glob("*.response.json"))
            for response in responses:
                turn_id = response.name.removesuffix(".response.json")
                self._sanitize_legacy_response(
                    self._turn_dir(record.session_id) / f"{turn_id}.request.json",
                    response,
                )
                if turn_id in acknowledged_turn_ids:
                    self.acknowledge_turn(record.session_id, turn_id)
                    acknowledged.append(turn_id)
            record = self.read(record.session_id) or record
            responses = list(self._turn_dir(record.session_id).glob("*.response.json"))
            if responses:
                if record.state != SessionState.RECOVERY_REQUIRED:
                    record = self._transition(record, SessionState.RECOVERY_REQUIRED, diagnostic={"reason": "completed_turn_without_event_ack", "count": len(responses)})
                recovery.append(record.session_id)
            elif self._live(record):
                pending_requests = list(
                    self._turn_dir(record.session_id).glob("*.request.json")
                )
                identity_matches = self._identity_matches(record)
                if (
                    record.state == SessionState.RECOVERY_REQUIRED
                    or not identity_matches
                    or pending_requests
                ):
                    if record.state != SessionState.RECOVERY_REQUIRED:
                        record = self._transition(
                            record,
                            SessionState.RECOVERY_REQUIRED,
                            diagnostic={
                                "reason": (
                                    "stale_session_identity"
                                    if not identity_matches
                                    else "inflight_turn_ambiguous_on_reconcile"
                                ),
                                "pending_request_count": len(pending_requests),
                            },
                        )
                    recovery.append(record.session_id)
                else:
                    live.append(record.session_id)
            else:
                if record.state == SessionState.TERMINATING:
                    self._transition(
                        record,
                        SessionState.TERMINATED,
                        diagnostic={"terminal_absent": True, "reconciled": True},
                    )
                    acknowledged.append(record.session_id)
                    continue
                if record.state not in {
                    SessionState.UNAVAILABLE,
                    SessionState.RECOVERY_REQUIRED,
                }:
                    record = self._transition(record, SessionState.UNAVAILABLE, diagnostic={"reason": "tmux_session_absent_on_reconcile"})
                unavailable.append(record.session_id)
        return ReconcileReport(tuple(live), tuple(unavailable), tuple(recovery), tuple(acknowledged))
