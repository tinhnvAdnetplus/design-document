from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from ai_runtime.store import (
    EventStoreConfig,
    EventWriter,
    GroupCommitConfig,
    GroupCommitPolicy,
    IdempotencyConflictError,
    QueueCapacityError,
    SQLiteEventReader,
    SQLiteEventStore,
    SequenceConflictError,
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def make_event(sequence: int, *, stream: str = "feature/test", suffix: str = "") -> dict:
    event = {
        "event_id": f"evt-{stream.replace('/', '-')}-{sequence}{suffix}",
        "protocol": "ai-runtime.events/v1",
        "type": "implementation.progress",
        "occurred_at": f"2026-08-03T00:00:{sequence:02d}Z",
        "producer": {"session_id": "test", "role": "test", "adapter": "test", "adapter_version": "1"},
        "aggregate": {"feature_id": stream, "stream": stream, "sequence": sequence},
        "correlation_id": f"cor-{stream}",
        "causation_id": None if sequence == 1 else f"evt-{stream.replace('/', '-')}-{sequence - 1}",
        "idempotency_key": f"{stream}/{sequence}",
        "policy_revision": "frozen-v2.2",
        "payload": {"sequence": sequence, "suffix": suffix},
        "attachments": [],
    }
    event["integrity"] = {
        "content_sha256": hashlib.sha256(canonical(event)).hexdigest(),
        "signature_ref": None,
    }
    return event


class EventStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "events.db"
        self.config = EventStoreConfig(self.database)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_required_sqlite_configuration_and_constraints(self):
        with SQLiteEventStore(self.config) as store:
            self.assertEqual("wal", str(store.pragmas["journal_mode"]).lower())
            self.assertEqual(2, store.pragmas["synchronous"])
            store.append(make_event(1))
            self.assertEqual("ok", store.quick_check())

        connection = sqlite3.connect(self.database)
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchone()[0]
        self.assertIn("event_id TEXT PRIMARY KEY NOT NULL", schema)
        self.assertIn("idempotency_key TEXT NOT NULL UNIQUE", schema)
        self.assertIn("UNIQUE (aggregate_stream, sequence)", schema)
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("UPDATE events SET event_type='tampered'")
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM events")
        connection.close()

    def test_idempotency_ordering_and_deterministic_replay(self):
        with SQLiteEventStore(self.config) as store:
            first = make_event(1)
            self.assertEqual("APPENDED", store.append(first).status)
            self.assertEqual("DUPLICATE_IGNORED", store.append(first).status)

            changed = make_event(1, suffix="different")
            changed["event_id"] = first["event_id"]
            changed["idempotency_key"] = first["idempotency_key"]
            unsigned = dict(changed)
            unsigned.pop("integrity")
            changed["integrity"]["content_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
            with self.assertRaises(IdempotencyConflictError):
                store.append(changed)
            with self.assertRaises(SequenceConflictError):
                store.append(make_event(3))
            store.append(make_event(2))

        with SQLiteEventReader(self.config) as reader:
            replay_one = list(reader.iter_events())
            replay_two = list(reader.iter_events())
            self.assertEqual(replay_one, replay_two)
            self.assertEqual([1, 2], [item["aggregate"]["sequence"] for item in replay_one])
            self.assertEqual(2, reader.count())

    def test_group_commit_uses_one_writer_and_does_not_failure_couple(self):
        group = GroupCommitConfig(
            policy=GroupCommitPolicy.TIME_WINDOW,
            max_batch_size=16,
            window_ms=20,
            max_queue_size=64,
        )
        with EventWriter(self.config, group) as writer:
            futures = [writer.submit(make_event(index)) for index in range(1, 9)]
            invalid = writer.submit(make_event(10))
            receipts = [future.result(timeout=2) for future in futures]
            with self.assertRaises(SequenceConflictError):
                invalid.result(timeout=2)
            self.assertTrue(any(receipt.batch_size > 1 for receipt in receipts))
            self.assertEqual(list(range(1, 9)), [event["aggregate"]["sequence"] for event in writer.iter_events()])

        with SQLiteEventReader(self.config) as reader:
            self.assertEqual(8, reader.count())

    def test_concurrent_submitters_are_serialized(self):
        group = GroupCommitConfig(max_batch_size=32, window_ms=5, max_queue_size=128)
        with EventWriter(self.config, group) as writer:
            events = [make_event(1, stream=f"feature/{index}") for index in range(32)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                receipts = list(pool.map(writer.append, events))
            self.assertEqual(32, len({receipt.global_position for receipt in receipts}))
            self.assertEqual(32, len(list(writer.iter_events())))

    def test_queue_capacity_is_enforced(self):
        validator_entered = threading.Event()
        release_validator = threading.Event()

        def blocking_validator(_):
            validator_entered.set()
            self.assertTrue(release_validator.wait(timeout=2))

        policy = GroupCommitConfig(
            policy=GroupCommitPolicy.IMMEDIATE,
            max_batch_size=1,
            window_ms=0,
            max_queue_size=1,
            enqueue_timeout_ms=0,
        )
        writer = EventWriter(self.config, policy, blocking_validator).start()
        try:
            first = writer.submit(make_event(1))
            self.assertTrue(validator_entered.wait(timeout=2))
            second = writer.submit(make_event(2))
            with self.assertRaises(QueueCapacityError):
                writer.submit(make_event(3))
            release_validator.set()
            self.assertEqual("APPENDED", first.result(timeout=2).status)
            self.assertEqual("APPENDED", second.result(timeout=2).status)
        finally:
            release_validator.set()
            writer.close(timeout=2)

    def test_acknowledged_commit_survives_abrupt_process_exit(self):
        source_root = Path(__file__).resolve().parents[2] / "src"
        script = r'''
import hashlib, json, os, sys
from pathlib import Path
from ai_runtime.store import EventStoreConfig, EventWriter, GroupCommitConfig, GroupCommitPolicy
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
event = {"event_id":"crash-safe","protocol":"ai-runtime.events/v1","type":"feature.requested","occurred_at":"2026-08-03T00:00:00Z","producer":{"session_id":"test","role":"test","adapter":"test","adapter_version":"1"},"aggregate":{"feature_id":"crash","stream":"crash","sequence":1},"correlation_id":"cor-crash","causation_id":None,"idempotency_key":"crash/1","policy_revision":"v2.2","payload":{"durable":True}}
event["integrity"] = {"content_sha256": hashlib.sha256(canonical(event)).hexdigest(), "signature_ref":None}
writer = EventWriter(EventStoreConfig(Path(sys.argv[1])), GroupCommitConfig(policy=GroupCommitPolicy.IMMEDIATE, max_batch_size=1, window_ms=0))
writer.start()
writer.append(event)
print("ACK", flush=True)
os._exit(9)
'''
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.database)],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(9, result.returncode)
        self.assertEqual("ACK", result.stdout.strip())
        with SQLiteEventReader(self.config) as reader:
            events = list(reader.iter_events())
        self.assertEqual("crash-safe", events[0]["event_id"])
        self.assertTrue(events[0]["payload"]["durable"])


if __name__ == "__main__":
    unittest.main()
