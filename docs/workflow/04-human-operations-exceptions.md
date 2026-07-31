# 17 — Human Operations and Exceptions

## Purpose

This chapter defines the human maintainer’s role, explicit interventions, and
exception paths. Humans remain responsible for policy changes and exceptional
authority; the runtime records those actions as first-class evidence.

## Human capabilities

| Action | Default authority | Required evidence |
| --- | --- | --- |
| request feature | maintainer | request event |
| approve high-risk plan | maintainer | approval event |
| cancel feature | maintainer | cancellation reason |
| inspect status/logs | maintainer/read-only user | access policy |
| retry recovery | maintainer | recovery request |
| override merge policy | restricted maintainer | signed override and rationale |
| alter policy/config | administrator | versioned configuration change |
| delete quarantined worktree | restricted maintainer | inspection and confirmation |

Human intervention is not a gap in automation. It is the correct handling path
when source state, permissions, or external consequence cannot be safely
inferred.

## Required override record

An override includes operator identity, timestamp, affected aggregate, prior
state, requested action, justification, risk classification, policy revision,
approver if required, and resulting Git/event evidence. An override cannot be
a free-text terminal instruction to an agent.

## Common exception procedures

### Dirty worktree after crash

1. Revoke stale writer lease and prevent automatic cleanup.
2. Create a read-only archive or filesystem snapshot under approved policy.
3. Inspect Git status and diff without destructive commands.
4. Decide to preserve, manually commit, continue in a recovered session, or
   explicitly delete.
5. Record decision and only then allow cleanup.

### Stale approval

The runtime automatically invalidates stale approval. A maintainer may not
simply extend its expiry if head, base, policy, tests, or protected paths
changed. The feature needs re-review. A time-only expiration may be renewed
through configured reviewer evidence.

### Emergency integration fix

An emergency path may allow a human to merge a fix outside the normal feature
flow, but it must record reason, commit range, risk, and post-hoc root
synchronization. The exception should trigger retrospective review. It does not
change the normal rule that agent merges require Claude approval.

### Adapter outage

Disable the affected role, preserve pending events, and expose blocked
features. Do not silently reassign Claude approval to Codex or an arbitrary
agent. A human may use configured emergency policy but must record the role
substitution.

## Operational status

A maintainer needs concise answers:

- which feature is blocked and at what state;
- which session holds each lease;
- whether Git has uncommitted or divergent work;
- which event/approval is pending or stale;
- whether a Knowledge Cache is current;
- what recovery step is safe next.

The runtime status command must derive these answers from projections and
verified Git observations rather than terminal conversation summaries.

## Escalation

| Trigger | Initial action | Escalate to |
| --- | --- | --- |
| lease near expiry | notify holder | maintainer after deadline |
| delivery expired | mark unavailable/retry path | maintainer |
| repeated protocol rejection | suspend session | security reviewer |
| integration conflict | return to implementation | maintainer if repeated |
| dirty recovery | quarantine | maintainer |
| policy override request | hold action | authorized administrator |
| suspected secret leak | redact/revoke | security incident process |

### Knowledge Evolution exception

If provenance validation rejects a candidate snapshot, a maintainer may inspect
the Git diff and governed evidence, correct configuration or source metadata,
and request a new evolution attempt. A maintainer MUST NOT paste a conversation
summary into Knowledge Cache, override provenance failure with free text, or
use an optional Root Update Commit to alter application code.

## Trade-offs

Human exceptions reduce full autonomy but avoid unsafe guesses. The runtime
makes the exceptional path auditable and narrow so that emergency flexibility
does not become a hidden alternate workflow.
