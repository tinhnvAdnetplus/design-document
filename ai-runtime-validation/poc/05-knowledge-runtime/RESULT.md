# PoC 05 — knowledge-runtime: Executed Result

- Status: **PASS**
- Assertions: **9/9**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-05/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-05/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| KR-01 | PASS | six named, populated domains | {"architecture": 1, "business": 1, "convention": 1, "dependency": 1, "project": 1, "workspace": 1} |
| KR-02 | PASS | confirmed, inferred, open, transient | ["confirmed", "inferred", "open", "transient"] |
| KR-03 | PASS | every commit and path resolves | {"commit": "d20425ef57baea5dbd70f27fd07d61db92d9fc96", "path": "architecture.txt"} |
| KR-04 | PASS | missing provenance rejected | rejected |
| KR-05 | PASS | >128 KiB input, <128 KiB output, confirmed fact retained | {"after_bytes": 246, "before_bytes": 164155} |
| KR-06 | PASS | 131073-byte packet rejected | {"bytes": 131073, "result": "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED"} |
| KR-07 | PASS | merged commit reachable before evolution | {"events": ["merge.completed", "knowledge.evolution.started", "knowledge.snapshot.published"], "reachable": true} |
| KR-08 | PASS | independent layer values; no conversation directory | {"conversation_enabled": false, "layers": ["knowledge", "prompt", "resume"]} |
| KR-09 | PASS | snapshot <=128 KiB | 2337 |
