# PoC 09 — performance: Executed Result

- Status: **FAIL**
- Assertions: **8/9**
- Score: **88.9%**
- Executed at: `2026-08-05T03:32:47.076508Z`
- Git revision: `b72d2c36c026f89f521e9a0ab17f9c28ace27df2`
- Evidence: [`artifacts/20260805T033246Z-ab38bb/poc-09/report.json`](../../artifacts/20260805T033246Z-ab38bb/poc-09/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| PERF-01 | FAIL | p99 < 50 ms | AssertionError: {'p50': 294.2999485, 'p95': 507.780056, 'p99': 722.113552} |
| PERF-02 | PASS | p99 < 100 ms | {"p50": 0.00265, "p95": 0.0045, "p99": 0.0065} |
| PERF-03 | PASS | ready evidence in <2000 ms | {"duration_ms": 35.076, "ready": true} |
| PERF-04 | PASS | 100 commits materialized in <5000 ms | {"bytes": 4902, "commits": 100, "duration_ms": 18.401} |
| PERF-05 | PASS | 131072 accepted; 131073 rejected | {"131071": "accepted", "131072": "accepted", "131073": "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED"} |
| PERF-06 | PASS | 10 distinct completed artifacts | {"duration_ms": 14.135, "flows": 10, "unique_digests": 10} |
| PERF-07 | PASS | average <2048 bytes/event | {"accept_throughput_per_second": 3.1070627206822135, "bytes_per_event": 157.26666666666668} |
| PERF-08 | PASS | persistent median / cold median <0.20 | {"cold_median_ms": 38.3304035, "persistent_median_ms": 0.09295, "ratio": 0.0024249679500504082} |
| PERF-09 | PASS | positive peak RSS and declared workload/model mode | {"environment": {"cpu_count": 8, "model_usage": "deterministic mock; no vendor model invoked", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "python": "3.14.4"}, "peak_rss_kib": 36984, "workload": {"concurr... |
