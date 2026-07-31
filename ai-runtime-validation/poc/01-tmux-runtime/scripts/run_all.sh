#!/bin/bash
# scripts/run_all.sh
# Orchestrates the full PoC 01 execution.

set -e

# Make scripts executable
chmod +x ./*.sh

echo "=== Starting PoC 01: tmux-runtime ==="
./cleanup_sessions.sh
./create_sessions.sh
./check_sessions.sh
./send_event_notice.sh
./cleanup_sessions.sh
echo "=== PoC 01 Complete ==="
