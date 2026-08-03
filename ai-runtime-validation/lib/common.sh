#!/usr/bin/env bash
set -Eeuo pipefail

VALIDATION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export VALIDATION_ROOT

die() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

utc_timestamp() {
  date -u +%Y%m%dT%H%M%SZ
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

run_poc() {
  local poc="$1"
  shift || true
  require_command python3
  exec python3 "${VALIDATION_ROOT}/lib/validation_lab.py" run --poc "$poc" "$@"
}
