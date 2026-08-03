#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOCKET="ai-runtime-poc"
tmux -L "$SOCKET" kill-server 2>/dev/null || true
if tmux -L "$SOCKET" list-sessions >/dev/null 2>&1; then
  printf '[FAIL] tmux demo server survived cleanup\n' >&2
  exit 1
fi
if [[ "${1:-}" == "--all" ]]; then
  find "$ROOT/tmp" -mindepth 1 -not -name .gitkeep -delete
fi
printf '[PASS] cleanup verified tmux demo server absent%s\n' "$([[ "${1:-}" == "--all" ]] && printf ' and tmp cleared' || true)"
