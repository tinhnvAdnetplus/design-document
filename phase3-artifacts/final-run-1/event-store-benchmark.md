# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:20.837210Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 39.799 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.048 | 0.082 | 0.131 | 0.293 | 0.023 |
| write | 300 | 0.004 | 0.015 | 0.053 | 0.084 | 0.008 |
| flush | 300 | 0.002 | 0.004 | 0.009 | 0.100 | 0.006 |
| fsync | 300 | 0.001 | 0.002 | 0.004 | 0.009 | 0.001 |
| commit | 300 | 0.013 | 0.036 | 0.093 | 0.232 | 0.018 |
| close | 300 | 0.015 | 0.026 | 0.053 | 0.707 | 0.041 |
| accept_immediate | 300 | 0.297 | 0.789 | 1.084 | 1.731 | 0.204 |
| accept_group_commit | 300 | 27.752 | 36.508 | 39.799 | 39.895 | 6.468 |
| batch_commit | 10 | 1.088 | 7.814 | 7.814 | 7.814 | 2.151 |
| projection | 100 | 0.159 | 0.384 | 0.543 | 1.128 | 0.123 |
| replay | 100 | 30.104 | 39.762 | 64.333 | 78.703 | 6.989 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
