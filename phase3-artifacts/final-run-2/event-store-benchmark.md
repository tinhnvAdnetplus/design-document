# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:24.395682Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 52.164 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.068 | 0.114 | 0.229 | 0.019 |
| write | 300 | 0.004 | 0.009 | 0.026 | 0.049 | 0.004 |
| flush | 300 | 0.002 | 0.003 | 0.005 | 0.023 | 0.001 |
| fsync | 300 | 0.001 | 0.001 | 0.002 | 0.005 | 0.000 |
| commit | 300 | 0.009 | 0.022 | 0.040 | 0.083 | 0.008 |
| close | 300 | 0.009 | 0.022 | 0.032 | 0.143 | 0.009 |
| accept_immediate | 300 | 0.374 | 0.730 | 0.942 | 1.270 | 0.167 |
| accept_group_commit | 300 | 37.500 | 49.544 | 52.164 | 52.233 | 9.481 |
| batch_commit | 10 | 1.137 | 12.724 | 12.724 | 12.724 | 3.665 |
| projection | 100 | 0.135 | 0.250 | 0.521 | 0.555 | 0.075 |
| replay | 100 | 29.405 | 35.357 | 46.994 | 47.729 | 4.092 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
