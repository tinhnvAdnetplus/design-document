# Expected Results

| ID | Required evidence |
| --- | --- |
| CLI-01 | `agy` and `codex` versions and paths are discovered |
| CLI-02 | Both CLIs return schema-valid structured events |
| CLI-03 | Both CLIs resume a prior conversation/session and recall a nonce |
| CLI-04 | Both TUI readiness states are detected and live processes respond after tmux `send-keys` |
| CLI-05 | Codex native fork is observed; Antigravity fork gap is explicit |
| CLI-06 | tmux server is removed and the fixture repository remains clean |
| CLI-07 | Evidence contains no raw output, home path, email, or credential text |

All required live gates produce `PHASE_3_APPROVED_WITH_ADAPTATIONS`. Missing
CLI/auth produces `INCONCLUSIVE`; behavioral incompatibility produces
`PHASE_3_BLOCKED`.
