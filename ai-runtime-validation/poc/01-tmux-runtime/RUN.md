# Execution Steps: 01-tmux-runtime

## Prerequisites
- `tmux` installed on the system (version 3.0+ recommended).
- Bash shell.

## Execution Steps
1. Navigate to the script directory:
   ```bash
   cd scripts/
   ```
2. Execute the full PoC runner:
   ```bash
   ./run_all.sh
   ```
3. Alternatively, run the scripts interactively:
   ```bash
   ./create_sessions.sh
   ./check_sessions.sh
   ./send_event_notice.sh
   ./cleanup_sessions.sh
   ```

## Expected Output
The runner should output logs confirming:
- Creation of `claude-root` and feature sessions.
- Verification that sessions exist via `has-session`.
- Delivery of the event notification.
- Successful cleanup of all sessions upon completion.
