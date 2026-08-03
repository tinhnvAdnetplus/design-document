# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:05:45.838309Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 42.937 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.043 | 0.109 | 0.158 | 0.208 | 0.024 |
| write | 300 | 0.042 | 0.090 | 0.132 | 0.152 | 0.018 |
| flush | 300 | 0.061 | 0.102 | 0.133 | 0.166 | 0.020 |
| fsync | 300 | 6.795 | 7.770 | 8.124 | 9.553 | 0.618 |
| commit | 300 | 8.967 | 11.090 | 20.097 | 28.859 | 2.304 |
| close | 300 | 0.010 | 0.029 | 0.041 | 0.138 | 0.010 |
| accept_immediate | 300 | 4.835 | 10.661 | 18.907 | 50.885 | 3.960 |
| accept_group_commit | 300 | 30.785 | 42.624 | 42.937 | 43.015 | 5.748 |
| batch_commit | 2 | 11.776 | 12.901 | 12.901 | 12.901 | 1.591 |
| projection | 100 | 0.143 | 0.319 | 0.354 | 0.440 | 0.067 |
| replay | 100 | 11.840 | 15.926 | 17.499 | 17.506 | 1.910 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
