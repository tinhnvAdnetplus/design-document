# PoC 07 — scheduler: Executed Result

- Status: **PASS**
- Assertions: **6/6**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-07/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-07/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| SCH-01 | PASS | serialized queue equals in-memory queue | {"count": 3, "path": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T072146Z-2fd45e/poc-07/delivery-queue.json"} |
| SCH-02 | PASS | critical-new, high, normal-old | ["critical-new", "high", "normal-old"] |
| SCH-03 | PASS | 2,4,8,16 seconds and visible after threshold | {"escalation": "visible", "seconds": [2, 4, 8, 16]} |
| SCH-04 | PASS | ready selected; all-busy queue remains pending | {"assigned": "ready", "pending_when_full": true} |
| SCH-05 | PASS | SLA-aged normal event dispatches before fresh critical | ["normal-aged", "critical-fresh"] |
| SCH-06 | PASS | 1000-item tick <100 ms with no consumer wait | {"duration_ms": 0.274, "eligible": 1000} |
