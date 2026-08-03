# Validation Failure Report

## 01 TMUX-03 — working directories are assigned

- Expected: each pane cwd equals assigned isolated directory
- Observed: AssertionError: {'claude-root': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'codex-root': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'claude-feature-f123-plan-1': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'codex-feature-f123-1': '/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T031347Z-f12f3c/poc-01/workspace/codex-feature'}
- Diagnostic: AssertionError: {'claude-root': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'codex-root': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'claude-feature-f123-plan-1': '/home/tinhnv/project/docs/design-document/ai-runtime-validation', 'codex-feature-f123-1': '/home/tinhnv/project/docs/design-document/ai-runtime-validation/artifacts/20260803T031347Z-f12f3c/poc-01/workspace/codex-feature'}

