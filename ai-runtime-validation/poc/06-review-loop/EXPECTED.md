# PoC 06 — Review Loop: Expected Results

## Pass Criteria

### RL-01: Feature Lifecycle State Traversal (T-04, T-05, T-06)
- Transitions strictly follow: `feature.requested` → `plan.ready` → `plan.approved` → `implementation.ready` → `review.requested` → `merge.approved`.
- Invalid state jumps (e.g., `feature.requested` → `implementation.ready`) are rejected.

### RL-02: Approval Binding Immutability
- Approval bindings securely capture the exact commit SHA and plan hash.
- Any subsequent modifications to the plan or code without re-approval fail validation.

### RL-03: Stale Approval Invalidation
- Changing code after `review.requested` or `merge.approved` automatically revokes the Approval Binding.
- System requires a new `review.requested` and `merge.approved` cycle.

### RL-04: Review/Fix Cycle Escalation (T-26)
- Receiving multiple consecutive `changes.requested` events triggers an escalation protocol (e.g., notifying the Orchestrator or human fallback).

### RL-05: Forged Approval Rejection (INV-04)
- Agent (e.g., Codex Implementer) cannot self-approve its own implementation.
- Approval bindings missing a valid cryptographic signature or originating from the wrong role (e.g., not Claude Reviewer) are rejected with `AUTHORIZATION_DENIED`.

### RL-06: Writer Lease Management
- Only one agent holds the Writer Lease at any given time.
- Implementation agent cannot write if the Planner or Reviewer holds the lease.

## Fail Criteria
- Features merged without `merge.approved` from the designated Reviewer.
- Forged approvals bypass INV-04.
- Multiple agents hold the Writer Lease concurrently causing race conditions.