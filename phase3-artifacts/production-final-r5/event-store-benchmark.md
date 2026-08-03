# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:59:49.368580Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 30.778 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.031 | 0.074 | 0.114 | 0.135 | 0.017 |
| write | 300 | 0.005 | 0.015 | 0.030 | 0.090 | 0.007 |
| flush | 300 | 0.002 | 0.004 | 0.010 | 0.027 | 0.002 |
| fsync | 300 | 0.001 | 0.003 | 0.003 | 0.005 | 0.001 |
| commit | 300 | 0.010 | 0.024 | 0.039 | 0.108 | 0.008 |
| close | 300 | 0.009 | 0.025 | 0.039 | 0.056 | 0.006 |
| accept_immediate | 300 | 0.311 | 0.746 | 1.112 | 1.308 | 0.186 |
| accept_group_commit | 300 | 24.663 | 30.520 | 30.778 | 30.846 | 5.211 |
| batch_commit | 5 | 1.058 | 5.478 | 5.478 | 5.478 | 2.012 |
| projection | 100 | 0.142 | 0.326 | 0.392 | 0.495 | 0.072 |
| replay | 100 | 27.867 | 33.461 | 52.945 | 58.996 | 4.746 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
