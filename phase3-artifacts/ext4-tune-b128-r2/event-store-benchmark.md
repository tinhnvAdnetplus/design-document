# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:02:40.309111Z`
- Workload: **300 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **FAIL** (group-commit p99 65.360 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 300 | 0.076 | 0.165 | 0.479 | 0.960 | 0.084 |
| write | 300 | 0.043 | 0.072 | 0.090 | 0.137 | 0.013 |
| flush | 300 | 0.059 | 0.100 | 0.117 | 0.137 | 0.016 |
| fsync | 300 | 6.768 | 7.902 | 8.939 | 9.866 | 0.735 |
| commit | 300 | 8.976 | 10.182 | 11.759 | 17.776 | 0.917 |
| close | 300 | 0.020 | 0.038 | 0.087 | 0.804 | 0.047 |
| accept_immediate | 300 | 5.031 | 10.581 | 14.533 | 23.749 | 2.833 |
| accept_group_commit | 300 | 48.324 | 64.865 | 65.360 | 65.427 | 12.393 |
| batch_commit | 3 | 14.060 | 14.843 | 14.843 | 14.843 | 2.109 |
| projection | 100 | 0.125 | 0.266 | 0.499 | 1.759 | 0.171 |
| replay | 100 | 26.258 | 33.007 | 55.937 | 66.272 | 5.672 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
