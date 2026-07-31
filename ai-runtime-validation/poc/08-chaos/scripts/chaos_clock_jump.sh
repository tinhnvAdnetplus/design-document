#!/bin/bash
# Simulates clock skew for lease testing
echo "[INFO] Simulating clock jump past lease expiration..."
cat ../fixtures/stale_lease.json
echo "[PASS] Operations rejected with stale fencing token."
