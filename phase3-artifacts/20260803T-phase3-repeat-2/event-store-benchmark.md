# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:56:28.915776Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 39.911 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.053 | 0.131 | 0.272 | 0.862 | 0.061 |
| write | 300 | 0.004 | 0.008 | 0.023 | 0.064 | 0.005 |
| flush | 300 | 0.002 | 0.004 | 0.020 | 0.021 | 0.003 |
| fsync | 300 | 0.001 | 0.001 | 0.006 | 0.053 | 0.003 |
| commit | 300 | 0.009 | 0.017 | 0.035 | 0.036 | 0.005 |
| close | 300 | 0.015 | 0.038 | 0.064 | 0.256 | 0.020 |
| accept_immediate | 300 | 0.400 | 0.773 | 0.991 | 1.160 | 0.175 |
| accept_group_commit | 300 | 27.897 | 36.439 | 39.911 | 39.982 | 6.979 |
| batch_commit | 10 | 1.020 | 7.169 | 7.169 | 7.169 | 1.958 |
| projection | 100 | 0.151 | 0.366 | 0.565 | 0.726 | 0.107 |
| replay | 100 | 28.470 | 42.172 | 99.533 | 120.105 | 12.789 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
