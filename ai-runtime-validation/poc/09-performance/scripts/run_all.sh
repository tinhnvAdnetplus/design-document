#!/bin/bash
echo "Running PoC 09 Benchmark Suite..."
cd "$(dirname "$0")"

./measure_event_latency.sh
./measure_recovery_time.sh
./test_packet_budget.sh
./measure_event_store_growth.sh
./test_concurrent_features.sh
./compare_session_modes.sh
./generate_benchmark_report.sh

echo "Suite completed."
