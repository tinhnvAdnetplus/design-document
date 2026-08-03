# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:05.803492Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 30.951 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.075 | 0.154 | 0.233 | 0.021 |
| write | 150 | 0.041 | 0.083 | 0.109 | 0.119 | 0.016 |
| flush | 150 | 0.061 | 0.094 | 0.128 | 0.209 | 0.019 |
| fsync | 150 | 6.806 | 7.629 | 9.946 | 11.198 | 0.654 |
| commit | 150 | 8.144 | 9.966 | 10.811 | 11.969 | 1.207 |
| close | 150 | 0.010 | 0.020 | 0.030 | 0.048 | 0.005 |
| accept_immediate | 150 | 9.046 | 10.583 | 11.450 | 22.858 | 2.164 |
| accept_group_commit | 150 | 19.162 | 30.822 | 30.951 | 30.976 | 4.334 |
| batch_commit | 2 | 9.941 | 10.068 | 10.068 | 10.068 | 0.180 |
| projection | 100 | 0.057 | 0.155 | 0.176 | 0.205 | 0.037 |
| replay | 100 | 5.288 | 7.796 | 9.904 | 9.973 | 1.174 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
