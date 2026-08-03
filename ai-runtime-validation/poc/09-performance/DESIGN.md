# PoC 09 Design: Performance & Budget Validation

## Experiment Design
This PoC creates deterministic local loads against executable V2.2 contract boundaries. It measures actual file append/fsync, in-process notification, Git history traversal, process readiness, concurrency, packet-size enforcement, storage growth, and persistent-process dispatch.

## Architecture Mapping
- **Event Store**: Local append-only log with real writes, flushes, and `fsync` timing.
- **Cache Registry**: File-based cache rebuilt from an actual 100-commit disposable Git history.
- **Session Registry**: Compares actual process startup with a persistent worker dispatch.
- **Durable Delivery Queue**: Validates notify latency targets.

## Runtime Topology
A master test script (`run_all.sh`) invokes sub-benchmarks. Each sub-script focuses on a specific dimension from the Chapter 20 benchmark table.

## Expected Behavior
- Packets generated dynamically must not exceed the budgets defined in `fixtures/token_budgets.json`.
- Event Store appends must take <50ms (accept latency) and notification <100ms.
- Persistent root + fork must show significantly faster startup than cold fresh session.
