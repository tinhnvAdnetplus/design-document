#!/bin/bash
# scripts/validate_schema.sh
EVENT_FILE=$1

if [ ! -f "$EVENT_FILE" ]; then
  echo "Error: File not found."
  exit 1
fi

PROTOCOL=$(jq -r '.protocol' "$EVENT_FILE")
if [ "$PROTOCOL" != "ai-runtime.events/v1" ]; then
  echo "SCHEMA_INVALID: Invalid protocol"
  exit 1
fi

REQUIRED_FIELDS=("event_id" "type" "occurred_at" "producer" "aggregate" "correlation_id" "idempotency_key" "payload")
for field in "${REQUIRED_FIELDS[@]}"; do
  if ! jq -e ".$field" "$EVENT_FILE" >/dev/null; then
    echo "SCHEMA_INVALID: Missing field $field"
    exit 1
  fi
done

echo "VALID"
exit 0
