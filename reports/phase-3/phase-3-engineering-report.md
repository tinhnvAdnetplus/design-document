# Phase 3 Engineering Report

## Outcome

Phase 3.1–3.5 is implemented without changing the frozen V2.2 architecture, validation assertions, or performance thresholds. The production Event Store uses SQLite WAL, one persistent writer connection, explicit transactions, `synchronous=FULL`, bounded group commit, and deterministic replay.

The final unchanged validation run passed **82/82** assertions. PERF-01 measured **31.612 ms p99** against the frozen **<50 ms** criterion. Five production Event Store runs on the workspace's ext4 filesystem measured group-commit p99 between **25.121 and 28.598 ms** for the same 150-event workload.

## Delivered implementation

- `src/ai_runtime/store/event_store.py` — append-only SQLite schema, envelope validation, integrity verification, idempotency, contiguous aggregate ordering, explicit transactions, WAL checkpoints, persistent replay reader, and deterministic projection API.
- `src/ai_runtime/store/writer.py` — one thread-confined persistent writer, asynchronous futures, durable acknowledgements, bounded queue, immediate/time-window policy, maximum batch size, failure isolation, and graceful drain.
- `benchmarks/event_store_benchmark.py` — CSV, JSON, and Markdown exporters for open, write, flush, fsync, commit, close, batch commit, projection, replay, and end-to-end acceptance.
- `tests/runtime/test_event_store.py` — six tests covering SQL configuration and constraints, append-only triggers, idempotency, ordering, replay, group commit, concurrent producers, queue capacity, and acknowledged-commit crash recovery.

## Durable acceptance path

1. A submission is timestamped and enters a queue capped at 4,096 items.
2. The writer gathers at most 512 events for at most 2 ms.
3. Each event is schema-envelope checked and its canonical SHA-256 is verified.
4. `BEGIN IMMEDIATE` establishes the single-writer transaction.
5. Identity, idempotency, and stream sequence constraints are applied with statement-atomic inserts.
6. SQLite returns from `COMMIT` under WAL and `synchronous=FULL`.
7. Only then are successful futures resolved and acceptance acknowledged.

Rejected events never receive an acceptance acknowledgement. One invalid event does not cause unrelated valid submissions in the same gathered group to fail.

## Why the SLA is reached

The previous PoC storage path performed 150 open/write/flush/fsync/close cycles. On this ext4/WSL2 host, isolated fsync p99 reached 8.952 ms in the representative run and 30.236 ms in the noisiest repeat. A per-event durable boundary therefore makes the tail proportional to host storage jitter.

The production path removes per-event connection lifecycle work and shares one WAL commit across a bounded concurrent batch. For the 150-event burst, the final policy required one commit. In the representative run:

- immediate durable acceptance p99: **13.605 ms**;
- group-commit batch transaction: **14.609 ms**;
- group-commit acceptance p99, including queueing: **28.598 ms**;
- group-commit worst case: **28.735 ms**.

The initial 64-event configuration failed a deliberately heavier 300-event ext4 burst at 66.844 ms p99 because five serial fsync-backed commits accumulated in the queue. Increasing the bounded maximum to 512 and removing redundant event-envelope serialization reduced durable-boundary count and writer CPU work. No durability mode, threshold, or workload criterion was weakened.

## Correctness and recovery evidence

- The database rejects `UPDATE` and `DELETE` through triggers.
- A subprocess appended an event, received its post-commit acknowledgement, and exited immediately with `os._exit(9)`; a new reader recovered the integrity-valid event.
- Exact duplicate content returns `DUPLICATE_IGNORED`; a reused idempotency key with different content returns `IDEMPOTENCY_CONFLICT`.
- Sequence gaps return `AGGREGATE_SEQUENCE_CONFLICT`.
- Replay orders globally by durable position and per stream by aggregate sequence, re-verifies SHA-256, is streaming, and has no side-effect execution path.
- SQLite `quick_check` returned `ok` in tests.

## Bottleneck analysis

The remaining acceptance cost is dominated by the ext4 durable commit and canonical event preparation. Open, write, flush, and close are each below 0.2 ms p99 in isolation. The flame-graph condition was not triggered because the final SLA passes and the phase breakdown identifies the storage boundary directly.

The isolated fsync distribution remains host-sensitive. Queue admission is therefore bounded and fails with explicit backpressure instead of allowing unbounded tail growth. Workloads that continuously exceed one writer's service rate require capacity planning; the implementation does not conceal overload.

## Recommendation

**READY FOR EVENT STORE MERGE**

This recommendation applies to the Event Store infrastructure merge. CI should retain the unchanged PERF-01 gate and add supported-host repetitions. A real power-cut laboratory and non-WSL filesystem matrix are recommended follow-up hardening, not blockers for this first store merge.

