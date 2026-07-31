# Documentation Summary

This summary is the canonical table of contents for the AI Multi-Agent Runtime
specification. Chapter numbers are stable identifiers; filenames may gain a
minor prefix without changing the chapter identifier cited by another document.

## Start here

- [Project Overview and Vision](README.md)
- [Architecture Overview](architecture/01-architecture-overview.md)
- [Agent Model and Decision Records](architecture/02-agent-model-decisions.md)
- [Runtime Overview](runtime/01-runtime-overview.md)
- [V2 Architecture Review](architecture/05-v2-architecture-review.md)
- [ADR-011 — Version 2 Runtime Evolution](architecture/06-v2-design-decisions.md)
- [V1 → V2 Migration Guide](implementation/05-v1-v2-migration-plan.md)

## Architecture

- [01 — Architecture Overview](architecture/01-architecture-overview.md)
  - system boundaries and component responsibilities
  - deployment topology and failure domains
  - architectural invariants and quality attributes
- [02 — Agent Model and Decision Records](architecture/02-agent-model-decisions.md)
  - root, feature, reviewer, and merger roles
  - role ownership, capability matrix, and ADRs
- [03 — State Model and Diagrams](architecture/03-state-model-diagrams.md)
  - aggregate state, state machines, and sequences
  - component, deployment, and class diagrams
- [04 — Architectural Decisions](architecture/04-decision-records.md)
  - decisions, alternatives, consequences, and revision policy
- [05 — V2 Architecture Review](architecture/05-v2-architecture-review.md)
  - assessment of every independent-review proposal
  - accepted, refined, and rejected V2 concepts
- [ADR-011 — Version 2 Runtime Evolution](architecture/06-v2-design-decisions.md)
  - binding V2 vocabulary, decisions, and rejected interpretations

## Runtime

- [05 — Runtime Overview and Requirements](runtime/01-runtime-overview.md)
  - functional requirements, Capability Registry, and root-context replacement guidance
  - adapter boundaries and runtime interfaces
- [06 — Claude and Codex Runtimes](runtime/02-claude-codex-runtimes.md)
  - CLI adapter and agent-compliance contracts, capability discovery, and vendor-specific behavior
  - terminal control, readiness, and output boundaries
- [07 — Persistent Sessions and Resume](runtime/03-persistent-sessions-resume.md)
  - normal persistence and exceptional resume strategy
  - reboot, crash, and fresh-session reconstruction
- [08 — Session and Feature Lifecycle](runtime/04-session-lifecycle.md)
  - lifecycle states, leases, cleanup, and abandonment
- [09 — Knowledge Runtime, Fork, and Cache Strategy](runtime/05-fork-knowledge-prompt-cache.md)
  - snapshots, cache registry, compression, fork discipline, and token optimization
- [10 — tmux Runtime and Orchestrator](runtime/06-tmux-orchestrator.md)
  - session layout, `send-keys`, event delivery, and supervision

## Protocol

- [11 — Communication Protocol](protocol/01-communication-protocol.md)
  - event-driven interaction, ordering, acknowledgement, and retry
- [12 — Message Format and JSON Events](protocol/02-message-json-event-protocol.md)
  - envelope schema, event catalog, validation, and examples
- [13 — Protocol Error Handling](protocol/03-protocol-error-handling.md)
  - rejection, deduplication, poison events, and compatibility

## Workflow

- [14 — Feature and Review Lifecycle](workflow/01-feature-review-lifecycle.md)
  - plan, implement, review, fix, approve, and terminate flow
- [15 — Merge Strategy and Git Workflow](workflow/02-merge-git-workflow.md)
  - branches, worktrees, commits, checks, and merge authority
- [16 — Knowledge Synchronization](workflow/03-knowledge-synchronization.md)
  - post-merge inspection, cache updates, and provenance
- [17 — Human Operations and Exceptions](workflow/04-human-operations-exceptions.md)
  - intervention points, overrides, and incident workflow

## Implementation

- [18 — Configuration and Workspace Layout](implementation/01-configuration-workspace.md)
  - configuration reference, ownership files, and directory tree
- [19 — Reference Implementation](implementation/03-reference-implementation.md)
  - modules, pseudocode, shell examples, and integration order
- [20 — Testing and Benchmark Strategy](implementation/04-testing-benchmarks.md)
  - test pyramid, fixtures, chaos scenarios, and measurements
- [V1 → V2 Migration Guide](implementation/05-v1-v2-migration-plan.md)
  - compatible rollout, validation gates, and rollback

## Operations

- [21 — Logging, Monitoring, and Metrics](operations/01-logging-monitoring-metrics.md)
  - Event Store logs, dashboards, alerts, and privacy controls
- [22 — Performance, Tokens, and Capacity](operations/02-performance-token-capacity.md)
  - prompt budgets, latency, throughput, and benchmarking
- [23 — Recovery and Fault Tolerance](operations/03-recovery-fault-tolerance.md)
  - fault matrix, recovery procedure, and data integrity
- [24 — Deadlock Prevention and Concurrency](operations/04-deadlock-concurrency.md)
  - leases, ordering, starvation, and safe parallelism

## Security

- [25 — Security Architecture](security/01-security-architecture.md)
  - threat model, trust zones, secrets, and command restrictions
- [26 — Permission Model](security/02-permission-model.md)
  - capabilities, workspace access, policy evaluation, and audit

## Appendix

- [27 — Protocol and tmux Examples](appendix/01-protocol-tmux-examples.md)
  - end-to-end event, config, shell, and failure examples
- [28 — Future Roadmap](appendix/02-future-roadmap.md)
  - staged roadmap and adapter expansion criteria
- [29 — Glossary and Reference](appendix/03-glossary-reference.md)
  - defined terms, status codes, and reference checklists
- [V2 Changelog](CHANGELOG.md)
  - version history and compatibility notes

## Cross-reference rules

Documents link by relative Markdown path. A statement labeled **Normative** is
binding where it uses MUST, MUST NOT, SHOULD, or MAY. A decision record records
the reason behind an architectural choice but does not override an explicit
normative requirement. Implementation examples are illustrative unless their
section says otherwise.

## Reading paths

| Reader | Recommended sequence | Outcome |
| --- | --- | --- |
| Runtime implementer | 01, 05–13, 18–24 | A conforming local runtime. |
| Agent adapter author | 02, 05–10, 11–13, 25–26 | A compatible adapter with safe recovery. |
| Repository maintainer | 01–06, 14–17, 25–26 | Policy, review, merge, and V2 rationale. |
| SRE or platform engineer | 03, 06, 10–13, 21–24 | Operable deployment and incident procedures. |
| Security reviewer | 02, 05–06, 11–13, 17, 25–26 | Trust boundaries and authorization evidence. |

## Requirement traceability

| Area | Primary chapters | Evidence |
| --- | --- | --- |
| Persistent agents | 05–10 | lifecycle tests and tmux inspection |
| Resume and recovery | 07, 23 | reboot / lost-ID and Registry-gated resume scenario |
| Feature isolation | 08, 14–15, 18 | worktree ownership test |
| Event protocol | 11–13 | schema and delivery tests |
| Approval authority | 02, 14–15, 26 | authorization test |
| Knowledge Runtime/cache | 05, 09, 16, 21 | rebuild, provenance, and migration test |
| Event Store, scheduler, and capabilities | 01, 05–13, 21–24 | replay, Registry revalidation, queue fairness, and recovery test |
| Operations | 21–24 | dashboard, alert, and chaos evidence |
| Security | 25–26 | capability and secret-handling tests |

## Documentation maintenance

Update this summary when adding, removing, or substantially changing a chapter.
Every normative interface change MUST update its owner chapter, corresponding
examples, test strategy, and at least one decision record or changelog entry.
