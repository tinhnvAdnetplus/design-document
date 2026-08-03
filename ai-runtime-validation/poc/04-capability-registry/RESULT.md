# PoC 04 — capability-registry: Executed Result

- Status: **PASS**
- Assertions: **7/7**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-04/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-04/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| CAP-01 | PASS | two current documents and one capabilities() call each | {"calls": {"claude": 1, "codex": 1}, "entries": ["claude", "codex"]} |
| CAP-02 | PASS | claude native; codex synthetic | {"claude": "native", "codex": "synthetic"} |
| CAP-03 | PASS | undeclared resume becomes reconstruction | {"claude": "resume", "codex": "fresh_reconstruction"} |
| CAP-04 | PASS | fresh capabilities() call per trigger and adapter | {"audit": [{"active": ["claude", "codex"], "trigger": "startup"}, {"active": ["claude", "codex"], "trigger": "restart"}, {"active": ["claude", "codex"], "trigger": "adapter_upgrade"}, {"active": ["claude", "codex"], "trigger": "manual_cl... |
| CAP-05 | PASS | older/equal document rejected | {"candidate": "0.1", "current": "1.0"} |
| CAP-06 | PASS | ADAPTER_UNAVAILABLE | ADAPTER_UNAVAILABLE |
| CAP-07 | PASS | missing adapter is unavailable | ADAPTER_UNAVAILABLE |
