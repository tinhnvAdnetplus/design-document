# 04 — Architectural Decisions

## Purpose

This chapter records architectural decisions that constrain v1. A decision
record states context, decision, alternatives, consequences, and reversal
conditions. It is not a transcript of discussion and does not replace normative
requirements in owner chapters.

## ADR lifecycle

| Status | Meaning | Change rule |
| --- | --- | --- |
| Accepted | binding design decision | supersede with a new ADR |
| Deprecated | still informative, no longer preferred | cite replacement |
| Superseded | replaced by identified ADR | preserve history |
| Proposed | not binding | cannot justify implementation divergence |

A new ADR is required when a change alters durable truth, permission authority,
transport semantics, recovery guarantees, or an externally consumed protocol.

## ADR-001 — Git is the source of truth

**Status:** Accepted

**Context.** CLI vendors may retain conversations and resume identifiers, but
those artifacts are unavailable, non-portable, incomplete, or costly to replay
after a crash.

**Decision.** Git commits, refs, trees, and configured remotes are the source of
truth for code. Session history, prompt caches, and resume IDs are disposable
caches. Runtime recovery MUST work after all resume IDs are lost.

**Alternatives.** Treat a conversation store as canonical; serialize every
conversation to the repository; prohibit cache persistence.

**Consequences.** Reconstructing a session requires a compact Git-derived
packet. Uncommitted changes require explicit recovery handling. The runtime
cannot claim a complete narrative when event logs are lost, but it can recover
code truth.

## ADR-002 — One persistent root per enabled agent

**Status:** Accepted

**Context.** Repeatedly creating broad project sessions consumes prompt tokens
and loses practical in-process context.

**Decision.** Each enabled adapter owns one persistent root process during
normal runtime operation. Roots retain a compact project model and do not
implement feature changes.

**Alternatives.** Start a CLI for every request; use one shared root; retain
multiple roots per agent.

**Consequences.** Health checking and session recovery are required. A root
cache can drift and must be synchronized from Git. One root makes authority and
observability simple but limits concurrent project-wide reasoning.

## ADR-003 — Forked and disposable feature sessions

**Status:** Accepted

**Context.** Feature detail is useful temporarily but inflates a root context
and can bias unrelated later work.

**Decision.** Every feature role starts a distinct short-lived session created
through the adapter fork capability or a recorded compatible equivalent. The
session is destroyed after merge, abandonment, or terminal failure.

**Alternatives.** Reuse root for all work; start a brand-new prompt; retain
feature sessions indefinitely.

**Consequences.** Fork creation and cleanup must be reliable. The root avoids
transcript bloat. Feature continuity is captured in plan, events, and Git, not
an immortal session.

## ADR-004 — Asynchronous events, not RPC

**Status:** Accepted

**Context.** Interactive CLI agents can be busy, wait for user input, rate
limited, or unavailable. Synchronous calls turn those expected conditions into
global stalls.

**Decision.** Agents exchange append-only events. Senders persist/emit and
return; receivers process when scheduled and emit successors. Correlation is
allowed, blocking dependency is not.

**Alternatives.** HTTP RPC between adapters; shared prompt file with polling;
direct terminal conversation.

**Consequences.** The runtime needs delivery acknowledgements, deduplication,
timeouts, and user-facing status. It gains failure isolation and auditability.

## ADR-005 — Claude approval and Codex implementation profile

**Status:** Accepted

**Context.** A baseline workflow needs deterministic separation between source
writer and merge approver.

**Decision.** In v1, Codex Implementer writes feature code and Claude Reviewer
is the only non-human role allowed to approve merge. A deterministic merger
updates integration after policy verification.

**Alternatives.** Any agent may approve; same session writes and approves;
human-only approval.

**Consequences.** Adapter registration must map capabilities explicitly. This
does not evaluate model quality; it is a governance boundary. A future profile
may change the mapping only through policy and ADR revision.

## ADR-006 — tmux as local execution boundary

**Status:** Accepted

**Context.** The initial runtime must keep interactive CLI processes alive and
observable on a single host.

**Decision.** Each root and feature session runs in an independently named
tmux session. The adapter uses send-keys for notification and bounded capture
for diagnostics.

**Alternatives.** Raw child processes; containers only; web terminal service.

**Consequences.** Unix users can inspect sessions with standard tools. Pane
output remains non-authoritative. Distributed execution is deferred.

## ADR-007 — Worktree isolation with writer leases

**Status:** Accepted

**Context.** Concurrent agents touching a shared checkout create untraceable
conflicts and unsafe cleanup.

**Decision.** A feature receives an isolated Git worktree and an exclusive
writer lease with fencing token. Review sessions use read-only worktrees or
immutable Git objects. Integration has a dedicated protected worktree.

**Alternatives.** Shared checkout; lock files without fencing; branch-only
isolation.

**Consequences.** Disk and cleanup overhead increase. Recovery can identify
owner and branch deterministically. A stale process cannot write after lease
replacement when gateways enforce fencing.

## ADR-008 — Derived, per-root knowledge caches

**Status:** Accepted

**Context.** Root sessions need continuity, but a shared transcript database
would create opaque authority and context bloat.

**Decision.** Each root maintains its own compact cache updated only by that
root after integrated Git changes. Cache records cite commit ranges, files,
migrations, dependency changes, generated artifacts, and API changes.

**Alternatives.** Replay all conversations; central shared memory; no cache.

**Consequences.** Cache updates are asynchronous and may differ in phrasing.
Every cache must be reconstructible and must yield to Git on conflict.

## ADR-009 — Structured approvals bind immutable evidence

**Status:** Accepted

**Context.** Natural-language review output is ambiguous and can be stale after
a rebase or policy change.

**Decision.** Merge approval binds feature head, target base, integration
branch, plan version, check evidence digest, policy revision, and expiration.

**Alternatives.** Free-text approval; latest-review-wins; merge any reviewed
branch head.

**Consequences.** A small source change after review requires a new approval.
The merger can decide mechanically. Review tools must produce structured data.

## ADR-010 — Minimal prompt retention

**Status:** Accepted

**Context.** Prompts and pane captures can contain source excerpts, credentials,
or sensitive project context.

**Decision.** Operational logs store event metadata, hashes, paths under policy,
and bounded status summaries by default. Raw prompts and transcripts require
opt-in retention with access control and redaction.

**Alternatives.** Log everything for debug; prohibit all terminal capture.

**Consequences.** Some incidents need a deliberately enabled diagnostic mode.
The default has lower privacy risk and less storage cost.

## Decision rationale summary

| Decision | Primary advantage | Principal limitation | Revisit trigger |
| --- | --- | --- | --- |
| Git-first | portable recovery | uncommitted work is weak evidence | transactionally captured workspaces |
| persistent roots | token efficiency | process health burden | adapter context persistence changes |
| disposable forks | bounded feature context | lifecycle overhead | safe per-task context snapshots |
| events | failure isolation | eventual visibility | strong real-time coordination need |
| role split | clear authority | extra handoff latency | policy quorum requirement |
| tmux | inspectable local runtime | single-host limit | remote scheduler |
| leases | safe concurrency | fencing integration | filesystem-level isolation |
| root caches | concise continuity | cache drift | verified semantic index |

## Decision amendment procedure

1. Open a proposed ADR with a problem statement and affected requirements.
2. Include a migration plan, rollback path, compatibility impact, and security
   analysis.
3. Update the owner chapter and protocol schema before implementation.
4. Add tests proving both pre-migration and post-migration recovery paths.
5. Mark the prior ADR superseded only after compatible implementation ships.

A documentation-only clarification MAY amend examples without a new ADR when it
does not change authority, data ownership, required behavior, or interoperability.

## Future decisions

Expected future ADR topics include remote workers, durable queues, signed
events, multi-reviewer quorum, sandboxed agent execution, cache provenance
attestations, and adapter capability negotiation. None should be implemented as
an undocumented option because each touches a core invariant.

