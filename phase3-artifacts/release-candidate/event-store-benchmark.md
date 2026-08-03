# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:01:16.883311Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 33.343 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.031 | 0.075 | 0.124 | 0.155 | 0.020 |
| write | 300 | 0.004 | 0.023 | 0.029 | 0.053 | 0.006 |
| flush | 300 | 0.002 | 0.006 | 0.023 | 0.113 | 0.007 |
| fsync | 300 | 0.001 | 0.002 | 0.015 | 0.022 | 0.002 |
| commit | 300 | 0.009 | 0.031 | 0.056 | 0.154 | 0.013 |
| close | 300 | 0.009 | 0.021 | 0.041 | 0.132 | 0.009 |
| accept_immediate | 300 | 0.333 | 0.668 | 0.857 | 1.505 | 0.159 |
| accept_group_commit | 300 | 22.937 | 33.097 | 33.343 | 33.405 | 5.239 |
| batch_commit | 5 | 1.307 | 1.409 | 1.409 | 1.409 | 0.195 |
| projection | 100 | 0.136 | 0.289 | 0.353 | 0.532 | 0.069 |
| replay | 100 | 30.368 | 40.732 | 50.348 | 107.414 | 8.825 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
