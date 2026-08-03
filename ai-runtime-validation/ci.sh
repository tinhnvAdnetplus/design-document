#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${ROOT}/scripts/validate_environment.sh"
exec "${ROOT}/run-all.sh"
