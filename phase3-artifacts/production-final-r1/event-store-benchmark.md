# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:35.610723Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 31.178 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.063 | 0.103 | 0.153 | 0.016 |
| write | 300 | 0.004 | 0.017 | 0.023 | 0.031 | 0.004 |
| flush | 300 | 0.002 | 0.003 | 0.015 | 0.020 | 0.002 |
| fsync | 300 | 0.001 | 0.001 | 0.019 | 0.044 | 0.003 |
| commit | 300 | 0.009 | 0.028 | 0.059 | 0.079 | 0.009 |
| close | 300 | 0.009 | 0.020 | 0.037 | 0.053 | 0.005 |
| accept_immediate | 300 | 0.320 | 0.642 | 0.853 | 1.090 | 0.137 |
| accept_group_commit | 300 | 21.603 | 30.935 | 31.178 | 31.244 | 4.733 |
| batch_commit | 5 | 1.100 | 7.638 | 7.638 | 7.638 | 2.984 |
| projection | 100 | 0.141 | 0.311 | 0.407 | 0.563 | 0.078 |
| replay | 100 | 28.090 | 37.679 | 43.147 | 73.080 | 5.515 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
