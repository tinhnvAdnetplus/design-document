#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

for tool in bash git tmux jq python3 sha256sum timeout; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '[PASS] ENV command available: %s (%s)\n' "$tool" "$(command -v "$tool")"
  else
    printf '[FAIL] ENV missing required command: %s\n' "$tool" >&2
    failures=$((failures + 1))
  fi
done

if python3 -c 'import jsonschema' >/dev/null 2>&1; then
  printf '[PASS] ENV Python Draft-07 JSON Schema validator available\n'
else
  printf '[FAIL] ENV Python package jsonschema is required\n' >&2
  failures=$((failures + 1))
fi

for path in "$ROOT/lib/validation_lab.py" "$ROOT/run-all.sh" "$ROOT/run-selected.sh" "$ROOT/../docs/README.md"; do
  if [[ -e "$path" ]]; then
    printf '[PASS] ENV required path exists: %s\n' "$path"
  else
    printf '[FAIL] ENV required path missing: %s\n' "$path" >&2
    failures=$((failures + 1))
  fi
done

(( failures == 0 )) || exit 1
printf '[PASS] ENV all executable prerequisites verified\n'
