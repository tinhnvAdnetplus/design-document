# Phase 3 Event Store Benchmark

- Captured: `2026-08-03T04:07:10.640486Z`
- Workload: **150 events**
- Durability: `journal_mode=WAL`, `synchronous=FULL`
- PERF-01 equivalent result: **PASS** (group-commit p99 28.598 ms; target < 50.000 ms)

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.044 | 0.102 | 0.182 | 0.204 | 0.025 |
| write | 150 | 0.042 | 0.082 | 0.094 | 0.107 | 0.014 |
| flush | 150 | 0.059 | 0.092 | 0.117 | 0.129 | 0.015 |
| fsync | 150 | 6.860 | 7.912 | 8.952 | 9.371 | 0.618 |
| commit | 150 | 7.127 | 8.791 | 10.938 | 10.959 | 0.851 |
| close | 150 | 0.010 | 0.025 | 0.048 | 0.068 | 0.007 |
| accept_immediate | 150 | 9.015 | 10.752 | 13.605 | 21.175 | 2.118 |
| accept_group_commit | 150 | 25.522 | 28.296 | 28.598 | 28.735 | 1.423 |
| batch_commit | 1 | 14.609 | 14.609 | 14.609 | 14.609 | 0.000 |
| projection | 100 | 0.059 | 0.201 | 0.254 | 0.262 | 0.050 |
| replay | 100 | 5.933 | 9.063 | 9.724 | 9.866 | 1.414 |

`commit` is SQLite WAL `COMMIT` latency. `fsync` is an isolated host-filesystem fsync. `batch_commit` is one explicit Event Store transaction shared by a bounded batch. Acceptance measurements include queueing through durable acknowledgement.
