# Phase 3 Validation Comparison

## Before versus after

| Measurement | Before Phase 3 | After Phase 3 | Change |
| --- | ---: | ---: | ---: |
| Validation assertions | 81/82 | 82/82 | +1 PASS |
| PERF-01 status | FAIL | PASS | Gate closed |
| PERF-01 p50 | 34.992 ms | 8.922 ms | -74.5% |
| PERF-01 p95 | 427.021 ms | 10.269 ms | -97.6% |
| PERF-01 p99 | 657.666 ms | 31.612 ms | -95.2% |
| PERF-01 threshold | <50 ms | <50 ms | Unchanged |

Before evidence: authoritative run `20260803T032110Z-2986e3`. After evidence: final unchanged-suite run `20260803T040752Z-130658`.

The frozen PoC reports only p50/p95/p99, so worst case and standard deviation cannot be reconstructed from its artifacts without modifying the test. Those required statistics are recorded by the Phase 3 production benchmark: representative p50 **25.522 ms**, p95 **28.296 ms**, p99 **28.598 ms**, worst **28.735 ms**, and standard deviation **1.423 ms**.

## Suite outcome

| PoC | Before | After |
| --- | ---: | ---: |
| 01 — tmux runtime | 8/8 | 8/8 |
| 02 — event protocol | 12/12 | 12/12 |
| 03 — session resume | 8/8 | 8/8 |
| 04 — capability registry | 7/7 | 7/7 |
| 05 — knowledge runtime | 9/9 | 9/9 |
| 06 — review loop | 6/6 | 6/6 |
| 07 — scheduler | 6/6 | 6/6 |
| 08 — chaos | 7/7 | 7/7 |
| 09 — performance | 8/9 | 9/9 |
| 10 — end-to-end | 10/10 | 10/10 |
| **Total** | **81/82** | **82/82** |

## Causality note

The frozen PERF-01 implementation still exercises its original NDJSON open/write/flush/fsync/close path; it has no production-runtime injection seam. It was intentionally not modified. Therefore, the improved frozen-suite result proves that the existing criterion passes on the final run, but it does not by itself prove the new SQLite implementation caused that particular number.

The causal performance evidence comes from the separate Phase 3 benchmark, which directly exercises `EventWriter` and `SQLiteEventStore` on ext4 under WAL/FULL durability and passed five consecutive runs. This distinction prevents an environmental pass from being misrepresented as implementation evidence.

## Integrity of comparison

- Architecture documents: unchanged.
- Validation engine: unchanged and checksum-verified.
- PERF threshold configuration: unchanged and checksum-verified.
- No failed or tuning run was deleted or presented as a pass.

