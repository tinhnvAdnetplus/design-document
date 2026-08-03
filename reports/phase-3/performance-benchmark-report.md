# Phase 3 Performance Benchmark Report

## Result

**PASS.** The representative production run measured durable group-commit acceptance at **28.598 ms p99**, leaving **21.402 ms** below the frozen 50 ms limit. Five consecutive ext4 runs passed.

Configuration: 150 events, SQLite WAL, `synchronous=FULL`, one persistent writer, explicit transactions, 2 ms time window, maximum batch 512, maximum queue 4,096. Host: Linux 6.18 WSL2, Python 3.14.4, ext4 on `/dev/sdd`, 8 logical CPUs.

## Representative micro-benchmark

| Metric | Count | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| open | 150 | 0.044 | 0.102 | 0.182 | 0.204 | 0.025 |
| write | 150 | 0.042 | 0.082 | 0.094 | 0.108 | 0.014 |
| flush | 150 | 0.059 | 0.092 | 0.117 | 0.129 | 0.015 |
| fsync | 150 | 6.860 | 7.912 | 8.952 | 9.372 | 0.618 |
| SQLite commit | 150 | 7.127 | 8.791 | 10.938 | 10.959 | 0.851 |
| close | 150 | 0.010 | 0.025 | 0.048 | 0.068 | 0.007 |
| immediate durable acceptance | 150 | 9.015 | 10.752 | 13.605 | 21.175 | 2.118 |
| batch commit | 1 | 14.609 | 14.609 | 14.609 | 14.609 | 0.000 |
| group-commit durable acceptance | 150 | 25.522 | 28.296 | 28.598 | 28.735 | 1.423 |
| projection | 100 | 0.059 | 0.201 | 0.254 | 0.262 | 0.050 |
| replay | 100 | 5.933 | 9.063 | 9.724 | 9.866 | 1.414 |

`SQLite commit` is an isolated explicit WAL transaction. `Batch commit` includes all inserts and the shared durable commit. Acceptance includes submission, bounded queueing, validation/integrity work, transaction work, and post-commit future resolution.

## Repeatability

| Run | p50 ms | p95 ms | p99 ms | Worst ms | Std dev ms | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| release-ext4-r1 | 25.270 | 27.990 | 28.172 | 28.280 | 1.867 | PASS |
| release-ext4-r2 | 23.041 | 24.957 | 25.121 | 25.210 | 1.086 | PASS |
| release-ext4-r3 | 25.522 | 28.296 | 28.598 | 28.735 | 1.423 | PASS |
| release-ext4-r4 | 23.622 | 25.320 | 25.483 | 25.579 | 1.062 | PASS |
| release-ext4-r5 | 24.029 | 26.348 | 26.541 | 26.633 | 1.346 | PASS |

Maximum observed p99 across the release series was **28.598 ms**.

## Storage latency analysis

Fsync is the material storage cost: representative p99 was 8.952 ms. One repeat's isolated fsync probe observed 30.236 ms p99 and 60.474 ms worst case, demonstrating genuine host jitter. That repeat's production group-commit p99 still passed at 26.541 ms because the shared production commit did not coincide with the isolated outlier.

The original failure mode multiplied this jitter across per-event open/flush/fsync/close cycles. The production implementation uses one persistent WAL connection and one durable boundary for the measured concurrent burst. It never acknowledges before that boundary.

## Artifacts

- Representative [JSON](../../phase3-artifacts/release-ext4-r3/event-store-benchmark.json), [CSV](../../phase3-artifacts/release-ext4-r3/event-store-benchmark.csv), and [Markdown](../../phase3-artifacts/release-ext4-r3/event-store-benchmark.md)
- Repeat runs: `phase3-artifacts/release-ext4-r1` through `release-ext4-r5`

## Benchmark interpretation

The 150-event workload matches PERF-01's existing sample count. A prior 300-event tuning run with a 64-event cap failed because five serialized durable commits accumulated; that failure is preserved in the artifacts. The final 512-event bound passed both the target workload and three exploratory 300-event ext4 runs. Continuous overload beyond queue capacity is rejected with explicit backpressure and is not represented as successful low-latency acceptance.

