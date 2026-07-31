# PoC 10 Design: End-to-End Flow

## Experiment Design
A unified script mimics the full lifecycle of a feature development request by interacting with simulated components (Orchestrator, Event Store, Knowledge Runtime, Capability Registry). 

## Architecture Mapping
- **Orchestrator**: Dispatches events to simulated agents (Claude Planner, Codex Implementer, Claude Reviewer, Merger).
- **Event Store**: Stores events conforming to `ai-runtime.events/v1`.
- **Knowledge Runtime**: Handles `knowledge.evolution.started` and `knowledge.snapshot.published`.
- **Session Registry**: Manages Root session and Feature session topologies.

## Runtime Topology
1. Setup initiates a Root session and tmux server.
2. Feature session is forked. Adapters (mocked) bind to tmux sessions.
3. Agents process events, generate payloads, and transition states.
4. Finally, cleanup tears down tmux sessions and Feature sessions.

## Expected Behavior
The event sequence MUST strictly follow the specification logic, carrying over `correlation_id` and appropriately updating `causation_id`. Writer Leases must prevent conflicting writes.
