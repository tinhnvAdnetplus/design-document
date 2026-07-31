# ADR-011 — Version 2 Runtime Evolution

**Status:** Accepted and binding

**Date:** 2026-07-31

**Supersedes:** No prior ADR. This ADR evolves, but does not invalidate,
ADR-001 through ADR-010.

**Decision owner:** Project architecture authority

## 1. Purpose and authority

This Architecture Decision Record is the single source of truth for Version 2
implementation. It captures the frozen outcomes of the completed independent
architecture review. All Version 2 documentation, diagrams, configuration,
protocol descriptions, test plans, and future implementation work MUST conform
to this ADR.

This ADR does not reopen or repeat the review. A partially accepted proposal is
accepted only in the constrained form stated here. A rejected interpretation is
permanently rejected unless applying this ADR exposes a direct contradiction
with a retained invariant; such a contradiction requires a new superseding ADR.

## 2. Retained Version 1 invariants

The following invariants remain binding:

1. Git commits, refs, and reachable object graph are the source of truth for
   application code and code history.
2. Sessions, resume references, prompts, conversations, and caches are
   disposable and cannot become code truth.
3. One persistent root exists per enabled agent; roots never implement feature
   code or hold feature writer leases.
4. Feature sessions are forked, isolated, role-bound, and destroyed at a
   terminal feature state.
5. The baseline policy assigns Codex implementation and Claude merge approval.
6. Agent collaboration is asynchronous event delivery, never blocking RPC.
7. The merger alone mutates the integration branch after exact approval
   validation.
8. Only each named root publishes its own long-lived knowledge artifact after
   integration.
9. Loss of every vendor resume identifier must not prevent recovery.
10. tmux remains a local execution boundary and notification transport, not an
    authority, event database, or distributed scheduler.

## 3. Binding V2 vocabulary

| Term | Binding definition | Explicitly not |
| --- | --- | --- |
| Knowledge Runtime | Logical control-plane component for snapshots, cache registry, compression, evolution, validation, and publication coordination. | A new persistent AI process, transcript database, or source of truth. |
| Knowledge Snapshot | Bounded, versioned, provenance-linked view of one knowledge domain. | A complete conversation or unrestricted memory. |
| Knowledge Evolution | Pipeline invoked by synchronization to derive a validated new snapshot from eligible evidence. | Autonomous learning or unvalidated fact generation. |
| Cache Taxonomy | Four disposable layers: Prompt, Conversation, Resume, and Knowledge Cache. | Four independently deployed services. |
| Conversation Cache | Restricted diagnostic-only cache, disabled by default. | Normal root memory or canonical audit log. |
| Resume Scope | Role-specific exceptional-recovery eligibility and lifetime. | A normal workflow handoff or context refresh. |
| Session Lineage Graph | Derived DAG/forest of fork and reconstruction parentage. | Transport, authority, or direct communication graph. |
| Event Store | Append-only store of accepted events, deliveries, command intents, and replay evidence. | Source of truth for code or a blind side-effect replayer. |
| Dispatcher | Internal orchestrator module that routes an eligible event notice to a registered target. | A synchronous RPC broker. |
| Eligibility Scheduler | Internal orchestrator module that selects eligible deliveries and deterministic intents by policy. | A persistent CLI worker pool. |
| Root Update Commit | Optional metadata-only checkpoint for sanitized knowledge manifest/provenance. | An integration or application-code commit. |

## 4. Frozen decisions

### D-01 — Knowledge Runtime

**Disposition:** Partially accepted; accepted as refined below.

**Decision.** V2 MUST introduce Knowledge Runtime as a named logical component
within the control plane. It manages the lifecycle of six snapshot domains:
Project, Architecture, Business, Workspace, Dependency, and Convention.

| Snapshot domain | Required evidence boundary |
| --- | --- |
| Project | Git identity, integration baseline, and versioned configuration |
| Architecture | code, architecture documents, ADRs, and governed artifacts |
| Business | repository-backed domain rules and terminology only |
| Workspace | Git worktree, branch, lease, and runtime observations |
| Dependency | manifests, lockfiles, and generator metadata |
| Convention | versioned style, build, test, and repository rules |

Knowledge Runtime MUST validate provenance, scope, confidence, and size before
publication. It does not author application code, approve merges, mutate Git
integration, or own a model conversation.

### D-02 — Knowledge Evolution Engine

**Disposition:** Partially accepted; accepted as a pipeline, not a replacement
for synchronization.

**Decision.** Knowledge Synchronization remains the workflow trigger and event
contract. It MUST invoke Knowledge Evolution:

~~~text
detect affected domains -> collect Git/governed-event evidence -> compress
-> construct candidate snapshot -> validate -> atomically publish -> notify root
~~~

The persistent root session is not replaced after evolution. It receives a new
snapshot version and remains the same runtime identity. The pipeline MUST NOT
replay full conversations by default or publish facts without eligible evidence.

### D-03 — Cache Taxonomy

**Disposition:** Partially accepted; accepted with layer-specific retention.

**Decision.** V2 MUST define the following cache layers under a single Cache
Registry managed by Knowledge Runtime:

| Layer | Owner/lifetime | Binding restriction |
| --- | --- | --- |
| Prompt Cache | adapter/session; ephemeral | derived input only; no authority |
| Conversation Cache | restricted diagnostics; short retention | disabled by default; no automatic promotion |
| Resume Cache | adapter-private; abnormal recovery window | opaque and never required for recovery |
| Knowledge Cache | named root; across normal work | provenance-linked and rebuildable from Git/evidence |

All cache layers are disposable. Cache registry metadata, not cache contents,
is the runtime's normal operational record.

### D-04 — Resume Lifecycle

**Disposition:** Partially accepted; accepted with V1 role names.

**Decision.** V2 MUST define Resume Scopes for Root, Planner, Implementer, and
Reviewer. “Feature Resume” is a grouping term for planner, implementer, and
reviewer scopes; “Worker Resume” is not introduced because V2 has no generic
worker role.

Resume is allowed only after abnormal process/host loss. Each scope expires at
the corresponding session's terminal lifecycle boundary. A resumed implementer
MUST receive a current writer lease; a resumed reviewer MUST receive current
immutable review evidence; no resume can restore expired authority.

### D-05 — Session Lineage Graph

**Disposition:** Partially accepted; accepted as a derived provenance graph.

**Decision.** V2 MUST project fork and fresh-reconstruction ancestry as a
directed acyclic forest. Node metadata includes session ID, parent session ID,
root, feature, role, snapshot version, fork/reconstruction type, and terminal
disposition. The graph supports diagnostics, cache provenance, and cleanup.

It MUST NOT route messages, grant permissions, cause automatic transcript
inheritance, or replace event causation. Communication remains Event Store
events delivered by Dispatcher.

### D-06 — Knowledge Compression

**Disposition:** Accepted.

**Decision.** Knowledge Compression is a required stage of Knowledge Evolution.
It converts eligible evidence into bounded candidate facts classified as
confirmed fact, explicitly labelled inference, open question, or transient
summary. A fact without provenance is rejected. Conversation Cache eviction is
retention policy; no compression stage may delete Git or Event Store audit
evidence.

### D-07 — Scheduler decomposition

**Disposition:** Partially accepted; accepted without a persistent-worker pool.

**Decision.** The orchestrator MUST explicitly contain Dispatcher, Eligibility
Scheduler, Durable Delivery Queue, Priority Policy, Retry Schedule, and Session
Registry modules. They select and route work asynchronously, respecting leases,
policy, deadlines, and capacity.

Claude and Codex root/fork sessions MUST NOT be modelled as an interchangeable
Worker Pool. A separate stateless-worker capability may be proposed only by a
future ADR.

### D-08 — Event Store

**Disposition:** Accepted.

**Decision.** V2 MUST name Event Store as the first-class append-only runtime
evidence component. It stores accepted events, delivery records, command
intents, acknowledgements, and projection-replay evidence. It supports audit,
observability, recovery, and idempotency.

Event Store replay MUST rebuild projections and reconcile deterministic
postconditions. It MUST NOT blindly replay terminal input, Git mutation, or
other external effects.

### D-09 — Complete Runtime Sequence

**Disposition:** Accepted.

**Decision.** V2 documentation MUST contain one normative summary diagram that
shows fork, implementation, review, retry, merge, Knowledge Evolution, root
notification, optional metadata-only Root Update Commit, feature destruction,
and root idle. The diagram must distinguish integration commit from optional
metadata commit and point to lifecycle/state requirements for details.

### D-10 — Runtime Lifecycle and loops

**Disposition:** Partially accepted; accepted as two loops.

**Decision.** V2 MUST define:

~~~text
Control Loop:
Receive -> Validate and Persist -> Project -> Schedule/Dispatch
-> Execute or Observe -> Emit/Project outcome -> Idle

Agent Loop:
Receive notice -> Read immutable packet -> Process assigned role
-> Emit structured event or deferral -> Idle
~~~

Review is a feature-workflow transition, not a mandatory stage of every control
loop. Neither loop waits for another agent's completion.

## 5. Permanently rejected interpretations

The following are permanently rejected by V2 and MUST NOT be introduced as
synonyms or implementation shortcuts:

1. Central authoritative conversation memory or transcript-first recovery.
2. A separate autonomous LLM “knowledge engine” that writes facts without
   evidence validation.
3. Normal-use resume, resume as a context-refresh operation, or resume IDs as
   correctness dependencies.
4. Direct session graph messaging, graph-derived permission, or inherited child
   conversation state.
5. A generic Worker Pool for stateful persistent Claude/Codex sessions.
6. Event Store replay that blindly executes unconfirmed external effects.
7. Root Update Commit changing application code, integration history, or merge
   authority.
8. Conversation Cache as a normal durable knowledge or audit layer.
9. A universal runtime loop that makes review mandatory for recovery, telemetry,
   scheduling, or other non-feature operations.

## 6. Required V2 component contract

Every V2 component listed below MUST have one owner chapter that defines its
responsibility, lifecycle, interactions, and limitations. Other chapters MUST
reference that definition rather than redefining it.

| Component | Owner chapter |
| --- | --- |
| Knowledge Runtime, snapshot domains, Cache Registry, Compression | Runtime 09 |
| Knowledge Synchronization and Evolution trigger | Workflow 16 |
| Event Store | Architecture 01 and Protocol 11 |
| Scheduler/Dispatcher/Queue/Session Registry | Runtime 10 |
| Resume scopes | Runtime 07 |
| Session Lineage Graph | Architecture 03 and Runtime 08 |
| Control and Agent loops | Runtime 05 and Runtime 10 |
| Root Update Commit | Workflow 16 and Workflow 15 |

## 7. Conformance and change control

An implementation or document change conforms to V2 only when it preserves the
retained invariants, uses the binding vocabulary, and passes the migration and
test requirements referenced by this ADR. Documentation MUST update affected
diagrams, configuration, operations, security, and glossary material together.

Any contradiction, expansion of a rejected interpretation, or material change
to a frozen decision requires a new ADR that supersedes or amends ADR-011.
