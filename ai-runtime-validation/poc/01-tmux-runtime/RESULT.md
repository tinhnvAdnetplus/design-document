# PoC 01 — tmux-runtime: Executed Result

- Status: **PASS**
- Assertions: **8/8**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-01/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-01/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| TMUX-01 | PASS | exactly four V2.2-named sessions | ["claude-feature-f123-plan-1", "claude-root", "codex-feature-f123-1", "codex-root"] |
| TMUX-02 | PASS | one pane per session | {"claude-feature-f123-plan-1": ["%2"], "claude-root": ["%0"], "codex-feature-f123-1": ["%3"], "codex-root": ["%1"]} |
| TMUX-03 | PASS | each pane cwd equals assigned isolated directory | {"claude-feature-f123-plan-1": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T072146Z-2fd45e/poc-01/workspace/claude-feature", "claude-root": "/home/tinhnv/project/docs/design-document/ai-runtime-vali... |
| TMUX-04 | PASS | target marker contains unique command token | event-f14863ffefbe4be98da2956c0189a9d4 |
| TMUX-05 | PASS | captured pane includes execution token | bash-5.3$ printf '%s' 'event-f14863ffefbe4be98da2956c0189a9d4' > received.txt; p rintf 'EXECUTED:event-f14863ffefbe4be98da2956c0189a9d4\n' EXECUTED:event-f14863ffefbe4be98da2956c0189a9d4 bash-5.3$                      |
| TMUX-06 | PASS | only target workspace receives marker | {"claude-feature-f123-plan-1": false, "claude-root": true, "codex-feature-f123-1": false, "codex-root": false} |
| TMUX-07 | PASS | tmux send-keys returns in <100 ms | 4.65 |
| TMUX-08 | PASS | has-session fails for all created sessions | true |
