# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:54:39.741331Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 44.572 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.031 | 0.073 | 0.121 | 0.324 | 0.025 |
| write | 300 | 0.004 | 0.011 | 0.024 | 0.084 | 0.006 |
| flush | 300 | 0.002 | 0.004 | 0.008 | 0.012 | 0.001 |
| fsync | 300 | 0.001 | 0.002 | 0.003 | 0.038 | 0.002 |
| commit | 300 | 0.009 | 0.015 | 0.023 | 0.047 | 0.003 |
| close | 300 | 0.009 | 0.022 | 0.034 | 0.051 | 0.005 |
| accept_immediate | 300 | 0.337 | 0.704 | 0.988 | 1.702 | 0.187 |
| accept_group_commit | 300 | 30.505 | 40.738 | 44.572 | 44.635 | 9.042 |
| batch_commit | 10 | 1.569 | 3.603 | 3.603 | 3.603 | 0.896 |
| projection | 100 | 0.148 | 0.330 | 0.381 | 0.427 | 0.073 |
| replay | 100 | 28.383 | 39.538 | 48.474 | 49.306 | 4.882 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
