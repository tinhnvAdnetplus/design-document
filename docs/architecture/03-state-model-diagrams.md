# 03 — State Model and Diagrams

## Purpose

This chapter formalizes runtime state. It defines aggregates, transition rules,
and diagrams that prevent an implementation from progressing an invalid feature.

## Design approach

Runtime state is an event-sourced control projection, not a replacement for Git
state. A feature aggregate answers “what may happen next?” while Git answers
“what code and history exist?” The projection never manufactures source truth;
it records authority, lifecycle, delivery, and recovery evidence.

## Aggregate model

| Aggregate | Key | Owns | Does not own |
| --- | --- | --- | --- |
| Feature | feature ID | workflow stage, plan/head/base, review cycle | source contents |
| Session | session ID | role, adapter status, terminal identity, lifecycle | Git branch truth |
| Lease | lease ID | resource, holder, expiry, fencing token | permission policy |
| Delivery | delivery ID | target, attempt, acknowledgement | event validity |
| Knowledge Cache | root ID | Git range and derived knowledge version | repository truth |
| Knowledge snapshot | root ID and version | bounded domain facts and provenance | transcript history |
| Lineage node | session ID | parent/child fork or reconstruction relation | permissions or delivery route |
| Merge | merge ID | candidate, approval binding, integration result | approval authority |

A projection MUST retain the event IDs that produced each field. If two events
attempt an incompatible transition, the projection records a conflict rather
than choosing by arrival time alone.

## Feature state machine

~~~mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Planning: feature.requested accepted
    Planning --> PlanReady: plan.ready
    PlanReady --> AwaitingPlanApproval: policy requires gate
    AwaitingPlanApproval --> Implementing: plan.approved
    PlanReady --> Implementing: automatic low-risk policy
    Implementing --> AwaitingReview: implementation.ready
    AwaitingReview --> Implementing: changes.requested
    AwaitingReview --> Approved: merge.approved
    Approved --> Merging: merge.started
    Merging --> Merged: merge.completed success
    Merging --> MergeFailed: merge.completed failure
    MergeFailed --> Implementing: rebase or fix required
    Requested --> Abandoned: feature.cancelled
    Planning --> Abandoned: feature.cancelled
    PlanReady --> Abandoned: feature.cancelled
    Implementing --> Abandoned: feature.cancelled
    AwaitingReview --> Abandoned: feature.cancelled
    Approved --> Abandoned: approval invalidated and cancellation
    Merged --> Synchronizing: root sync scheduled
    Synchronizing --> Completed: all required roots synchronized
    Abandoned --> [*]
    Completed --> [*]
~~~

A feature MAY be marked blocked as an overlay state while retaining its last
business stage. A block includes code, owner, evidence event, and expiry or
operator action. A block MUST prevent automatic side effects but not forensic
inspection.

The `AwaitingReview -> Implementing` edge is bounded. The projection counts
`changes.requested` as fix cycles and `implementation.ready` as dispatch rounds.
When fix cycles reach `policy.review.max_fix_cycles`, the Runtime appends
`feature.blocked` instead of traversing that edge again. `feature.unblocked`
clears the overlay and records a new bounded allowance; neither event changes
the business stage, and neither may be inferred from an idle terminal.

## Session state machine

~~~mermaid
stateDiagram-v2
    [*] --> Provisioning
    Provisioning --> Starting: tmux allocated
    Starting --> Ready: adapter health evidence
    Starting --> Failed: launch failure
    Ready --> Busy: delivery acknowledged
    Busy --> Ready: reconciled terminal event or explicit deferral
    Ready --> Draining: terminal cleanup requested
    Busy --> Draining: terminal cleanup requested
    Draining --> Terminated: tmux destroyed and leases released
    Ready --> Unavailable: heartbeat/reconcile failure
    Busy --> Unavailable: process failure
    Busy --> Unavailable: task deadline without terminal event
    Unavailable --> Resuming: exceptional resume allowed
    Resuming --> Ready: resume verified
    Resuming --> Reconstructing: resume absent or invalid
    Reconstructing --> Ready: fresh session verified
    Reconstructing --> Failed: reconstruction failure
    Failed --> [*]
    Terminated --> [*]
~~~

Busy is an observation state, not a lock on workflow progress. An agent can be
busy while an unrelated event is stored for later delivery. The orchestrator
MUST not synchronously wait for it to become ready.

## Lease state machine

~~~mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Granted: authorization and resource free
    Requested --> Denied: policy or conflict
    Granted --> Renewing: holder requests extension
    Renewing --> Granted: renewal accepted
    Renewing --> Expired: deadline reached
    Granted --> Released: holder or terminal cleanup
    Granted --> Revoked: policy or incident action
    Denied --> [*]
    Released --> [*]
    Expired --> [*]
    Revoked --> [*]
~~~

Each write-bearing operation carries a fencing token. The worktree and Git
gateway reject a command with a token lower than the current granted token.
Expiry alone is not enough when a paused process resumes after a newer writer
received the lease.

## Event handling state machine

~~~mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Rejected: schema or policy invalid
    Received --> Stored: append durable event
    Stored --> Projected: update aggregate
    Projected --> PendingDelivery: target identified
    PendingDelivery --> Delivered: adapter accepted notice
    PendingDelivery --> RetryWait: transient delivery failure
    RetryWait --> PendingDelivery: retry schedule
    Delivered --> Acknowledged: consumer acknowledgement
    Delivered --> Expired: acknowledgement deadline
    Acknowledged --> [*]
    Rejected --> [*]
    Expired --> [*]
~~~

Delivery success only means the adapter accepted the notice. It does not mean
the agent understood, acted, or produced a successor event. Acknowledgement is
a protocol-level record; a resulting workflow event is stronger evidence.

## Core sequence: successful feature

~~~mermaid
sequenceDiagram
    participant H as Human/Policy
    participant O as Orchestrator
    participant CP as Claude Planner
    participant CI as Codex Implementer
    participant CR as Claude Reviewer
    participant M as Merger
    participant G as Git
    participant R as Roots

    H->>O: feature.requested
    O->>O: validate, append, project
    O-->>CP: event notice
    CP->>O: plan.ready
    O-->>CI: plan.approved / event notice
    CI->>G: commit feature branch
    CI->>O: implementation.ready(head, base)
    O-->>CR: review.requested
    CR->>O: merge.approved(binding)
    O->>M: merge command
    M->>G: validate and merge
    M->>O: merge.completed
    O-->>R: knowledge.sync.requested
    R->>G: inspect integrated range
    R->>O: knowledge.synchronized
~~~

## Complete V2 runtime sequence

~~~mermaid
sequenceDiagram
    participant O as Control Loop
    participant CP as Claude Root/Planner
    participant CI as Codex Root/Implementer
    participant CR as Claude Reviewer
    participant M as Merger
    participant K as Knowledge Runtime
    participant G as Git

    O->>CP: fork planning packet
    CP->>O: plan.ready
    O->>CI: fork implementation packet and writer lease
    CI->>G: commit feature head
    CI->>O: implementation.ready
    O->>CR: review packet
    alt changes requested
        CR->>O: changes.requested
        O->>CI: retry implementation notice
        CI->>O: implementation.ready(new head)
        O->>CR: review packet
    end
    CR->>O: merge.approved
    O->>M: eligible merge intent
    M->>G: integrate exact reviewed head
    M->>O: merge.completed
    O->>K: synchronize/evolve snapshots
    K->>G: collect integrated evidence
    K->>O: knowledge.synchronized
    O->>CP: publish snapshot, destroy feature child, idle
    O->>CI: publish snapshot, destroy feature child, idle
    Note over K,G: Optional metadata-only Root Update Commit
~~~

This is a lifecycle summary. Its retry branch does not preserve a stale approval
and its final commit is never an application-code commit.

## Core sequence: crash and reconstruction

~~~mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as State/Event Store
    participant T as tmux
    participant G as Git
    participant A as New Adapter Session

    O->>T: health check
    T-->>O: session absent
    O->>S: record session.unavailable
    O->>G: inspect branch, worktree, and HEAD
    G-->>O: committed head and dirty-state result
    O->>S: expire lease / project recovery plan
    O->>A: start fresh session with reconstruction packet
    A->>O: session.ready
    O->>S: record recovery.completed
~~~

The new session receives Git facts and a compact cache, not a blind transcript
replay. If a dirty feature worktree exists, recovery stops for human or policy
decision; it MUST NOT discard or auto-commit unknown changes.

## Component relationship diagram

~~~mermaid
classDiagram
    class Orchestrator {
      +accept(event)
      +project(event)
      +schedule(delivery)
      +reconcile()
    }
    class EventLog {
      +append(event)
      +read(stream, offset)
    }
    class PolicyEngine {
      +authorize(subject, action, resource)
      +validateTransition(state, event)
    }
    class Adapter {
      +start(spec)
      +fork(spec)
      +notify(eventRef)
      +resume(spec)
      +stop(session)
    }
    class WorktreeManager {
      +create(feature)
      +grantLease(session)
      +releaseLease(lease)
    }
    class GitGateway {
      +status(worktree)
      +verify(commit)
      +merge(candidate)
    }
    Orchestrator --> EventLog
    Orchestrator --> PolicyEngine
    Orchestrator --> Adapter
    Orchestrator --> WorktreeManager
    Orchestrator --> GitGateway
~~~

## Transition validation

A transition is accepted only if all conditions hold:

1. The event schema and version are supported.
2. The sender identity matches the authenticated session record.
3. The role holds the required capability.
4. The aggregate is in an allowed prior state.
5. Referenced commits, branches, leases, and policy revision resolve.
6. The causation chain is valid or the event is explicitly root-caused.
7. Idempotency checks show the event is new or equivalent.
8. Side-effect preconditions are re-evaluated immediately before execution.

A validation failure produces an event rejection. It must not be represented as
an agent failure unless the event indicates compromise or repeated misuse.

## Derived-state rebuild

Projection rebuilding processes events in stable order: stream sequence first,
then recorded timestamp only for diagnostics. It validates event hash and schema
against the versioned registry. A state rebuild MUST produce the same feature
terminal state for the same accepted event stream and policy revision.

If historical policy is unavailable, the implementation MUST mark the projection
policy-unverified. It MAY reconstruct operational visibility but MUST NOT
automatically merge or grant new permissions from that projection.

## Session lineage projection

~~~mermaid
flowchart TD
    CR[Claude Root] -->|fork, snapshot 41| CP[Planner: feature 0042]
    CR -->|fork, snapshot 41| RV[Reviewer: feature 0042]
    XR[Codex Root] -->|fork, snapshot 39| CI[Implementer: feature 0042]
    CI -.->|reconstruction lineage| CI2[Implementer retry: feature 0042]
~~~

Solid edges are fork lineage; dashed edges are fresh reconstruction lineage.
This graph is a projection over session events and carries no transport or
authority semantics.

## Trade-offs and extensions

Finite state machines make invalid paths explicit but require migration effort
when the workflow evolves. The runtime favors explicit state over ad-hoc flags
because recovery, metrics, and authorization rely on a common answer to the
question of what happens next.

Future implementations may use a durable workflow engine or database
transactions. They must preserve append-only evidence, idempotent delivery, and
fencing. They must not hide an approval, lease grant, or merge behind an opaque
queue action.
