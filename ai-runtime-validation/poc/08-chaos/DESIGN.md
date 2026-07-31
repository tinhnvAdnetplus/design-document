# Experiment Design: Chaos & Fault Tolerance

## Architecture Mapping
- **Event Store**: Immutable append-only log, source of truth.
- **Derived State Store**: Projections rebuilt on failure.
- **Cache Registry**: Handles disk-full conditions gracefully.
- **Session Lineage Graph**: Determines resume capability.

## Runtime Topology
- Fault injection scripts mimicking sudden termination, disk constraints, and clock drift.
- Recovery scripts implementing Chapter 23 11-step procedure.

## Expected Behavior
1. A crash during `knowledge.evolution.started` leaves a dirty worktree; upon restart, system quarantines it.
2. Clock jump past a Writer Lease expiration causes subsequent commits to fail with Authorization Denied.
3. Disk full during cache write gracefully falls back to not caching, preserving old valid cache.
