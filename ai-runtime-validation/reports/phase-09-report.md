# Phase 09 Report — Performance and Token Budgets

## Executed Result

- Status: **FAIL**
- Assertions: **8/9**
- Executed: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Assertion report: [PoC RESULT](../poc/09-performance/RESULT.md)
- Machine evidence: [report.json](../artifacts/20260803T032110Z-2986e3/poc-09/report.json)

## Validated Scope

Notification, recovery, 100-commit rebuild, packet boundaries, ten concurrent flows, event-store growth, persistent dispatch, and memory/environment reporting passed executable assertions.

## Failure

`PERF-01` measured fsync-backed event acceptance at **657.666 ms p99**, above the frozen **50 ms** target. A follow-up isolated run measured **77.994 ms p99**, confirming that the target is not repeatably met on this host.

## Dependency

The validation harness must not implement runtime storage. Closing this result requires the Phase 3 Event Store implementation or an approved durable-storage strategy, followed by the same benchmark.

## Specification Impact

No specification change is proposed. The existing SLO remains an open validation gate.
