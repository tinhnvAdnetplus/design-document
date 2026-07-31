# 08 — Session and Feature Lifecycle

## Purpose

This chapter defines lifecycle ownership, cleanup, feature identity, and
terminal conditions for root and feature sessions.

## Lifecycle rules

A root is a long-lived resource owned by its configured adapter. A feature
session is a disposable resource owned by one feature role. The runtime creates
a record before starting either process and records a terminal lifecycle event
before forgetting the process.

| Rule | Root | Feature |
| --- | --- | --- |
| one per enabled adapter | yes | no |
| normal restart allowed | no | no |
| fork parent required | n/a | yes |
| worktree writer lease | no | implementer only |
| cache update authority | own cache only | none |
| automatic terminal cleanup | host shutdown only | required |
| can outlive merge | yes | no |
| can share feature ID | n/a | no concurrent same role attempt |

## Root lifecycle

~~~mermaid
flowchart LR
    A[Configured] --> B[Provisioned]
    B --> C[Starting]
    C --> D[Ready]
    D --> E[Busy with root task]
    E --> D
    D --> F[Unavailable]
    F --> G[Resume or reconstruct]
    G --> D
    D --> H[Draining for maintenance]
    H --> I[Terminated]
~~~

A root is ready when it has a valid adapter observation, current policy
revision, repository identity, and cache status. It is not required to have an
empty inbox or an up-to-date cache if it has been marked unavailable for
planning until synchronization completes.

## Feature lifecycle

A feature begins when a request receives a stable ID. It ends only when the
runtime records completed, abandoned, or failed terminal state. The feature
contains roles and attempts; an implementation retry gets a new session ID and
attempt number while retaining the feature ID and event correlation.

| Stage | Session operation | Worktree state | Required evidence |
| --- | --- | --- | --- |
| requested | none | none | immutable request |
| planning | fork planner | optional read-only | plan artifact |
| implementing | fork implementer | writer lease | branch and lease |
| reviewing | fork reviewer | read-only | diff and check packet |
| merging | no feature writer action | integration lock | approval binding |
| synchronizing | roots only | Git integration range | cache provenance |
| terminal | destroy features | remove or archive | cleanup record |

## Creation procedure

1. Validate the requested feature ID, branch namespace, and target integration
   ref.
2. Append a creation intent before creating a terminal or worktree.
3. Allocate session ID, feature attempt, terminal name, and data directory.
4. Create a Git worktree only for a session that can write or needs an isolated
   reproducible snapshot.
5. Grant a lease only after the terminal is ready and policy authorizes it.
6. Publish session-ready and role-assigned events.
7. Deliver the feature packet by event reference.

The ordering prevents orphaned writer access. A worktree created before a
terminal is ready remains unleased and can be safely garbage-collected.

## Cleanup procedure

~~~text
function terminate_feature(session):
  stop delivery to session
  revoke or release active leases
  inspect worktree status and branch reachability
  if dirty or uncommitted:
      quarantine; emit cleanup.blocked
      return
  persist terminal cleanup intent
  ask adapter for graceful stop
  kill terminal only after grace deadline
  archive minimal metadata and event references
  remove worktree under explicit path validation
  emit session.terminated
~~~

Cleanup MUST be idempotent. Repeating it after a crash should see an already
absent terminal or worktree and record that outcome without treating it as an
error. Cleanup MUST NOT remove a worktree whose directory does not match the
runtime-generated registry path.

## Branch and worktree ownership

A feature branch has one primary implementer writer. The implementer may run
tests, generate source, and create commits within its assigned worktree. A
reviewer operates on an immutable head commit or its own read-only checkout.
The integration worktree is held only by the merger while an integration lock
is active.

| Resource | Owner | Release condition |
| --- | --- | --- |
| feature branch name | feature aggregate | merge or explicit abandonment |
| feature worktree | writer session | successful cleanup |
| writer lease | implementer session | review, expiry, or cleanup |
| review snapshot | reviewer session | review terminal state |
| integration worktree | merger | merge command completes |
| root cache directory | named root | root shutdown or cache rebuild |

## Abandonment

A feature is abandoned when a human cancels it, a policy deadline expires, or
recovery establishes that it cannot safely continue. Abandonment is not
deletion: the runtime retains event evidence, preserves any dirty worktree, and
records disposition of branch and terminal artifacts.

A clean abandoned branch may be retained for a configured period. A dirty
abandoned worktree is quarantined until an authorized human retains, commits,
or deletes it. No agent can mark unknown work as safe merely to complete
cleanup.

## Lease renewal

A writer lease has a deadline and a fencing token. The implementer renews only
while it is active and the feature is implementing. The runtime denies renewal
during review, merge, cancellation, or policy suspension. A renewal does not
alter the feature head or approval state.

Recommended policy uses short leases with explicit renewal rather than a single
very long lease. This detects lost sessions earlier and makes a forced recovery
safer, at the cost of periodic control traffic.

## Terminal conditions

| Condition | Session result | Feature result |
| --- | --- | --- |
| plan accepted | planner terminated | advances to implementation |
| implementation ready | implementer retained until review outcome | awaiting review |
| changes requested | reviewer terminated | implementation resumed/new attempt |
| merge complete | all feature terminals terminated | synchronizing |
| sync complete | roots remain | completed |
| cancelled | all feature terminals terminated or quarantined | abandoned |
| unrecoverable protocol failure | session failed | blocked then failed/abandoned |

An implementer may remain alive between implementation-ready and review outcome
to reduce repair latency, but it holds no writer lease during review unless
policy explicitly allows a read-only wait state.

## Audit fields

Every lifecycle record MUST include runtime session ID, feature ID if present,
role, adapter/version, terminal identity, process observation, timestamps,
initiator, policy revision, cleanup disposition, and causation event. These
fields support safe reclamation and incident review without retaining a prompt.

## Limitations and future work

Per-feature terminals are simple and observable but consume resources. Future
pooling can reuse a process only if it provides hard context reset, independent
runtime identity, and the same disposal guarantees. Until then, terminal reuse
between features is prohibited.

