# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:04:08.482916Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 66.844 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.043 | 0.083 | 0.121 | 0.143 | 0.016 |
| write | 300 | 0.041 | 0.066 | 0.096 | 0.170 | 0.013 |
| flush | 300 | 0.058 | 0.087 | 0.109 | 0.136 | 0.014 |
| fsync | 300 | 7.738 | 9.082 | 10.006 | 14.841 | 1.162 |
| commit | 300 | 8.877 | 9.866 | 10.851 | 15.100 | 0.758 |
| close | 300 | 0.010 | 0.021 | 0.038 | 0.100 | 0.007 |
| accept_immediate | 300 | 4.788 | 10.665 | 15.026 | 27.483 | 3.154 |
| accept_group_commit | 300 | 43.549 | 66.525 | 66.844 | 66.980 | 12.950 |
| batch_commit | 5 | 10.187 | 16.303 | 16.303 | 16.303 | 2.787 |
| projection | 100 | 0.146 | 0.356 | 0.422 | 0.440 | 0.078 |
| replay | 100 | 11.356 | 18.467 | 36.761 | 37.785 | 4.833 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
