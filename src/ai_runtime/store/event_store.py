"""Append-only SQLite WAL Event Store.

The write connection is deliberately synchronous and thread-confined.  The
``EventWriter`` service owns it for its complete lifetime and is the only
production write path.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "ai-runtime.events/v1"
EVENT_TYPES = frozenset(
    {
        "feature.requested",
        "plan.ready",
        "plan.approved",
        "implementation.progress",
        "implementation.ready",
        "review.requested",
        "changes.requested",
        "merge.approved",
        "merge.started",
        "merge.completed",
        "knowledge.sync.requested",
        "knowledge.synchronized",
        "knowledge.evolution.started",
        "knowledge.snapshot.published",
        "cache.invalidated",
        "session.lineage.recorded",
        "session.unavailable",
        "lease.granted",
        "lease.revoked",
        "event.rejected",
    }
)


class EventStoreError(RuntimeError):
    """Base class for Event Store failures."""


class EventValidationError(EventStoreError):
    """The event envelope is incomplete or fails integrity validation."""


class IdempotencyConflictError(EventStoreError):
    """An idempotency key already identifies different event content."""


class EventIdConflictError(EventStoreError):
    """An event ID already identifies different event content."""


class SequenceConflictError(EventStoreError):
    """The aggregate stream sequence is not the next contiguous value."""


class CorruptEventStoreError(EventStoreError):
    """Persisted columns do not reconstruct a valid event."""


@dataclasses.dataclass(frozen=True, slots=True)
class EventStoreConfig:
    database_path: Path
    busy_timeout_ms: int = 5_000
    wal_autocheckpoint_pages: int = 1_000
    mmap_size_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_path", Path(self.database_path))
        if self.busy_timeout_ms <= 0:
            raise ValueError("busy_timeout_ms must be positive")
        if self.wal_autocheckpoint_pages <= 0:
            raise ValueError("wal_autocheckpoint_pages must be positive")
        if self.mmap_size_bytes < 0:
            raise ValueError("mmap_size_bytes cannot be negative")


@dataclasses.dataclass(frozen=True, slots=True)
class AppendResult:
    event_id: str
    global_position: int
    status: str
    commit_duration_ms: float


@dataclasses.dataclass(frozen=True, slots=True)
class _PreparedEvent:
    event_id: str
    event_type: str
    timestamp: str
    aggregate_stream: str
    sequence: int
    idempotency_key: str
    causation: str | None
    correlation: str
    sha256: str
    payload: bytes
    headers: bytes


Validator = Callable[[Mapping[str, Any]], None]


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventValidationError(f"event is not canonical JSON: {exc}") from exc


def content_sha256(event: Mapping[str, Any]) -> str:
    unsigned = dict(event)
    unsigned.pop("integrity", None)
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise EventValidationError(f"{key} must be an object")
    return result


def _required_text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise EventValidationError(f"{key} must be a non-empty string")
    return result


def prepare_event(event: Mapping[str, Any], validator: Validator | None = None) -> _PreparedEvent:
    if not isinstance(event, Mapping):
        raise EventValidationError("event must be an object")
    if validator is not None:
        validator(event)

    aggregate = _required_mapping(event, "aggregate")
    integrity = _required_mapping(event, "integrity")
    producer = _required_mapping(event, "producer")
    event_id = _required_text(event, "event_id")
    event_type = _required_text(event, "type")
    timestamp = _required_text(event, "occurred_at")
    if _required_text(event, "protocol") != PROTOCOL_VERSION:
        raise EventValidationError(f"unsupported protocol; expected {PROTOCOL_VERSION}")
    if event_type not in EVENT_TYPES:
        raise EventValidationError(f"unsupported event type: {event_type}")
    for producer_field in ("session_id", "role", "adapter", "adapter_version"):
        _required_text(producer, producer_field)
    _required_text(aggregate, "feature_id")
    _required_text(event, "policy_revision")
    try:
        parsed_timestamp = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventValidationError("occurred_at must be an RFC 3339 date-time") from exc
    if parsed_timestamp.tzinfo is None:
        raise EventValidationError("occurred_at must include a timezone")
    aggregate_stream = _required_text(aggregate, "stream")
    idempotency_key = _required_text(event, "idempotency_key")
    correlation = _required_text(event, "correlation_id")
    stored_sha = _required_text(integrity, "content_sha256")
    sequence = aggregate.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
        raise EventValidationError("aggregate.sequence must be a positive integer")
    causation = event.get("causation_id")
    if causation is not None and (not isinstance(causation, str) or not causation):
        raise EventValidationError("causation_id must be null or a non-empty string")
    if len(stored_sha) != 64:
        raise EventValidationError("integrity.content_sha256 must contain 64 hex characters")
    try:
        bytes.fromhex(stored_sha)
    except ValueError as exc:
        raise EventValidationError("integrity.content_sha256 is not hexadecimal") from exc
    computed_sha = content_sha256(event)
    if not hmac.compare_digest(stored_sha.lower(), computed_sha):
        raise EventValidationError("INTEGRITY_MISMATCH")

    normalized = dict(event)
    payload_value = normalized.pop("payload", None)
    if "payload" not in event:
        raise EventValidationError("payload is required")
    if not isinstance(payload_value, Mapping):
        raise EventValidationError("payload must be an object")
    return _PreparedEvent(
        event_id=event_id,
        event_type=event_type,
        timestamp=timestamp,
        aggregate_stream=aggregate_stream,
        sequence=sequence,
        idempotency_key=idempotency_key,
        causation=causation,
        correlation=correlation,
        sha256=stored_sha.lower(),
        payload=canonical_json(payload_value),
        headers=canonical_json(normalized),
    )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS event_store_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY NOT NULL,
    global_position INTEGER NOT NULL UNIQUE CHECK (global_position > 0),
    idempotency_key TEXT NOT NULL UNIQUE,
    aggregate_stream TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    causation TEXT,
    correlation TEXT NOT NULL,
    payload BLOB NOT NULL,
    headers BLOB NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    UNIQUE (aggregate_stream, sequence)
);

CREATE INDEX IF NOT EXISTS events_correlation_idx ON events(correlation, global_position);
CREATE INDEX IF NOT EXISTS events_causation_idx ON events(causation) WHERE causation IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events BEGIN
    SELECT RAISE(ABORT, 'EVENT_STORE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events BEGIN
    SELECT RAISE(ABORT, 'EVENT_STORE_APPEND_ONLY');
END;
"""


class SQLiteEventStore:
    """Low-level append-only store with one persistent write connection."""

    def __init__(self, config: EventStoreConfig, validator: Validator | None = None):
        self.config = config
        self.validator = validator
        self.config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            str(self.config.database_path),
            timeout=self.config.busy_timeout_ms / 1_000,
            isolation_level=None,
        )
        self._closed = False
        try:
            self._configure()
            self._initialize_schema()
        except BaseException:
            self._connection.close()
            self._closed = True
            raise

    def _configure(self) -> None:
        connection = self._connection
        mode = str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
        if mode != "wal":
            raise EventStoreError(f"SQLite refused WAL mode: {mode}")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute(f"PRAGMA busy_timeout={self.config.busy_timeout_ms}")
        connection.execute(f"PRAGMA wal_autocheckpoint={self.config.wal_autocheckpoint_pages}")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA temp_store=MEMORY")
        if self.config.mmap_size_bytes:
            connection.execute(f"PRAGMA mmap_size={self.config.mmap_size_bytes}")
        synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
        if synchronous != 2:
            raise EventStoreError(f"SQLite synchronous mode is not FULL: {synchronous}")

    def _initialize_schema(self) -> None:
        self._connection.executescript(_SCHEMA)
        row = self._connection.execute(
            "SELECT value FROM event_store_metadata WHERE key='schema_version'"
        ).fetchone()
        if row is None:
            self._connection.execute(
                "INSERT INTO event_store_metadata(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        elif int(row[0]) != SCHEMA_VERSION:
            raise EventStoreError(
                f"unsupported Event Store schema version {row[0]}; expected {SCHEMA_VERSION}"
            )

    @property
    def pragmas(self) -> dict[str, Any]:
        return {
            "journal_mode": self._connection.execute("PRAGMA journal_mode").fetchone()[0],
            "synchronous": self._connection.execute("PRAGMA synchronous").fetchone()[0],
            "wal_autocheckpoint": self._connection.execute("PRAGMA wal_autocheckpoint").fetchone()[
                0
            ],
            "busy_timeout": self._connection.execute("PRAGMA busy_timeout").fetchone()[0],
        }

    def append(self, event: Mapping[str, Any]) -> AppendResult:
        outcome = self.append_group([event])[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def append_group(
        self, events: Sequence[Mapping[str, Any]]
    ) -> list[AppendResult | BaseException]:
        """Commit independent submissions together without failure coupling.

        Invalid or conflicting submissions are rolled back to a per-event
        savepoint. Successful submissions share one durable commit.
        """
        if self._closed:
            raise EventStoreError("Event Store is closed")
        prepared: list[_PreparedEvent | BaseException] = []
        for event in events:
            try:
                prepared.append(prepare_event(event, self.validator))
            except BaseException as exc:
                prepared.append(exc)
        if not any(isinstance(item, _PreparedEvent) for item in prepared):
            return [item for item in prepared if isinstance(item, BaseException)]

        outcomes: list[AppendResult | BaseException | None] = [None] * len(prepared)
        started_ns = time.perf_counter_ns()
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            next_position = int(
                self._connection.execute(
                    "SELECT COALESCE(MAX(global_position), 0) + 1 FROM events"
                ).fetchone()[0]
            )
            expected_sequences: dict[str, int] = {}
            for index, item in enumerate(prepared):
                if isinstance(item, BaseException):
                    outcomes[index] = item
                    continue
                try:
                    if item.aggregate_stream not in expected_sequences:
                        last_sequence = self._connection.execute(
                            "SELECT sequence FROM events WHERE aggregate_stream=? ORDER BY sequence DESC LIMIT 1",
                            (item.aggregate_stream,),
                        ).fetchone()
                        expected_sequences[item.aggregate_stream] = (
                            1 if last_sequence is None else int(last_sequence[0]) + 1
                        )
                    status, position = self._insert_one(
                        item,
                        next_position,
                        expected_sequences[item.aggregate_stream],
                    )
                    outcomes[index] = AppendResult(item.event_id, position, status, 0.0)
                    if status == "APPENDED":
                        next_position += 1
                        expected_sequences[item.aggregate_stream] += 1
                except EventStoreError as exc:
                    outcomes[index] = exc
            self._connection.execute("COMMIT")
        except BaseException as exc:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            for index, outcome in enumerate(outcomes):
                if isinstance(outcome, AppendResult) or outcome is None:
                    outcomes[index] = exc
            return [item if item is not None else exc for item in outcomes]

        commit_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
        results: list[AppendResult | BaseException] = []
        for settled in outcomes:
            if settled is None:
                # Unreachable: every prepared slot is resolved above. Keep the
                # slot rather than dropping it, because the caller maps
                # outcomes back to submission futures by index.
                results.append(EventStoreError("submission was not resolved"))
            elif isinstance(settled, AppendResult):
                results.append(dataclasses.replace(settled, commit_duration_ms=commit_ms))
            else:
                results.append(settled)
        return results

    def _resolve_identity_conflict(self, event: _PreparedEvent) -> tuple[str, int] | None:
        duplicate = self._connection.execute(
            "SELECT event_id, global_position, payload, headers FROM events WHERE idempotency_key=?",
            (event.idempotency_key,),
        ).fetchone()
        if duplicate is not None:
            if bytes(duplicate[2]) == event.payload and bytes(duplicate[3]) == event.headers:
                return "DUPLICATE_IGNORED", int(duplicate[1])
            raise IdempotencyConflictError("IDEMPOTENCY_CONFLICT")
        same_id = self._connection.execute(
            "SELECT global_position, payload, headers FROM events WHERE event_id=?",
            (event.event_id,),
        ).fetchone()
        if same_id is not None:
            if bytes(same_id[1]) == event.payload and bytes(same_id[2]) == event.headers:
                return "DUPLICATE_IGNORED", int(same_id[0])
            raise EventIdConflictError("EVENT_ID_CONFLICT")
        return None

    def _insert_one(
        self, event: _PreparedEvent, position: int, expected_sequence: int
    ) -> tuple[str, int]:
        if event.sequence != expected_sequence:
            identity = self._resolve_identity_conflict(event)
            if identity is not None:
                return identity
            raise SequenceConflictError(f"AGGREGATE_SEQUENCE_CONFLICT expected={expected_sequence}")
        try:
            self._connection.execute(
                """
                INSERT INTO events(
                    event_id, global_position, idempotency_key, aggregate_stream,
                    sequence, event_type, timestamp, causation, correlation,
                    payload, headers, sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    position,
                    event.idempotency_key,
                    event.aggregate_stream,
                    event.sequence,
                    event.event_type,
                    event.timestamp,
                    event.causation,
                    event.correlation,
                    event.payload,
                    event.headers,
                    event.sha256,
                ),
            )
        except sqlite3.IntegrityError as exc:
            identity = self._resolve_identity_conflict(event)
            if identity is not None:
                return identity
            raise EventStoreError(f"SQLite invariant violation: {exc}") from exc
        return "APPENDED", position

    def quick_check(self) -> str:
        return str(self._connection.execute("PRAGMA quick_check").fetchone()[0])

    def checkpoint(self, mode: str = "PASSIVE") -> tuple[int, int, int]:
        normalized = mode.upper()
        if normalized not in {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}:
            raise ValueError("unsupported WAL checkpoint mode")
        row = self._connection.execute(f"PRAGMA wal_checkpoint({normalized})").fetchone()
        return int(row[0]), int(row[1]), int(row[2])

    def close(self) -> None:
        if not self._closed:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            self._connection.close()
            self._closed = True

    def __enter__(self) -> SQLiteEventStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
    try:
        headers = json.loads(bytes(row["headers"]))
        payload = json.loads(bytes(row["payload"]))
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise CorruptEventStoreError(
            f"CORRUPT_EVENT_STORE at global position {row['global_position']}"
        ) from exc
    reconstructed = dict(headers)
    reconstructed["payload"] = payload
    integrity = _required_mapping(reconstructed, "integrity")
    stored_integrity_sha = _required_text(integrity, "content_sha256").lower()
    if not hmac.compare_digest(str(row["sha256"]), stored_integrity_sha):
        raise CorruptEventStoreError(
            f"stored SHA column mismatch at global position {row['global_position']}"
        )
    if not hmac.compare_digest(content_sha256(reconstructed), stored_integrity_sha):
        raise CorruptEventStoreError(
            f"event integrity mismatch at global position {row['global_position']}"
        )
    return reconstructed


class SQLiteEventReader:
    """Persistent WAL reader for replay and projections."""

    def __init__(self, config: EventStoreConfig):
        self.config = config
        uri = f"file:{self.config.database_path.resolve()}?mode=ro"
        self._connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=self.config.busy_timeout_ms / 1_000,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._closed = False

    def iter_events(
        self, *, aggregate_stream: str | None = None, after_position: int = 0
    ) -> Iterator[dict[str, Any]]:
        if after_position < 0:
            raise ValueError("after_position cannot be negative")
        with self._lock:
            if self._closed:
                raise EventStoreError("Event Store reader is closed")
            if aggregate_stream is None:
                cursor = self._connection.execute(
                    "SELECT * FROM events WHERE global_position > ? ORDER BY global_position ASC",
                    (after_position,),
                )
            else:
                cursor = self._connection.execute(
                    """
                    SELECT * FROM events
                    WHERE aggregate_stream=? AND global_position > ?
                    ORDER BY sequence ASC, global_position ASC
                    """,
                    (aggregate_stream, after_position),
                )
            try:
                while rows := cursor.fetchmany(512):
                    for row in rows:
                        yield _decode_row(row)
            finally:
                cursor.close()

    def replay(
        self,
        projector: Callable[[Any, Mapping[str, Any]], Any],
        initial_state: Any,
        *,
        aggregate_stream: str | None = None,
        after_position: int = 0,
    ) -> Any:
        state = initial_state
        for event in self.iter_events(
            aggregate_stream=aggregate_stream, after_position=after_position
        ):
            state = projector(state, event)
        return state

    def count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def __enter__(self) -> SQLiteEventReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
