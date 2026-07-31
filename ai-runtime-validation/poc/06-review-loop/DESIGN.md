# PoC 06 — Review Loop: Design

## Objective
Validate the state machine transitions, approval binding security, and writer lease management within a multi-agent review loop for the AI Multi-Agent Runtime V2.2.

## Experiment Design
- Trace the full feature lifecycle from `feature.requested` to `merge.completed`.
- Enforce Role-Based Access Control (RBAC) across Claude Planner, Codex Implementer, Claude Reviewer, and Merger.
- Simulate unauthorized attempts to bypass approvals (INV-04).
- Inject post-approval code modifications to validate stale approval invalidation.
- Induce a review loop stuck in `changes.requested` to test escalation mechanisms.

## Architecture Mapping
- **Approval Binding**: Cryptographic or state-backed lock securing a `merge.approved` state to a specific commit.
- **Escalation**: Mechanism within the Event Store to flag stuck loops.
- **Writer Lease**: Mutex-like lock preventing concurrent writes to the Derived State Store or Git gateway.

## Runtime Topology
Claude Planner → (Plan) → Codex Implementer → (Implementation) → Claude Reviewer → (Approval) → Merger

## Expected Behavior
- Strict linear progression unless `changes.requested` pushes state back.
- Absolute enforcement of INV-04 (no self-approval).
- Writer lease exclusively held by the active agent role during their turn.