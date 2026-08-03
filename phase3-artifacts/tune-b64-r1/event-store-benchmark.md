# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:43.023050Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 37.053 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.077 | 0.113 | 0.166 | 0.019 |
| write | 300 | 0.004 | 0.026 | 0.042 | 0.064 | 0.008 |
| flush | 300 | 0.002 | 0.006 | 0.020 | 0.025 | 0.003 |
| fsync | 300 | 0.001 | 0.003 | 0.022 | 0.027 | 0.003 |
| commit | 300 | 0.009 | 0.022 | 0.029 | 0.056 | 0.005 |
| close | 300 | 0.009 | 0.029 | 0.040 | 0.080 | 0.008 |
| accept_immediate | 300 | 0.358 | 0.804 | 1.069 | 1.237 | 0.177 |
| accept_group_commit | 300 | 28.937 | 36.921 | 37.053 | 37.133 | 6.689 |
| batch_commit | 5 | 1.522 | 2.159 | 2.159 | 2.159 | 0.309 |
| projection | 100 | 0.135 | 0.323 | 0.481 | 0.488 | 0.078 |
| replay | 100 | 28.515 | 34.335 | 36.950 | 38.169 | 2.573 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
