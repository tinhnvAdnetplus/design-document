# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:02:03.448933Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 87.217 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.042 | 0.111 | 0.188 | 0.217 | 0.028 |
| write | 300 | 0.046 | 0.107 | 0.146 | 0.220 | 0.023 |
| flush | 300 | 0.065 | 0.131 | 0.186 | 0.375 | 0.032 |
| fsync | 300 | 7.789 | 9.842 | 19.774 | 35.698 | 2.684 |
| commit | 300 | 9.087 | 10.678 | 11.107 | 13.685 | 0.783 |
| close | 300 | 0.010 | 0.032 | 0.052 | 0.116 | 0.011 |
| accept_immediate | 300 | 4.956 | 11.621 | 22.678 | 48.617 | 4.219 |
| accept_group_commit | 300 | 58.424 | 86.955 | 87.217 | 87.294 | 19.646 |
| batch_commit | 5 | 12.761 | 18.351 | 18.351 | 18.351 | 3.086 |
| projection | 100 | 0.156 | 0.445 | 0.764 | 6.314 | 0.621 |
| replay | 100 | 30.448 | 59.188 | 68.657 | 78.287 | 9.972 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
