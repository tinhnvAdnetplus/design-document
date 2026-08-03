# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:02:30.058555Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 62.702 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.042 | 0.089 | 0.116 | 0.174 | 0.018 |
| write | 300 | 0.058 | 0.108 | 0.163 | 0.268 | 0.025 |
| flush | 300 | 0.074 | 0.129 | 0.243 | 0.791 | 0.051 |
| fsync | 300 | 8.591 | 12.906 | 28.674 | 182.358 | 10.503 |
| commit | 300 | 9.917 | 11.198 | 14.140 | 19.322 | 1.170 |
| close | 300 | 0.010 | 0.025 | 0.053 | 0.136 | 0.011 |
| accept_immediate | 300 | 4.960 | 10.778 | 17.750 | 24.638 | 3.050 |
| accept_group_commit | 300 | 46.747 | 62.447 | 62.702 | 62.850 | 10.911 |
| batch_commit | 3 | 11.217 | 11.969 | 11.969 | 11.969 | 1.383 |
| projection | 100 | 0.152 | 0.327 | 0.374 | 0.509 | 0.073 |
| replay | 100 | 28.586 | 39.043 | 50.503 | 94.636 | 7.945 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
