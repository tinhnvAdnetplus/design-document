#!/usr/bin/env bash
# =============================================================================
# validate_environment.sh — AI Multi-Agent Runtime V2.2 Validation Prerequisites
# =============================================================================
#
# Checks that all required tools are installed and meet minimum version
# requirements for running the PoC validation workspace.
#
# Usage:
#   ./scripts/validate_environment.sh
#
# Exit codes:
#   0 — All prerequisites met
#   1 — One or more prerequisites missing
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_command() {
    local cmd="$1"
    local min_version="$2"
    local purpose="$3"

    if command -v "$cmd" &>/dev/null; then
        local version
        case "$cmd" in
            bash)   version=$(bash --version | head -1 | grep -oP '\d+\.\d+') ;;
            tmux)   version=$(tmux -V 2>/dev/null | grep -oP '[\d.]+') ;;
            git)    version=$(git --version | grep -oP '[\d.]+') ;;
            jq)     version=$(jq --version 2>/dev/null | grep -oP '[\d.]+') ;;
            openssl) version=$(openssl version | grep -oP '[\d.]+' | head -1) ;;
            python3) version=$(python3 --version 2>/dev/null | grep -oP '[\d.]+') ;;
            *)      version="unknown" ;;
        esac
        echo -e "  ${GREEN}✓${NC} ${cmd} (${version}) — ${purpose}"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} ${cmd} (required: ${min_version}+) — ${purpose}"
        ((FAIL++))
    fi
}

check_optional() {
    local cmd="$1"
    local purpose="$2"

    if command -v "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} ${cmd} — ${purpose}"
        ((PASS++))
    else
        echo -e "  ${YELLOW}?${NC} ${cmd} — ${purpose} (optional)"
        ((WARN++))
    fi
}

echo ""
echo "============================================="
echo "  AI Multi-Agent Runtime V2.2"
echo "  Validation Environment Check"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
# Required tools
# ---------------------------------------------------------------------------
echo -e "${BLUE}Required tools:${NC}"
check_command "bash"    "4.0"  "Script execution"
check_command "tmux"    "3.0"  "Runtime substrate validation"
check_command "git"     "2.30" "Worktree and merge validation"
check_command "jq"      "1.6"  "JSON event processing"
check_command "openssl" "1.1"  "SHA-256 integrity hashing"
echo ""

# ---------------------------------------------------------------------------
# Optional tools
# ---------------------------------------------------------------------------
echo -e "${BLUE}Optional tools:${NC}"
check_optional "python3"  "Advanced fixture generation"
check_optional "sha256sum" "Alternative integrity hashing"
check_optional "bc"       "Numeric calculations in benchmarks"
check_optional "timeout"  "Command timeout for chaos testing"
echo ""

# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------
echo -e "${BLUE}Workspace structure:${NC}"

REQUIRED_DIRS=(
    "poc/01-tmux-runtime"
    "poc/02-event-protocol"
    "poc/03-session-resume"
    "poc/04-capability-registry"
    "poc/05-knowledge-runtime"
    "poc/06-review-loop"
    "poc/07-scheduler"
    "poc/08-chaos"
    "poc/09-performance"
    "poc/10-end-to-end"
    "reports"
    "scripts"
    "fixtures"
    "tmp"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "${VALIDATION_DIR}/${dir}" ]]; then
        echo -e "  ${GREEN}✓${NC} ${dir}/"
    else
        echo -e "  ${RED}✗${NC} ${dir}/ (missing)"
        ((FAIL++))
    fi
done
echo ""

# ---------------------------------------------------------------------------
# Architecture specification
# ---------------------------------------------------------------------------
echo -e "${BLUE}Architecture specification:${NC}"
SPEC_DIR="${VALIDATION_DIR}/../docs"
if [[ -d "$SPEC_DIR" ]]; then
    echo -e "  ${GREEN}✓${NC} docs/ directory found"
    if [[ -f "${SPEC_DIR}/README.md" ]]; then
        echo -e "  ${GREEN}✓${NC} docs/README.md (specification entry point)"
    else
        echo -e "  ${RED}✗${NC} docs/README.md missing"
        ((FAIL++))
    fi
else
    echo -e "  ${RED}✗${NC} docs/ directory not found — specification required"
    ((FAIL++))
fi
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================="
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "============================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}Environment check FAILED.${NC} Install missing prerequisites before running PoCs."
    exit 1
else
    echo -e "${GREEN}Environment check PASSED.${NC} Ready to execute validation PoCs."
    exit 0
fi
