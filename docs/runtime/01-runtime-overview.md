# 05 — Runtime Overview and Requirements

## Purpose

This chapter defines the runtime execution model and requirements for a
conforming local deployment. It connects the architecture to implementable
interfaces without prescribing a programming language.

## Runtime model

The runtime has four planes.

| Plane | Purpose | Main artifacts |
| --- | --- | --- |
| Control plane | accept events and coordinate deterministic actions | policy, state projection, leases |
| Execution plane | host interactive CLI processes | tmux sessions, adapters, worktrees |
| Evidence plane | preserve workflow facts | event log, Git commits, check reports |
| Context plane | provide bounded derived understanding | root caches, plan and review packets |

The planes are intentionally separate. A CLI process can be unavailable while
the control and evidence planes continue recording or reconciling facts. A
cache can be discarded without invalidating a Git commit.

## Functional requirements

| ID | Requirement | Rationale | Acceptance evidence |
| --- | --- | --- | --- |
| RT-01 | Start one named root session for each enabled adapter. | stable project context | root records and terminal inspection |
| RT-02 | Keep roots alive during normal development. | avoid repeated initialization | no start cycle per feature |
| RT-03 | Create feature sessions as forks. | bound context | fork operation event and metadata |
| RT-04 | Use one worktree per writable feature session. | isolate edits | worktree lease test |
| RT-05 | Deliver inter-agent notices asynchronously. | avoid global stalls | sender returns after durable route |
| RT-06 | Persist accepted events before side effects. | recovery and audit | crash injection test |
| RT-07 | Require structured approval for integration. | prevent ambiguous merge | authorization test |
| RT-08 | Destroy terminal feature sessions. | prevent context inflation | cleanup event and absent terminal |
| RT-09 | Update root cache only from post-merge evidence. | cache correctness | provenance test |
| RT-10 | Reconstruct with no CLI resume IDs. | vendor-independent recovery | lost-ID scenario |
| RT-11 | Expose health, delivery, lease, and token metrics. | operability | metrics contract test |
| RT-12 | Reject unsupported or unauthorized events. | protocol safety | negative schema suite |

## Non-functional requirements

| ID | Objective | Target or rule | Measurement |
| --- | --- | --- | --- |
| NFR-01 | Event acceptance | durable append before acknowledgement | fault injection |
| NFR-02 | Delivery latency | local p95 under configured target, default 2 s | event timestamps |
| NFR-03 | Isolation | no overlapping writer leases | concurrency suite |
| NFR-04 | Recovery | no resume ID required | simulated host reboot |
| NFR-05 | Audit | trace merge to review, commits, policy | event graph query |
| NFR-06 | Privacy | no raw prompt logging by default | log inspection |
| NFR-07 | Availability | failure of one adapter does not stop others | process-kill test |
| NFR-08 | Compatibility | versioned schemas and capabilities | old event fixture |
| NFR-09 | Capacity | bounded queues and cache sizes | load test |
| NFR-10 | Determinism | policy decisions reproduce from evidence | projection replay |

Targets are deployment-specific configuration, not promises about model latency.
The runtime MUST record measured values and protect itself with deadlines,
queue limits, and backpressure.

## Runtime interfaces

~~~text
Orchestrator
  accept(event) -> accepted | rejected
  status(aggregate) -> projection
  reconcile() -> report

Adapter
  capabilities() -> capability document
  start(session spec) -> observation
  fork(fork spec) -> observation
  notify(event reference) -> delivery observation
  resume(recovery spec) -> observation
  stop(session spec) -> observation

Git gateway
  create_worktree(feature)
  inspect(worktree or commit)
  commit_guard(lease token)
  merge(approved candidate)

Policy engine
  authorize(subject, action, resource, context)
  validate_transition(state, event)
  validate_merge(binding)
~~~

An interface returns structured observations and error codes. It MUST NOT require
callers to parse a natural-language terminal pane as a protocol response.

## Startup sequence

1. Load immutable configuration and verify file permissions.
2. Open or rebuild state projection from the event log.
3. Inspect configured Git repository, integration ref, and registered worktrees.
4. Reconcile any active leases against live processes and Git state.
5. Start or attach root sessions in deterministic adapter order.
6. Verify root readiness with adapter-specific evidence.
7. Mark ready roots available for fork requests and root-sync events.
8. Publish runtime health only after policy, event store, Git gateway, and
   required roots meet configured readiness criteria.

Startup may be partially available. A configured Codex root can be unavailable
while Claude planning remains observable, but the orchestrator MUST refuse paths
that require the missing role rather than silently remapping authority.

## Normal event processing

~~~text
function accept(event):
  validate schema, protocol version, and event hash
  authenticate source session and authorize source capability
  load aggregate with optimistic version
  validate allowed transition and causal references
  append event durably
  project event with expected aggregate version
  if event causes side effect:
      enqueue durable delivery or command intent
  return accepted event reference
~~~

The command intent is persisted before terminal or Git execution. Reconciliation
can therefore determine whether a side effect was pending, attempted, confirmed,
or uncertain after a crash.

## Idle semantics

An agent becomes idle after it emits a successor event or explicitly indicates
it has no more work. Idle does not require an empty terminal pane. The adapter
maintains a bounded inbox reference and may notify a busy agent later, but it
does not require the sending agent to wait.

The runtime SHOULD set an agent busy only while it holds an assigned task or a
delivery acknowledgement indicates active handling. A root sitting in a CLI
prompt is ready, not busy.

## Backpressure

The runtime MUST bound per-session pending deliveries and total retained event
payload size. When a limit is reached, it accepts no new work that targets the
overloaded session and emits a visible backpressure status. It does not drop a
valid approval, implementation result, or recovery event.

Suggested default controls:

| Control | Default | Reason |
| --- | ---: | --- |
| pending notices per session | 32 | avoid unbounded prompt injection |
| inline event payload | 16 KiB | preserve terminal reliability |
| event attachment size | 1 MiB | force Git/file references for large data |
| root cache size | 256 KiB | prevent context inflation |
| feature context packet | 128 KiB | bound fork startup |
| capture pane diagnostic | 8 KiB | reduce sensitive retention |
| delivery attempts | 5 | expose a persistent fault quickly |

## Lifecycle boundaries

A root session is provisioned at runtime startup, remains available across
features, and is resumed only after abnormal loss. A feature session is
provisioned for one feature role, handles bounded work, and is terminated after
a terminal workflow event. A merge is not complete until required root-sync
events either complete or are visibly pending under policy.

## Failure behavior

| Condition | Required behavior |
| --- | --- |
| adapter command unavailable | mark session unavailable; do not restart-loop |
| terminal absent | reconcile process state and begin recovery |
| event store unavailable | stop accepting state-changing events |
| Git inspection failure | block merge and cache sync |
| feature worktree dirty after crash | preserve, quarantine, require resolution |
| approval stale | invalidate and request fresh review |
| policy change denies action | refuse action and record reason |
| delivery timeout | retry within policy then escalate |
| root cache failure | keep Git workflow valid; mark sync pending |

## Trade-offs

Persistent interactive processes reduce token and setup cost, but make runtime
health less trivial than one-shot jobs. The event log permits independent
progress, but users must understand eventual delivery and inspect status rather
than waiting on an RPC response. The runtime chooses those costs because coding
agents are naturally long-lived, asynchronous actors.

## Implementation guidance

A v1 implementation SHOULD begin with one orchestrator process, a SQLite or
append-only local store, an explicit file lock, a Git gateway that invokes
non-interactive Git, and small adapter processes. It SHOULD avoid shared-memory
state and automatic shell retries that can duplicate edits or commits.

See [Claude and Codex Runtimes](02-claude-codex-runtimes.md) and
[Communication Protocol](../protocol/01-communication-protocol.md).

