# PoC 08: 08-chaos

## Objective
Validate fault tolerance and recovery behavior under various failure scenarios, proving that the architecture handles crashes, data loss, and state corruption gracefully per Chapter 23.

## Scope
- Crash before event append → event not accepted.
- Crash after append before projection → replay projects event.
- Crash after intent before execution → reconcile executes/observes once.
- Crash during tmux notify → duplicate-safe delivery.
- Crash during worktree creation → orphan detected and cleaned safely.
- Crash during merge → actual ref determines outcome.
- Disk-full cache write → old cache preserved.
- Recovery order from Chapter 23 (11-step recovery procedure).
- Dirty worktree quarantine (never auto-delete).
- Silent completion failure reconciliation.
- Lost resume IDs → fresh reconstruction succeeds.
- Clock jump → lease uses safe expiration handling.
- Adapter behavior contradicts Capability Registry → ADAPTER_UNAVAILABLE.

## Architecture Assumptions Being Validated
1. Fault Tolerance and Recovery behaviors defined in Chapter 23.
2. Invariants regarding data integrity and system recovery.
3. Proper quarantine of dirty state (never automatically destroyed).
4. Safe Lease checking robust to clock jumps.
5. Duplicate-safe tmux notification (idempotency).

## Success Criteria
- 11-step recovery procedure successfully resolves mocked crash states.
- System detects missing events/projections and safely replays.
- Dirty worktrees are quarantined rather than deleted.
- Expired fencing tokens successfully reject operations.
