# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:51.868018Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 40.020 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.044 | 0.091 | 0.158 | 0.178 | 0.020 |
| write | 150 | 0.042 | 0.086 | 0.150 | 0.163 | 0.020 |
| flush | 150 | 0.058 | 0.113 | 0.172 | 0.277 | 0.028 |
| fsync | 150 | 6.776 | 7.710 | 8.019 | 9.732 | 0.580 |
| commit | 150 | 6.992 | 8.074 | 8.558 | 11.037 | 0.624 |
| close | 150 | 0.010 | 0.018 | 0.034 | 0.037 | 0.004 |
| accept_immediate | 150 | 8.832 | 10.117 | 11.807 | 21.827 | 2.166 |
| accept_group_commit | 150 | 27.857 | 39.841 | 40.020 | 40.045 | 8.688 |
| batch_commit | 3 | 9.490 | 10.706 | 10.706 | 10.706 | 1.131 |
| projection | 100 | 0.056 | 0.149 | 0.173 | 0.331 | 0.040 |
| replay | 100 | 5.589 | 7.840 | 9.216 | 14.867 | 1.393 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
