# AI Multi-Agent Runtime — Design Specification

This repository is the normative architecture specification for **AI Multi-Agent
Runtime**, a persistent collaboration runtime for Claude CLI and Codex CLI.

The runtime keeps each CLI agent alive in its own `tmux` session, creates an
isolated forked session for feature work, and uses Git as the sole durable
source of truth. The V2 Knowledge Runtime manages bounded, provenance-linked
snapshots and cache layers; a session transcript, resume identifier, and prompt
cache remain explicitly disposable implementation details.

## Reading the specification

Start with the [documentation entry point](docs/README.md), then use the
[table of contents](docs/SUMMARY.md). The document set uses the following
normative terms:

| Term | Meaning |
| --- | --- |
| **MUST** | Required for a conforming implementation. |
| **MUST NOT** | Prohibited for a conforming implementation. |
| **SHOULD** | Recommended unless a documented reason exists. |
| **MAY** | Optional. |

## Design invariants

1. Git `HEAD` and the reachable Git object graph are the only source of truth.
2. A root agent owns project-wide understanding but never implements a feature.
3. Feature work happens in disposable forked sessions and isolated worktrees.
4. Claude is the merge approver; Codex is the implementation agent in the
   baseline workflow.
5. Agent-to-agent interaction is asynchronous event delivery, never a blocking
   request/reply dependency.
6. Normal development neither restarts nor resumes a running agent process.
7. Only a root session publishes its own evolved long-lived knowledge snapshot
   after a merge.
8. The Event Store records runtime evidence; it never replaces Git code truth
   or blindly replays external side effects.
9. Session lineage is a derived fork/reconstruction graph, never a direct
   agent-to-agent transport or authority graph.

## Scope

The initial release specifies a local, single-host runtime. It supports:

- Claude CLI and Codex CLI as persistent processes;
- `tmux` transport and process supervision boundaries;
- Git worktrees for feature isolation;
- append-only JSON events and agent acknowledgements;
- Event Store replay, scheduler/dispatcher queues, and a derived session
  lineage graph;
- Runtime-owned Capability Registry populated only by Adapter capability
  declarations, with revalidation on startup and upgrades;
- Knowledge Runtime snapshots, cache layers, and evidence-based evolution;
- restart recovery and best-effort CLI resume after a host or process failure;
- logging, metrics, token accounting, and least-privilege execution.

It does not replace Git hosting, CI, code review policy, secret management, or
human responsibility for merge policy. Those integrations are described only
where the runtime needs a stable boundary.

## Repository layout

```text
docs/
  architecture/     system structure, responsibilities, decisions
  runtime/          session, cache, tmux, and orchestrator behavior
  protocol/         event envelope, schemas, and delivery semantics
  workflow/         feature, review, merge, Git, and synchronization flow
  implementation/   configuration, layout, reference implementation, testing
  operations/       observability, performance, recovery, and concurrency
  security/         threat model and permission model
  appendix/         roadmap, glossary, and normative examples
```

## Status

This is the Version 2 design specification. Event protocol version `v1`
remains compatible; V2 adds explicit runtime components and vocabulary without
changing the Git-first source-of-truth boundary. See the
[V2 Architecture Review](docs/architecture/05-v2-architecture-review.md),
[V2 Design Decisions](docs/architecture/06-v2-design-decisions.md), and
[V1 → V2 Migration Guide](docs/implementation/05-v1-v2-migration-plan.md).

Implementation and validation have separate maturity levels:

- the frozen contract laboratory has passed 82/82 assertions;
- the SQLite WAL Event Store is a merge-ready production-oriented vertical slice;
- live Antigravity/Codex compatibility is tracked by the isolated Phase 2C PoC;
- the complete multi-agent runtime is not yet a production implementation.

See the [validation roadmap](ai-runtime-validation/ROADMAP.md), the
[Phase 3 Event Store recommendation](reports/phase-3/recommendation.md), and the
[evidence portability audit](ai-runtime-validation/reports/evidence-portability-audit.md).
