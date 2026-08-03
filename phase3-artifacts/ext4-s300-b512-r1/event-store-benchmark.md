# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:37.122134Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 46.069 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.073 | 0.165 | 0.280 | 0.536 | 0.050 |
| write | 300 | 0.039 | 0.075 | 0.101 | 0.140 | 0.016 |
| flush | 300 | 0.056 | 0.105 | 0.148 | 0.169 | 0.021 |
| fsync | 300 | 4.842 | 6.925 | 12.544 | 40.884 | 2.775 |
| commit | 300 | 7.518 | 10.267 | 26.949 | 54.741 | 4.370 |
| close | 300 | 0.017 | 0.037 | 0.086 | 1.622 | 0.094 |
| accept_immediate | 300 | 4.893 | 10.762 | 38.768 | 50.959 | 5.771 |
| accept_group_commit | 300 | 30.731 | 45.811 | 46.069 | 46.148 | 7.909 |
| batch_commit | 2 | 11.517 | 12.013 | 12.013 | 12.013 | 0.702 |
| projection | 100 | 0.146 | 0.361 | 0.548 | 0.561 | 0.091 |
| replay | 100 | 11.612 | 15.083 | 15.821 | 15.932 | 1.666 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
