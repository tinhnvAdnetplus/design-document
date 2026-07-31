# 05 — V2 Architecture Review Report

## Purpose

This report reviews the independent review against the Version 1 architecture.
It is a decision input, not a list of automatically accepted requirements.
Architectural consistency, Git-first durability, explicit authority, and
asynchronous event semantics remain the criteria for every conclusion.

## Review method

Each proposal is assessed against five questions:

1. Does it address a real V1 ambiguity or gap?
2. Does it conflict with a V1 invariant or capability boundary?
3. Does it add an independently useful concept or only another name?
4. Does it improve recovery, maintainability, or observability?
5. Can it be introduced without turning conversations into source of truth?

The decision labels mean:

| Label | Meaning |
| --- | --- |
| Agree | Adopt the proposal's architectural intent and implementation direction. |
| Partially Agree | Adopt a narrowed or renamed design that preserves V1 invariants. |
| Disagree | Do not add the proposal; document the reason and retain V1 design. |

## Executive conclusion

V1 already contains several proposed capabilities under less explicit names:
the event log, delivery scheduler, root cache, and cache synchronization.
The review correctly identifies that their boundaries are under-modelled. V2
therefore promotes knowledge lifecycle, event persistence, session lineage, and
scheduling to explicit architecture concepts.

V2 does not introduce a central conversation memory, an autonomous semantic
engine, direct session-to-session edges, or a generic worker pool for persistent
CLIs. Those additions would conflict with the V1 separation of Git truth,
disposable session state, exclusive worktree ownership, and non-blocking events.

## Item 1 — Knowledge Runtime

**Decision: Partially Agree.**

### Validity

The V1 root cache is correctly described as derived and disposable, but the
document set does not make its internal knowledge domains and lifecycle visible
enough. Architecture, conventions, dependencies, workspace status, and selected
business/domain facts are currently scattered across cache examples and root
responsibilities. This makes adapter authors likely to invent incompatible
cache layouts.

### Architectural fit

A Knowledge Runtime is compatible when defined as a logical control-plane
component, not a new persistent AI process and not a second source of truth. It
owns bounded knowledge snapshots, selection, provenance validation, compression,
and cache invalidation. It does not own application truth, feature workflow
state, approval, or Git mutation.

### V2 refinement

V2 introduces **Knowledge Runtime** with six snapshot domains:

| Snapshot | Scope | Primary evidence |
| --- | --- | --- |
| Project | repository identity, integration baseline, active constraints | Git/configuration |
| Architecture | components, interfaces, decisions | Git, ADRs, code/docs |
| Business | bounded domain rules and terminology present in repository | versioned product evidence |
| Workspace | worktree/branch/lease observations | Git/worktree manager |
| Dependency | manifests, lockfiles, generated dependency metadata | Git |
| Convention | style, test, build, repository rules | Git/configuration |

Business Snapshot is deliberately constrained to evidence in the repository or
explicitly attached governed artifacts. It is not a model-generated product
memory or a feed of external conversational claims.

### Complexity and maintainability

This adds an important stable boundary and lowers future adapter divergence.
It would be unnecessary complexity if implemented as a separate daemon,
database, or LLM. V2 requires a module and data contract inside the
orchestrator control plane, with root-owned snapshot artifacts.

### Affected documentation

Architecture Overview, Agent Model, State Model, Runtime Overview, Cache
Strategy, Orchestrator, Knowledge Synchronization, Configuration, Reference
Implementation, Operations, Security, Glossary, README, and SUMMARY.

## Item 2 — Knowledge Evolution Engine

**Decision: Partially Agree.**

### Validity

V1 synchronization explains when a root updates cache, but it under-specifies
how Git evidence becomes a revised, validated knowledge snapshot. The proposed
evolution sequence makes the need for an explicit transformation pipeline clear.

### Architectural fit

Replacing synchronization with an opaque engine would be wrong. Synchronization
is a required workflow trigger and completion event. V2 preserves it and defines
**Knowledge Evolution** as the internal pipeline that synchronization invokes.

### V2 refinement

The V2 pipeline is:

~~~text
Merge evidence
  -> detect affected knowledge domains
  -> collect Git and governed-event evidence
  -> compress into candidate facts
  -> validate provenance, confidence, scope, and budget
  -> atomically publish new snapshot version
  -> notify the unchanged persistent root
~~~

The root process is not replaced by an “updated root.” It remains the same
session; it receives a newer derived snapshot. This avoids confusion between
process identity and knowledge version.

### Complexity and maintainability

A named pipeline improves tests, telemetry, invalidation, and audit. It must
remain deterministic at boundaries: model-generated candidate summaries require
citation validation and bounded human/policy fallback. A general “knowledge
engine” that invents facts is rejected.

### Affected documentation

Knowledge Runtime chapter, Synchronization chapter, State Model, Event Protocol,
Testing, Metrics, Recovery, and diagrams.

## Item 3 — Cache Layer

**Decision: Partially Agree.**

### Validity

V1 distinguishes prompt cache, resume metadata, and root cache but lacks a
cache taxonomy, ownership model, retention policy, and invalidation matrix.
This is a real maintainability gap.

### Architectural fit

Four explicit cache classes fit the V1 rule that all caches are disposable:
Prompt Cache, Conversation Cache, Resume Cache, and Knowledge Cache. They must
not all receive equal durability or retention.

### V2 refinement

| Cache layer | V2 status | Important constraint |
| --- | --- | --- |
| Prompt Cache | explicit ephemeral derived layer | never source of authority |
| Conversation Cache | explicit diagnostic-only layer | disabled by default; no automatic promotion |
| Resume Cache | explicit adapter-private optimization | opaque; usable only after failure |
| Knowledge Cache | explicit root-owned derived layer | provenance and Git-based rebuild required |

The four layers are registered by the Knowledge Runtime and cache registry; they
are not four independently deployed services.

### Complexity and maintainability

The taxonomy prevents accidental transcript retention and vendor coupling.
Treating Conversation Cache as a normal durable layer would conflict with V1
and is rejected.

### Affected documentation

Runtime cache chapter, Resume, Configuration, Security, Logging, Recovery,
Testing, Glossary, and README.

## Item 4 — Resume Lifetime

**Decision: Partially Agree.**

### Validity

V1 says resume is exceptional but does not state lifetime by role. This leaves
feature and review recovery behavior too open.

### Architectural fit

The proposed root, feature, worker, and review categories overlap V1 roles.
“Worker” is not a V1 role and would introduce an undefined concept.

### V2 refinement

V2 defines **Resume Scope** for Root, Planner, Implementer, and Reviewer
sessions. A Feature Resume is a grouping name, not an additional session type.
All feature-role resume is bounded by feature terminal state and may never
recreate write authority without a fresh lease. Root resume lasts only for the
configured root identity and is attempted only after abnormal loss.

### Complexity and maintainability

A table of role-specific expiry, evidence, and fresh reconstruction improves
recovery predictability with little complexity. A generic worker-resume system
is deferred until stateless workers exist.

### Affected documentation

Persistent Sessions and Resume, Session Lifecycle, Claude/Codex Runtimes,
Recovery, Configuration, Testing, and Glossary.

## Item 5 — Session Graph

**Decision: Partially Agree.**

### Validity

V1 records parent root and feature IDs but lacks an explicit lineage model.
This makes fork provenance, cache inheritance, and recovery inspection harder
than necessary.

### Architectural fit

A graph must not be interpreted as a direct communication topology. Sessions
still communicate only through events, and a parent root never inherits child
conversation state automatically.

### V2 refinement

V2 adds a **Session Lineage Graph**, a directed acyclic forest. Nodes are
runtime sessions and edges are fork or reconstruction lineage. Feature,
role, cache version, and terminal state are node attributes. Event causation
remains an independent graph. There are no graph edges that grant authority or
permit direct RPC.

### Complexity and maintainability

The lineage graph is a projection/index over existing session events, not a
new store. It enables precise cleanup and visual diagnostics. Arbitrary
cross-session dependency edges are rejected because they duplicate event
causation and complicate recovery.

### Affected documentation

Architecture Overview, Agent Model, State Model, Lifecycle, Orchestrator,
Observability, Reference Implementation, and diagrams.

## Item 6 — Knowledge Compression

**Decision: Agree.**

### Validity

V1 treats compactness primarily as a token budget. The review correctly
identifies a more important requirement: retain evidenced understanding while
allowing disposable conversation material to expire.

### Architectural fit

Compression must never convert a model claim into a fact without evidence. It
must not delete audit events or Git history. “Forget conversation” applies to
the optional Conversation Cache under retention policy, not to the event store.

### V2 design

V2 names **Knowledge Compression** as the pipeline stage that produces
provenance-linked snapshot facts from eligible evidence. It distinguishes:
verbatim transient material, bounded summary, confirmed fact, inference, and
open question. Only confirmed facts and explicitly labelled inferences are
eligible for root knowledge snapshots.

### Complexity and maintainability

This improves long-term context quality and token efficiency. The data model
and provenance checks prevent it from becoming an opaque summarizer.

### Affected documentation

Knowledge Runtime, Cache Strategy, Synchronization, Security, Logging,
Testing, Token Capacity, and Glossary.

## Item 7 — Scheduler

**Decision: Partially Agree.**

### Validity

V1 contains scheduling responsibilities and delivery queues but does not expose
them as distinct orchestrator internals. This makes backpressure, priority, and
retry semantics easy to overlook.

### Architectural fit

A Dispatcher, Eligibility Scheduler, Durable Delivery Queue, Priority Classes,
and Retry Schedule are accepted. A generic Worker Pool is rejected for
persistent Claude/Codex CLIs: roots and forks are stateful, role-bound
processes, not interchangeable jobs.

### V2 refinement

The Scheduler selects eligible command intents and event deliveries without
waiting for task completion. The Dispatcher routes to registered sessions. The
Session Registry supplies capacity and availability. A future Stateless Worker
Pool may be added for non-persistent custom workers behind a distinct adapter
capability.

### Complexity and maintainability

This is a clarification and modularization of existing V1 behavior, not a
second orchestrator. It improves queue metrics, fairness, and retry tests while
protecting persistent-session semantics.

### Affected documentation

Architecture Overview, Runtime Overview, Orchestrator, Protocol, Error
Handling, Operations, Configuration, Reference Implementation, and roadmap.

## Item 8 — Event Store

**Decision: Agree.**

### Validity

V1 describes an event log and state store, but the review is correct that
Event Store should be a named durable component with explicit replay,
recovery, audit, and observability responsibilities.

### Architectural fit

The Event Store remains an operational evidence source, not source truth for
code. It supports projection replay and intent reconciliation; it never
blindly replays external side effects.

### Complexity and maintainability

This is a naming and contract clarification with substantial operational value.
It should not become an unbounded transcript database.

### Affected documentation

Architecture Overview, Runtime Overview, Protocol, State Model, Recovery,
Observability, Reference Implementation, Configuration, and Glossary.

## Item 9 — Complete Runtime Sequence

**Decision: Agree.**

### Validity

V1 has several partial sequences but no single end-to-end lifecycle including
retry, cleanup, idle, and the optional root update commit. This hampers
onboarding and design verification.

### V2 design

V2 adds a primary sequence and lifecycle flow from request through fork, plan,
implementation, review/retry, merge, knowledge evolution, optional metadata
checkpoint, feature destruction, and root idle. It distinguishes integration
commit from optional metadata-only root update commit.

### Complexity and maintainability

The diagram adds no runtime mechanism and improves shared understanding. It
must remain a summary that points to state-machine requirements rather than
supplanting them.

### Affected documentation

README, State Model, Feature Lifecycle, Knowledge Synchronization, appendix
examples, and SUMMARY.

## Item 10 — Runtime Loop

**Decision: Partially Agree.**

### Validity

The review correctly asks for an explicit control loop, but its proposed
universal sequence incorrectly makes “Review” a mandatory orchestrator stage.
Review is a workflow role and not part of lease expiration, root sync, recovery,
or telemetry loops.

### V2 refinement

V2 defines two loops:

~~~text
Control Loop:
Receive -> Validate and Persist -> Project -> Schedule/Dispatch
-> Execute or Observe -> Emit/Project outcome -> Idle

Agent Loop:
Receive notice -> Read immutable packet -> Process assigned role
-> Emit structured event -> Idle
~~~

The feature workflow invokes review through a normal event transition. Neither
loop blocks awaiting another agent.

### Complexity and maintainability

Two small loops clarify responsibilities without a misleading monolithic
runtime pipeline. The alternative proposed loop is rejected as a universal
state machine.

### Affected documentation

Runtime Overview, Orchestrator, Protocol, State Model, Reference
Implementation, Testing, and diagrams.

## Rejected interpretations

The following interpretations are explicitly rejected:

- a centrally authoritative conversation-memory database;
- automatic replay of all conversation material after merge;
- an LLM that independently mutates root knowledge without evidence validation;
- direct session graph communication or inherited child transcripts;
- generic worker-pool treatment of stateful persistent CLI agents;
- resume during normal task flow;
- blind replay of event side effects;
- treating optional cache metadata commits as application code commits.

## V2 acceptance criteria

V2 is complete when the named concepts appear once in the component model and
are used consistently in runtime, protocol, operations, security, configuration,
testing, and glossary documentation; all diagrams preserve event-driven
communication and Git-first source truth; and the migration path operates with
existing V1 state.

