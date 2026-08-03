# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:24.541270Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 36.150 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.056 | 0.108 | 0.149 | 0.169 | 0.024 |
| write | 150 | 0.043 | 0.093 | 0.133 | 0.167 | 0.022 |
| flush | 150 | 0.067 | 0.108 | 0.138 | 0.141 | 0.019 |
| fsync | 150 | 6.859 | 7.925 | 8.669 | 9.552 | 0.598 |
| commit | 150 | 7.788 | 10.043 | 10.295 | 10.905 | 0.994 |
| close | 150 | 0.010 | 0.034 | 0.059 | 0.060 | 0.010 |
| accept_immediate | 150 | 9.366 | 10.798 | 19.343 | 61.902 | 4.823 |
| accept_group_commit | 150 | 24.081 | 35.850 | 36.150 | 36.230 | 6.569 |
| batch_commit | 2 | 11.191 | 11.731 | 11.731 | 11.731 | 0.764 |
| projection | 100 | 0.061 | 0.173 | 0.190 | 0.236 | 0.041 |
| replay | 100 | 5.799 | 10.759 | 11.302 | 14.018 | 1.799 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
