#!/usr/bin/env bash
set -Eeuo pipefail
SOCKET="ai-runtime-poc"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-runtime-demo.XXXXXX")"
sessions=(claude-root codex-root claude-feature-0042-plan-1 codex-feature-0042-1 claude-feature-0042-review-1)
tmux -L "$SOCKET" kill-server 2>/dev/null || true
for session in "${sessions[@]}"; do
  tmux -L "$SOCKET" new-session -d -s "$session" -c "$WORK_DIR" bash --noprofile --norc
done
observed="$(tmux -L "$SOCKET" list-sessions -F '#{session_name}' | sort)"
expected="$(printf '%s\n' "${sessions[@]}" | sort)"
[[ "$observed" == "$expected" ]] || { printf '[FAIL] tmux demo session set mismatch\n' >&2; exit 1; }
printf '[PASS] tmux demo created and verified %s isolated sessions on socket %s\n' "${#sessions[@]}" "$SOCKET"
printf 'Cleanup with: %s/scripts/cleanup.sh\n' "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
