# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:55:45.102894Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 40.835 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.028 | 0.054 | 0.114 | 0.158 | 0.015 |
| write | 300 | 0.004 | 0.022 | 0.033 | 0.136 | 0.011 |
| flush | 300 | 0.002 | 0.004 | 0.020 | 0.023 | 0.003 |
| fsync | 300 | 0.001 | 0.002 | 0.020 | 0.042 | 0.004 |
| commit | 300 | 0.009 | 0.027 | 0.094 | 0.217 | 0.018 |
| close | 300 | 0.009 | 0.013 | 0.027 | 0.069 | 0.005 |
| accept_immediate | 300 | 0.323 | 0.705 | 1.077 | 1.319 | 0.165 |
| accept_group_commit | 300 | 27.682 | 38.335 | 40.835 | 40.926 | 7.836 |
| batch_commit | 10 | 1.166 | 5.168 | 5.168 | 5.168 | 1.306 |
| projection | 100 | 0.131 | 0.287 | 0.357 | 0.469 | 0.066 |
| replay | 100 | 26.909 | 34.440 | 42.634 | 76.811 | 6.115 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
