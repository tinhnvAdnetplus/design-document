"""Persistent roots, capability-bound feature forks, and terminal events.

This module deliberately does not parse a model TUI.  A declaration may start
and observe an interactive root, but feature delivery is enabled only when the
adapter owns a version-bound, validated structured terminal-event mapping.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import re
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .sessions import (
    ForkCapability,
    ReadinessDetector,
    SessionError,
    SessionKind,
    SessionObservation,
    SessionRecord,
    SessionRecoveryRequiredError,
    SessionSpec,
    SessionState,
    SessionSupervisor,
    SessionUnavailableError,
    TerminationBehavior,
    TransportMode,
    TrustPromptBehavior,
    _canonical,
    _safe_identifier,
    _sha_text,
    _utc_now,
)


class CapabilityUnavailableError(SessionUnavailableError):
    """A requested path is not present in the current adapter declaration."""


class ForkMode(enum.StrEnum):
    NATIVE = "native"
    SYNTHETIC = "synthetic"


class CapabilityValidation(enum.StrEnum):
    VALIDATED = "validated"
    FAIL_CLOSED = "fail_closed"


@dataclasses.dataclass(frozen=True, slots=True)
class PersistentAdapterDeclaration:
    """Adapter-owned declaration bound to one exact observed CLI version."""

    adapter: str
    adapter_version: str
    declaration_revision: str
    roles: frozenset[str]
    root_launch_command: tuple[str, ...]
    root_readiness: ReadinessDetector
    synthetic_launch_command: tuple[str, ...] | None
    native_fork_command: tuple[str, ...] | None
    resume_command: tuple[str, ...] | None
    persistent_root: CapabilityValidation
    native_fork: CapabilityValidation
    resume: CapabilityValidation
    structured_terminal_events: CapabilityValidation
    validation_provenance_sha256: str | None
    writes_workspace: bool
    merge_authority: bool = False
    temporary: bool = False
    trust_prompt: TrustPromptBehavior = TrustPromptBehavior.REJECT
    termination: TerminationBehavior = TerminationBehavior.GRACEFUL_THEN_KILL

    def __post_init__(self) -> None:
        _safe_identifier(self.adapter, "adapter", 48)
        _safe_identifier(self.declaration_revision, "declaration_revision", 128)
        if not self.adapter_version or not self.root_launch_command or not self.roles:
            raise ValueError("declaration requires version, root launch, and roles")
        if self.validation_provenance_sha256 is not None and not re.fullmatch(
            r"[0-9a-f]{64}", self.validation_provenance_sha256
        ):
            raise ValueError("validation provenance must be a SHA-256 digest")
        if self.native_fork == CapabilityValidation.VALIDATED and (
            self.native_fork_command is None or self.validation_provenance_sha256 is None
        ):
            raise ValueError("validated native fork requires command mapping and provenance")
        if self.persistent_root == CapabilityValidation.VALIDATED and (
            self.validation_provenance_sha256 is None
        ):
            raise ValueError("validated persistent root requires validation provenance")
        if self.resume == CapabilityValidation.VALIDATED and (
            self.resume_command is None or self.validation_provenance_sha256 is None
        ):
            raise ValueError("validated resume requires command mapping and provenance")
        if self.structured_terminal_events == CapabilityValidation.VALIDATED and (
            self.validation_provenance_sha256 is None
        ):
            raise ValueError("validated terminal events require validation provenance")
        if self.merge_authority and (self.adapter != "claude" or self.temporary):
            raise ValueError("only a non-temporary Claude declaration may claim merge authority")
        if self.merge_authority and self.validation_provenance_sha256 is None:
            raise ValueError("merge authority requires explicit validation provenance")
        if self.adapter == "antigravity" and (
            not self.temporary
            or self.merge_authority
            or self.native_fork != CapabilityValidation.FAIL_CLOSED
        ):
            raise ValueError("Antigravity must remain temporary, advisory, and synthetic")

    @property
    def digest(self) -> str:
        value = dataclasses.asdict(self)
        value["roles"] = sorted(self.roles)
        return _sha_text(_canonical(value))

    @property
    def supports_synthetic_fork(self) -> bool:
        return self.synthetic_launch_command is not None


class CapabilityRegistry:
    """Fresh in-memory registry; it is never rebuilt from pane or Event Store."""

    def __init__(self) -> None:
        self._declarations: dict[str, PersistentAdapterDeclaration] = {}

    def register(self, declaration: PersistentAdapterDeclaration) -> None:
        current = self._declarations.get(declaration.adapter)
        if current is not None and current != declaration:
            raise SessionRecoveryRequiredError(
                f"capability declaration changed for {declaration.adapter}; explicit revalidation required"
            )
        self._declarations[declaration.adapter] = declaration

    def require(self, adapter: str) -> PersistentAdapterDeclaration:
        try:
            return self._declarations[adapter]
        except KeyError as exc:
            raise CapabilityUnavailableError(f"no current capability declaration for {adapter}") from exc

    def versions(self) -> dict[str, str]:
        return {name: item.adapter_version for name, item in self._declarations.items()}


@dataclasses.dataclass(frozen=True, slots=True)
class TerminalEventIntent:
    reference_id: str
    session_id: str
    event_reference: str
    intent_sha256: str
    packet_sha256: str


@dataclasses.dataclass(frozen=True, slots=True)
class StructuredTerminalResult:
    reference_id: str
    session_id: str
    event: Mapping[str, Any]
    evidence: Mapping[str, Any]


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


class StructuredTerminalEventChannel:
    """Runtime-owned immutable inbox/outbox with durable result acknowledgements."""

    def __init__(self, state_dir: Path):
        self.root = Path(state_dir).resolve() / "terminal-events"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _session(self, session_id: str) -> Path:
        path = self.root / _safe_identifier(session_id, "session_id", 128)
        for name in ("inbox", "outbox", "acks", "diagnostics"):
            (path / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    @staticmethod
    def notification(reference_id: str) -> str:
        _safe_identifier(reference_id, "reference_id", 128)
        return f"EVENT {reference_id}"

    def persist_intent(
        self,
        *,
        session_id: str,
        event_reference: str,
        packet: Mapping[str, Any],
        reference_id: str | None = None,
    ) -> TerminalEventIntent:
        _safe_identifier(event_reference, "event_reference", 128)
        reference = reference_id or f"ref-{uuid.uuid4().hex}"
        _safe_identifier(reference, "reference_id", 128)
        session = self._session(session_id)
        target = session / "inbox" / f"{reference}.json"
        packet_json = _canonical(packet)
        if len(packet_json.encode("utf-8")) > 131_072:
            raise CapabilityUnavailableError("terminal event packet exceeds 128 KiB")
        packet_sha = _sha_text(packet_json)
        intent_payload = {
            "reference_id": reference,
            "session_id": session_id,
            "event_reference": event_reference,
            "packet": dict(packet),
            "packet_sha256": packet_sha,
            "created_at": _utc_now(),
            "status": "PERSISTED",
        }
        intent_sha = _sha_text(_canonical(intent_payload))
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            existing_sha = _sha_text(_canonical({k: v for k, v in existing.items() if k != "intent_sha256"}))
            if existing.get("intent_sha256") != existing_sha or existing_sha != intent_sha:
                raise SessionRecoveryRequiredError("terminal intent reference collision")
        else:
            _atomic_json(target, {**intent_payload, "intent_sha256": intent_sha})
        return TerminalEventIntent(reference, session_id, event_reference, intent_sha, packet_sha)

    def mark_notified(self, intent: TerminalEventIntent) -> None:
        session = self._session(intent.session_id)
        _atomic_json(
            session / f"{intent.reference_id}.delivery.json",
            {
                "reference_id": intent.reference_id,
                "intent_sha256": intent.intent_sha256,
                "notified_at": _utc_now(),
                "status": "NOTIFIED",
            },
        )

    def collect(
        self,
        intent: TerminalEventIntent,
        *,
        validator: Callable[[Mapping[str, Any]], None],
    ) -> StructuredTerminalResult | None:
        session = self._session(intent.session_id)
        ack = session / "acks" / f"{intent.reference_id}.json"
        if ack.exists():
            return None
        output = session / "outbox" / f"{intent.reference_id}.json"
        if not output.exists():
            return None
        if output.stat().st_size > 1_048_576:
            size = output.stat().st_size
            digest = hashlib.sha256()
            with output.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65_536), b""):
                    digest.update(chunk)
            output.unlink(missing_ok=True)
            _atomic_json(
                session / "diagnostics" / f"{intent.reference_id}.json",
                {
                    "reference_id_sha256": _sha_text(intent.reference_id),
                    "raw_sha256": digest.hexdigest(),
                    "raw_bytes": size,
                    "exit_status": "OVERSIZED",
                    "duration_ms": 0.0,
                    "observed_at": _utc_now(),
                    "diagnostic_redacted": "invalid_result oversized",
                },
            )
            raise SessionRecoveryRequiredError("oversized structured terminal result was discarded")
        raw = output.read_bytes()
        started = _utc_now()
        try:
            envelope = json.loads(raw)
            if not isinstance(envelope, Mapping):
                raise ValueError("result envelope is not an object")
            if (
                envelope.get("reference_id") != intent.reference_id
                or envelope.get("session_id") != intent.session_id
                or envelope.get("intent_sha256") != intent.intent_sha256
            ):
                raise ValueError("result identity does not match intent")
            event = envelope.get("event")
            if not isinstance(event, Mapping):
                raise ValueError("structured event is not an object")
            validator(event)
        except Exception as exc:
            output.unlink(missing_ok=True)
            _atomic_json(
                session / "diagnostics" / f"{intent.reference_id}.json",
                {
                    "reference_id_sha256": _sha_text(intent.reference_id),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "raw_bytes": len(raw),
                    "exit_status": "INVALID",
                    "duration_ms": 0.0,
                    "observed_at": started,
                    "diagnostic_redacted": f"invalid_result type={type(exc).__name__}"[:256],
                },
            )
            raise SessionRecoveryRequiredError("invalid structured terminal result was discarded") from exc
        evidence = {
            "reference_id": intent.reference_id,
            "intent_sha256": intent.intent_sha256,
            "packet_sha256": intent.packet_sha256,
            "result_sha256": hashlib.sha256(raw).hexdigest(),
            "result_bytes": len(raw),
            "structured_terminal_channel": "runtime_reference_v1",
            "raw_output_retained": False,
        }
        return StructuredTerminalResult(intent.reference_id, intent.session_id, dict(event), evidence)

    def acknowledge(self, intent: TerminalEventIntent, *, accepted_event_id: str) -> None:
        _safe_identifier(accepted_event_id, "accepted_event_id", 128)
        session = self._session(intent.session_id)
        ack = session / "acks" / f"{intent.reference_id}.json"
        payload = {
            "reference_id": intent.reference_id,
            "intent_sha256": intent.intent_sha256,
            "accepted_event_id": accepted_event_id,
            "accepted_event_id_sha256": _sha_text(accepted_event_id),
            "acknowledged_at": _utc_now(),
        }
        if ack.exists():
            existing = json.loads(ack.read_text(encoding="utf-8"))
            if existing.get("intent_sha256") != intent.intent_sha256 or existing.get(
                "accepted_event_id"
            ) != accepted_event_id:
                raise SessionRecoveryRequiredError("terminal result acknowledgement conflict")
        else:
            _atomic_json(ack, payload)
        (session / "inbox" / f"{intent.reference_id}.json").unlink(missing_ok=True)
        (session / "outbox" / f"{intent.reference_id}.json").unlink(missing_ok=True)
        (session / f"{intent.reference_id}.delivery.json").unlink(missing_ok=True)

    def pending_results(self, session_id: str) -> tuple[str, ...]:
        session = self._session(session_id)
        return tuple(path.stem for path in sorted((session / "outbox").glob("*.json")))

    def _read_intent(self, session_id: str, reference_id: str) -> TerminalEventIntent | None:
        path = self._session(session_id) / "inbox" / f"{reference_id}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("session_id") != session_id or value.get("reference_id") != reference_id:
            raise SessionRecoveryRequiredError("persisted terminal intent identity is invalid")
        unsigned = {key: item for key, item in value.items() if key != "intent_sha256"}
        if value.get("intent_sha256") != _sha_text(_canonical(unsigned)):
            raise SessionRecoveryRequiredError("persisted terminal intent integrity is invalid")
        return TerminalEventIntent(
            reference_id=reference_id,
            session_id=session_id,
            event_reference=str(value["event_reference"]),
            intent_sha256=str(value["intent_sha256"]),
            packet_sha256=str(value["packet_sha256"]),
        )

    def acknowledge_known_events(
        self, session_id: str, accepted_event_ids: frozenset[str]
    ) -> tuple[str, ...]:
        """Clear a response already proven durable by Event Store replay."""
        session = self._session(session_id)
        acknowledged: list[str] = []
        for output in sorted((session / "outbox").glob("*.json")):
            reference = output.stem
            intent = self._read_intent(session_id, reference)
            if intent is None:
                continue
            try:
                envelope = json.loads(output.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            event = envelope.get("event") if isinstance(envelope, Mapping) else None
            event_id = event.get("event_id") if isinstance(event, Mapping) else None
            if (
                event_id in accepted_event_ids
                and envelope.get("session_id") == session_id
                and envelope.get("intent_sha256") == intent.intent_sha256
            ):
                self.acknowledge(intent, accepted_event_id=event_id)
                acknowledged.append(reference)
        return tuple(acknowledged)

    def cleanup_session(self, session_id: str) -> Mapping[str, Any]:
        session = self._session(session_id)
        pending = len(list((session / "outbox").glob("*.json")))
        inbox = len(list((session / "inbox").glob("*.json")))
        if pending or inbox:
            return {"cleaned": False, "pending_results": pending, "pending_intents": inbox}
        return {"cleaned": True, "durable_ack_count": len(list((session / "acks").glob("*.json")))}


@dataclasses.dataclass(frozen=True, slots=True)
class FeatureSessionRequest:
    adapter: str
    feature_id: str
    role: str
    attempt: int
    cwd: Path
    git_base: str
    worktree_binding: Path | None = None
    reconstruction_provenance_sha256: str | None = None
    resume_reference_sha256: str | None = None

    def __post_init__(self) -> None:
        _safe_identifier(self.feature_id, "feature_id", 64)
        _safe_identifier(self.role, "role", 64)
        if self.attempt <= 0:
            raise ValueError("attempt must be positive")
        object.__setattr__(self, "cwd", Path(self.cwd).resolve())
        if not self.cwd.is_dir():
            raise ValueError("feature session cwd must exist")
        if not re.fullmatch(r"[0-9a-f]{40}", self.git_base):
            raise ValueError("git_base must be an exact 40-character Git object ID")
        if self.worktree_binding is not None:
            object.__setattr__(self, "worktree_binding", Path(self.worktree_binding).resolve())


@dataclasses.dataclass(frozen=True, slots=True)
class FactoryReconcileReport:
    roots: tuple[str, ...]
    features: tuple[str, ...]
    recovery_required: tuple[str, ...]
    completed_unacknowledged: tuple[str, ...]
    orphaned_parent: tuple[str, ...]


def _render(command: tuple[str, ...], values: Mapping[str, str]) -> tuple[str, ...]:
    rendered = []
    for item in command:
        for key, value in values.items():
            item = item.replace("{" + key + "}", value)
        rendered.append(item)
    return tuple(rendered)


class FeatureSessionFactory:
    """Unified root/fork/session lifecycle factory."""

    def __init__(
        self,
        supervisor: SessionSupervisor,
        *,
        repository: Path,
        policy_revision: str,
        capabilities: CapabilityRegistry,
        worktree_root: Path | None = None,
    ):
        self.supervisor = supervisor
        self.repository = Path(repository).resolve()
        self.policy_revision = policy_revision
        self.capabilities = capabilities
        self.worktree_root = Path(worktree_root).resolve() if worktree_root else None
        self.channel = StructuredTerminalEventChannel(supervisor.state_dir)
        self.root_registry = supervisor.state_dir / "active-roots.json"

    def _roots(self) -> dict[str, str]:
        if not self.root_registry.exists():
            return {}
        return dict(json.loads(self.root_registry.read_text(encoding="utf-8")))

    def _write_roots(self, roots: Mapping[str, str]) -> None:
        _atomic_json(self.root_registry, roots)

    def _root_spec(self, declaration: PersistentAdapterDeclaration, session_id: str) -> SessionSpec:
        launch = _render(
            declaration.root_launch_command,
            {
                "session_id": session_id,
                "state_dir": str(self.supervisor.state_dir),
                "cwd": str(self.repository),
            },
        )
        return SessionSpec(
            session_id=session_id,
            adapter=declaration.adapter,
            adapter_version=declaration.adapter_version,
            role="root",
            cwd=self.repository,
            launch_command=launch,
            readiness=declaration.root_readiness,
            trust_prompt=declaration.trust_prompt,
            termination=declaration.termination,
            transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
            session_kind=SessionKind.ROOT,
            policy_revision=self.policy_revision,
            capability_revision=declaration.declaration_revision,
            capability_sha256=declaration.digest,
            read_only=True,
        )

    def provision_root(self, adapter: str, *, readiness_timeout: float = 30) -> SessionObservation:
        declaration = self.capabilities.require(adapter)
        if declaration.persistent_root != CapabilityValidation.VALIDATED:
            raise CapabilityUnavailableError(
                f"{adapter} persistent root readiness/identity is fail-closed"
            )
        roots = self._roots()
        session_id = roots.get(adapter, f"{adapter}-root")
        observation = self.supervisor.start(
            self._root_spec(declaration, session_id), readiness_timeout=readiness_timeout
        )
        roots[adapter] = session_id
        self._write_roots(roots)
        return observation

    def root(self, adapter: str) -> SessionRecord:
        session_id = self._roots().get(adapter)
        record = self.supervisor.read(session_id) if session_id else None
        if record is None:
            raise CapabilityUnavailableError(f"{adapter} root is not provisioned")
        return record

    def observe(self, session_id: str) -> SessionObservation:
        record = self.supervisor.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        declaration = self.capabilities.require(record.adapter)
        if record.session_kind == str(SessionKind.ROOT):
            spec = self._root_spec(declaration, record.session_id)
        else:
            spec = self._feature_spec_from_record(declaration, record)
        return self.supervisor.observe(spec)

    readiness = observe

    def _feature_id(self, request: FeatureSessionRequest) -> str:
        return f"{request.adapter}-feature-{request.feature_id}-{request.role}-{request.attempt}"

    def _feature_values(self, request: FeatureSessionRequest, root: SessionRecord) -> dict[str, str]:
        return {
            "session_id": self._feature_id(request),
            "parent_session_id": root.session_id,
            "feature_id": request.feature_id,
            "role": request.role,
            "attempt": str(request.attempt),
            "cwd": str(request.cwd),
            "state_dir": str(self.supervisor.state_dir),
        }

    def _make_feature_spec(
        self,
        declaration: PersistentAdapterDeclaration,
        request: FeatureSessionRequest,
        root: SessionRecord,
        mode: ForkMode,
        command: tuple[str, ...],
    ) -> SessionSpec:
        session_id = self._feature_id(request)
        launch = _render(command, self._feature_values(request, root))
        worktree = str(request.worktree_binding) if request.worktree_binding else None
        return SessionSpec(
            session_id=session_id,
            adapter=declaration.adapter,
            adapter_version=declaration.adapter_version,
            role=request.role,
            cwd=request.cwd,
            launch_command=launch,
            readiness=ReadinessDetector(r"^AI_RUNTIME_EVENT_READY {session_identity}$"),
            trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
            termination=declaration.termination,
            transport_mode=TransportMode.TMUX_INTERACTIVE_V1,
            feature_id=request.feature_id,
            fork=ForkCapability.NATIVE if mode == ForkMode.NATIVE else ForkCapability.SYNTHETIC,
            session_kind=SessionKind.FEATURE,
            attempt=request.attempt,
            parent_root_id=root.session_id,
            fork_mode=str(mode),
            policy_revision=self.policy_revision,
            git_base=request.git_base,
            worktree_binding=worktree,
            capability_revision=declaration.declaration_revision,
            capability_sha256=declaration.digest,
            read_only=request.role != "implementer",
            resume_reference_sha256=request.resume_reference_sha256,
            reconstruction_sha256=request.reconstruction_provenance_sha256,
        )

    def _validate_feature_scope(
        self, declaration: PersistentAdapterDeclaration, request: FeatureSessionRequest
    ) -> SessionRecord:
        if request.role not in declaration.roles:
            raise CapabilityUnavailableError(f"{declaration.adapter} does not own role {request.role}")
        if request.role == "implementer":
            if declaration.adapter != "codex" or not declaration.writes_workspace:
                raise CapabilityUnavailableError("only Codex may own an implementer writer session")
            if request.worktree_binding is None or request.cwd != request.worktree_binding:
                raise SessionRecoveryRequiredError("Codex writer cwd must equal its generated worktree")
            if request.cwd == self.repository:
                raise SessionRecoveryRequiredError("Codex cannot write the integration worktree")
            if (
                self.worktree_root is None
                or request.cwd.parent != self.worktree_root
                or request.cwd.name != request.feature_id
            ):
                raise SessionRecoveryRequiredError(
                    "Codex writer must bind the runtime-generated feature worktree"
                )
        elif request.worktree_binding is not None:
            raise SessionRecoveryRequiredError("read-only feature roles cannot own a writer worktree")
        root = self.root(declaration.adapter)
        if root.state != SessionState.READY or not self.observe(root.session_id).ready:
            raise CapabilityUnavailableError("parent root is not ready")
        existing = self.supervisor.read(self._feature_id(request))
        if existing is not None:
            raise SessionRecoveryRequiredError("a feature-role attempt is never reusable")
        return root

    def create_from_root(
        self, request: FeatureSessionRequest, *, readiness_timeout: float = 30
    ) -> SessionObservation:
        declaration = self.capabilities.require(request.adapter)
        if declaration.structured_terminal_events != CapabilityValidation.VALIDATED:
            raise CapabilityUnavailableError(
                f"{request.adapter} structured persistent event channel is fail-closed"
            )
        if declaration.native_fork == CapabilityValidation.VALIDATED:
            return self.native_fork(request, readiness_timeout=readiness_timeout)
        if declaration.supports_synthetic_fork:
            return self.synthetic_fork(request, readiness_timeout=readiness_timeout)
        raise CapabilityUnavailableError(f"{request.adapter} has no eligible fork strategy")

    def native_fork(
        self, request: FeatureSessionRequest, *, readiness_timeout: float = 30
    ) -> SessionObservation:
        declaration = self.capabilities.require(request.adapter)
        if (
            declaration.native_fork != CapabilityValidation.VALIDATED
            or declaration.native_fork_command is None
            or declaration.structured_terminal_events != CapabilityValidation.VALIDATED
        ):
            raise CapabilityUnavailableError("native fork command/channel is not validated")
        root = self._validate_feature_scope(declaration, request)
        spec = self._make_feature_spec(
            declaration, request, root, ForkMode.NATIVE, declaration.native_fork_command
        )
        try:
            observation = self.supervisor.start(spec, readiness_timeout=readiness_timeout)
        except SessionError as exc:
            record = self.supervisor.read(spec.session_id)
            if record is not None and record.state != SessionState.RECOVERY_REQUIRED:
                self.supervisor._transition(
                    record,
                    SessionState.RECOVERY_REQUIRED,
                    diagnostic={"reason": "native_fork_readiness_or_identity_failed"},
                )
            raise SessionRecoveryRequiredError("native fork did not establish verified readiness") from exc
        return observation

    def synthetic_fork(
        self, request: FeatureSessionRequest, *, readiness_timeout: float = 30
    ) -> SessionObservation:
        declaration = self.capabilities.require(request.adapter)
        if declaration.synthetic_launch_command is None:
            raise CapabilityUnavailableError("synthetic fork is not declared")
        if declaration.structured_terminal_events != CapabilityValidation.VALIDATED:
            raise CapabilityUnavailableError("synthetic fork has no validated terminal-event channel")
        if request.reconstruction_provenance_sha256 is None:
            raise SessionRecoveryRequiredError("synthetic fork requires reconstruction provenance")
        root = self._validate_feature_scope(declaration, request)
        spec = self._make_feature_spec(
            declaration,
            request,
            root,
            ForkMode.SYNTHETIC,
            declaration.synthetic_launch_command,
        )
        return self.supervisor.start(spec, readiness_timeout=readiness_timeout)

    def _feature_spec_from_record(
        self, declaration: PersistentAdapterDeclaration, record: SessionRecord
    ) -> SessionSpec:
        command = (
            declaration.native_fork_command
            if record.fork_mode == str(ForkMode.NATIVE)
            else declaration.synthetic_launch_command
        )
        if command is None:
            raise CapabilityUnavailableError("recorded feature strategy is no longer declared")
        root = self.supervisor.read(record.parent_root_id or "")
        if root is None:
            raise SessionRecoveryRequiredError("feature parent root record is missing")
        request = FeatureSessionRequest(
            adapter=record.adapter,
            feature_id=record.feature_id or "missing",
            role=record.role,
            attempt=record.attempt,
            cwd=Path(record.cwd),
            git_base=record.git_base or "unknown",
            worktree_binding=Path(record.worktree_binding) if record.worktree_binding else None,
            reconstruction_provenance_sha256=record.reconstruction_sha256,
            resume_reference_sha256=record.resume_reference_sha256,
        )
        return self._make_feature_spec(
            declaration, request, root, ForkMode(record.fork_mode), command
        )

    def deliver_event_reference(
        self,
        session_id: str,
        *,
        event_reference: str,
        packet: Mapping[str, Any],
        reference_id: str | None = None,
    ) -> TerminalEventIntent:
        record = self.supervisor.read(session_id)
        if record is None or record.session_kind != str(SessionKind.FEATURE):
            raise SessionUnavailableError("event delivery requires a registered feature session")
        declaration = self.capabilities.require(record.adapter)
        if declaration.structured_terminal_events != CapabilityValidation.VALIDATED:
            raise CapabilityUnavailableError("structured terminal event channel is fail-closed")
        observation = self.observe(session_id)
        if not observation.ready or observation.state != SessionState.READY:
            raise SessionUnavailableError("feature session is not ready for delivery")
        intent = self.channel.persist_intent(
            session_id=session_id,
            event_reference=event_reference,
            packet=packet,
            reference_id=reference_id,
        )
        notice = self.channel.notification(intent.reference_id)
        try:
            self.supervisor._tmux(
                ["send-keys", "-t", f"{record.tmux_name}:0.0", "-l", notice], check=True
            )
            self.supervisor._tmux(
                ["send-keys", "-t", f"{record.tmux_name}:0.0", "Enter"], check=True
            )
        except SessionError:
            self.supervisor._transition(
                record,
                SessionState.RECOVERY_REQUIRED,
                diagnostic={"reason": "terminal_notification_ambiguous"},
            )
            raise
        self.channel.mark_notified(intent)
        return intent

    def collect_structured_event(
        self,
        intent: TerminalEventIntent,
        *,
        validator: Callable[[Mapping[str, Any]], None],
    ) -> StructuredTerminalResult | None:
        return self.channel.collect(intent, validator=validator)

    def acknowledge_structured_event(
        self, intent: TerminalEventIntent, *, accepted_event_id: str
    ) -> None:
        self.channel.acknowledge(intent, accepted_event_id=accepted_event_id)

    def accept_structured_event(
        self,
        intent: TerminalEventIntent,
        *,
        writer: Any,
        validator: Callable[[Mapping[str, Any]], None],
    ) -> StructuredTerminalResult | None:
        """Validate, durably append, then acknowledge without a resend window."""
        result = self.collect_structured_event(intent, validator=validator)
        if result is None:
            return None
        event_id = result.event.get("event_id")
        if not isinstance(event_id, str):
            raise SessionRecoveryRequiredError("structured terminal event has no event_id")
        writer.append(result.event, timeout=10)
        self.acknowledge_structured_event(intent, accepted_event_id=event_id)
        return result

    def resume_or_reconstruct(
        self,
        session_id: str,
        *,
        worktree_clean: bool,
        readiness_timeout: float = 30,
    ) -> SessionObservation:
        record = self.supervisor.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        declaration = self.capabilities.require(record.adapter)
        spec = (
            self._root_spec(declaration, session_id)
            if record.session_kind == str(SessionKind.ROOT)
            else self._feature_spec_from_record(declaration, record)
        )
        resume_command = None
        if (
            record.resume_reference_sha256
            and declaration.resume == CapabilityValidation.VALIDATED
            and declaration.resume_command is not None
        ):
            resume_command = _render(
                declaration.resume_command,
                {
                    "cwd": record.cwd,
                    "state_dir": str(self.supervisor.state_dir),
                    "session_id": record.session_id,
                },
            )
        if (
            resume_command is None
            and record.session_kind == str(SessionKind.FEATURE)
            and declaration.synthetic_launch_command is not None
        ):
            spec = dataclasses.replace(
                spec,
                launch_command=_render(
                    declaration.synthetic_launch_command,
                    {
                        "session_id": record.session_id,
                        "cwd": record.cwd,
                        "state_dir": str(self.supervisor.state_dir),
                        "feature_id": record.feature_id or "feature",
                        "role": record.role,
                        "attempt": str(record.attempt),
                        "parent_session_id": record.parent_root_id or "root",
                    },
                ),
                fork=ForkCapability.SYNTHETIC,
                fork_mode=str(ForkMode.SYNTHETIC),
                resume_reference_sha256=None,
            )
        try:
            return self.supervisor.resume_or_reconstruct(
                spec,
                worktree_clean=worktree_clean,
                resume_command=resume_command,
                readiness_timeout=readiness_timeout,
            )
        except (SessionUnavailableError, SessionRecoveryRequiredError):
            if resume_command is None or not worktree_clean:
                raise
            if record.session_kind == str(SessionKind.FEATURE) and declaration.synthetic_launch_command:
                failed = self.supervisor.read(record.session_id) or record
                if self.supervisor._live(failed):
                    self.supervisor._tmux(["kill-session", "-t", failed.tmux_name], check=True)
                synthetic = dataclasses.replace(
                    spec,
                    launch_command=_render(
                        declaration.synthetic_launch_command,
                        {
                            "session_id": record.session_id,
                            "cwd": record.cwd,
                            "state_dir": str(self.supervisor.state_dir),
                            "feature_id": record.feature_id or "feature",
                            "role": record.role,
                            "attempt": str(record.attempt),
                            "parent_session_id": record.parent_root_id or "root",
                        },
                    ),
                    fork=ForkCapability.SYNTHETIC,
                    fork_mode=str(ForkMode.SYNTHETIC),
                    resume_reference_sha256=None,
                )
                return self.supervisor.resume_or_reconstruct(
                    synthetic,
                    worktree_clean=True,
                    resume_command=None,
                    readiness_timeout=readiness_timeout,
                )
            raise

    def terminate(self, session_id: str, *, grace_seconds: float = 2) -> SessionRecord:
        record = self.supervisor.read(session_id)
        if record is None:
            raise SessionUnavailableError("session is not registered")
        if record.session_kind == str(SessionKind.ROOT):
            raise SessionError("root termination requires controlled replacement or shutdown")
        cleanup = self.channel.cleanup_session(session_id)
        if not cleanup.get("cleaned"):
            raise SessionRecoveryRequiredError("feature has unacknowledged terminal event evidence")
        return self.supervisor.terminate(session_id, grace_seconds=grace_seconds)

    def replace_root(
        self, adapter: str, *, reason: str, readiness_timeout: float = 30
    ) -> SessionObservation:
        if not reason.strip():
            raise ValueError("root replacement requires a reason")
        declaration = self.capabilities.require(adapter)
        old = self.root(adapter)
        self.supervisor.drain(old.session_id)
        self.supervisor.terminate(old.session_id)
        roots = self._roots()
        generation = 2
        while self.supervisor.read(f"{adapter}-root-r{generation}") is not None:
            generation += 1
        replacement_id = f"{adapter}-root-r{generation}"
        observation = self.supervisor.start(
            self._root_spec(declaration, replacement_id), readiness_timeout=readiness_timeout
        )
        self.supervisor.mark_replaced(old.session_id, replacement_id)
        roots[adapter] = replacement_id
        self._write_roots(roots)
        return observation

    def reconcile(
        self, *, acknowledged_event_ids: frozenset[str] = frozenset()
    ) -> FactoryReconcileReport:
        base = self.supervisor.reconcile(adapter_versions=self.capabilities.versions())
        roots: list[str] = []
        features: list[str] = []
        recovery = list(base.recovery_required)
        unacked: list[str] = []
        orphaned: list[str] = []
        active_roots = self._roots()
        for record in self.supervisor.records():
            if record.state == SessionState.TERMINATED:
                continue
            try:
                declaration = self.capabilities.require(record.adapter)
            except CapabilityUnavailableError:
                recovery.append(record.session_id)
                continue
            if (
                record.policy_revision != self.policy_revision
                or record.capability_revision != declaration.declaration_revision
                or record.capability_sha256 != declaration.digest
            ):
                if record.state != SessionState.RECOVERY_REQUIRED:
                    self.supervisor._transition(
                        record,
                        SessionState.RECOVERY_REQUIRED,
                        diagnostic={"reason": "policy_or_capability_drift_on_reconcile"},
                    )
                recovery.append(record.session_id)
                continue
            if record.session_kind == str(SessionKind.ROOT):
                if active_roots.get(record.adapter) == record.session_id:
                    roots.append(record.session_id)
            elif record.session_kind == str(SessionKind.FEATURE):
                features.append(record.session_id)
                parent = self.supervisor.read(record.parent_root_id or "")
                if parent is None or parent.state == SessionState.TERMINATED:
                    orphaned.append(record.session_id)
                if acknowledged_event_ids:
                    self.channel.acknowledge_known_events(
                        record.session_id, acknowledged_event_ids
                    )
                if self.channel.pending_results(record.session_id):
                    unacked.append(record.session_id)
        return FactoryReconcileReport(
            tuple(sorted(set(roots))),
            tuple(sorted(set(features))),
            tuple(sorted(set(recovery))),
            tuple(sorted(set(unacked))),
            tuple(sorted(set(orphaned))),
        )


def fixture_worker_command() -> tuple[str, ...]:
    """Deterministic structured-channel command used by contract tests."""
    worker = Path(__file__).resolve().parent / "_terminal_event_worker.py"
    return (
        sys.executable,
        str(worker),
        "--state-dir",
        "{state_dir}",
        "--session-id",
        "{session_id}",
        "--identity",
        "{session_identity}",
    )
