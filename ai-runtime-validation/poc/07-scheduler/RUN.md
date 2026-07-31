# Execution Steps: PoC 07

## Prerequisites
- Bash 4.4+
- `jq` installed for JSON processing

## Steps
1. Run `scripts/run_all.sh` to execute the entire suite.
2. Alternatively, run individual scripts:
   - `./scripts/simulate_delivery_queue.sh`
   - `./scripts/test_priority_dispatch.sh`
   - `./scripts/test_retry_backoff.sh`
   - `./scripts/test_non_blocking.sh`
   - `./scripts/test_session_registry.sh`
   - `./scripts/test_fairness.sh`

## Expected Output
All scripts should report `[PASS]` for their respective validation constraints.
