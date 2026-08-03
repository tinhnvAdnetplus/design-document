# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:03:00.710309Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 70.477 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.044 | 0.072 | 0.095 | 0.160 | 0.013 |
| write | 300 | 0.045 | 0.076 | 0.099 | 0.162 | 0.016 |
| flush | 300 | 0.067 | 0.115 | 0.150 | 0.152 | 0.022 |
| fsync | 300 | 6.844 | 7.882 | 8.181 | 10.791 | 0.636 |
| commit | 300 | 7.859 | 10.817 | 14.557 | 15.960 | 1.549 |
| close | 300 | 0.011 | 0.018 | 0.029 | 0.047 | 0.004 |
| accept_immediate | 300 | 5.324 | 10.680 | 20.343 | 39.585 | 3.800 |
| accept_group_commit | 300 | 45.832 | 69.975 | 70.477 | 70.603 | 11.317 |
| batch_commit | 2 | 11.934 | 12.033 | 12.033 | 12.033 | 0.140 |
| projection | 100 | 0.126 | 0.323 | 0.533 | 0.545 | 0.077 |
| replay | 100 | 27.701 | 34.950 | 37.868 | 53.527 | 4.026 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
