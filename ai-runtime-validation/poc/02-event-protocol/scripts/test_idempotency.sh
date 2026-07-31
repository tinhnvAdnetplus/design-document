#!/bin/bash
# scripts/test_idempotency.sh
echo "[INFO] Testing idempotency constraint..."
./append_event_store.sh ../fixtures/valid_events/feature_requested.json > /dev/null
RESULT=$(./append_event_store.sh ../fixtures/valid_events/feature_requested.json)

if [[ "$RESULT" == *"IDEMPOTENCY_CONFLICT"* ]]; then
  echo "[PASS] Idempotency conflict successfully caught."
else
  echo "[FAIL] Idempotency check failed: $RESULT"
fi
