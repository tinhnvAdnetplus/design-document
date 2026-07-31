# 13 — Protocol Error Handling

## Purpose

This chapter specifies errors, retries, rejection, deduplication, poison-event
handling, and compatibility failure behavior.

## Error classes

| Class | Example | Retry? | Required response |
| --- | --- | ---: | --- |
| schema | missing event ID | no | reject with stable code |
| authorization | implementer approves merge | no | reject and audit |
| transition | review before implementation ready | no | reject or hold by policy |
| conflict | aggregate version changed | yes with reload | retry projection only |
| transport transient | terminal server temporarily unavailable | yes | bounded backoff |
| adapter ambiguous | terminal prompt state unknown | no blind retry | mark unavailable |
| Git transient | lock contention | yes bounded | revalidate then retry |
| Git integrity | referenced commit absent | no | block workflow |
| policy mismatch | approval revision stale | no | invalidate and re-review |
| resource exhaustion | queue/cache size exceeded | conditional | backpressure event |
| cache provenance | candidate knowledge fact lacks eligible evidence | no | reject candidate and keep prior snapshot |
| lineage invalid | fork/reconstruction parent inconsistent | no | quarantine lineage record |
| security | path escape or signature failure | no | revoke/block and alert |

Every error response includes a machine code, stable event reference, category,
safe summary, retryability, and recommended operator action. It excludes raw
terminal capture and secrets.

## Rejection record

~~~json
{
  "type": "event.rejected",
  "payload": {
    "rejected_event_id": "evt_01J...",
    "code": "AUTHORIZATION_DENIED",
    "category": "authorization",
    "retryable": false,
    "message": "Producer role lacks merge approval capability.",
    "policy_revision": "policy-2026-07-31.1",
    "recommended_action": "Use configured reviewer role."
  }
}
~~~

A rejected event is retained for audit but does not advance business state. An
agent should not repeatedly resubmit a non-retryable event; repeated violations
can trigger session suspension under policy.

## Idempotency

A producer creates a stable idempotency key for an intended logical action.
The Event Store stores the first accepted event digest for that key within the
aggregate. A duplicate with the same digest returns the existing result. A
duplicate key with different content is rejected as an idempotency conflict.

Command intents use their own idempotency key derived from event ID and action.
Before retrying, the executor performs a confirmation query: inspect terminal
existence, lease record, worktree path, or Git ancestry as appropriate.

## Retry policy

~~~text
attempt 1: immediate
attempt 2: after 1 second
attempt 3: after 5 seconds
attempt 4: after 30 seconds
attempt 5: after 2 minutes
then: mark delivery expired and escalate
~~~

Actual values are configuration. The policy must cap attempts, use jitter where
multiple sessions contend, and stop retrying after a terminal condition changes.
A retry never recreates a feature session silently after it was terminated.

## Poison events

A poison event repeatedly fails due to malformed content, invariant violation,
or an incompatibility requiring intervention. The runtime moves it to a
quarantine stream with its validation evidence, increments a metric, and blocks
only the affected aggregate unless security policy requires broader isolation.

Quarantine is an operational state, not deletion. A maintainer may correct
configuration, migrate an event, or abandon the feature through an auditable
override.

An Event Store replay failure is poison projection evidence, not permission to
re-run a side effect. The runtime retains the event and blocks only the action
whose deterministic confirmation cannot establish a safe outcome.

## Causal gaps

An event that names an unknown causation ID or arrives before its predecessor
is placed in a pending-causation store for a bounded interval. If the
predecessor arrives and validation succeeds, it can proceed. If the deadline
expires, the event is rejected or quarantined according to type. The runtime
must not invent a predecessor merely to preserve flow.

## Stale and conflicting events

| Condition | Handling |
| --- | --- |
| implementation ready for prior head | reject as stale; request current head |
| approval for changed base/head | invalidate approval |
| old lease token writes | deny at gateway and emit security event |
| feature canceled while event queued | record delivery cancellation |
| duplicate merge completion | verify Git outcome then deduplicate |
| concurrent review responses | preserve both; policy selects valid approval |
| policy changed mid-task | reauthorize next side effect |

## Error visibility

Operators need a concise status that answers what failed, what evidence exists,
and whether manual action is necessary. The runtime exposes aggregate status,
last accepted event, pending delivery count, active lease, terminal observation,
and safe error code. Detailed restricted diagnostics remain access-controlled.

Scheduler errors additionally expose queue class, attempt, next eligibility,
and Session Registry reason. Knowledge errors expose snapshot domain, cache
layer, provenance status, and whether the prior snapshot remains usable.

## Compatibility failures

Unsupported protocol major versions, unknown critical event types, invalid
canonicalization, or missing historical policy are compatibility failures. The
runtime MUST refuse automatic state-changing behavior. Read-only event
inspection may remain available so upgrades and migration tools can operate.

## Trade-offs

Bounded retries improve resilience but can delay clear failure. Aggressive
retries against an ambiguous terminal can duplicate a command, so adapter
ambiguity is intentionally treated as unavailable rather than transient. This
is a safety-first choice that favors a fresh reconstruction over uncertain
interactive state.
