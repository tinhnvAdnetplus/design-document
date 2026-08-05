# Phase 3 Benchmark Artifacts

## Retention rule

A benchmark run is committed here **only when a report cites it as evidence**.
Exploratory and tuning runs are reproducible from
`benchmarks/event_store_benchmark.py` and are not kept in Git history going
forward.

Write throwaway runs outside the repository:

```bash
python3 benchmarks/event_store_benchmark.py --output /tmp/event-store-bench
```

## Retained runs

| Run | Samples | Batch cap | Cited by | Why it is kept |
| --- | ---: | ---: | --- | --- |
| `release-ext4-r1` | 150 | 512 | [performance report](../reports/phase-3/performance-benchmark-report.md) §Repeatability | release repeatability series |
| `release-ext4-r2` | 150 | 512 | same | release repeatability series |
| `release-ext4-r3` | 150 | 512 | same, §Artifacts | representative run (28.598 ms p99) |
| `release-ext4-r4` | 150 | 512 | same | release repeatability series |
| `release-ext4-r5` | 150 | 512 | same | release repeatability series |
| `ext4-optimized-b64` | 300 | 64 | same, §Benchmark interpretation | preserved failure (66.844 ms p99) that motivated the 512-event cap |
| `ext4-s300-b512-r1` | 300 | 512 | same | exploratory 300-event confirmation |
| `ext4-s300-b512-r2` | 300 | 512 | same | exploratory 300-event confirmation |
| `ext4-s300-b512-r3` | 300 | 512 | same | exploratory 300-event confirmation |

All retained runs share the frozen production configuration: SQLite WAL,
`synchronous=FULL`, one persistent writer, explicit transactions, 2 ms group
window, 4,096 queue cap.

## Pruned runs

36 tuning runs (`tune-b*`, `ext4-tune-*`, `ext4-optimized-b128/b256`,
`ext4-s150-*`, `ext4-release-r1`, `final-run-*`, `production-final-r*`,
`release-candidate`, `20260803T-phase3-*`) were removed from the working tree.
They remain reachable in Git history at commit `25fbb89` and can be restored
with:

```bash
git checkout 25fbb89 -- phase3-artifacts/<run-name>
```
