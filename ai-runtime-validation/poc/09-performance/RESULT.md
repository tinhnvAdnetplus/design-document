# PoC 09 — performance: Executed Result

- Status: **FAIL**
- Assertions: **8/9**
- Score: **88.9%**
- Executed at: `2026-08-03T03:21:10.493027Z`
- Git revision: `3cfe3261b7169b96d98dc416aa92f93aa93c8863`
- Evidence: [`artifacts/20260803T032110Z-2986e3/poc-09/report.json`](../../artifacts/20260803T032110Z-2986e3/poc-09/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| PERF-01 | FAIL | p99 < 50 ms | AssertionError: {'p50': 34.991752000000005, 'p95': 427.021412, 'p99': 657.666418} |
| PERF-02 | PASS | p99 < 100 ms | {"p50": 0.0026, "p95": 0.0044, "p99": 0.0057} |
| PERF-03 | PASS | ready evidence in <2000 ms | {"duration_ms": 34.043, "ready": true} |
| PERF-04 | PASS | 100 commits materialized in <5000 ms | {"bytes": 4902, "commits": 100, "duration_ms": 41.952} |
| PERF-05 | PASS | 131072 accepted; 131073 rejected | {"131071": "accepted", "131072": "accepted", "131073": "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED"} |
| PERF-06 | PASS | 10 distinct completed artifacts | {"duration_ms": 12.629, "flows": 10, "unique_digests": 10} |
| PERF-07 | PASS | average <2048 bytes/event | {"accept_throughput_per_second": 9.782739827537519, "bytes_per_event": 157.26666666666668} |
| PERF-08 | PASS | persistent median / cold median <0.20 | {"cold_median_ms": 19.473801, "persistent_median_ms": 0.12719999999999998, "ratio": 0.006531852718429236} |
| PERF-09 | PASS | positive peak RSS and declared workload/model mode | {"environment": {"cpu_count": 8, "model_usage": "deterministic mock; no vendor model invoked", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "python": "3.14.4"}, "peak_rss_kib": 113372, "workload": {"concur... |
