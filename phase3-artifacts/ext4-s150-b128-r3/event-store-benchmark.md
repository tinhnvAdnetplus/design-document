# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:10.399275Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 30.543 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.115 | 0.278 | 0.319 | 0.036 |
| write | 150 | 0.042 | 0.075 | 0.122 | 0.157 | 0.017 |
| flush | 150 | 0.061 | 0.100 | 0.168 | 0.981 | 0.077 |
| fsync | 150 | 6.786 | 7.857 | 10.596 | 11.437 | 0.772 |
| commit | 150 | 7.014 | 9.768 | 10.240 | 13.314 | 1.127 |
| close | 150 | 0.011 | 0.017 | 0.036 | 0.083 | 0.007 |
| accept_immediate | 150 | 9.503 | 10.795 | 17.980 | 21.610 | 2.290 |
| accept_group_commit | 150 | 19.249 | 30.414 | 30.543 | 30.568 | 4.308 |
| batch_commit | 2 | 9.814 | 10.589 | 10.589 | 10.589 | 1.096 |
| projection | 100 | 0.057 | 0.116 | 0.193 | 0.202 | 0.031 |
| replay | 100 | 5.288 | 8.092 | 9.298 | 9.322 | 1.261 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
