# PoC 09 Design: Performance & Budget Validation

## Experiment Design
This PoC creates synthetic loads against simulated V2.2 core components to measure performance characteristics and resource constraints. It uses mock Event Store, Cache Registry, and Session Manager interfaces that mimic expected I/O and compute boundaries.

## Architecture Mapping
- **Event Store**: Simulated via a local append-only log with configurable I/O latency.
- **Cache Registry**: Simulated file-based cache to test Cache rebuild time.
- **Session Registry**: Tracks session creation for cold vs. persistent tests.
- **Durable Delivery Queue**: Validates notify latency targets.

## Runtime Topology
A master test script (`run_all.sh`) invokes sub-benchmarks. Each sub-script focuses on a specific dimension from the Chapter 20 benchmark table.

## Expected Behavior
- Packets generated dynamically must not exceed the budgets defined in `fixtures/token_budgets.json`.
- Event Store appends must take <50ms (accept latency) and notification <100ms.
- Persistent root + fork must show significantly faster startup than cold fresh session.
