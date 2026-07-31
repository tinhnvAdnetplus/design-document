#!/bin/bash
echo "Running PoC 07 Suite..."
./scripts/simulate_delivery_queue.sh
./scripts/test_priority_dispatch.sh
./scripts/test_retry_backoff.sh
./scripts/test_non_blocking.sh
./scripts/test_session_registry.sh
./scripts/test_fairness.sh
echo "All PoC 07 tests complete."
