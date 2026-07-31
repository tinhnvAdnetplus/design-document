# 15 — Merge Strategy and Git Workflow

## Purpose

This chapter defines Git branch, worktree, commit, review-base, and integration
rules. Git remains the source of truth throughout the workflow.

## Branch model

| Ref | Owner | Write authority | Purpose |
| --- | --- | --- | --- |
| main or configured integration ref | merger | merger only | integrated history |
| ai/feature ID | implementer with lease | feature writer | isolated proposed change |
| review snapshot ref | runtime read-only | none after creation | optional reproducible review |
| runtime metadata refs | runtime service | configured only | optional evidence pointers |

The runtime must never use a floating branch name alone as review evidence.
Every review and approval refers to immutable commits.

## Worktree model

~~~text
/srv/ai-runtime/
  repo.git/                     bare or primary object store
  integration/                  protected integration worktree
  worktrees/
    feat-0042/                  Codex writer worktree
    review-feat-0042-1/         optional read-only reviewer worktree
  state/
    events/
    sessions/
    leases/
    caches/
~~~

The worktree manager creates paths from generated feature IDs only. It validates
that a path is beneath the configured worktree root before cleanup.

## Commit requirements

A feature implementation MUST create one or more commits with clean index and
working tree before requesting review. Commit messages should include feature ID
or correlation reference under repository policy. Commits must not include
runtime secrets, transient cache files, or unreviewed generated artifacts.

The implementation-ready event includes all commits between base and head. The
merger checks ancestry and disallows a head that is not reachable from the
feature branch’s recorded head.

## Merge algorithm

~~~text
function merge(approval):
  acquire integration lock
  fetch or verify configured integration ref
  assert approval is valid and unexpired
  assert feature head equals reviewed head
  assert required checks evidence is current
  compute merge base(reviewed base, integration head)
  reject if policy requires rebase/review
  merge or fast-forward exact feature head
  run required local validation
  create integration commit if needed
  verify resulting ref and tree
  emit merge.completed with all commit IDs
  release integration lock
~~~

The integration lock is process-independent where practical. If the runtime
crashes while holding it, reconciliation verifies the actual Git ref before
releasing or replaying an intent.

## Fast-forward, merge, and squash

| Strategy | Allowed? | Use case | Evidence requirement |
| --- | --- | --- | --- |
| fast-forward | policy-defined | linear integration history | exact head |
| merge commit | recommended default | preserve feature boundary | parents and review head |
| squash | policy-defined | repository preference | source range and resulting commit |
| rebase merge | policy-defined | linear history with rewritten head | fresh review binding |
| force push integration | prohibited | none | human emergency process only |

The runtime records both source head and resulting integration commit regardless
of strategy. A squash merge needs extra traceability because the approved head
does not become the final commit ID.

## Root update commit boundary

The commit created by a feature merge is complete before root synchronization.
If the repository enables cache-audit commits, a root later creates a
metadata-only commit on the dedicated runtime knowledge branch. It is not a
second implementation commit and cannot amend, rebase, or merge application
history. The metadata commit references the integrated commit range and cache
digest so it can be audited or discarded independently.

## Protected paths

Policy may require additional review, tests, or human approval for paths such
as migrations, CI configuration, authentication, infrastructure, lockfiles, and
runtime policy. The merger evaluates protected paths from the actual diff at
merge time, not only from implementer declarations.

## Git command safety

Git commands run non-interactively with a configured repository and worktree.
The gateway disables user hooks unless the repository explicitly requires
controlled hooks, validates remotes and refs, and avoids destructive commands
during ordinary workflow. It never runs a merge against an unclean integration
worktree.

## Conflict handling

A conflict during rebase or merge is not automatically resolved by the merger.
The feature returns to implementation with a conflict report and new target
base. Codex resolves in its worktree under a new or renewed writer lease, tests,
commits, and triggers fresh review. The prior approval is invalid.

## CI integration

CI status is evidence, not a second source of Git truth. A configuration
defines required checks, freshness window, provenance, and whether local
validation can substitute in offline mode. A merge is blocked when required
check status is unknown or failed.

## Recovery

If a merger crashes, reconciliation inspects integration HEAD, merge state,
worktree cleanliness, and merge intent. It emits an observed outcome only after
Git verification. It does not run abort or reset automatically when uncommitted
integration changes exist.

## Trade-offs

Dedicated worktrees and immutable review heads add Git operations but eliminate
ambiguous shared checkout state. Strict approval invalidation may cause repeated
reviews when integration moves; this protects against changes outside the
reviewed diff.
