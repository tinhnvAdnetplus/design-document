# 19 — Reference Implementation

## Purpose

This chapter proposes a production-oriented reference implementation structure,
interfaces, pseudocode, and build order. It is language-neutral; examples use
typed pseudocode and shell commands.

## Module layout

~~~text
src/
  main/                 process startup and dependency wiring
  config/               schema, loading, revisioning
  domain/               events, aggregates, state transitions
  policy/               capabilities, protected paths, authorization
  capabilities/         Runtime Capability Registry and revalidation
  store/                Event Store, projection, attachments
  knowledge/            snapshots, Cache Registry, compression, evolution
  lineage/              session-lineage projection
  adapters/
    base/               common adapter contract
    claude/
    codex/
  tmux/                 terminal command wrapper and observation
  git/                  worktree, commit, merge gateway
  scheduler/            dispatcher, eligibility, queues, deadlines, reconciliation
  cache/                root packet and knowledge-cache support
  observability/        logs, metrics, tracing
  cli/                  operator and in-terminal runtime client
test/
  unit/
  integration/
  contract/
  chaos/
~~~

The domain module should not invoke tmux, a CLI, or Git directly. Side effects
are represented as command intents and executed through adapters/gateways.

## Core domain types

~~~text
Feature {
  id, state, branch, baseCommit, headCommit,
  planDigest, approvalBinding, activeAttempt, blockedReason
}

Session {
  id, agentId, role, lifecycle, tmuxName,
  adapterVersion, rootId, featureId, resumeMetadata,
  parentSessionId, knowledgeSnapshotVersion, lineageEdgeType
}

Lease {
  id, resource, holderSessionId, fencingToken,
  issuedAt, expiresAt, state
}

Event {
  id, protocol, type, producer, aggregate,
  correlationId, causationId, policyRevision, payload, digest
}

CommandIntent {
  id, sourceEventId, kind, status,
  idempotencyKey, preconditions, resultReference
}

KnowledgeSnapshot {
  rootId, version, domains, integrationHead,
  facts, provenance, digest, validationState
}

CapabilityDocument {
  adapterId, adapterVersion, cliVersion, fork, resume,
  notify, readinessObservation, reconciliationObservation, digest
}
~~~

Types are immutable after append. The projection builds current mutable views
by applying accepted events.

## Adapter interface

~~~text
interface AgentAdapter {
  capabilities(): CapabilityDocument
  start(spec: SessionSpec): Observation
  fork(spec: ForkSpec): Observation
  notify(spec: NotificationSpec): Observation
  inspect(spec: SessionSpec): Observation
  resume(spec: RecoverySpec): Observation
  stop(spec: SessionSpec): Observation
}
~~~

An observation contains status, timestamp, controlled diagnostic reference,
terminal identity, adapter/CLI version, and retryability. It never returns raw
prompt content as a required field.

Capability Registry is initialized only from `AgentAdapter.capabilities()`.
Capability Discovery remains inside the adapter implementation; the Runtime
does not derive entries from CLI output, probing, or model reasoning. Startup,
Runtime restart, adapter upgrade, and an operator-declared manual CLI upgrade
all obtain and validate a fresh Capability Document before adapter-dependent
work proceeds.

## Event acceptance pseudocode

~~~text
function submit(event):
  schema.validate(event)
  authenticate(event.producer)
  policy.authorize(event.producer, event.type, event.aggregate)
  transaction:
    stream = store.loadStream(event.aggregate)
    transition.validate(stream.state, event)
    idempotency.check(event)
    store.append(event)
    projection.apply(event)
    intents = deriveIntents(event, projection)
    store.appendIntents(intents)
  scheduler.wake()
  return accepted(event.id)
~~~

The transaction boundary includes append, idempotency, and projection version
check. Effect execution occurs afterward. SQLite transaction semantics are
suitable when a single orchestrator owns writes.

## Reconciler pseudocode

~~~text
function reconcile():
  for adapter in enabledAdapters():
    registry.revalidate(adapter.capabilities())
    if document missing, stale, or contradicted by observation:
      mark adapter ADAPTER_UNAVAILABLE and fence dependent intents

  for session in projection.nonTerminalSessions():
    observed = adapter(session.agentId).inspect(session)
    compare observation with session and terminal registry
    if unavailable:
      append session.unavailable if not already recorded

    if task deadline elapsed without terminal event or explicit deferral:
      reconcile Git, Event Store, artifacts, and lease state
      append session.unavailable; block follow-on work if completion is uncertain

  for lease in projection.activeLeases():
    if expired or owner unavailable:
      append lease.expired or lease.revoked

  for intent in store.pendingIntents():
    confirm precondition and prior effect
    execute safely or mark uncertain/block

  for feature in projection.featuresNeedingRecovery():
    build recovery plan from Git, events, and configuration
~~~

Reconciliation is not conversational polling. It observes runtime resources and
deterministic Git state on a controlled schedule. Event Store replay rebuilds
projection and lineage/cache views; it does not replay an unconfirmed effect.

## V2 control loop

~~~text
function control_loop():
  receive event submission, scheduled eligibility, or runtime observation
  validate and persist Event Store evidence
  project feature/session/lineage/cache/capability state
  scheduler.select_eligible(CapabilityRegistry)
  dispatcher.route_notice() or gateway.execute_confirmed_intent()
  collect observation; emit and project outcome
  return idle without waiting for agent completion
~~~

Persistent agents use the separate Agent Loop defined in Runtime Overview.
They are Session Registry entries, not worker-pool members.

## Git gateway

The gateway is the only code path that creates runtime worktrees, verifies
feature evidence, or mutates integration. It executes a small allow-list of
non-interactive Git operations, validates repository root and worktree manifest,
and uses a lock for integration mutation.

~~~sh
git -C /srv/ai-runtime/repo.git worktree add   /srv/ai-runtime/worktrees/feat-0042 -b ai/feat-0042 091e4d9c
git -C /srv/ai-runtime/integration status --porcelain=v1
git -C /srv/ai-runtime/integration merge --no-ff ab12cd34
~~~

The actual implementation should invoke process arguments directly, not through
an interpolated shell string. It checks output, exit code, current ref, and
postcondition after each mutating operation.

## Root synchronization service

The cache service gathers a bounded evidence packet from Git and events,
requests a root-derived cache update, validates provenance, and atomically
installs the result. It has no ability to write application code. A cache write
is successful only when its integration head matches current configured head.
When enabled by policy, the service asks the owning root to write a
metadata-only cache manifest commit to the dedicated runtime knowledge branch.
That operation is separate from integration merge and is guarded to prevent
application-path changes.

V2 implements this service as Knowledge Runtime: detect affected domains,
collect Git diff/Event Store evidence, compress candidates, validate provenance
and budgets, then publish the named root's snapshot atomically. Conversation
Cache is never an implicit input.

## In-terminal client

A small runtime client invoked through terminal notification should:

1. validate its environment and runtime session ID;
2. resolve the immutable event record;
3. acknowledge delivery;
4. present a concise event/task packet to the CLI;
5. help the agent emit structured result events;
6. never grant capabilities or write outside assigned policy.

This keeps tmux key injection fixed-form while allowing adapters to evolve UI
handling.

## Build order

| Phase | Deliverable | Exit criterion |
| --- | --- | --- |
| 1 | event schema, store, projection | replay deterministic |
| 2 | configuration, policy, and Capability Registry | invalid authority/capability rejected |
| 3 | Git worktree/lease gateway | concurrent writer test passes |
| 4 | tmux wrapper and mock adapter | lifecycle test passes |
| 5 | Claude/Codex adapters | contract fixtures and revalidation pass |
| 6 | feature/review/merge intents | end-to-end happy path |
| 7 | cache synchronization | rebuild test passes |
| 8 | observability and recovery | chaos suite passes |
| 9 | hardening | security review passes |

## Implementation recommendations

Use atomic rename for file artifacts, database transactions for event/projection
updates, monotonic clocks for deadlines, and UTC timestamps for evidence.
Avoid singleton global state, interactive Git prompts, shell interpolation,
unbounded queues, and automatic deletion of unknown directories.

## Limitations

The reference design intentionally does not prescribe a web dashboard, remote
queue, or managed database. Those are replaceable integration concerns once the
local control-plane semantics are proven.
