# Phase 3 Architecture Compliance Report

## Decision

The implementation conforms to the frozen V2.2 Event Store boundary. It records runtime evidence and does not change Git's role as code source of truth, replay external side effects, change agent authority, or alter any architecture document.

| Requirement | Implementation evidence | Status |
| --- | --- | --- |
| Append-only | No mutation API; SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers abort with `EVENT_STORE_APPEND_ONLY` | PASS |
| Durable | `journal_mode=WAL`, `synchronous=FULL`, explicit `COMMIT`; acknowledgement occurs afterward | PASS |
| Atomic | `BEGIN IMMEDIATE`; statement-atomic event inserts; success futures resolve only after transaction commit | PASS |
| Replayable | Persistent read connection streams rows in stable durable order | PASS |
| Deterministic | Canonical JSON, global position ordering, stream sequence ordering, SHA verification | PASS |
| Idempotent | `UNIQUE(idempotency_key)` plus exact payload/header comparison; conflicts fail closed | PASS |
| Crash-safe | WAL/FULL configuration plus abrupt post-ack process-exit recovery test | PASS |
| Single writer | One dedicated writer thread owns one thread-confined connection | PASS |
| Persistent connection | Connection opens at writer start and closes only after queue drain | PASS |
| Group commit | Immediate or time-window policy; 2 ms window, 512-event batch cap, 4,096 queue cap, configurable | PASS |
| No early acknowledgement | Futures are completed only after `SQLiteEventStore.append_group()` returns from `COMMIT` | PASS |
| `PRIMARY KEY(event_id)` | `event_id TEXT PRIMARY KEY NOT NULL` | PASS |
| `UNIQUE(idempotency_key)` | Declared in `events` table | PASS |
| `UNIQUE(aggregate_stream, sequence)` | Declared in `events` table and contiguous next-sequence check | PASS |
| Payload | Canonical JSON BLOB in `payload` | PASS |
| Headers | Canonical envelope-without-payload JSON BLOB in `headers` | PASS |
| SHA-256 | Lowercase 64-character digest in `sha256`; checked on acceptance and replay | PASS |
| Timestamp | `occurred_at` persisted in `timestamp`; timezone required | PASS |
| Causation | `causation_id` persisted in `causation` | PASS |
| Correlation | `correlation_id` persisted in `correlation` and indexed | PASS |

## Protocol behavior

The store accepts only `ai-runtime.events/v1`, the frozen event catalog, required producer metadata, aggregate feature/stream/sequence data, a timezone-bearing timestamp, policy revision, object payload, correlation, idempotency key, and a valid content SHA-256. A caller may additionally inject the complete Draft-07 validator at the acceptance boundary.

Causation is intentionally not a foreign key. V2.2 permits bounded pending-causation handling before final acceptance, so storage must persist causation without inventing a stronger architecture rule.

## Architecture immutability evidence

No file under `docs/` was changed. The frozen validation engine and PERF configuration retained these checksums before and after implementation:

- `ai-runtime-validation/lib/validation_lab.py`: `fefb26e4c0400e074b293f17011a6d17d540da692f89fba8a08dcc74760d1ebc`
- `ai-runtime-validation/poc/09-performance/fixtures/benchmark_config.json`: `749af917e38dc2579af3311d2ae07ced2516d3be94ec3c29d9a3105e9f398a67`

## Scope boundaries

This phase does not implement projections as durable materialized tables, the scheduler, policy authorization, Git intents, adapters, or external side effects. The replay API is deliberately pure: it applies a caller-provided projector and cannot execute runtime effects.

