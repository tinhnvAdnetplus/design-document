# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:01.319213Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 39.004 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.029 | 0.067 | 0.087 | 0.102 | 0.013 |
| write | 300 | 0.004 | 0.021 | 0.036 | 0.049 | 0.007 |
| flush | 300 | 0.002 | 0.006 | 0.022 | 0.043 | 0.004 |
| fsync | 300 | 0.001 | 0.003 | 0.017 | 0.037 | 0.003 |
| commit | 300 | 0.009 | 0.020 | 0.029 | 0.043 | 0.004 |
| close | 300 | 0.009 | 0.023 | 0.036 | 0.059 | 0.006 |
| accept_immediate | 300 | 0.363 | 0.699 | 0.988 | 1.106 | 0.145 |
| accept_group_commit | 300 | 28.980 | 38.520 | 39.004 | 39.068 | 4.535 |
| batch_commit | 3 | 2.893 | 3.116 | 3.116 | 3.116 | 1.084 |
| projection | 100 | 0.130 | 0.326 | 0.402 | 0.556 | 0.084 |
| replay | 100 | 28.646 | 32.773 | 36.575 | 37.333 | 2.221 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
