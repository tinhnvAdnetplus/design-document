# Expected Results: PoC 09

## Measurable Pass Criteria
1. **Event Accept Latency**: 99th percentile < 50ms.
2. **Notify Latency**: 99th percentile < 100ms.
3. **Recovery Time**: < 2000ms from process start to ready state.
4. **Cache Rebuild Time**: < 5000ms for standard 100-commit range.
5. **Token/Prompt Budget**: Packets > 128 KiB MUST be rejected with error `SCHEMA_INVALID` or specific budget exception.
6. **Concurrent Features**: System successfully orchestrates 10 concurrent non-conflicting feature flows without degradation.
7. **Event Store Growth**: Average bytes/event < 2KB.
8. **Session Mode Comparison**: Persistent root + fork latency < 20% of cold fresh session setup latency.
