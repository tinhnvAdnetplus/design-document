# PoC 01 — tmux-runtime: Executed Result

- Status: **PASS**
- Assertions: **8/8**
- Score: **100.0%**
- Executed at: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Evidence: [`artifacts/20260803T032110Z-2986e3/poc-01/report.json`](../../artifacts/20260803T032110Z-2986e3/poc-01/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| TMUX-01 | PASS | exactly four V2.2-named sessions | ["claude-feature-f123-plan-1", "claude-root", "codex-feature-f123-1", "codex-root"] |
| TMUX-02 | PASS | one pane per session | {"claude-feature-f123-plan-1": ["%2"], "claude-root": ["%0"], "codex-feature-f123-1": ["%3"], "codex-root": ["%1"]} |
| TMUX-03 | PASS | each pane cwd equals assigned isolated directory | {"claude-feature-f123-plan-1": "/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T032110Z-2986e3/poc-01/workspace/claude-feature", "claude-root": "/home/tinhnv/project/docs/design-document/ai-runtime-vali... |
| TMUX-04 | PASS | target marker contains unique command token | event-2e48456c51a84675aff4a6c2e2d865fd |
| TMUX-05 | PASS | captured pane includes execution token | bash-5.3$ printf '%s' 'event-2e48456c51a84675aff4a6c2e2d865fd' > received.txt; p rintf 'EXECUTED:event-2e48456c51a84675aff4a6c2e2d865fd\n' EXECUTED:event-2e48456c51a84675aff4a6c2e2d865fd bash-5.3$                      |
| TMUX-06 | PASS | only target workspace receives marker | {"claude-feature-f123-plan-1": false, "claude-root": true, "codex-feature-f123-1": false, "codex-root": false} |
| TMUX-07 | PASS | tmux send-keys returns in <100 ms | 6.775 |
| TMUX-08 | PASS | has-session fails for all created sessions | true |
