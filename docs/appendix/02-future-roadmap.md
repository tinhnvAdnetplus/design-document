# 28 — Future Roadmap

## Purpose

This appendix describes future directions without changing current requirements.
Every expansion must retain Git-first truth, explicit authority, event-driven
coordination, and reconstructible context.

## Stage 1 — Local V2 hardening

Deliver stable Claude and Codex adapters, deterministic Event Store/projection,
worktree leases, structured review approval, Knowledge Runtime, Cache Taxonomy,
Session Lineage Graph, Capability Registry, scheduler decomposition,
observability, and chaos recovery. Exit criteria are adapter contract tests,
lost-resume recovery,
knowledge-evolution provenance, and secure default logging.

## Stage 2 — Adapter expansion

Potential adapters include Gemini CLI, OpenAI Responses API, local LLMs, MCP
servers, and custom AI workers. An adapter is admitted only when it provides:

| Requirement | Reason |
| --- | --- |
| current Capability Document from `capabilities()` | Runtime Registry and deterministic adapter selection |
| bounded packet interface | token and privacy control |
| start/fork or compatible child semantics | feature isolation |
| readiness and stop observation | lifecycle supervision |
| exceptional recovery path | no vendor lock-in |
| structured result emission | event protocol compliance |
| tested permission boundary | safety |

A stateless API worker may implement a synthetic fork using immutable packet
provenance. It must advertise that it has no persistent native session.

## Stage 3 — Stronger isolation

Add per-agent containers or sandbox accounts, network proxies, filesystem
namespaces, sandboxed Git gateways, secret broker integration, signed events,
and remote append-only audit. These changes improve defense in depth but add
operational cost and need migration for existing state directories.

## Stage 4 — Distributed execution

Remote workers require durable shared Event Store, authenticated transport,
distributed or centralized lease authority, clock/skew policy, remote
attestation, artifact transfer, and recovery across hosts. tmux remains a local
adapter implementation, not the distributed protocol.

## Stage 5 — Review policy evolution

Possible profiles include human-plus-agent approval, specialist security
review, quorum review, repository-code-owner mapping, and risk-adaptive gates.
Each must define exact approval binding, invalidation, conflict resolution,
identity, and audit evidence before replacing single-Claude approval.

## Non-goal guardrails

Roadmap items must not turn transcript memory into source truth, grant agents
broad unscoped shell or merge authority, erase Git worktree isolation, or
convert event delivery into hidden synchronous RPC, or turn persistent CLI
sessions into a generic worker pool. A new capability that needs one of these
changes requires an ADR and explicit migration plan.

## Research topics

- Provenance-aware semantic cache selection.
- Tree Hash Carry Forward for a future, evidence-preserving optimization of
  unchanged repository-tree identification. It is not part of the V2 baseline
  workflow, fork semantics, Knowledge Evolution, or Root Update Commit.
- Formal verification of workflow state machines.
- Differential review using multiple independent agents.
- Token-aware scheduler fairness.
- Safe model tool-use sandboxing.
- Privacy-preserving aggregate observability.
- Commit-linked knowledge graph generation.

## Prioritization criteria

Prioritize features that reduce recovery risk, improve authorization evidence,
or lower repeated context cost without weakening auditability. Defer convenience
features that obscure state ownership or make a correct recovery harder.
