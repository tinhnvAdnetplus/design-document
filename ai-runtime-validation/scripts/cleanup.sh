#!/usr/bin/env bash
# =============================================================================
# cleanup.sh — AI Multi-Agent Runtime V2.2 Validation Cleanup
# =============================================================================
#
# Removes all temporary state created by PoC experiments:
# - tmux sessions on the ai-runtime socket
# - Temporary files in tmp/
# - Test Git repositories and worktrees
#
# Usage:
#   ./scripts/cleanup.sh [--all]
#
# Options:
#   --all   Also clean tmp/ directory contents
#
# This script is safe to run repeatedly (idempotent).
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="${VALIDATION_DIR}/tmp"
SOCKET_NAME="ai-runtime-poc"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo ""
echo "============================================="
echo "  AI Multi-Agent Runtime V2.2"
echo "  Validation Cleanup"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
# Kill tmux sessions on the PoC socket
# ---------------------------------------------------------------------------
echo -e "${YELLOW}Cleaning tmux sessions...${NC}"

if tmux -L "$SOCKET_NAME" list-sessions 2>/dev/null; then
    tmux -L "$SOCKET_NAME" kill-server 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Killed tmux server on socket: ${SOCKET_NAME}"
else
    echo -e "  ${GREEN}✓${NC} No tmux server running on socket: ${SOCKET_NAME}"
fi

# ---------------------------------------------------------------------------
# Clean temporary files
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--all" ]]; then
    echo ""
    echo -e "${YELLOW}Cleaning tmp/ directory...${NC}"
    if [[ -d "$TMP_DIR" ]]; then
        # Preserve the directory but remove contents
        find "$TMP_DIR" -mindepth 1 -not -name '.gitkeep' -delete 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Cleaned tmp/ contents"
    fi
fi

# ---------------------------------------------------------------------------
# Clean test Git repositories
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}Cleaning test repositories...${NC}"

TEST_REPOS=(
    "${TMP_DIR}/test-repo"
    "${TMP_DIR}/test-worktrees"
    "${TMP_DIR}/event-store"
)

for repo in "${TEST_REPOS[@]}"; do
    if [[ -d "$repo" ]]; then
        rm -rf "$repo"
        echo -e "  ${GREEN}✓${NC} Removed: $(basename "$repo")"
    fi
done

echo ""
echo -e "${GREEN}Cleanup complete.${NC}"
echo ""
