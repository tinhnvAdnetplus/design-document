# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:46.791256Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 43.532 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.029 | 0.066 | 0.083 | 0.107 | 0.013 |
| write | 300 | 0.004 | 0.005 | 0.014 | 0.059 | 0.004 |
| flush | 300 | 0.002 | 0.003 | 0.005 | 0.023 | 0.001 |
| fsync | 300 | 0.001 | 0.001 | 0.002 | 0.027 | 0.002 |
| commit | 300 | 0.009 | 0.015 | 0.018 | 0.034 | 0.002 |
| close | 300 | 0.009 | 0.027 | 0.032 | 0.053 | 0.006 |
| accept_immediate | 300 | 0.334 | 0.715 | 0.901 | 1.349 | 0.161 |
| accept_group_commit | 300 | 32.339 | 43.144 | 43.532 | 43.670 | 8.471 |
| batch_commit | 5 | 1.716 | 1.820 | 1.820 | 1.820 | 0.150 |
| projection | 100 | 0.149 | 0.400 | 0.508 | 1.477 | 0.157 |
| replay | 100 | 30.616 | 48.240 | 59.431 | 67.798 | 7.090 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
