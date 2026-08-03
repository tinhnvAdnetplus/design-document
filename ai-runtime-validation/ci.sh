#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${ROOT}/scripts/validate_environment.sh"
exec python3 "${ROOT}/lib/validation_lab.py" run --poc all
