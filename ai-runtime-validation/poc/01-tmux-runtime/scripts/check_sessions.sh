#!/bin/bash
# scripts/check_sessions.sh
# Validates session existence and controlled naming.

SOCKET="ai-runtime"

echo "[INFO] Checking required sessions..."
while read session_name; do
  # Skip empty lines
  [ -z "$session_name" ] && continue

  if tmux -L $SOCKET has-session -t "$session_name" 2>/dev/null; then
    echo "[PASS] Session exists: $session_name"
  else
    echo "[FAIL] Session missing: $session_name"
  fi
done < ../fixtures/session_names.txt
