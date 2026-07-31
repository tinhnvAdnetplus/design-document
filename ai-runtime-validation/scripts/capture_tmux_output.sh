#!/usr/bin/env bash
# =============================================================================
# capture_tmux_output.sh — Capture tmux pane output for evidence
# =============================================================================
#
# Captures the current pane content from a tmux session and saves it to a file
# for experiment evidence collection.
#
# Usage:
#   ./scripts/capture_tmux_output.sh <session-name> [output-file]
#
# Arguments:
#   session-name   Name of the tmux session to capture
#   output-file    Path to save captured output (default: tmp/<session-name>.txt)
#
# Example:
#   ./scripts/capture_tmux_output.sh claude-root
#   ./scripts/capture_tmux_output.sh codex-feature-0042-1 evidence/impl_output.txt
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="$(dirname "$SCRIPT_DIR")"
SOCKET_NAME="ai-runtime-poc"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <session-name> [output-file]"
    echo ""
    echo "Example:"
    echo "  $0 claude-root"
    echo "  $0 codex-feature-0042-1 evidence/output.txt"
    exit 1
fi

SESSION_NAME="$1"
OUTPUT_FILE="${2:-${VALIDATION_DIR}/tmp/${SESSION_NAME}-$(date +%Y%m%d-%H%M%S).txt}"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Check session exists
if ! tmux -L "$SOCKET_NAME" has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "ERROR: Session '${SESSION_NAME}' not found on socket '${SOCKET_NAME}'"
    exit 1
fi

# Capture pane content
tmux -L "$SOCKET_NAME" capture-pane -t "${SESSION_NAME}:0.0" -p > "$OUTPUT_FILE"

echo "Captured output from '${SESSION_NAME}' → ${OUTPUT_FILE}"
echo "Lines captured: $(wc -l < "$OUTPUT_FILE")"
