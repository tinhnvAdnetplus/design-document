"""Vendor-neutral contract implemented by agent CLI adapters."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..runtime.feature_sessions import PersistentAdapterDeclaration
    from ..runtime.sessions import AdapterSessionContract


class StructuredTask(enum.StrEnum):
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"


@dataclasses.dataclass(frozen=True, slots=True)
class AdapterCapability:
    name: str
    version: str
    roles: frozenset[StructuredTask]
    structured_output: bool
    resume: bool
    native_fork: bool
    writes_workspace: bool
    merge_authority: bool = False
    temporary: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class AdapterResult:
    value: Mapping[str, Any]
    evidence: Mapping[str, Any]


class AdapterError(RuntimeError):
    """The configured CLI is unavailable or violated its adapter contract."""


class AgentAdapter(Protocol):
    @property
    def capability(self) -> AdapterCapability: ...

    @property
    def session_contract(self) -> AdapterSessionContract: ...

    @property
    def persistent_declaration(self) -> PersistentAdapterDeclaration: ...

    def invoke(
        self,
        task: StructuredTask,
        *,
        prompt: str,
        cwd: Path,
        schema: Mapping[str, Any],
        timeout_seconds: float,
        feature_id: str | None = None,
    ) -> AdapterResult: ...

    def acknowledge(self, result: AdapterResult) -> None: ...
