# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:50.901042Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 38.526 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.095 | 0.224 | 0.722 | 0.054 |
| write | 300 | 0.010 | 0.024 | 0.048 | 0.182 | 0.013 |
| flush | 300 | 0.003 | 0.008 | 0.024 | 0.054 | 0.005 |
| fsync | 300 | 0.002 | 0.003 | 0.018 | 0.033 | 0.003 |
| commit | 300 | 0.009 | 0.029 | 0.062 | 0.145 | 0.012 |
| close | 300 | 0.009 | 0.030 | 0.094 | 0.117 | 0.014 |
| accept_immediate | 300 | 0.494 | 1.193 | 7.795 | 9.401 | 1.127 |
| accept_group_commit | 300 | 30.355 | 38.223 | 38.526 | 38.687 | 7.738 |
| batch_commit | 5 | 1.653 | 2.219 | 2.219 | 2.219 | 0.385 |
| projection | 100 | 0.154 | 0.325 | 0.417 | 0.575 | 0.081 |
| replay | 100 | 31.640 | 49.992 | 69.456 | 79.502 | 9.656 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
