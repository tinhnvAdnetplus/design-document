#!/usr/bin/env bash
# =============================================================================
# start_tmux_demo.sh — Demonstrate V2.2 tmux session topology
# =============================================================================
#
# Creates a demonstration tmux server with the V2.2 naming convention:
# - claude-root     (persistent Claude root session)
# - codex-root      (persistent Codex root session)
# - claude-feature-0042-plan-1    (planner session)
# - codex-feature-0042-1          (implementer session)
# - claude-feature-0042-review-1  (reviewer session)
#
# Uses a dedicated socket (ai-runtime-poc) to avoid conflicts.
#
# Usage:
#   ./scripts/start_tmux_demo.sh
#
# Cleanup:
#   tmux -L ai-runtime-poc kill-server
#   # or use ./scripts/cleanup.sh
# =============================================================================

set -euo pipefail

SOCKET_NAME="ai-runtime-poc"
WORK_DIR="${TMPDIR:-/tmp}/ai-runtime-validation"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$WORK_DIR"

echo ""
echo "============================================="
echo "  tmux Runtime Demo — V2.2 Naming Convention"
echo "============================================="
echo ""

# Kill existing demo server if present
tmux -L "$SOCKET_NAME" kill-server 2>/dev/null || true

# ---------------------------------------------------------------------------
# Create root sessions (persistent)
# ---------------------------------------------------------------------------
echo -e "${BLUE}Creating root sessions...${NC}"

tmux -L "$SOCKET_NAME" new-session -d -s "claude-root" -c "$WORK_DIR"
echo -e "  ${GREEN}✓${NC} claude-root"

tmux -L "$SOCKET_NAME" new-session -d -s "codex-root" -c "$WORK_DIR"
echo -e "  ${GREEN}✓${NC} codex-root"

# ---------------------------------------------------------------------------
# Create feature sessions (disposable)
# ---------------------------------------------------------------------------
echo ""
echo -e "${BLUE}Creating feature sessions...${NC}"

tmux -L "$SOCKET_NAME" new-session -d -s "claude-feature-0042-plan-1" -c "$WORK_DIR"
echo -e "  ${GREEN}✓${NC} claude-feature-0042-plan-1 (planner)"

tmux -L "$SOCKET_NAME" new-session -d -s "codex-feature-0042-1" -c "$WORK_DIR"
echo -e "  ${GREEN}✓${NC} codex-feature-0042-1 (implementer)"

tmux -L "$SOCKET_NAME" new-session -d -s "claude-feature-0042-review-1" -c "$WORK_DIR"
echo -e "  ${GREEN}✓${NC} claude-feature-0042-review-1 (reviewer)"

# ---------------------------------------------------------------------------
# List sessions
# ---------------------------------------------------------------------------
echo ""
echo -e "${BLUE}Active sessions:${NC}"
tmux -L "$SOCKET_NAME" list-sessions -F '  #{session_name} (created: #{session_created})'

echo ""
echo -e "${GREEN}Demo running.${NC} Use 'tmux -L $SOCKET_NAME attach -t <name>' to inspect."
echo "Cleanup: tmux -L $SOCKET_NAME kill-server"
echo ""
