# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:25.916572Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 46.584 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.042 | 0.097 | 0.132 | 0.239 | 0.022 |
| write | 300 | 0.042 | 0.085 | 0.117 | 0.141 | 0.017 |
| flush | 300 | 0.059 | 0.094 | 0.117 | 0.152 | 0.016 |
| fsync | 300 | 6.818 | 7.915 | 8.626 | 10.694 | 0.660 |
| commit | 300 | 8.938 | 10.180 | 13.754 | 18.059 | 1.288 |
| close | 300 | 0.010 | 0.022 | 0.041 | 0.067 | 0.007 |
| accept_immediate | 300 | 5.000 | 10.840 | 14.678 | 23.342 | 3.016 |
| accept_group_commit | 300 | 35.887 | 46.319 | 46.584 | 46.673 | 8.160 |
| batch_commit | 2 | 11.119 | 11.307 | 11.307 | 11.307 | 0.266 |
| projection | 100 | 0.141 | 0.275 | 0.396 | 0.704 | 0.077 |
| replay | 100 | 11.178 | 14.289 | 20.725 | 20.839 | 2.038 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
