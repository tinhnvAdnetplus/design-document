# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:17.194151Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 49.426 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.043 | 0.068 | 0.122 | 0.141 | 0.014 |
| write | 300 | 0.039 | 0.081 | 0.120 | 0.151 | 0.017 |
| flush | 300 | 0.059 | 0.113 | 0.144 | 0.308 | 0.025 |
| fsync | 300 | 6.889 | 8.788 | 11.765 | 14.934 | 0.985 |
| commit | 300 | 9.026 | 10.298 | 13.009 | 13.958 | 0.871 |
| close | 300 | 0.010 | 0.014 | 0.028 | 0.031 | 0.003 |
| accept_immediate | 300 | 4.972 | 9.777 | 10.683 | 27.088 | 2.853 |
| accept_group_commit | 300 | 35.694 | 49.099 | 49.426 | 49.633 | 8.644 |
| batch_commit | 3 | 13.895 | 18.115 | 18.115 | 18.115 | 4.645 |
| projection | 100 | 0.133 | 0.350 | 0.428 | 0.445 | 0.069 |
| replay | 100 | 10.659 | 17.625 | 19.099 | 23.314 | 2.407 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
