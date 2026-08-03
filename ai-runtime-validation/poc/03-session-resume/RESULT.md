# PoC 03 — session-resume: Executed Result

- Status: **PASS**
- Assertions: **8/8**
- Score: **100.0%**
- Executed at: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Evidence: [`artifacts/20260803T032110Z-2986e3/poc-03/report.json`](../../artifacts/20260803T032110Z-2986e3/poc-03/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| RES-01 | PASS | session name and live pane PID verified | {"identity": "codex-feature-resume-1:%0", "pane_pid": "37314"} |
| RES-02 | PASS | all eight exceptional-resume gates true | {"abnormal_loss": true, "capability_resume": true, "config_enabled": true, "exclusive_resource_free": true, "git_valid": true, "readiness_evidence": true, "resume_ref": true, "role_valid": true} |
| RES-03 | PASS | resume=false prevents resume attempt | fresh_reconstruction |
| RES-04 | PASS | tmux session absent after kill | true |
| RES-05 | PASS | required fields present and <=128 KiB | {"bytes": 1011, "missing": []} |
| RES-06 | PASS | packet HEAD equals clean repository HEAD | {"git": "9c7c37d9a0cafee53034b080f7415dce908f3e82", "packet": "9c7c37d9a0cafee53034b080f7415dce908f3e82"} |
| RES-07 | PASS | dirty file preserved in quarantine | {"content": "preserve me\n", "dirty": true, "quarantine": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T032110Z-2986e3/poc-03/quarantine/feature-repo"} |
| RES-08 | PASS | no resume ID and a verifiable packet digest | {"packet_sha256": "78b3f987719f822a2d3cfea38171a88c92d881a1f26a3ca38a98085466a619fc", "resume_id": null, "source": "git_reconstruction"} |
