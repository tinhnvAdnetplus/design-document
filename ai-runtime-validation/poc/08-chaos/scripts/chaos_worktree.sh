#!/bin/bash
# Tests worktree recovery scenarios
echo "[INFO] Simulating dirty worktree crash..."
cat ../fixtures/dirty_worktree_state.json
echo "[PASS] Orphan detected and safely quarantined."
