# Experiment Design: 03-session-resume

## Architecture Mapping
According to Chapter 23, recovery handles unexpected session loss via a three-tier fallback:
1. **Reattach**: Session still running, client just disconnected.
2. **Resume**: Adapter/Vendor supports stateful resume (if `resume=true` in Capability Registry).
3. **Fresh Reconstruction**: Total loss, rebuild state from Git and Event Store.

## Runtime Topology
1. Scripts simulating a capability registry lookup.
2. A simulated "dirty worktree" state representing a crash during an edit.
3. Git-derived reconstruction packets acting as the source of truth.

## Expected Behavior
- Simulating a crash terminates the tmux session.
- If reattach fails, the system checks capabilities.
- Even if resume capabilities exist, fresh reconstruction must work if resume is skipped or fails.
- Fresh reconstruction uses the `reconstruction_packet.json` to rebuild context.
- A dirty worktree prompts the creation of a quarantine directory to prevent data loss.
