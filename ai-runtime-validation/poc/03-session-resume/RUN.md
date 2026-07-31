# Execution Steps: 03-session-resume

## Prerequisites
- Bash shell.
- jq for JSON parsing.
- tmux for session simulation.

## Execution Steps
1. Navigate to the scripts directory:
   ```bash
   cd scripts/
   ```
2. Run the master orchestration script:
   ```bash
   ./run_all.sh
   ```

## Expected Output
- Reattach test attempts and succeeds (or fails over properly).
- Capability registry is queried for `resume=true`.
- Fresh reconstruction packet is generated from fixtures.
- Dirty worktree test successfully creates a simulated quarantine directory.
