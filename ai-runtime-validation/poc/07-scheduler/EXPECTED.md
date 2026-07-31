# Expected Results

1. **Non-blocking Loop**: `test_non_blocking.sh` execution time < 100ms.
2. **Priority Ordering**: `test_priority_dispatch.sh` delivers 'critical' before 'high', before 'normal'.
3. **Backoff Schedule**: `test_retry_backoff.sh` demonstrates intervals of 2s, 4s, 8s, etc.
4. **Capacity Limits**: `test_session_registry.sh` shows events pending when session capacity is exhausted.
5. **Fairness**: `test_fairness.sh` shows no starvation for lower priority events if SLA approaches.
