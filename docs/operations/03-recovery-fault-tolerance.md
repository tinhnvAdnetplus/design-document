# 23 — Recovery and Fault Tolerance

## Purpose

This chapter defines fault domains, recovery order, and data-integrity rules.

## Fault matrix

| Failure | Durable truth affected? | Automatic action | Human gate |
| --- | --- | --- | --- |
| agent CLI exits | no | mark unavailable, recover | if dirty worktree |
| tmux server exits | no Git loss | reconcile all sessions | no, unless ambiguity |
| orchestrator exits | no if append transactional | restart and rebuild projection | no |
| event projection corrupt | event log retained | rebuild projection | if log integrity fails |
| event log corrupt | Git retained | stop mutation, restore/audit | yes |
| Git remote unavailable | local Git retained | block remote-dependent merge | policy |
| integration merge crash | inspect Git | reconcile outcome | if unclean |
| disk full | potentially state/cache | stop writes safely | likely |
| policy config invalid | no | refuse start/reload | administrator |
| resume ID lost | no | fresh reconstruction | no |

## Recovery order

1. Stop automatic side effects if event store, policy, or Git identity is
   uncertain.
2. Validate configuration digest and repository identity.
3. Rebuild derived projection from verified event log.
4. Inspect integration ref, Git merge state, registered worktrees, and dirty
   status.
5. Reconcile active leases and fence unavailable holders.
6. Reconcile terminal sessions through adapter observations.
7. Determine resume or fresh reconstruction under session policy.
8. Replay pending idempotent command intents only after confirmation query.
9. Resume deliveries and root synchronization.
10. Publish recovery report with unresolved items.

## Data-integrity rules

The runtime MUST never auto-delete a dirty worktree, overwrite a Git ref after
an uncertain merge, use a stale approval, or assume a pane equals a session.
It MUST preserve evidence before cleanup and prefer blocked state over unsafe
progress.

## Graceful degradation

Loss of root cache affects token efficiency, not Git correctness. Loss of one
adapter blocks only features requiring its role. Loss of observability should
not stop a safe local workflow but must be visible. Loss of event durability,
policy validation, or Git identity stops state-changing actions.

## Backup and restore

Back up configuration, event store, policy revisions, sanitized cache records,
and Git repository according to retention policy. Test restore into an isolated
host. A restore must verify event integrity and recompute projection; it must
not trust copied process IDs or terminal names.

## Recovery validation

Every release runs host-reboot, killed-agent, lost-resume-ID, duplicate-intent,
merge-crash, and dirty-worktree scenarios. Recovery reports should state known
unknowns rather than presenting a false clean state.

## Trade-offs

Fail-closed recovery can pause work that a human could possibly infer. This
protects code and approvals from uncertain external side effects. The explicit
human exception workflow supplies a documented path when speed is necessary.

