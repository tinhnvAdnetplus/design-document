# Measurable Pass Criteria: 01-tmux-runtime

## 1. Session Lifecycle
- `tmux -L ai-runtime list-sessions` must output exactly the names defined in the PoC creation script.
- Root sessions and feature sessions are explicitly distinguishable by name.

## 2. Event Delivery
- Sending an event via `send-keys` results in the command being present in the target pane's history or execution output.

## 3. Isolation & Teardown
- Terminating a feature session (`kill-session -t codex-feature-test-1`) removes it from `list-sessions` but leaves `claude-root` unaffected.
- Teardown cleanly removes the `ai-runtime` socket.
