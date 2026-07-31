#!/bin/bash
echo "Running PoC 10 End-to-End Suite..."
cd "$(dirname "$0")"

./setup_end_to_end.sh
./simulate_feature_request.sh
./simulate_implementation.sh
./simulate_review.sh
./simulate_merge.sh
./verify_invariants.sh
./verify_event_chain.sh
./verify_cleanup.sh
./generate_report.sh

echo "End-to-End Suite completed."
