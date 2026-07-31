#!/bin/bash
# scripts/cleanup_sessions.sh
# Tears down the tmux server and cleans up test sessions.

SOCKET="ai-runtime"
echo "[INFO] Killing all sessions on socket ${SOCKET}..."
tmux -L $SOCKET kill-server 2>/dev/null || true
echo "[SUCCESS] Cleanup complete."
