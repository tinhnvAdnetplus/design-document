# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T03:58:57.913631Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 48.692 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.030 | 0.088 | 0.150 | 0.332 | 0.031 |
| write | 300 | 0.004 | 0.007 | 0.017 | 0.031 | 0.003 |
| flush | 300 | 0.002 | 0.003 | 0.006 | 0.013 | 0.001 |
| fsync | 300 | 0.001 | 0.002 | 0.003 | 0.049 | 0.003 |
| commit | 300 | 0.009 | 0.028 | 0.040 | 0.244 | 0.015 |
| close | 300 | 0.009 | 0.025 | 0.040 | 0.106 | 0.009 |
| accept_immediate | 300 | 0.341 | 0.685 | 0.944 | 1.635 | 0.175 |
| accept_group_commit | 300 | 37.358 | 48.408 | 48.692 | 48.749 | 5.782 |
| batch_commit | 3 | 2.796 | 3.464 | 3.464 | 3.464 | 1.189 |
| projection | 100 | 0.147 | 0.331 | 0.485 | 0.573 | 0.084 |
| replay | 100 | 27.868 | 44.941 | 72.640 | 78.959 | 8.250 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
