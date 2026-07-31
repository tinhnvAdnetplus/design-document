#!/bin/bash
# scripts/append_event_store.sh
EVENT_FILE=$1
STORE_FILE="../store.ndjson"

VALIDATION_RESULT=$(./validate_schema.sh "$EVENT_FILE")
if [ "$VALIDATION_RESULT" != "VALID" ]; then
  echo "$VALIDATION_RESULT"
  exit 1
fi

IDEMPOTENCY_KEY=$(jq -r '.idempotency_key' "$EVENT_FILE")

if [ -f "$STORE_FILE" ]; then
  if grep -q "\"idempotency_key\": \"$IDEMPOTENCY_KEY\"" "$STORE_FILE"; then
    echo "IDEMPOTENCY_CONFLICT: Event already exists"
    exit 1
  fi
fi

jq -c . "$EVENT_FILE" >> "$STORE_FILE"
echo "APPEND_SUCCESS"
exit 0
