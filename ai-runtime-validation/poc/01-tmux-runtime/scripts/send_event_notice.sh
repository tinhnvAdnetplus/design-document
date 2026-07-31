#!/bin/bash
# scripts/send_event_notice.sh
# Validates event notification delivery via send-keys targeting a specific pane.

SOCKET="ai-runtime"
TARGET="claude-root"
COMMAND=$(cat ../fixtures/sample_event_command.txt)

echo "[INFO] Sending event notification to ${TARGET}..."
tmux -L $SOCKET send-keys -t $TARGET "$COMMAND" Enter
echo "[SUCCESS] Event sent to $TARGET."
