# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:56:32.272289Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 43.326 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.059 | 0.096 | 0.252 | 0.020 |
| write | 300 | 0.004 | 0.009 | 0.020 | 0.033 | 0.003 |
| flush | 300 | 0.002 | 0.004 | 0.007 | 0.011 | 0.001 |
| fsync | 300 | 0.001 | 0.002 | 0.003 | 0.072 | 0.004 |
| commit | 300 | 0.009 | 0.017 | 0.032 | 0.042 | 0.004 |
| close | 300 | 0.009 | 0.014 | 0.030 | 0.081 | 0.006 |
| accept_immediate | 300 | 0.373 | 0.790 | 1.093 | 1.426 | 0.189 |
| accept_group_commit | 300 | 30.292 | 40.644 | 43.326 | 43.393 | 7.286 |
| batch_commit | 10 | 1.283 | 3.018 | 3.018 | 3.018 | 0.711 |
| projection | 100 | 0.140 | 0.322 | 0.392 | 0.530 | 0.077 |
| replay | 100 | 26.999 | 37.967 | 54.917 | 69.485 | 6.483 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
