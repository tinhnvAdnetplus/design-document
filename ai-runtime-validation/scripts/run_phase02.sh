#!/usr/bin/env bash
# =============================================================================
# run_phase02.sh — Execute Phase 2: Event Protocol Validation
# =============================================================================
#
# Runs all experiments in poc/02-event-protocol and collects evidence.
#
# Usage:
#   ./scripts/run_phase02.sh
#
# Prerequisites:
#   Phase 1 should be completed successfully.
#   ./scripts/validate_environment.sh must pass
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="$(dirname "$SCRIPT_DIR")"
POC_DIR="${VALIDATION_DIR}/poc/02-event-protocol"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "============================================="
echo "  Phase 2 — Event Protocol"
echo "  Validation Runner"
echo "============================================="
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"
for cmd in jq openssl; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}ERROR: ${cmd} is required but not installed.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} ${cmd} available"
done
echo ""

# Run PoC
echo -e "${BLUE}Executing PoC 02 — Event Protocol...${NC}"
echo ""

if [[ -x "${POC_DIR}/scripts/run_all.sh" ]]; then
    cd "$POC_DIR"
    bash scripts/run_all.sh
    EXIT_CODE=$?
else
    echo -e "${RED}ERROR: ${POC_DIR}/scripts/run_all.sh not found or not executable.${NC}"
    echo "Make it executable with: chmod +x ${POC_DIR}/scripts/run_all.sh"
    exit 1
fi

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}Phase 2 PASSED.${NC}"
else
    echo -e "${RED}Phase 2 FAILED.${NC} Review output above for details."
fi

echo ""
echo "Next steps:"
echo "  1. Record results in poc/02-event-protocol/RESULT.md"
echo "  2. Document issues in poc/02-event-protocol/ISSUES.md"
echo "  3. Update reports/phase-02-report.md"
echo "  4. Add entries to experiment-log.md"
echo ""

exit $EXIT_CODE
