# PoC 09 — performance: Executed Result

- Status: **PASS**
- Assertions: **9/9**
- Score: **100.0%**
- Executed at: `2026-08-03T07:21:47.380026Z`
- Git revision: `1ee96f7dc65c3737c3bda7e28f5b23df75e10d0e`
- Evidence: [`artifacts/20260803T072146Z-2fd45e/poc-09/report.json`](../../artifacts/20260803T072146Z-2fd45e/poc-09/report.json)

## Assertion evidence

| ID | Status | Expected | Observed |
| --- | --- | --- | --- |
| PERF-01 | PASS | p99 < 50 ms | {"p50": 9.0715, "p95": 20.9457, "p99": 32.6408} |
| PERF-02 | PASS | p99 < 100 ms | {"p50": 0.0028, "p95": 0.0046, "p99": 0.0062} |
| PERF-03 | PASS | ready evidence in <2000 ms | {"duration_ms": 43.003, "ready": true} |
| PERF-04 | PASS | 100 commits materialized in <5000 ms | {"bytes": 4902, "commits": 100, "duration_ms": 17.478} |
| PERF-05 | PASS | 131072 accepted; 131073 rejected | {"131071": "accepted", "131072": "accepted", "131073": "SCHEMA_INVALID:PACKET_BUDGET_EXCEEDED"} |
| PERF-06 | PASS | 10 distinct completed artifacts | {"duration_ms": 25.38, "flows": 10, "unique_digests": 10} |
| PERF-07 | PASS | average <2048 bytes/event | {"accept_throughput_per_second": 83.27112961446439, "bytes_per_event": 157.26666666666668} |
| PERF-08 | PASS | persistent median / cold median <0.20 | {"cold_median_ms": 20.5079, "persistent_median_ms": 0.1177, "ratio": 0.005739251703002258} |
| PERF-09 | PASS | positive peak RSS and declared workload/model mode | {"environment": {"cpu_count": 8, "model_usage": "deterministic mock; no vendor model invoked", "platform": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "python": "3.14.4"}, "peak_rss_kib": 119324, "workload": {"concur... |
