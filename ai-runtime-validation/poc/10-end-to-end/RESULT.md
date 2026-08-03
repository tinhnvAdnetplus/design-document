# PoC 10 — end-to-end: Executed Result

- Status: **PASS**
- Assertions: **10/10**
- Score: **100.0%**
- Executed at: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Evidence: [`artifacts/20260803T032110Z-2986e3/poc-10/report.json`](../../artifacts/20260803T032110Z-2986e3/poc-10/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| E2E-01 | PASS | exact ten-event lifecycle | ["feature.requested", "plan.ready", "plan.approved", "implementation.ready", "review.requested", "merge.approved", "merge.started", "merge.completed", "knowledge.sync.requested", "knowledge.synchronized"] |
| E2E-02 | PASS | sequence 1..10; one correlation; each causation points to predecessor | {"causes_match": true, "correlations": ["cor-e2e-validation"], "sequences": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} |
| E2E-03 | PASS | Claude reviewer signature matches implementation head | {"head": "df084ec0a7ce8d34b4467178300fdc176ba93dea", "role": "claude_reviewer", "signature_valid": true} |
| E2E-04 | PASS | feature head reachable and merge event matches main | {"feature_reachable": true, "integration_head": "3c79a7f13ebbfd3f12da75f650a949e0405ab93c"} |
| E2E-05 | PASS | knowledge.sync.requested index follows merge.completed | {"knowledge_index": 8, "merge_index": 7} |
| E2E-06 | PASS | feature absent; root alive | {"feature_absent": true, "root_alive": true} |
| E2E-07 | PASS | 10/10 invariant predicates true | {"INV-01": true, "INV-02": true, "INV-03": true, "INV-04": true, "INV-05": true, "INV-06": true, "INV-07": true, "INV-08": true, "INV-09": true, "INV-10": true} |
| E2E-08 | PASS | feature cleaned; deliberately persistent root remains managed | {"feature_absent": true, "managed_roots": 1} |
| E2E-09 | PASS | isolated tmux socket has no server | true |
| E2E-10 | PASS | fsync-backed non-empty store; zero schema errors | {"bytes": 7228, "events": 10} |

## Dependencies

- Real vendor Claude/Codex CLI compatibility remains a Phase 3 integration dependency; this run uses deterministic contract adapters.
