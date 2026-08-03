# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:56.189233Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 41.953 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.043 | 0.080 | 0.095 | 0.112 | 0.012 |
| write | 150 | 0.039 | 0.077 | 0.108 | 0.314 | 0.026 |
| flush | 150 | 0.056 | 0.109 | 0.158 | 0.159 | 0.022 |
| fsync | 150 | 6.791 | 7.754 | 8.716 | 9.639 | 0.611 |
| commit | 150 | 7.023 | 8.075 | 8.910 | 10.884 | 0.713 |
| close | 150 | 0.010 | 0.015 | 0.028 | 0.080 | 0.006 |
| accept_immediate | 150 | 7.815 | 9.866 | 10.895 | 21.838 | 1.989 |
| accept_group_commit | 150 | 29.160 | 41.823 | 41.953 | 41.977 | 9.217 |
| batch_commit | 3 | 10.434 | 11.849 | 11.849 | 11.849 | 1.130 |
| projection | 100 | 0.054 | 0.142 | 0.179 | 0.221 | 0.034 |
| replay | 100 | 5.226 | 7.143 | 9.342 | 9.628 | 1.066 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
