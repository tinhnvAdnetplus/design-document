# 14 — Feature and Review Lifecycle

## Purpose

This chapter specifies the baseline collaboration flow: plan, implementation,
review, fix, approval, merge, root synchronization, and commit evidence.

## Baseline lifecycle

~~~mermaid
sequenceDiagram
    participant P as Claude Planner
    participant I as Codex Implementer
    participant R as Claude Reviewer
    participant M as Merger
    P->>P: fork and analyze request
    P->>I: plan approved event
    I->>I: implement in leased worktree
    I->>R: implementation ready event
    R->>I: changes requested, if needed
    I->>R: updated implementation ready event
    R->>M: structured merge approval
    M->>M: validate and merge
    M->>P: merge completed, root sync
~~~

The logical sequence must be preserved even when an adapter reuses a terminal
or a human reviews an exception. The implementer never treats a review comment
as merge permission; only a valid approval event changes approval state.

## Planning

The Claude planner receives a feature request and produces a plan with:

- problem and desired outcome;
- explicitly excluded scope;
- affected components, APIs, migrations, and generated files;
- implementation steps and worktree assumptions;
- acceptance criteria and test strategy;
- rollout, compatibility, and security concerns;
- requested permissions or external operations;
- Git base and Knowledge Cache evidence.

The plan is an artifact with a digest. If implementation materially changes
scope, affected protected paths, migration strategy, or compatibility behavior,
the implementer must request a plan revision instead of silently continuing.

## Plan approval

Policy decides whether a plan needs human approval based on risk classification.
The baseline can auto-approve low-risk plans only if Claude reviewer capability
or explicit policy rule validates them. High-risk categories should include
database migrations, authentication, dependency upgrades, generated protocol
changes, force updates, and external side effects.

## Implementation

Codex Implementer receives an approved plan, feature branch, unique worktree,
writer lease, test policy, and context references. It must inspect current Git
state before change, work only within the allocated worktree, run required
tests, and create coherent commits.

The implementation-ready event binds branch head and base. It includes changed
paths, tests, migrations, generated output, risks, and a diff digest. A dirty
worktree or missing commit is not eligible for review.

## Review

Claude Reviewer receives immutable review evidence:

| Evidence | Why it is needed |
| --- | --- |
| approved plan and digest | verify scope |
| base, head, merge-base | verify exact change |
| diff and changed paths | inspect behavior |
| test results and reports | assess verification |
| migration/dependency markers | assess risk |
| policy revision | apply current constraints |
| prior findings | avoid repeated unresolved defects |

The reviewer must emit either changes requested, merge approved, or review
blocked. It must not write source code. Findings identify path, location where
available, severity, rationale, expected outcome, and whether re-review is
required.

## Fix cycle

A changes-requested event returns the feature to implementation. The prior
approval state is absent. Codex fixes in the same worktree only if its writer
lease is re-granted; otherwise a new implementation attempt forks from the
current root with the prior evidence packet.

Each material new head requires a new implementation-ready event and review.
The runtime may allow a policy-defined minor documentation correction to use
targeted re-review, but it may not retain a merge approval across a changed
head.

## Approval

Approval is an explicit structured event from Claude Reviewer and binds all
reviewed immutable references. Before merge, the runtime rechecks:

1. reviewer session and role capability;
2. feature state and approval expiration;
3. exact reviewed feature head;
4. exact or validly compatible target base;
5. policy revision and protected-path rules;
6. required tests and CI evidence;
7. integration lock availability.

Any mismatch invalidates approval and returns the feature to implementation or
review. The system does not attempt to infer whether a stale approval “probably”
still applies.

## Merge and terminal flow

After the merger emits success, the integration commit becomes the reference
for Knowledge Synchronization and Knowledge Evolution. Feature sessions are
destroyed after merge outcome is stable. Knowledge Runtime collects the Git diff
and governed Event Store evidence; each root publishes only its own validated
snapshot and emits synchronization evidence. The feature reaches completed when
configured root-sync obligations complete, or when policy records a deferred
evolution with visible degradation.

The complete V2 sequence in [State Model and Diagrams](../architecture/03-state-model-diagrams.md)
is normative for the relationship between review retry, merge, evolution,
optional metadata-only Root Update Commit, feature destruction, and root idle.

## Review quality constraints

Review packets must be diff-scoped and not rely on the implementer’s narrative.
Review should check correctness, policy compliance, tests, compatibility,
migration safety, generated source consistency, public API behavior, and
unintended changes. It should not expand into unrelated refactoring unless a
finding demonstrates a direct risk.

## Exceptional paths

| Condition | Flow |
| --- | --- |
| reviewer unavailable | retain review request; escalate by SLA |
| reviewer detects dangerous change | changes requested or block; no merge |
| CI fails after approval | invalidate approval; return for fix |
| integration base advances | rebase/revalidate then re-review as policy requires |
| human rejects plan | abandon or revise plan |
| implementer crashes | apply recovery chapter before continuation |
| feature is canceled | revoke lease, terminate sessions, preserve evidence |

## Trade-offs

The flow adds explicit handoffs and may cost more wall time than a single agent
commit. It separates the person or process that writes code from the one that
authorizes integration, making defects and deviations easier to review.
Persistent roots and concise packets reduce the token cost of those handoffs.
