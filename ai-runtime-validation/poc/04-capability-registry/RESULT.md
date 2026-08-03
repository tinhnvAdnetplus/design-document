# PoC 04 — capability-registry: Executed Result

- Status: **PASS**
- Assertions: **7/7**
- Score: **100.0%**
- Executed at: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Evidence: [`artifacts/20260803T032110Z-2986e3/poc-04/report.json`](../../artifacts/20260803T032110Z-2986e3/poc-04/report.json)

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
