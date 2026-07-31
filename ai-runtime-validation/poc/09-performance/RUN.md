# Running PoC 09

## Prerequisites
- Bash 4.4+
- `jq` for JSON processing
- standard Unix utilities (`time`, `dd`, `awk`)

## Execution Steps
Run the complete benchmark suite:
```bash
cd scripts/
./run_all.sh
```

To run individual tests:
```bash
./scripts/measure_event_latency.sh
./scripts/test_packet_budget.sh
```

## Expected Output
A formatted benchmark report detailing latency, throughput, token budget enforcement results, and session mode comparisons.
