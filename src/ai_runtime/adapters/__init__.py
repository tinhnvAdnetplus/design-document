"""Agent CLI adapter boundary."""

from .base import (
    AdapterCapability,
    AdapterError,
    AdapterResult,
    AgentAdapter,
    StructuredTask,
)
from .cli import AntigravityAdapter, ClaudeCLIAdapter, CodexCLIAdapter

__all__ = [
    "AdapterCapability",
    "AdapterError",
    "AdapterResult",
    "AgentAdapter",
    "AntigravityAdapter",
    "ClaudeCLIAdapter",
    "CodexCLIAdapter",
    "StructuredTask",
]
