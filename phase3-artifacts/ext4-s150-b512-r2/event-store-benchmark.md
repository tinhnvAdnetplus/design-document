# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:19.767811Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 33.218 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.082 | 0.201 | 0.376 | 0.035 |
| write | 150 | 0.040 | 0.077 | 0.105 | 0.111 | 0.013 |
| flush | 150 | 0.059 | 0.102 | 0.227 | 0.347 | 0.031 |
| fsync | 150 | 6.842 | 8.694 | 10.986 | 13.485 | 1.012 |
| commit | 150 | 7.024 | 8.666 | 9.962 | 48.507 | 3.449 |
| close | 150 | 0.010 | 0.020 | 0.063 | 0.100 | 0.010 |
| accept_immediate | 150 | 8.756 | 10.649 | 19.972 | 22.559 | 2.348 |
| accept_group_commit | 150 | 31.384 | 33.059 | 33.218 | 33.318 | 1.073 |
| batch_commit | 1 | 14.884 | 14.884 | 14.884 | 14.884 | 0.000 |
| projection | 100 | 0.068 | 0.184 | 0.238 | 2.853 | 0.280 |
| replay | 100 | 5.891 | 11.783 | 18.115 | 19.926 | 2.931 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
