# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:38.970544Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 41.144 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.029 | 0.077 | 0.122 | 0.180 | 0.020 |
| write | 300 | 0.004 | 0.020 | 0.037 | 0.107 | 0.009 |
| flush | 300 | 0.002 | 0.006 | 0.062 | 0.112 | 0.011 |
| fsync | 300 | 0.001 | 0.003 | 0.009 | 0.023 | 0.002 |
| commit | 300 | 0.009 | 0.023 | 0.044 | 0.115 | 0.010 |
| close | 300 | 0.009 | 0.028 | 0.045 | 0.106 | 0.009 |
| accept_immediate | 300 | 0.312 | 0.690 | 0.957 | 1.359 | 0.162 |
| accept_group_commit | 300 | 32.045 | 37.703 | 41.144 | 41.204 | 6.429 |
| batch_commit | 5 | 1.044 | 1.604 | 1.604 | 1.604 | 0.272 |
| projection | 100 | 0.155 | 0.321 | 0.389 | 0.419 | 0.070 |
| replay | 100 | 27.841 | 34.392 | 40.781 | 68.321 | 4.805 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
