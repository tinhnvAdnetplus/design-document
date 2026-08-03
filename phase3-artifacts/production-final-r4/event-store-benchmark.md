# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:45.944002Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 33.606 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.031 | 0.082 | 0.126 | 0.225 | 0.023 |
| write | 300 | 0.004 | 0.016 | 0.023 | 0.052 | 0.005 |
| flush | 300 | 0.002 | 0.003 | 0.009 | 0.024 | 0.002 |
| fsync | 300 | 0.001 | 0.001 | 0.003 | 0.014 | 0.001 |
| commit | 300 | 0.013 | 0.029 | 0.047 | 0.083 | 0.009 |
| close | 300 | 0.009 | 0.030 | 0.059 | 0.180 | 0.014 |
| accept_immediate | 300 | 0.364 | 0.668 | 0.817 | 1.032 | 0.136 |
| accept_group_commit | 300 | 26.584 | 33.337 | 33.606 | 33.674 | 5.950 |
| batch_commit | 5 | 1.131 | 6.179 | 6.179 | 6.179 | 2.280 |
| projection | 100 | 0.142 | 0.364 | 0.477 | 0.554 | 0.092 |
| replay | 100 | 29.366 | 46.919 | 70.687 | 87.324 | 9.132 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
