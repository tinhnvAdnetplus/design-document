#!/usr/bin/env bash
set -Eeuo pipefail

[[ $# -eq 1 ]] || {
  printf 'usage: %s <artifact-run-directory>\n' "$0" >&2
  exit 2
}

run_dir="$(realpath "$1")"
[[ -d "$run_dir" ]] || {
  printf '[FAIL] artifact directory does not exist: %s\n' "$run_dir" >&2
  exit 1
}
[[ -f "$run_dir/manifest.sha256" ]] || {
  printf '[FAIL] manifest is missing: %s\n' "$run_dir/manifest.sha256" >&2
  exit 1
}
[[ -f "$run_dir/portable-git-evidence.json" ]] || {
  printf '[FAIL] portable Git evidence index is missing\n' >&2
  exit 1
}

if find "$run_dir" -type d -name .git -print -quit | grep -q .; then
  printf '[FAIL] live nested .git metadata remains in the evidence package\n' >&2
  exit 1
fi

(
  cd "$run_dir"
  sha256sum -c manifest.sha256
)

python3 - "$run_dir" <<'PY'
import hashlib
import json
import pathlib
import sys

BUNDLE_KEYS = {"bundle", "bundle_sha256"}
REVISION_KEYS = {"base_revision", "tested_revision"}

root = pathlib.Path(sys.argv[1])
records = json.loads((root / "portable-git-evidence.json").read_text(encoding="utf-8"))
bundles = revisions = 0
for record in records:
    if BUNDLE_KEYS <= record.keys():
        bundle = root / record["bundle"]
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        if digest != record["bundle_sha256"]:
            raise SystemExit(f"[FAIL] Git bundle checksum mismatch: {record['bundle']}")
        bundles += 1
    elif REVISION_KEYS <= record.keys():
        # Increment packages recorded a revision summary in this file before
        # it moved to revision-evidence.json. There is no bundle to hash.
        revisions += 1
    else:
        raise SystemExit(f"[FAIL] unrecognized portable evidence record: {sorted(record)}")
print(f"[PASS] portable evidence verified: {bundles} Git bundles, {revisions} revision records")
PY
