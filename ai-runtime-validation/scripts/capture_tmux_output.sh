#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOCKET="ai-runtime-poc"
[[ $# -ge 1 ]] || { printf 'usage: %s <session> [output-file]\n' "$0" >&2; exit 2; }
session="$1"
output="${2:-${ROOT}/tmp/${session}-$(date -u +%Y%m%dT%H%M%SZ).txt}"
tmux -L "$SOCKET" has-session -t "$session" 2>/dev/null || { printf '[FAIL] session not found: %s\n' "$session" >&2; exit 1; }
mkdir -p "$(dirname "$output")"
tmux -L "$SOCKET" capture-pane -p -S -1000 -t "${session}:0.0" > "$output"
[[ -f "$output" ]] || { printf '[FAIL] capture artifact not created\n' >&2; exit 1; }
printf '[PASS] captured %s bytes from %s into %s\n' "$(wc -c < "$output")" "$session" "$output"
