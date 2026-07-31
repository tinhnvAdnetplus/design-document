# Measurable Pass Criteria: 03-session-resume

## 1. Reattach vs Reconstruction
- The recovery script prioritizes reattach.
- If the session does not exist, it falls back to reconstruction.

## 2. Capability Validation
- Resume is only attempted if `capability_document.json` declares `"resume": true`.

## 3. Fresh Reconstruction
- The `build_reconstruction_packet.sh` script successfully assembles a payload including repository identity, role contract, and cache references.

## 4. Dirty Worktree Quarantine
- If uncommitted changes exist (simulated via file flags), the script moves the worktree to a quarantine path (e.g., `quarantine-<timestamp>`) rather than discarding work.
