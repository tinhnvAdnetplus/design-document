# 24 — Deadlock Prevention and Concurrency

## Purpose

This chapter defines safe parallelism, resource ordering, lease behavior, and
deadlock prevention.

## Concurrency model

Features may plan, implement, review, and synchronize concurrently. They may
not hold the same worktree writer lease or integration merge lock concurrently.
Root sessions are independent read-mostly actors; each owns only its own cache.

| Resource | Concurrency | Guard |
| --- | ---: | --- |
| root cache | one writer per root | root identity |
| feature worktree | one writer | lease plus fencing |
| feature review | one active approval attempt | aggregate sequence |
| integration worktree | one merger | integration lock |
| event stream | serialized per aggregate | optimistic version |
| terminal session | one adapter controller | session identity |
| Git object store | Git-managed | read/write repository rules |

## Lock ordering

When an action needs multiple resources, acquire in this order:

1. feature aggregate version;
2. policy/configuration revision snapshot;
3. feature worktree lease;
4. integration lock;
5. Git command-specific lock.

A process must not wait while holding a higher-order resource for a human or
agent response. Agent work happens outside integration lock. This avoids the
classic deadlock of an implementer waiting for review while blocking a merger.

## Leases and fencing

Leases expire, can be revoked, and carry increasing fencing tokens. A gateway
checks token before write-sensitive worktree or Git operation. A stale agent may
still have a running terminal, but its old token cannot authorize new write
effects after recovery grants a newer one.

## Starvation controls

Review and merge queues are FIFO within priority class. A feature whose base
keeps advancing receives a configurable retry count then maintainer attention.
Long-running implementation must renew lease and emit progress; otherwise it
is fenced to prevent indefinite resource occupation.

## Deadlock detection

The projection exposes wait-for relationships: session to lease, feature to
review, merge to integration lock, root to sync evidence. A cycle or deadline
breach triggers a blocked state and releases only resources whose release is
safe. The runtime never kills an agent solely to break a cycle if it may leave
dirty uncommitted work; it revokes authority and follows recovery procedure.

## Parallel merge policy

Only one integration mutation occurs at a time. Multiple approved features can
wait. Before each merge, the merger validates that its approval is still bound
to current integration base. This can produce re-review work but prevents
implicit changes from a prior merge entering an approved candidate.

## Trade-offs

Serial integration limits merge throughput but makes Git state and approval
binding deterministic. Fine-grained parallel merges introduce conflict and
review invalidation complexity that is not justified for v1.

