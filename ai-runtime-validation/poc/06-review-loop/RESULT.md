# PoC 06 — review-loop: Executed Result

- Status: **PASS**
- Assertions: **6/6**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-06/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-06/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| RL-01 | PASS | normal chain completes; requested->implementation denied | {"final": "merge.completed", "invalid_jump_allowed": false} |
| RL-02 | PASS | HMAC validates head/base/plan/policy/role | {"binding_sha256": "96704407440576cd4e696afc0a6a6b41f60b37d7fe96cf0809a3482e19a46077", "signature": "d5461383c6f4f735cb108c0a872674640f8b05d27ef479a0d87a0fab8e7e1b8e"} |
| RL-03 | PASS | changed head fails binding signature | false |
| RL-04 | PASS | AUTHORIZATION_DENIED | AUTHORIZATION_DENIED |
| RL-05 | PASS | third changes.requested escalates | ["redispatch", "redispatch", "escalate_and_block"] |
| RL-06 | PASS | one holder; recovery token increases | {"collision": [false, 1], "first": [true, 1], "lease": {"fencing_token": 2, "holder": "codex_recovery"}, "recovery": [true, 2]} |
