# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:54.373545Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 45.750 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.093 | 0.176 | 0.406 | 0.038 |
| write | 300 | 0.010 | 0.031 | 0.101 | 0.220 | 0.022 |
| flush | 300 | 0.003 | 0.011 | 0.027 | 0.037 | 0.004 |
| fsync | 300 | 0.002 | 0.004 | 0.017 | 0.108 | 0.008 |
| commit | 300 | 0.015 | 0.036 | 0.136 | 0.565 | 0.038 |
| close | 300 | 0.009 | 0.030 | 0.051 | 0.894 | 0.052 |
| accept_immediate | 300 | 0.384 | 0.899 | 1.878 | 2.334 | 0.282 |
| accept_group_commit | 300 | 35.836 | 45.329 | 45.750 | 45.809 | 7.683 |
| batch_commit | 3 | 4.151 | 4.919 | 4.919 | 4.919 | 2.019 |
| projection | 100 | 0.135 | 0.272 | 0.470 | 1.309 | 0.131 |
| replay | 100 | 27.922 | 32.552 | 43.672 | 48.077 | 3.649 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
