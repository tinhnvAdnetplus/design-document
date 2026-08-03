# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:53.969009Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 43.745 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.049 | 0.114 | 0.231 | 0.331 | 0.034 |
| write | 300 | 0.041 | 0.081 | 0.117 | 0.146 | 0.016 |
| flush | 300 | 0.060 | 0.098 | 0.130 | 0.169 | 0.018 |
| fsync | 300 | 6.845 | 7.884 | 11.911 | 35.697 | 1.962 |
| commit | 300 | 7.058 | 8.110 | 8.943 | 10.814 | 0.570 |
| close | 300 | 0.010 | 0.029 | 0.058 | 0.134 | 0.012 |
| accept_immediate | 300 | 4.913 | 9.706 | 14.732 | 20.920 | 2.471 |
| accept_group_commit | 300 | 31.640 | 43.418 | 43.745 | 43.824 | 5.803 |
| batch_commit | 2 | 12.294 | 13.976 | 13.976 | 13.976 | 2.378 |
| projection | 100 | 0.175 | 0.384 | 0.462 | 0.588 | 0.093 |
| replay | 100 | 12.247 | 19.776 | 23.324 | 23.503 | 3.271 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
