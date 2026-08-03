# Experiment Design: Eligibility Scheduler & Dispatcher

## Architecture Mapping
- **Eligibility Scheduler**: Determines which events are ready for delivery based on SLA, retry backoff, and priority.
- **Dispatcher**: Delivers eligible events to target sessions.
- **Durable Delivery Queue**: Stores pending deliveries with metadata (attempts, next_retry).
- **Session Registry**: Tracks session state, capacity, and role (e.g., Claude Planner, Codex Implementer).

## Runtime Topology
- Deterministic Orchestrator tick over a file-backed delivery queue (bounded and non-blocking).
- Event Store -> Durable Delivery Queue -> Dispatcher -> Session (tmux).

## Expected Behavior
1. High-priority events bypass normal-priority queues.
2. Events failing delivery are retried with exponential backoff until escalation.
3. Sessions report their capacity; Dispatcher skips at-capacity sessions.
4. Orchestrator completes its tick in bounded time, never waiting for agent responses.
