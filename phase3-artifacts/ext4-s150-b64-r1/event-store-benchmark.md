# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:47.405194Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 47.881 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.082 | 0.160 | 0.201 | 0.022 |
| write | 150 | 0.041 | 0.070 | 0.092 | 0.100 | 0.012 |
| flush | 150 | 0.061 | 0.098 | 0.114 | 0.116 | 0.016 |
| fsync | 150 | 8.038 | 9.950 | 28.461 | 35.125 | 3.356 |
| commit | 150 | 9.006 | 10.215 | 11.063 | 11.809 | 0.718 |
| close | 150 | 0.010 | 0.020 | 0.030 | 0.041 | 0.005 |
| accept_immediate | 150 | 9.442 | 11.841 | 20.559 | 21.453 | 2.541 |
| accept_group_commit | 150 | 34.182 | 47.753 | 47.881 | 47.904 | 9.702 |
| batch_commit | 3 | 12.220 | 14.429 | 14.429 | 14.429 | 2.468 |
| projection | 100 | 0.060 | 0.172 | 0.282 | 0.413 | 0.055 |
| replay | 100 | 5.496 | 8.417 | 11.240 | 14.366 | 1.667 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
