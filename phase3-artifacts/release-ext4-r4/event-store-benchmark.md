# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:07:15.305673Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 25.483 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.041 | 0.081 | 0.093 | 0.153 | 0.016 |
| write | 150 | 0.043 | 0.098 | 0.148 | 0.151 | 0.021 |
| flush | 150 | 0.062 | 0.123 | 0.155 | 0.201 | 0.025 |
| fsync | 150 | 6.760 | 7.907 | 9.123 | 10.059 | 0.708 |
| commit | 150 | 7.944 | 9.856 | 10.357 | 15.943 | 1.276 |
| close | 150 | 0.010 | 0.022 | 0.036 | 0.146 | 0.012 |
| accept_immediate | 150 | 8.893 | 10.837 | 18.690 | 22.071 | 2.399 |
| accept_group_commit | 150 | 23.622 | 25.320 | 25.483 | 25.579 | 1.062 |
| batch_commit | 1 | 12.582 | 12.582 | 12.582 | 12.582 | 0.000 |
| projection | 100 | 0.056 | 0.202 | 0.287 | 0.406 | 0.063 |
| replay | 100 | 5.905 | 8.846 | 10.444 | 11.569 | 1.375 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
