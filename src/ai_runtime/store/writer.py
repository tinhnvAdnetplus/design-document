"""Single-writer queue with bounded, configurable group commit."""

from __future__ import annotations

import dataclasses
import enum
import queue
import threading
import time
import uuid
from collections.abc import Mapping
from concurrent.futures import Future
from typing import Any

from .event_store import (
    AppendResult,
    EventStoreConfig,
    SQLiteEventReader,
    SQLiteEventStore,
    Validator,
)


class WriterClosedError(RuntimeError):
    pass


class QueueCapacityError(RuntimeError):
    pass


class GroupCommitPolicy(enum.StrEnum):
    IMMEDIATE = "immediate"
    TIME_WINDOW = "time_window"


@dataclasses.dataclass(frozen=True, slots=True)
class GroupCommitConfig:
    policy: GroupCommitPolicy = GroupCommitPolicy.TIME_WINDOW
    max_batch_size: int = 512
    window_ms: float = 2.0
    max_queue_size: int = 4_096
    enqueue_timeout_ms: float = 50.0

    def __post_init__(self) -> None:
        if self.max_batch_size <= 0:
            raise ValueError("max_batch_size must be positive")
        if not 0 <= self.window_ms <= 1_000:
            raise ValueError("window_ms must be between 0 and 1000")
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        if self.enqueue_timeout_ms < 0:
            raise ValueError("enqueue_timeout_ms cannot be negative")
        if self.policy == GroupCommitPolicy.IMMEDIATE and self.max_batch_size != 1:
            object.__setattr__(self, "max_batch_size", 1)


@dataclasses.dataclass(frozen=True, slots=True)
class AppendReceipt:
    event_id: str
    global_position: int
    status: str
    batch_id: str
    batch_size: int
    commit_duration_ms: float
    acceptance_latency_ms: float


@dataclasses.dataclass(slots=True)
class _Request:
    event: Mapping[str, Any]
    future: Future[AppendReceipt]
    submitted_ns: int


_STOP = object()


class EventWriter:
    """Own exactly one persistent SQLite write connection and writer thread."""

    def __init__(
        self,
        store_config: EventStoreConfig,
        group_commit: GroupCommitConfig | None = None,
        validator: Validator | None = None,
    ):
        self.store_config = store_config
        self.group_commit = group_commit or GroupCommitConfig()
        self.validator = validator
        self._queue: queue.Queue[_Request | object] = queue.Queue(
            maxsize=self.group_commit.max_queue_size
        )
        self._state_lock = threading.Lock()
        self._started = False
        self._closing = False
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._fatal_error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name="event-store-writer",
            daemon=False,
        )
        self._reader: SQLiteEventReader | None = None

    def start(self) -> EventWriter:
        with self._state_lock:
            if self._closing:
                raise WriterClosedError("Event Writer is closing")
            if not self._started:
                self._started = True
                self._thread.start()
        self._ready.wait()
        if self._startup_error is not None:
            raise RuntimeError("Event Writer failed to start") from self._startup_error
        if self._reader is None:
            self._reader = SQLiteEventReader(self.store_config)
        return self

    def submit(self, event: Mapping[str, Any]) -> Future[AppendReceipt]:
        future: Future[AppendReceipt] = Future()
        request = _Request(event, future, time.perf_counter_ns())
        with self._state_lock:
            if not self._started or self._closing:
                error = WriterClosedError("Event Writer is not accepting submissions")
                if self._fatal_error is not None:
                    raise error from self._fatal_error
                raise error
            try:
                self._queue.put(
                    request,
                    timeout=self.group_commit.enqueue_timeout_ms / 1_000,
                )
            except queue.Full as exc:
                raise QueueCapacityError(
                    f"Event Writer queue reached {self.group_commit.max_queue_size} items"
                ) from exc
        return future

    def append(self, event: Mapping[str, Any], timeout: float | None = None) -> AppendReceipt:
        return self.submit(event).result(timeout=timeout)

    def iter_events(self, **kwargs: Any):
        if self._reader is None:
            raise WriterClosedError("Event Writer is not started")
        return self._reader.iter_events(**kwargs)

    def replay(self, projector, initial_state, **kwargs: Any):
        if self._reader is None:
            raise WriterClosedError("Event Writer is not started")
        return self._reader.replay(projector, initial_state, **kwargs)

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    def close(self, timeout: float | None = None) -> None:
        with self._state_lock:
            if not self._started:
                self._closing = True
                return
            if not self._closing:
                self._closing = True
                self._queue.put(_STOP)
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            raise TimeoutError("Event Writer did not drain before close timeout")
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    def _run(self) -> None:
        store: SQLiteEventStore | None = None
        try:
            store = SQLiteEventStore(self.store_config, self.validator)
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()
            return
        self._ready.set()
        try:
            while True:
                item = self._queue.get()
                if item is _STOP:
                    break
                assert isinstance(item, _Request)
                batch = [item]
                stop_after_batch = False
                if self.group_commit.policy == GroupCommitPolicy.TIME_WINDOW:
                    deadline = time.monotonic() + self.group_commit.window_ms / 1_000
                    while len(batch) < self.group_commit.max_batch_size:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        try:
                            candidate = self._queue.get(timeout=remaining)
                        except queue.Empty:
                            break
                        if candidate is _STOP:
                            stop_after_batch = True
                            break
                        assert isinstance(candidate, _Request)
                        batch.append(candidate)
                try:
                    self._commit_batch(store, batch)
                except BaseException as exc:
                    for request in batch:
                        if not request.future.done():
                            request.future.set_exception(exc)
                    raise
                if stop_after_batch:
                    break
        except BaseException as exc:
            self._fatal_error = exc
            self._fail_pending(exc)
            with self._state_lock:
                self._closing = True
        finally:
            store.close()

    def _fail_pending(self, error: BaseException) -> None:
        while True:
            try:
                candidate = self._queue.get_nowait()
            except queue.Empty:
                return
            if isinstance(candidate, _Request) and not candidate.future.done():
                candidate.future.set_exception(error)

    @staticmethod
    def _commit_batch(store: SQLiteEventStore, batch: list[_Request]) -> None:
        outcomes = store.append_group([request.event for request in batch])
        completed_ns = time.perf_counter_ns()
        batch_id = uuid.uuid4().hex
        for request, outcome in zip(batch, outcomes, strict=True):
            if request.future.cancelled():
                continue
            if isinstance(outcome, BaseException):
                request.future.set_exception(outcome)
                continue
            assert isinstance(outcome, AppendResult)
            request.future.set_result(
                AppendReceipt(
                    event_id=outcome.event_id,
                    global_position=outcome.global_position,
                    status=outcome.status,
                    batch_id=batch_id,
                    batch_size=len(batch),
                    commit_duration_ms=outcome.commit_duration_ms,
                    acceptance_latency_ms=(completed_ns - request.submitted_ns) / 1_000_000,
                )
            )

    def __enter__(self) -> EventWriter:
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.close()
