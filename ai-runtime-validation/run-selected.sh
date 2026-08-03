#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ $# -ge 1 ]] || { printf 'usage: %s <01> [02 ...]\n' "$0" >&2; exit 2; }
args=()
for poc in "$@"; do
  args+=(--poc "$poc")
done
exec python3 "${ROOT}/lib/validation_lab.py" run "${args[@]}" --record
