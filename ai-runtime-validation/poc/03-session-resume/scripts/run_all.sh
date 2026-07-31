#!/bin/bash
# scripts/run_all.sh
set -e
chmod +x ./*.sh

echo "=== Starting PoC 03: Session Resume ==="

# 1. Test Reattach
tmux -L ai-runtime new-session -d -s test-resume
./test_reattach.sh test-resume

# 2. Simulate Loss
./simulate_session_loss.sh test-resume
./test_reattach.sh test-resume || echo "[INFO] Expected reattach failure."

# 3. Check Capability
RESUME_CAP=$(jq -r '.capabilities.resume' ../fixtures/capability_document.json)
echo "[INFO] Capability registry resume= $RESUME_CAP"

# 4. Fresh Reconstruction
PACKET_FILE="../fixtures/feature_reconstruction_packet.json"
./test_fresh_reconstruction.sh "$PACKET_FILE"

# 5. Dirty Worktree
./test_dirty_worktree.sh

echo "=== PoC 03 Complete ==="
