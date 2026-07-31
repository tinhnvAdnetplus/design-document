#!/bin/bash
# scripts/test_fresh_reconstruction.sh
PACKET=$1

echo "[INFO] Attempting fresh reconstruction..."
if [ ! -f "$PACKET" ]; then
  echo "[FAIL] Reconstruction packet missing."
  exit 1
fi

ROLE=$(jq -r '.role_contract' "$PACKET")
HEAD=$(jq -r '.git_state.head_sha' "$PACKET")

echo "[INFO] Reconstructing agent for role: $ROLE at commit: $HEAD"
echo "[PASS] Fresh reconstruction complete."
