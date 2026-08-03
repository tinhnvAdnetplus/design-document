# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:15.096738Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 29.238 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.042 | 0.110 | 0.178 | 0.226 | 0.026 |
| write | 150 | 0.042 | 0.074 | 0.103 | 0.135 | 0.015 |
| flush | 150 | 0.057 | 0.103 | 0.129 | 0.157 | 0.020 |
| fsync | 150 | 6.842 | 8.049 | 12.695 | 13.976 | 1.025 |
| commit | 150 | 7.135 | 9.884 | 23.158 | 38.085 | 3.283 |
| close | 150 | 0.010 | 0.036 | 0.046 | 0.053 | 0.009 |
| accept_immediate | 150 | 7.736 | 10.693 | 30.733 | 49.801 | 4.682 |
| accept_group_commit | 150 | 27.489 | 29.094 | 29.238 | 29.316 | 1.115 |
| batch_commit | 1 | 13.461 | 13.461 | 13.461 | 13.461 | 0.000 |
| projection | 100 | 0.056 | 0.131 | 0.178 | 0.179 | 0.032 |
| replay | 100 | 5.382 | 6.990 | 8.541 | 8.807 | 0.994 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
