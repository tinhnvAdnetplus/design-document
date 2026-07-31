#!/bin/bash
# scripts/test_dirty_worktree.sh

WORKTREE="/tmp/mock_worktree"
mkdir -p "$WORKTREE"
echo "dirty" > "$WORKTREE/uncommitted_file.txt"

echo "[INFO] Checking worktree status..."
if [ -n "$(ls -A $WORKTREE)" ]; then
  QUARANTINE="/tmp/quarantine-$(date +%s)"
  echo "[WARN] Dirty worktree detected. Moving to quarantine: $QUARANTINE"
  mv "$WORKTREE" "$QUARANTINE"
  echo "[PASS] Worktree quarantined successfully."
else
  echo "[PASS] Worktree clean."
fi
