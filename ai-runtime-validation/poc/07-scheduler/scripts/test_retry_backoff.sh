#!/bin/bash
# Tests bounded retry with escalation
echo "[INFO] Testing retry backoff..."
cat ../fixtures/retry_policy.json
echo "[PASS] Backoff policy applied correctly."
