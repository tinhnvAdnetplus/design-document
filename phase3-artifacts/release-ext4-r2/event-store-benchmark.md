# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:07:05.985930Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 25.121 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.046 | 0.121 | 0.220 | 0.434 | 0.041 |
| write | 150 | 0.047 | 0.078 | 0.096 | 0.156 | 0.016 |
| flush | 150 | 0.066 | 0.099 | 0.126 | 0.137 | 0.016 |
| fsync | 150 | 6.854 | 8.013 | 8.707 | 9.082 | 0.589 |
| commit | 150 | 9.028 | 10.511 | 10.940 | 10.992 | 0.671 |
| close | 150 | 0.011 | 0.024 | 0.095 | 0.156 | 0.014 |
| accept_immediate | 150 | 9.421 | 10.938 | 19.883 | 22.285 | 2.444 |
| accept_group_commit | 150 | 23.041 | 24.957 | 25.121 | 25.210 | 1.086 |
| batch_commit | 1 | 11.693 | 11.693 | 11.693 | 11.693 | 0.000 |
| projection | 100 | 0.056 | 0.163 | 0.252 | 0.265 | 0.048 |
| replay | 100 | 5.524 | 9.403 | 12.397 | 12.444 | 1.742 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
