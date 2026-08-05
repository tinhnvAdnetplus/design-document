#!/usr/bin/env bash
# Opt-in only. This PoC consumes authenticated model quota and is deliberately
# excluded from run-all.sh and ci.sh.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${ROOT}/scripts/live_contract_probe.py" "$@"
