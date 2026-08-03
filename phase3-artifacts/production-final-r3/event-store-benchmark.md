# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:42.240240Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 34.502 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.072 | 0.102 | 0.117 | 0.015 |
| write | 300 | 0.004 | 0.004 | 0.010 | 0.031 | 0.002 |
| flush | 300 | 0.002 | 0.003 | 0.004 | 0.025 | 0.001 |
| fsync | 300 | 0.001 | 0.001 | 0.002 | 0.005 | 0.000 |
| commit | 300 | 0.009 | 0.025 | 0.035 | 0.116 | 0.009 |
| close | 300 | 0.009 | 0.028 | 0.036 | 0.145 | 0.010 |
| accept_immediate | 300 | 0.305 | 0.609 | 0.789 | 1.114 | 0.129 |
| accept_group_commit | 300 | 22.055 | 34.110 | 34.502 | 34.581 | 5.678 |
| batch_commit | 5 | 1.261 | 7.824 | 7.824 | 7.824 | 2.978 |
| projection | 100 | 0.124 | 0.343 | 0.394 | 0.474 | 0.081 |
| replay | 100 | 27.452 | 32.650 | 34.537 | 36.257 | 2.290 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
