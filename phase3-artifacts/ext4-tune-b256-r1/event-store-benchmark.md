# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:02:50.565532Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 61.731 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.042 | 0.078 | 0.106 | 0.133 | 0.015 |
| write | 300 | 0.042 | 0.074 | 0.113 | 0.148 | 0.015 |
| flush | 300 | 0.064 | 0.098 | 0.134 | 0.294 | 0.021 |
| fsync | 300 | 6.812 | 7.826 | 8.603 | 16.995 | 0.859 |
| commit | 300 | 8.342 | 9.889 | 12.063 | 22.799 | 1.416 |
| close | 300 | 0.010 | 0.021 | 0.039 | 0.115 | 0.008 |
| accept_immediate | 300 | 5.021 | 10.920 | 11.965 | 21.747 | 2.942 |
| accept_group_commit | 300 | 45.436 | 61.314 | 61.731 | 61.869 | 7.663 |
| batch_commit | 2 | 12.364 | 14.360 | 14.360 | 14.360 | 2.822 |
| projection | 100 | 0.148 | 0.341 | 0.388 | 0.410 | 0.071 |
| replay | 100 | 28.314 | 39.311 | 46.681 | 47.831 | 4.643 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
