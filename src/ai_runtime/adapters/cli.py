"""Version-bound subprocess adapters for Claude, Antigravity, and Codex."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import AdapterCapability, AdapterError, AdapterResult, StructuredTask
from ..runtime.feature_sessions import (
    CapabilityValidation,
    PersistentAdapterDeclaration,
)
from ..runtime.sessions import (
    AdapterSessionContract,
    ForkCapability,
    ReadinessDetector,
    SessionRecoveryRequiredError,
    SessionSpec,
    SessionSupervisor,
    SessionUnavailableError,
    StructuredOutputChannel,
    TerminationBehavior,
    TransportMode,
    TrustPromptBehavior,
    TurnRequest,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact(value: str, cwd: Path) -> str:
    result = value.replace(str(Path.home()), "$HOME").replace(str(cwd), "$WORKTREE")
    result = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", result)
    result = re.sub(
        r"(?i)(api[_-]?key|token|authorization|bearer)(\s*[=:]\s*)\S+",
        r"\1\2<REDACTED>",
        result,
    )
    return result[:2_048]


def _walk(value: Any):
    yield value
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, str):
        candidate = value.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1)
        if candidate.startswith(("{", "[")):
            try:
                yield from _walk(json.loads(candidate))
            except json.JSONDecodeError:
                return


def _extract_structured(
    output: str, task: StructuredTask, required: set[str]
) -> Mapping[str, Any] | None:
    roots: list[Any] = []
    stripped = output.strip()
    if stripped:
        try:
            roots.append(json.loads(stripped))
        except json.JSONDecodeError:
            pass
    for line in output.splitlines():
        try:
            roots.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for root in roots:
        for node in _walk(root):
            if isinstance(node, Mapping) and required.issubset(node):
                candidate = dict(node)
                try:
                    _validate_result(task, candidate)
                except AdapterError:
                    continue
                return candidate
    return None


def _validate_result(task: StructuredTask, value: Mapping[str, Any]) -> None:
    required = _SubprocessAdapter.required_keys[task]
    if set(value) != required:
        raise AdapterError(
            f"structured {task} result fields differ from schema: {sorted(value)}"
        )
    if not isinstance(value.get("summary"), str):
        raise AdapterError(f"structured {task} summary must be a string")
    list_fields = {
        StructuredTask.PLAN: ("steps", "acceptance_criteria", "risks"),
        StructuredTask.IMPLEMENT: ("tests",),
        StructuredTask.REVIEW: ("findings",),
    }[task]
    for field in list_fields:
        candidate = value.get(field)
        if not isinstance(candidate, list) or not all(isinstance(item, str) for item in candidate):
            raise AdapterError(f"structured {task} {field} must be an array of strings")
    if task == StructuredTask.IMPLEMENT and not re.fullmatch(
        r"[0-9a-f]{40}", str(value.get("commit", ""))
    ):
        raise AdapterError("structured implementation commit must be a 40-character Git object ID")
    if task == StructuredTask.REVIEW and value.get("verdict") not in {
        "approve",
        "changes_requested",
    }:
        raise AdapterError("structured review verdict is invalid")


def _shape_diagnostic(output: str) -> str:
    try:
        root = json.loads(output.strip())
    except json.JSONDecodeError:
        roots = []
        for line in output.splitlines():
            try:
                roots.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        root = roots[-1] if roots else None
    if not isinstance(root, Mapping):
        return f"root_type={type(root).__name__}"
    structured = root.get("structured_output")
    structured_shape = (
        sorted(structured) if isinstance(structured, Mapping) else type(structured).__name__
    )
    response = root.get("response")
    response_shape: object = type(response).__name__
    if isinstance(response, str):
        try:
            decoded_response = json.loads(response)
        except json.JSONDecodeError:
            response_shape = f"text:{len(response)}"
        else:
            response_shape = (
                {key: type(value).__name__ for key, value in decoded_response.items()}
                if isinstance(decoded_response, Mapping)
                else type(decoded_response).__name__
            )
    return (
        f"root_keys={sorted(root)} status={root.get('status')!r} "
        f"structured_shape={structured_shape} response_shape={response_shape}"
    )


class _SubprocessAdapter:
    required_keys: dict[StructuredTask, set[str]] = {
        StructuredTask.PLAN: {"summary", "steps", "acceptance_criteria", "risks"},
        StructuredTask.IMPLEMENT: {"summary", "tests", "commit"},
        StructuredTask.REVIEW: {"verdict", "summary", "findings"},
    }

    def __init__(self, *, binary: str, model: str | None = None):
        self.binary = binary
        self.model = model
        self.supervisor: SessionSupervisor | None = None
        path = shutil.which(binary)
        if path is None:
            raise AdapterError(f"adapter executable is unavailable: {binary}")
        self.path = path
        version = subprocess.run(
            [path, "--version"], text=True, capture_output=True, timeout=10, check=False
        )
        if version.returncode != 0:
            raise AdapterError(f"cannot discover {binary} version")
        self.version = (version.stdout + version.stderr).strip().splitlines()[0]

    def bind_supervisor(self, supervisor: SessionSupervisor) -> None:
        """Bind the required runtime transport before the first invocation."""
        if self.supervisor is not None and self.supervisor is not supervisor:
            raise AdapterError("adapter is already bound to a different session supervisor")
        self.supervisor = supervisor

    @property
    def session_contract(self) -> AdapterSessionContract:
        return self._session_contract

    @property
    def persistent_declaration(self) -> PersistentAdapterDeclaration:
        return self._persistent_declaration

    def _command(
        self,
        task: StructuredTask,
        *,
        prompt: str,
        cwd: Path,
        schema_path: Path,
        schema_json: str,
        timeout_seconds: float,
    ) -> list[str]:
        raise NotImplementedError

    def invoke(
        self,
        task: StructuredTask,
        *,
        prompt: str,
        cwd: Path,
        schema: Mapping[str, Any],
        timeout_seconds: float,
        feature_id: str | None = None,
    ) -> AdapterResult:
        if task not in self.capability.roles:
            raise AdapterError(f"{self.capability.name} does not support task {task}")
        if self.supervisor is None:
            raise AdapterError(
                f"{self.capability.name} has no SessionSupervisor; direct subprocess fallback is disabled"
            )
        timeout = min(max(float(timeout_seconds), 5.0), 300.0)
        with tempfile.TemporaryDirectory(prefix="ai-runtime-schema-") as temporary:
            schema_path = Path(temporary) / f"{task}.schema.json"
            schema_json = json.dumps(schema, sort_keys=True, separators=(",", ":"))
            schema_path.write_text(schema_json + "\n", encoding="utf-8")
            command = self._command(
                task,
                prompt=prompt,
                cwd=cwd,
                schema_path=schema_path,
                schema_json=schema_json,
                timeout_seconds=timeout,
            )
            try:
                session_id = self._session_id(task, cwd, feature_id)
                spool = self.supervisor.spool_dir / session_id
                worker_path = Path(__file__).resolve().parents[1] / "runtime" / "_session_worker.py"
                launch = (
                    sys.executable,
                    str(worker_path),
                    "--spool",
                    str(spool),
                    "--identity",
                    "{session_identity}",
                )
                detector = ReadinessDetector(
                    r"^AI_RUNTIME_READY {session_identity}$",
                    pane_lines=40,
                )
                spec = SessionSpec(
                    session_id=session_id,
                    adapter=self.capability.name,
                    adapter_version=self.capability.version,
                    role=str(task),
                    cwd=cwd,
                    launch_command=launch,
                    readiness=detector,
                    trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
                    termination=self.session_contract.termination,
                    transport_mode=TransportMode.TMUX_SUPERVISED_NONINTERACTIVE_V1,
                    feature_id=feature_id,
                    resume=self.session_contract.resume,
                    fork=self.session_contract.fork,
                )
                self.supervisor.start(spec, readiness_timeout=min(timeout, 30))
                prompt_sha = _digest(prompt)
                turn_id = "turn-" + _digest(
                    "\0".join(
                        (
                            self.capability.name,
                            self.capability.version,
                            str(task),
                            str(cwd.resolve()),
                            prompt_sha,
                        )
                    )
                )[:48]
                observation = self.supervisor.send_turn(
                    spec,
                    TurnRequest(
                        turn_id=turn_id,
                        command=tuple(command),
                        cwd=cwd,
                        timeout_seconds=timeout,
                        prompt_sha256=prompt_sha,
                        task=str(task),
                    ),
                )
            except (SessionUnavailableError, SessionRecoveryRequiredError) as exc:
                raise AdapterError(
                    f"{self.capability.name} persistent transport failed closed: {exc}"
                ) from exc
        if observation.timed_out:
            self.supervisor.reject_turn(
                observation.session_id,
                observation.turn_id,
                reason="adapter_timeout",
                evidence=observation.evidence,
            )
            raise AdapterError(f"{self.capability.name} {task} timed out after {timeout:.0f}s")
        if observation.exit_code != 0:
            detail = _redact(observation.stderr or observation.stdout, cwd)
            self.supervisor.reject_turn(
                observation.session_id,
                observation.turn_id,
                reason="adapter_nonzero_exit",
                evidence=observation.evidence,
            )
            raise AdapterError(
                f"{self.capability.name} {task} exited {observation.exit_code}: {detail}"
            )
        value = _extract_structured(observation.stdout, task, self.required_keys[task])
        if value is None:
            self.supervisor.reject_turn(
                observation.session_id,
                observation.turn_id,
                reason="invalid_structured_result",
                evidence=observation.evidence,
            )
            raise AdapterError(
                f"{self.capability.name} returned no valid structured {task} result; "
                f"{_shape_diagnostic(observation.stdout)}"
            )
        try:
            _validate_result(task, value)
        except AdapterError:
            self.supervisor.reject_turn(
                observation.session_id,
                observation.turn_id,
                reason="structured_result_contract_violation",
                evidence=observation.evidence,
            )
            raise
        evidence = {
            "adapter": self.capability.name,
            "adapter_version": self.capability.version,
            "task": str(task),
            **dict(observation.evidence),
        }
        return AdapterResult(value=value, evidence=evidence)

    def acknowledge(self, result: AdapterResult) -> None:
        if self.supervisor is None:
            raise AdapterError("cannot acknowledge without a SessionSupervisor")
        session_id = result.evidence.get("session_id")
        turn_id = result.evidence.get("turn_id")
        if not isinstance(session_id, str) or not isinstance(turn_id, str):
            raise AdapterError("adapter result lacks supervised turn identity")
        self.supervisor.acknowledge_turn(session_id, turn_id)

    def _session_id(
        self,
        task: StructuredTask,
        cwd: Path,
        feature_id: str | None,
    ) -> str:
        scope = _digest(str(cwd.resolve()))[:16]
        feature = feature_id or "root"
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", feature):
            raise AdapterError("feature_id is not safe for session identity")
        return f"{self.capability.name}-{task}-{feature}-{scope}"


class AntigravityAdapter(_SubprocessAdapter):
    """Temporary Claude-role substitute; deliberately has no merge authority."""

    def __init__(self, *, model: str = "gemini-3.6-flash-low", binary: str = "agy"):
        super().__init__(binary=binary, model=model)
        self._capability = AdapterCapability(
            name="antigravity",
            version=self.version,
            roles=frozenset({StructuredTask.PLAN, StructuredTask.REVIEW}),
            structured_output=True,
            resume=True,
            native_fork=False,
            writes_workspace=False,
            merge_authority=False,
            temporary=True,
        )
        self._session_contract = AdapterSessionContract(
            launch_command=(
                self.path,
                "--sandbox",
                "--mode",
                "plan",
                "--disable-slash-commands",
                "--log-file",
                "/dev/null",
                "--model",
                str(self.model),
            ),
            readiness=ReadinessDetector(
                r"Plan mode:",
                trust_pattern=r"Do you trust the contents",
            ),
            trust_prompt=TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY,
            resume=True,
            fork=ForkCapability.SYNTHETIC,
            structured_output=StructuredOutputChannel.JSON_STDOUT,
            termination=TerminationBehavior.GRACEFUL_THEN_KILL,
        )
        self._persistent_declaration = PersistentAdapterDeclaration(
            adapter="antigravity",
            adapter_version=self.version,
            declaration_revision=f"antigravity-persistent-v1-{_digest(self.version)[:12]}",
            roles=frozenset({"planner", "reviewer"}),
            root_launch_command=self._session_contract.launch_command,
            root_readiness=self._session_contract.readiness,
            synthetic_launch_command=self._session_contract.launch_command,
            native_fork_command=None,
            resume_command=None,
            persistent_root=CapabilityValidation.FAIL_CLOSED,
            native_fork=CapabilityValidation.FAIL_CLOSED,
            resume=CapabilityValidation.FAIL_CLOSED,
            structured_terminal_events=CapabilityValidation.FAIL_CLOSED,
            validation_provenance_sha256=None,
            writes_workspace=False,
            merge_authority=False,
            temporary=True,
            trust_prompt=self._session_contract.trust_prompt,
            termination=self._session_contract.termination,
        )

    @property
    def capability(self) -> AdapterCapability:
        return self._capability

    def _command(self, task, *, prompt, cwd, schema_path, schema_json, timeout_seconds):
        return [
            self.path,
            "--sandbox",
            "--mode",
            "plan",
            "--disable-slash-commands",
            "--log-file",
            "/dev/null",
            "--model",
            str(self.model),
            "--output-format",
            "json",
            "--json-schema",
            str(schema_path),
            "--print-timeout",
            f"{int(timeout_seconds)}s",
            "--print",
            prompt,
        ]


class ClaudeCLIAdapter(_SubprocessAdapter):
    """Production planner/reviewer and the only authority-eligible adapter."""

    def __init__(
        self,
        *,
        model: str | None = None,
        binary: str = "claude",
        merge_authority: bool = False,
        authority_validation_sha256: str | None = None,
    ):
        super().__init__(binary=binary, model=model)
        if merge_authority and not re.fullmatch(r"[0-9a-f]{64}", authority_validation_sha256 or ""):
            raise AdapterError("Claude merge authority requires explicit live validation provenance")
        self._capability = AdapterCapability(
            name="claude",
            version=self.version,
            roles=frozenset({StructuredTask.PLAN, StructuredTask.REVIEW}),
            structured_output=True,
            resume=True,
            native_fork=False,
            writes_workspace=False,
            merge_authority=merge_authority,
            temporary=False,
        )
        interactive = [self.path, "--permission-mode", "plan", "--disable-slash-commands"]
        if self.model:
            interactive.extend(["--model", self.model])
        self._session_contract = AdapterSessionContract(
            launch_command=tuple(interactive),
            readiness=ReadinessDetector(
                r"(?:^|\n).*?[❯>]\s*$",
                trust_pattern=r"Do you trust the contents",
            ),
            trust_prompt=TrustPromptBehavior.REJECT,
            resume=True,
            fork=ForkCapability.SYNTHETIC,
            structured_output=StructuredOutputChannel.JSON_STDOUT,
            termination=TerminationBehavior.GRACEFUL_THEN_KILL,
        )
        self._persistent_declaration = PersistentAdapterDeclaration(
            adapter="claude",
            adapter_version=self.version,
            declaration_revision=f"claude-persistent-v1-{_digest(self.version)[:12]}",
            roles=frozenset({"planner", "reviewer"}),
            root_launch_command=self._session_contract.launch_command,
            root_readiness=self._session_contract.readiness,
            synthetic_launch_command=self._session_contract.launch_command,
            native_fork_command=None,
            resume_command=None,
            persistent_root=CapabilityValidation.FAIL_CLOSED,
            native_fork=CapabilityValidation.FAIL_CLOSED,
            resume=CapabilityValidation.FAIL_CLOSED,
            structured_terminal_events=CapabilityValidation.FAIL_CLOSED,
            validation_provenance_sha256=authority_validation_sha256,
            writes_workspace=False,
            merge_authority=merge_authority,
            temporary=False,
            trust_prompt=self._session_contract.trust_prompt,
            termination=self._session_contract.termination,
        )

    @property
    def capability(self) -> AdapterCapability:
        return self._capability

    def _command(self, task, *, prompt, cwd, schema_path, schema_json, timeout_seconds):
        command = [
            self.path,
            "--print",
            "--permission-mode",
            "plan",
            "--disable-slash-commands",
            "--output-format",
            "json",
            "--json-schema",
            schema_json,
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.append(prompt)
        return command


class CodexCLIAdapter(_SubprocessAdapter):
    """Workspace-scoped implementation adapter."""

    def __init__(self, *, model: str | None = None, binary: str = "codex"):
        super().__init__(binary=binary, model=model)
        self._capability = AdapterCapability(
            name="codex",
            version=self.version,
            roles=frozenset({StructuredTask.IMPLEMENT}),
            structured_output=True,
            resume=True,
            native_fork=False,
            writes_workspace=True,
            merge_authority=False,
            temporary=False,
        )
        interactive = [
            self.path,
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--no-alt-screen",
        ]
        if self.model:
            interactive.extend(["--model", self.model])
        self._session_contract = AdapterSessionContract(
            launch_command=tuple(interactive),
            readiness=ReadinessDetector(
                r"model:\s+(?!loading)\S+",
                trust_pattern=r"Do you trust the contents",
            ),
            trust_prompt=TrustPromptBehavior.REJECT,
            resume=True,
            fork=ForkCapability.SYNTHETIC,
            structured_output=StructuredOutputChannel.JSONL_STDOUT,
            termination=TerminationBehavior.GRACEFUL_THEN_KILL,
        )
        self._persistent_declaration = PersistentAdapterDeclaration(
            adapter="codex",
            adapter_version=self.version,
            declaration_revision=f"codex-persistent-v1-{_digest(self.version)[:12]}",
            roles=frozenset({"implementer"}),
            root_launch_command=self._session_contract.launch_command,
            root_readiness=self._session_contract.readiness,
            synthetic_launch_command=self._session_contract.launch_command,
            native_fork_command=None,
            resume_command=None,
            persistent_root=CapabilityValidation.FAIL_CLOSED,
            native_fork=CapabilityValidation.FAIL_CLOSED,
            resume=CapabilityValidation.FAIL_CLOSED,
            structured_terminal_events=CapabilityValidation.FAIL_CLOSED,
            validation_provenance_sha256=None,
            writes_workspace=True,
            merge_authority=False,
            temporary=False,
            trust_prompt=self._session_contract.trust_prompt,
            termination=self._session_contract.termination,
        )

    @property
    def capability(self) -> AdapterCapability:
        return self._capability

    def _command(self, task, *, prompt, cwd, schema_path, schema_json, timeout_seconds):
        common_git_dir = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        command = [
            self.path,
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
            "--cd",
            str(cwd),
            "--add-dir",
            common_git_dir,
            "--config",
            'model_reasoning_effort="low"',
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.extend(
            [
                "exec",
                "--ignore-rules",
                "--json",
                "--output-schema",
                str(schema_path),
                prompt,
            ]
        )
        return command
