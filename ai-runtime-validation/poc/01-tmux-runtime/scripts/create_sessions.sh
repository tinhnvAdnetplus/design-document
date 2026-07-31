#!/bin/bash
# scripts/create_sessions.sh
# Simulates the Orchestrator launching isolated tmux sessions for agents.

SOCKET="ai-runtime"
CWD=$(pwd)

echo "[INFO] Creating Root Sessions..."
tmux -L $SOCKET new-session -d -s claude-root -c "$CWD"
tmux -L $SOCKET new-session -d -s codex-root -c "$CWD"

echo "[INFO] Creating Feature Sessions..."
FEATURE_ID="f123"
ATTEMPT="1"
tmux -L $SOCKET new-session -d -s "claude-feature-${FEATURE_ID}-plan-${ATTEMPT}" -c "$CWD"
tmux -L $SOCKET new-session -d -s "codex-feature-${FEATURE_ID}-${ATTEMPT}" -c "$CWD"

echo "[SUCCESS] Sessions created."
tmux -L $SOCKET list-sessions
