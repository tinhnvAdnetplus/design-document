#!/usr/bin/env python3
"""Phase 3 Event Store micro-benchmark with CSV/JSON/Markdown exporters."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from ai_runtime.store import (
    EventStoreConfig,
    EventWriter,
    GroupCommitConfig,
    GroupCommitPolicy,
    SQLiteEventReader,
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def event(sequence: int, stream: str = "benchmark/main") -> dict[str, Any]:
    value = {
        "event_id": f"evt-{stream.replace('/', '-')}-{sequence:08d}",
        "protocol": "ai-runtime.events/v1",
        "type": "implementation.progress",
        "occurred_at": "2026-08-03T00:00:00Z",
        "producer": {"session_id": "benchmark", "role": "runtime_benchmark", "adapter": "benchmark", "adapter_version": "1.0.0"},
        "aggregate": {"feature_id": stream, "stream": stream, "sequence": sequence},
        "correlation_id": f"cor-{stream}",
        "causation_id": None if sequence == 1 else f"evt-{stream.replace('/', '-')}-{sequence - 1:08d}",
        "idempotency_key": f"benchmark/{stream}/{sequence}",
        "policy_revision": "v2.2-frozen",
        "payload": {"sequence": sequence, "data": "x" * 128},
        "attachments": [],
    }
    value["integrity"] = {
        "content_sha256": hashlib.sha256(canonical(value)).hexdigest(),
        "signature_ref": None,
    }
    return value


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def summarize(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "worst_ms": max(values),
        "mean_ms": statistics.fmean(values),
        "stdev_ms": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def elapsed_ms(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000


def phase_breakdown(work: Path, samples: int) -> dict[str, list[float]]:
    phases = {name: [] for name in ("open", "write", "flush", "fsync", "commit", "close")}
    raw_path = work / "raw-fsync.dat"
    with raw_path.open("ab", buffering=64 * 1024) as handle:
        for index in range(samples):
            start = time.perf_counter_ns()
            handle.write(canonical({"event": index, "payload": "x" * 128}) + b"\n")
            phases["write"].append(elapsed_ms(start))
            start = time.perf_counter_ns()
            handle.flush()
            phases["flush"].append(elapsed_ms(start))
            start = time.perf_counter_ns()
            os.fsync(handle.fileno())
            phases["fsync"].append(elapsed_ms(start))

    database = work / "phase-breakdown.db"
    connection = sqlite3.connect(database, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("CREATE TABLE phase_events(id INTEGER PRIMARY KEY, payload BLOB NOT NULL)")
    for index in range(samples):
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("INSERT INTO phase_events(id, payload) VALUES (?, ?)", (index, b"x" * 128))
        start = time.perf_counter_ns()
        connection.execute("COMMIT")
        phases["commit"].append(elapsed_ms(start))
    connection.close()

    for _ in range(samples):
        start = time.perf_counter_ns()
        connection = sqlite3.connect(database, isolation_level=None)
        phases["open"].append(elapsed_ms(start))
        start = time.perf_counter_ns()
        connection.close()
        phases["close"].append(elapsed_ms(start))
    return phases


def acceptance_benchmarks(
    work: Path, samples: int, batch_size: int, window_ms: float
) -> tuple[dict[str, list[float]], EventStoreConfig]:
    observed: dict[str, list[float]] = {
        "accept_immediate": [],
        "accept_group_commit": [],
        "batch_commit": [],
    }
    immediate_config = EventStoreConfig(work / "immediate.db")
    immediate_policy = GroupCommitConfig(
        policy=GroupCommitPolicy.IMMEDIATE,
        max_batch_size=1,
        window_ms=0,
        max_queue_size=max(4_096, samples + 1),
    )
    with EventWriter(immediate_config, immediate_policy) as writer:
        for sequence in range(1, samples + 1):
            observed["accept_immediate"].append(
                writer.append(event(sequence), timeout=10).acceptance_latency_ms
            )

    group_config = EventStoreConfig(work / "group-commit.db")
    group_policy = GroupCommitConfig(
        policy=GroupCommitPolicy.TIME_WINDOW,
        max_batch_size=batch_size,
        window_ms=window_ms,
        max_queue_size=max(4_096, samples + 1),
    )
    with EventWriter(group_config, group_policy) as writer:
        futures = [writer.submit(event(sequence)) for sequence in range(1, samples + 1)]
        receipts = [future.result(timeout=30) for future in futures]
        observed["accept_group_commit"] = [receipt.acceptance_latency_ms for receipt in receipts]
        observed["batch_commit"] = [
            receipt.commit_duration_ms
            for index, receipt in enumerate(receipts)
            if index == 0 or receipt.batch_id != receipts[index - 1].batch_id
        ]
    return observed, group_config


def replay_benchmarks(config: EventStoreConfig, samples: int) -> dict[str, list[float]]:
    observed = {"projection": [], "replay": []}
    with SQLiteEventReader(config) as reader:
        events = list(reader.iter_events())
        iterations = max(30, min(samples, 100))
        for _ in range(iterations):
            start = time.perf_counter_ns()
            projection: dict[str, dict[str, Any]] = {}
            for item in events:
                projection[item["aggregate"]["stream"]] = {
                    "sequence": item["aggregate"]["sequence"],
                    "state": item["type"],
                    "last_event_id": item["event_id"],
                }
            observed["projection"].append(elapsed_ms(start))
            start = time.perf_counter_ns()
            replayed = list(reader.iter_events())
            observed["replay"].append(elapsed_ms(start))
            if replayed != events:
                raise AssertionError("replay is not deterministic")
    return observed


def filesystem_details(path: Path) -> dict[str, Any]:
    stat = os.statvfs(path)
    return {
        "path": str(path.resolve()),
        "block_size": stat.f_bsize,
        "fragment_size": stat.f_frsize,
        "filesystem_bytes": stat.f_blocks * stat.f_frsize,
        "available_bytes": stat.f_bavail * stat.f_frsize,
    }


def export(output: Path, payload: dict[str, Any], raw: dict[str, list[float]]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "event-store-benchmark.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output / "event-store-benchmark.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["metric", "count", "p50_ms", "p95_ms", "p99_ms", "worst_ms", "mean_ms", "stdev_ms"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for metric, values in raw.items():
            writer.writerow({"metric": metric, **summarize(values)})
    lines = [
        "# Phase 3 Event Store Benchmark",
        "",
        f"- Captured: `{payload['captured_at']}`",
        f"- Workload: **{payload['configuration']['samples']} events**",
        f"- Durability: `journal_mode=WAL`, `synchronous=FULL`",
        f"- PERF-01 equivalent result: **{payload['sla']['status']}** (group-commit p99 {payload['sla']['observed_p99_ms']:.3f} ms; target < {payload['sla']['target_p99_ms']:.3f} ms)",
        "",
        "| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric, stats in payload["statistics"].items():
        lines.append(
            f"| {metric} | {stats['count']} | {stats['p50_ms']:.3f} | {stats['p95_ms']:.3f} | {stats['p99_ms']:.3f} | {stats['worst_ms']:.3f} | {stats['stdev_ms']:.3f} |"
        )
    lines.extend(
        [
            "",
            "`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.",
        ]
    )
    (output / "event-store-benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--window-ms", type=float, default=2.0)
    parser.add_argument("--target-p99-ms", type=float, default=50.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples < 100:
        parser.error("--samples must be at least 100 for p99 measurement")

    captured = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or Path("phase3-artifacts") / captured
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".benchmark-work-", dir=output) as directory:
        work = Path(directory)
        raw = phase_breakdown(work, args.samples)
        acceptance, replay_config = acceptance_benchmarks(
            work, args.samples, args.batch_size, args.window_ms
        )
        raw.update(acceptance)
        raw.update(replay_benchmarks(replay_config, args.samples))
        statistics_payload = {name: summarize(values) for name, values in raw.items()}
        observed_p99 = float(statistics_payload["accept_group_commit"]["p99_ms"])
        payload = {
            "captured_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "configuration": {
                "samples": args.samples,
                "batch_size": args.batch_size,
                "window_ms": args.window_ms,
                "max_queue_size": max(4_096, args.samples + 1),
                "journal_mode": "WAL",
                "synchronous": "FULL",
                "single_writer": True,
                "persistent_connection": True,
                "explicit_transactions": True,
            },
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "processor": platform.processor(),
                "cpu_count": os.cpu_count(),
                "filesystem": filesystem_details(work),
            },
            "statistics": statistics_payload,
            "fsync_statistics": statistics_payload["fsync"],
            "sla": {
                "metric": "accept_group_commit",
                "target_p99_ms": args.target_p99_ms,
                "observed_p99_ms": observed_p99,
                "status": "PASS" if observed_p99 < args.target_p99_ms else "FAIL",
            },
            "raw_samples_ms": raw,
        }
        export(output, payload, raw)
    print(output.resolve())
    print(f"group commit p99: {observed_p99:.3f} ms ({payload['sla']['status']})")
    return 0 if payload["sla"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
