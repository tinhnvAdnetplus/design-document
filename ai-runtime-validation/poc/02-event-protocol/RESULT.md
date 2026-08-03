# PoC 02 — event-protocol: Executed Result

- Status: **PASS**
- Assertions: **12/12**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-02/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-02/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| EVT-01 | PASS | zero schema errors | [[], [], []] |
| EVT-02 | PASS | every invalid fixture has schema diagnostics | {"missing_fields.json": ["'occurred_at' is a required property", "'producer' is a required property", "'aggregate' is a required property", "'correlation_id' is a required property", "'idempotency_key' is a required property", "'policy_r... |
| EVT-03 | PASS | v2 rejected by v1 schema | ["'ai-runtime.events/v1' was expected"] |
| EVT-04 | PASS | three fsync-backed appends | ["APPENDED", "APPENDED", "APPENDED"] |
| EVT-05 | PASS | duplicate ignored and store remains three events | {"count": 3, "result": "DUPLICATE_IGNORED"} |
| EVT-06 | PASS | IDEMPOTENCY_CONFLICT | IDEMPOTENCY_CONFLICT |
| EVT-07 | PASS | sequence gap rejected | AGGREGATE_SEQUENCE_CONFLICT expected=4 |
| EVT-08 | PASS | three events project final state plan.approved | {"event_count": 3, "side_effects_replayed": 0, "streams": {"feature/feat-validation": {"last_event_id": "evt-validation-003", "sequence": 3, "state": "plan.approved"}}} |
| EVT-09 | PASS | byte-identical projections; zero blind side effects | 4d6877e5fd4dd38d8bb45a0f781537756b4a06b54fd035cba4a686f588369d6c |
| EVT-10 | PASS | modified payload fails digest | {"computed": "c3c8fb6e3d7f319b581a1b0320b4cb7da9235cd6d80caba0b7f9ec16252dc6af", "stored": "e5c7d12798546ba1cb41129ebda040b8e1fad7b26a6f5d0aa6b23b1c47b85f76"} |
| EVT-11 | PASS | INVALID_SIGNATURE | INVALID_SIGNATURE |
| EVT-12 | PASS | corruption names exact line | CORRUPT_EVENT_STORE line 4: Expecting property name enclosed in double quotes |
