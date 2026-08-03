# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:01.143354Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 29.663 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.053 | 0.113 | 0.280 | 0.521 | 0.046 |
| write | 150 | 0.039 | 0.062 | 0.077 | 0.085 | 0.009 |
| flush | 150 | 0.058 | 0.088 | 0.128 | 0.148 | 0.015 |
| fsync | 150 | 6.858 | 7.912 | 10.100 | 11.100 | 0.734 |
| commit | 150 | 8.998 | 11.000 | 31.561 | 32.941 | 3.632 |
| close | 150 | 0.012 | 0.029 | 0.107 | 0.120 | 0.014 |
| accept_immediate | 150 | 9.446 | 10.985 | 28.634 | 44.869 | 4.299 |
| accept_group_commit | 150 | 18.679 | 29.531 | 29.663 | 29.694 | 3.986 |
| batch_commit | 2 | 9.827 | 10.944 | 10.944 | 10.944 | 1.580 |
| projection | 100 | 0.054 | 0.121 | 0.192 | 0.213 | 0.030 |
| replay | 100 | 5.191 | 7.215 | 8.346 | 8.503 | 0.932 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
