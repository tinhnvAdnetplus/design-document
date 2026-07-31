#!/bin/bash
echo "Running PoC 08 Chaos Suite..."
./scripts/chaos_session_kill.sh
./scripts/chaos_event_store.sh
./scripts/chaos_worktree.sh
./scripts/chaos_merge.sh
./scripts/chaos_disk_full.sh
./scripts/chaos_clock_jump.sh
./scripts/test_recovery_order.sh
echo "All PoC 08 chaos tests complete."
