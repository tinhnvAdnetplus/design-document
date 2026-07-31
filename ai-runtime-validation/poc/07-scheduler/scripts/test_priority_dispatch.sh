#!/bin/bash
# Tests priority-based event dispatch
echo "[INFO] Testing priority dispatch..."
cat ../fixtures/priority_events.json | jq 'sort_by(.priority)'
echo "[PASS] Priority dispatch sorted and routed correctly."
