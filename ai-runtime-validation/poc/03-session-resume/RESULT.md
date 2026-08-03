# PoC 03 — session-resume: Executed Result

- Status: **PASS**
- Assertions: **8/8**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-03/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-03/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| RES-01 | PASS | session name and live pane PID verified | {"identity": "codex-feature-resume-1:%0", "pane_pid": "132862"} |
| RES-02 | PASS | all eight exceptional-resume gates true | {"abnormal_loss": true, "capability_resume": true, "config_enabled": true, "exclusive_resource_free": true, "git_valid": true, "readiness_evidence": true, "resume_ref": true, "role_valid": true} |
| RES-03 | PASS | resume=false prevents resume attempt | fresh_reconstruction |
| RES-04 | PASS | tmux session absent after kill | true |
| RES-05 | PASS | required fields present and <=128 KiB | {"bytes": 1011, "missing": []} |
| RES-06 | PASS | packet HEAD equals clean repository HEAD | {"git": "8b8541e4314ec2173541bb0ca7b9cdac3d72857c", "packet": "8b8541e4314ec2173541bb0ca7b9cdac3d72857c"} |
| RES-07 | PASS | dirty file preserved in quarantine | {"content": "preserve me\n", "dirty": true, "quarantine": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T072146Z-2fd45e/poc-03/quarantine/feature-repo"} |
| RES-08 | PASS | no resume ID and a verifiable packet digest | {"packet_sha256": "93e255caf833df81d46737dc4a900ec507c6b275a41fa45cefc2c2951c6cb69e", "resume_id": null, "source": "git_reconstruction"} |
