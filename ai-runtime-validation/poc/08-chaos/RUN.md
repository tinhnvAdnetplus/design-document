# Execution Steps: PoC 08

## Prerequisites
- Bash 4.4+
- `jq` installed

## Steps
1. Run `scripts/run_all.sh` to execute the chaos suite.
2. Or run individual scripts:
   - `./scripts/chaos_session_kill.sh`
   - `./scripts/chaos_event_store.sh`
   - `./scripts/chaos_worktree.sh`
   - `./scripts/chaos_merge.sh`
   - `./scripts/chaos_disk_full.sh`
   - `./scripts/chaos_clock_jump.sh`
   - `./scripts/test_recovery_order.sh`

## Expected Output
The recovery scripts should detect the simulated failures and apply the Chapter 23 resolution steps, logging `[PASS]` for each.
