#!/bin/bash
# scripts/replay_projection.sh
STORE_FILE="../store.ndjson"

echo "[INFO] Replaying Event Store..."
if [ ! -f "$STORE_FILE" ]; then
  echo "No events to replay."
  exit 0
fi

cat "$STORE_FILE" | while read -r line; do
  TYPE=$(echo "$line" | jq -r '.type')
  AGG=$(echo "$line" | jq -r '.aggregate.id')
  SEQ=$(echo "$line" | jq -r '.aggregate.sequence')
  echo "State Update: [$AGG @ $SEQ] -> $TYPE"
done
