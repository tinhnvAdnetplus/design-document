# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:07:20.071062Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 26.541 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.080 | 0.152 | 0.240 | 0.022 |
| write | 150 | 0.039 | 0.078 | 0.103 | 0.154 | 0.016 |
| flush | 150 | 0.059 | 0.100 | 0.141 | 0.144 | 0.017 |
| fsync | 150 | 6.869 | 7.920 | 30.235 | 60.474 | 5.044 |
| commit | 150 | 7.145 | 9.683 | 11.242 | 17.315 | 1.348 |
| close | 150 | 0.010 | 0.019 | 0.023 | 0.026 | 0.003 |
| accept_immediate | 150 | 9.481 | 10.877 | 11.665 | 24.303 | 2.429 |
| accept_group_commit | 150 | 24.029 | 26.348 | 26.541 | 26.633 | 1.346 |
| batch_commit | 1 | 11.295 | 11.295 | 11.295 | 11.295 | 0.000 |
| projection | 100 | 0.060 | 0.193 | 0.257 | 0.654 | 0.073 |
| replay | 100 | 5.628 | 8.498 | 9.027 | 9.377 | 1.274 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
