# PoC 08 — chaos: Executed Result

- Status: **PASS**
- Assertions: **7/7**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-08/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-08/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| CHAOS-01 | PASS | victim absent; survivor present | {"survivor_alive": true, "victim_dead": true} |
| CHAOS-02 | PASS | durable event projects after restart | {"projection_was_absent": true, "replayed": {"event_count": 1, "side_effects_replayed": 0, "streams": {"feature/feat-validation": {"last_event_id": "evt-validation-001", "sequence": 1, "state": "feature.requested"}}}} |
| CHAOS-03 | PASS | dirty file preserved under quarantine | {"git_status": "?? dirty.txt", "quarantine": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T072146Z-2fd45e/poc-08/quarantine/dirty-repo"} |
| CHAOS-04 | PASS | feature reachable from actual integration ref | {"actual_ref": "b5c1053ae1b55ef6e15b3c81eeec1d912fe0d809", "base": "8b8541e4314ec2173541bb0ca7b9cdac3d72857c", "feature": "401838d095e7dac963168e5ed9cd66a3d4a09940"} |
| CHAOS-05 | PASS | old cache digest unchanged; fallback selected | {"after": "e098559c16e514920412857c5ea4dd9b3f0d94c5a1270c6fc4b66e6da591cc1c", "before": "e098559c16e514920412857c5ea4dd9b3f0d94c5a1270c6fc4b66e6da591cc1c", "result": "fallback_without_cache"} |
| CHAOS-06 | PASS | both safe-time and token checks deny | {"clock_check": "AUTHORIZATION_DENIED", "token_check": "AUTHORIZATION_DENIED"} |
| CHAOS-07 | PASS | exact Chapter 23 ordering | ["stop_side_effects", "validate_config_and_repo", "rebuild_projection", "inspect_git_and_worktrees", "reconcile_leases", "reconcile_sessions", "revalidate_capabilities", "select_recovery", "confirm_pending_intents", "resume_deliveries", ... |
