#!/bin/bash
# scripts/test_reattach.sh
SESSION=$1

if tmux -L ai-runtime has-session -t "$SESSION" 2>/dev/null; then
  echo "[PASS] Reattach successful for $SESSION."
  exit 0
else
  echo "[FAIL] Reattach failed for $SESSION. Session not found."
  exit 1
fi
