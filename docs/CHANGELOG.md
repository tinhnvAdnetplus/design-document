# Changelog

All notable architecture-specification changes are recorded here. This document
uses semantic intent rather than implementation-release dates.

## Unreleased — Second Architecture Review Board Integration

### Integrated clarifications

- Added the Agent Compliance Contract: terminal-event obligation, observable
  completion reconciliation, silent-completion recovery, and test coverage.
- Promoted Capability Registry to a Runtime component populated only by
  `Adapter.capabilities()`, with Scheduler/fork/resume dependency,
  revalidation, and misreporting fail-closed behavior.
- Added configured review/fix escalation, explicit model-inference network
  permission, and Minimal versus Full V2 Conformance clarification.
- Clarified that Root Update Commit is optional metadata-only checkpointing;
  added only a roadmap entry for Tree Hash Carry Forward.

### Explicit non-changes

- No ADR, invariant, baseline workflow, Knowledge Runtime, Knowledge Evolution,
  Session Lineage Graph, Event Store, Root Session, Control Loop, Eligibility
  Scheduler, fork abstraction, Git-first, evidence-first, or Root Update Commit
  architecture was changed.

## Version 2 — Runtime Evolution

### Added

- **ADR-011** as the single binding authority for V2 decisions, refinements,
  and permanently rejected interpretations.
- **Knowledge Runtime** as the logical control-plane owner of snapshot
  selection, Cache Registry metadata, Knowledge Compression, validation, and
  publication coordination.
- Six bounded Knowledge Snapshot domains: Project, Architecture, Business,
  Workspace, Dependency, and Convention.
- **Knowledge Evolution** pipeline invoked by synchronization and driven by
  Git diff plus governed Event Store evidence.
- Explicit **Cache Taxonomy**: Prompt, Conversation, Resume, and Knowledge
  Cache, each with ownership, retention, and invalidation constraints.
- Role-specific **Resume Scope** lifetime for Root, Planner, Implementer, and
  Reviewer sessions.
- Derived **Session Lineage Graph** for fork/reconstruction provenance.
- First-class **Event Store** naming and replay constraints.
- Orchestrator **Dispatcher**, **Eligibility Scheduler**, Durable Delivery
  Queue, Priority Policy, Retry Schedule, and Session Registry boundaries.
- A complete V2 runtime sequence diagram covering retry, merge, evolution,
  optional metadata checkpoint, destruction, and idle.
- [V1 → V2 Migration Guide](implementation/05-v1-v2-migration-plan.md).

### Changed

- Knowledge synchronization now explicitly invokes Knowledge Evolution rather
  than describing cache update as an unspecified root action.
- Root knowledge is expressed as versioned, provenance-linked Knowledge
  Snapshots; a root process remains persistent across snapshot publication.
- Event log terminology is standardized to Event Store where referring to the
  durable runtime-evidence component.
- Runtime control and agent loops are specified separately to preserve
  non-blocking event-driven behavior.
- Root Update Commit is constrained to optional metadata-only cache manifests
  on a protected dedicated branch.
- Configuration, telemetry, security, recovery, and tests include V2 cache,
  lineage, scheduler, evolution, and Event Store constraints.

### Deprecated terminology

- “Root cache” remains a compatibility shorthand only; **Knowledge Cache** and
  **Knowledge Snapshot** are the normative V2 terms.
- “Event log” remains readable in historical V1 ADRs; **Event Store** is the
  normative V2 component name.
- “Feature Resume” is a grouping label only. “Worker Resume” is not a V2 term.

### Explicit non-changes

- Git remains the source of truth for application code and history.
- Claude approval/Codex implementation remains the baseline policy profile.
- tmux remains local process/notification infrastructure only.
- Sessions, resumes, prompts, conversations, and caches remain disposable.
- Feature sessions remain isolated and terminally destroyed.

### Rejected in V2

- Central authoritative conversation memory.
- Automatic transcript replay or unvalidated knowledge promotion.
- Direct session-graph transport or graph-derived authority.
- Generic worker-pool semantics for persistent Claude/Codex sessions.
- Blind Event Store replay of external effects.
- Root Update Commit modification of application code or integration history.

## Version 1 — Initial Architecture

- Established Git-first durability, persistent roots, disposable forked
  features, asynchronous events, worktree leases, deterministic merge approval,
  root synchronization, tmux runtime, recovery, security, and operations.
