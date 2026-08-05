#!/usr/bin/env bash
# CI entrypoint. With no arguments it runs the whole suite, exactly as before.
# Pass PoC numbers to run a subset, e.g. `ci.sh 01 02 09`.
#
# Unlike run-selected.sh this never passes --record, so it does not mutate
# RESULT.md or experiment-log.md.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${ROOT}/scripts/validate_environment.sh"

if [[ $# -eq 0 ]]; then
  exec python3 "${ROOT}/lib/validation_lab.py" run --poc all
fi

args=()
for poc in "$@"; do
  args+=(--poc "$poc")
done
exec python3 "${ROOT}/lib/validation_lab.py" run "${args[@]}"
