# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:07:01.053404Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 28.172 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.101 | 0.129 | 0.153 | 0.020 |
| write | 150 | 0.039 | 0.082 | 0.111 | 0.270 | 0.024 |
| flush | 150 | 0.057 | 0.100 | 0.157 | 0.182 | 0.020 |
| fsync | 150 | 8.739 | 10.123 | 14.921 | 21.988 | 1.419 |
| commit | 150 | 9.466 | 10.839 | 11.150 | 11.274 | 0.808 |
| close | 150 | 0.010 | 0.026 | 0.034 | 0.042 | 0.006 |
| accept_immediate | 150 | 9.612 | 11.465 | 12.626 | 22.855 | 2.299 |
| accept_group_commit | 150 | 25.270 | 27.989 | 28.172 | 28.280 | 1.867 |
| batch_commit | 1 | 12.173 | 12.173 | 12.173 | 12.173 | 0.000 |
| projection | 100 | 0.055 | 0.127 | 0.166 | 0.187 | 0.027 |
| replay | 100 | 5.501 | 7.243 | 7.986 | 8.469 | 0.908 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
