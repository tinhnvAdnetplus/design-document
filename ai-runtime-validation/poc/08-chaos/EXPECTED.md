# Expected Results

1. **Recovery Order**: `test_recovery_order.sh` completes all 11 steps sequentially.
2. **Disk Full**: `chaos_disk_full.sh` leaves previous cache untouched.
3. **Dirty Worktree**: `chaos_worktree.sh` marks folder as `.quarantined`.
4. **Clock Skew**: `chaos_clock_jump.sh` invalidates the active lease and fencing token.
5. **Event Store Replay**: `chaos_event_store.sh` successfully re-projects unprojected events.
