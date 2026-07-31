#!/bin/bash
# scripts/simulate_session_loss.sh
SESSION=$1
echo "[INFO] Simulating session loss for $SESSION..."
tmux -L ai-runtime kill-session -t "$SESSION" 2>/dev/null || true
echo "[SUCCESS] Session $SESSION destroyed."
