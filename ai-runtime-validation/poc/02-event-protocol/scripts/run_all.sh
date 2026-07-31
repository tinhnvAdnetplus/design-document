#!/bin/bash
# scripts/run_all.sh
set -e
chmod +x ./*.sh

rm -f ../store.ndjson

echo "=== Starting PoC 02: Event Protocol ==="

echo "--- Validating valid events ---"
for file in ../fixtures/valid_events/*.json; do
  echo "Appending $file"
  ./append_event_store.sh "$file"
done

echo "--- Validating invalid events ---"
for file in ../fixtures/invalid_events/*.json; do
  echo "Appending $file (expecting failure)"
  ./append_event_store.sh "$file" || true
done

echo "--- Testing Idempotency ---"
./test_idempotency.sh

echo "--- Replaying Projections ---"
./replay_projection.sh

echo "=== PoC 02 Complete ==="
