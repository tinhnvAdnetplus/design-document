"""Durable Event Store and its single-writer service."""

from .event_store import (
    AppendResult,
    CorruptEventStoreError,
    EventIdConflictError,
    EventStoreConfig,
    EventStoreError,
    EventValidationError,
    IdempotencyConflictError,
    SQLiteEventReader,
    SQLiteEventStore,
    SequenceConflictError,
)
from .writer import (
    AppendReceipt,
    EventWriter,
    GroupCommitConfig,
    GroupCommitPolicy,
    QueueCapacityError,
    WriterClosedError,
)

__all__ = [
    "AppendResult",
    "AppendReceipt",
    "CorruptEventStoreError",
    "EventStoreConfig",
    "EventStoreError",
    "EventValidationError",
    "EventIdConflictError",
    "EventWriter",
    "GroupCommitConfig",
    "GroupCommitPolicy",
    "IdempotencyConflictError",
    "QueueCapacityError",
    "SQLiteEventReader",
    "SQLiteEventStore",
    "SequenceConflictError",
    "WriterClosedError",
]
