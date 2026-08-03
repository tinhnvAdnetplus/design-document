"""Version-bound subprocess adapters for Claude, Antigravity, and Codex."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import AdapterCapability, AdapterError, AdapterResult, StructuredTask


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
    ) -> AdapterResult:
        if task not in self.capability.roles:
            raise AdapterError(f"{self.capability.name} does not support task {task}")
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
            started = time.perf_counter_ns()
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    text=True,
                    capture_output=True,
                    timeout=timeout + 5,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise AdapterError(
                    f"{self.capability.name} {task} timed out after {timeout:.0f}s"
                ) from exc
        duration_ms = (time.perf_counter_ns() - started) / 1_000_000
        if result.returncode != 0:
            detail = _redact(result.stderr or result.stdout, cwd)
            raise AdapterError(
                f"{self.capability.name} {task} exited {result.returncode}: {detail}"
            )
        value = _extract_structured(result.stdout, task, self.required_keys[task])
        if value is None:
            raise AdapterError(
                f"{self.capability.name} returned no valid structured {task} result; "
                f"{_shape_diagnostic(result.stdout)}"
            )
        _validate_result(task, value)
        evidence = {
            "adapter": self.capability.name,
            "adapter_version": self.capability.version,
            "task": str(task),
            "duration_ms": round(duration_ms, 3),
            "exit_code": result.returncode,
            "stdout_sha256": _digest(result.stdout),
            "stderr_sha256": _digest(result.stderr),
            "stdout_bytes": len(result.stdout.encode("utf-8")),
            "stderr_bytes": len(result.stderr.encode("utf-8")),
            "prompt_sha256": _digest(prompt),
        }
        return AdapterResult(value=value, evidence=evidence)


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
    """Production planner/reviewer adapter and baseline merge authority."""

    def __init__(self, *, model: str | None = None, binary: str = "claude"):
        super().__init__(binary=binary, model=model)
        self._capability = AdapterCapability(
            name="claude",
            version=self.version,
            roles=frozenset({StructuredTask.PLAN, StructuredTask.REVIEW}),
            structured_output=True,
            resume=True,
            native_fork=True,
            writes_workspace=False,
            merge_authority=True,
            temporary=False,
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
            native_fork=True,
            writes_workspace=True,
            merge_authority=False,
            temporary=False,
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
