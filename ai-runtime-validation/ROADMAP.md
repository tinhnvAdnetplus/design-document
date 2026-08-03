# AI Multi-Agent Runtime V2.2 — Validation Roadmap

## Overview

This roadmap defines the phased execution order for validating the AI Multi-Agent Runtime V2.2 Architecture Specification. Each phase builds on validated assumptions from prior phases and produces measurable evidence.

## Phase 2B Execution Status

Status: **CONTRACT VALIDATION COMPLETE**.

The final legacy-format run `artifacts/20260803T040752Z-130658` passed
`82/82` assertions. Evidence format v2 now exports nested repositories as
verified Git bundles so new manifests remain valid on a clean checkout.

| Status | Scope |
| --- | --- |
| **Completed** | PoCs 01–10; 82/82 assertions; portable evidence format v2; SQLite WAL Event Store vertical slice; clean-checkout CI workflow |
| **In Progress** | Phase 2C live Antigravity/Codex integration spike (PoC 11) |
| **Blocked** | Production runtime expansion remains gated on live CLI process, structured output, resume/fork, timeout, and cleanup evidence |

Phase 2B validates deterministic adapter contracts and does not claim
live-vendor behavior. Phase 2C temporarily uses Antigravity (`agy`) in place of
Claude CLI and keeps live, quota-consuming probes outside the default suite.

---

## Phase Dependency Graph

```
Phase 1: tmux Runtime
    │
    ▼
Phase 2: Event Protocol
    │
    ▼
Phase 3: Session Resume ◄──── Phase 4: Capability Registry
    │                              │
    ▼                              │
Phase 5: Knowledge Runtime ◄──────┘
    │
    ▼
Phase 6: Review Loop
    │
    ├──────────────────┐
    ▼                  ▼
Phase 7: Scheduler   Phase 8: Chaos
    │                  │
    ▼                  │
Phase 9: Performance ◄─┘
    │
    ▼
Phase 10: End-to-End Integration
```

---

## Phase 1 — tmux Runtime Substrate

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/01-tmux-runtime`](poc/01-tmux-runtime/README.md) |
| **Purpose** | Prove that tmux provides a viable runtime substrate for managing persistent agent sessions with proper naming, lifecycle management, and event notification delivery. |
| **Dependencies** | None (foundational) |
| **Expected Outputs** | Evidence of session creation/destruction, event delivery via `send-keys`, session enumeration, process isolation, and working directory assignment. |
| **Acceptance Criteria** | - Named tmux sessions created with V2.2 naming convention |
|  | - Event notices delivered via `send-keys` and received by target pane |
|  | - Session existence correctly detected via `has-session` |
|  | - Multiple concurrent sessions operate independently |
|  | - Cleanup fully removes all test sessions |
| **Estimated Complexity** | Low — Standard tmux operations with scripted validation |
| **Spec References** | Chapter 10 — tmux Runtime and Orchestrator |
| **Invariants Validated** | INV-07 (non-blocking), INV-08 (disposable features) |

---

## Phase 2 — Event Protocol and Event Store

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/02-event-protocol`](poc/02-event-protocol/README.md) |
| **Purpose** | Prove that the V2.2 JSON event envelope, validation pipeline, and append-only Event Store semantics work correctly, including idempotency and integrity verification. |
| **Dependencies** | Phase 1 (tmux for delivery testing) |
| **Expected Outputs** | Valid event generation, schema validation, idempotency deduplication, integrity hash verification, projection rebuild from replay. |
| **Acceptance Criteria** | - Events conform to `ai-runtime.events/v1` envelope schema |
|  | - Schema validation rejects malformed events with correct error codes |
|  | - Idempotency keys prevent duplicate event acceptance |
|  | - Content SHA-256 integrity verified on read |
|  | - Projection rebuilt identically from event replay |
|  | - Aggregate sequence ordering enforced |
| **Estimated Complexity** | Medium — JSON processing, schema validation, NDJSON store |
| **Spec References** | Chapters 11–13 — Communication Protocol, Message Format, Error Handling |
| **Invariants Validated** | INV-09 (correlation and provenance) |

---

## Phase 3 — Session Resume and Recovery

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/03-session-resume`](poc/03-session-resume/README.md) |
| **Purpose** | Prove that the runtime can recover from session loss through both vendor resume and fresh Git-derived reconstruction, validating that resume is an optimization and never a correctness dependency. |
| **Dependencies** | Phase 1 (tmux sessions), Phase 2 (event protocol) |
| **Expected Outputs** | Evidence of reattach, resume, and fresh reconstruction flows; reconstruction packet generation; dirty worktree quarantine behavior. |
| **Acceptance Criteria** | - Reattach to existing process succeeds when session is alive |
|  | - Resume attempt gated by Capability Registry `resume=true` |
|  | - Fresh reconstruction produces valid packet from Git state |
|  | - Reconstruction packet includes all required fields |
|  | - Dirty worktree detected and quarantined (never auto-deleted) |
|  | - Full feature workflow completes without resume IDs |
| **Estimated Complexity** | Medium — Git state inspection, tmux lifecycle, decision tree |
| **Spec References** | Chapters 7, 8, 23 — Sessions, Lifecycle, Recovery |
| **Invariants Validated** | INV-06 (exceptional resume only) |

---

## Phase 4 — Capability Registry

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/04-capability-registry`](poc/04-capability-registry/README.md) |
| **Purpose** | Prove that the Capability Registry correctly gates adapter operations based on declarative Capability Documents, with proper revalidation and mismatch handling. |
| **Dependencies** | Phase 1 (tmux for adapter context) |
| **Expected Outputs** | Evidence of capability registration, gating decisions, revalidation on triggers, and `ADAPTER_UNAVAILABLE` on mismatch. |
| **Acceptance Criteria** | - Capability Documents registered from adapter `capabilities()` only |
|  | - Fork gated by native_fork/synthetic_fork declaration |
|  | - Resume gated by `resume=true` declaration |
|  | - Revalidation triggered on startup, restart, adapter upgrade, manual CLI upgrade |
|  | - Declaration/observation mismatch produces `ADAPTER_UNAVAILABLE` |
|  | - Stale capability document rejected on revalidation |
| **Estimated Complexity** | Low–Medium — JSON-based registry with gating logic |
| **Spec References** | Chapters 5, 6, 10 — Runtime, Adapters, Orchestrator |
| **Invariants Validated** | Related to INV-06 (resume gating) |

---

## Phase 5 — Knowledge Runtime

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/05-knowledge-runtime`](poc/05-knowledge-runtime/README.md) |
| **Purpose** | Prove that Knowledge Runtime can manage Knowledge Snapshots across 6 domains, apply Knowledge Compression with provenance, and coordinate Knowledge Evolution after merge. |
| **Dependencies** | Phase 2 (event protocol), Phase 4 (capability registry for fork selection) |
| **Expected Outputs** | Valid Knowledge Snapshots, provenance validation, compression pipeline results, evolution after merge evidence, Cache Taxonomy isolation, budget enforcement. |
| **Acceptance Criteria** | - Knowledge Snapshot covers all 6 domains with proper schema |
|  | - Facts classified correctly (confirmed, inferred, open, transient) |
|  | - Unproven facts rejected at validation |
|  | - Compression pipeline produces bounded output with provenance |
|  | - Evolution triggered only after merge evidence (INV-05) |
|  | - Cache Taxonomy layers isolated; Conversation Cache disabled by default |
|  | - Token budget enforced (128 KiB total packet limit) |
| **Estimated Complexity** | High — Multi-domain snapshot, compression pipeline, Git evidence |
| **Spec References** | Chapter 9 — Knowledge Runtime; Chapter 16 — Knowledge Sync |
| **Invariants Validated** | INV-01 (Git-first), INV-05 (post-merge only) |

---

## Phase 6 — Review Loop and Approval

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/06-review-loop`](poc/06-review-loop/README.md) |
| **Purpose** | Prove the complete feature and review lifecycle from plan through merge, including approval binding immutability, escalation, and authorization enforcement. |
| **Dependencies** | Phase 2 (event protocol), Phase 5 (knowledge for sync) |
| **Expected Outputs** | Evidence of lifecycle state transitions, approval binding verification, stale approval rejection, escalation at cycle limit, forged approval rejection, writer lease management. |
| **Acceptance Criteria** | - Feature lifecycle traverses all states correctly |
|  | - Approval binding is immutable and verified at merge time |
|  | - Stale approvals invalidated when head/base/policy change |
|  | - Review/fix cycles escalate at configured limit |
|  | - Forged approvals (wrong role) rejected |
|  | - Writer leases granted/revoked at correct lifecycle transitions |
|  | - Only Claude reviewer authority can emit merge.approved (INV-04) |
| **Estimated Complexity** | Medium–High — State machine, approval binding, escalation |
| **Spec References** | Chapters 8, 14 — Session Lifecycle, Review Lifecycle |
| **Invariants Validated** | INV-03 (single writer), INV-04 (Claude approval), INV-08 (disposable) |

---

## Phase 7 — Scheduler and Dispatcher

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/07-scheduler`](poc/07-scheduler/README.md) |
| **Purpose** | Prove the Eligibility Scheduler and Dispatcher design selects work by priority and policy without blocking on agent responses or creating a worker pool. |
| **Dependencies** | Phase 2 (events), Phase 6 (delivery context) |
| **Expected Outputs** | Evidence of priority dispatch, durable delivery queue, bounded retry, non-blocking orchestration, session registry, fairness under load. |
| **Acceptance Criteria** | - Critical priority events dispatched before normal |
|  | - Delivery queue retains notices until terminal outcome |
|  | - Retry follows bounded backoff then escalation |
|  | - Orchestration loop demonstrably non-blocking |
|  | - Session Registry reports accurate lifecycle and capacity |
|  | - Scheduler fairness maintained under load |
| **Estimated Complexity** | Medium — Priority queue, concurrency, timing validation |
| **Spec References** | Chapters 10, 11 — Orchestrator, Communication Protocol |
| **Invariants Validated** | INV-07 (non-blocking producers) |

---

## Phase 8 — Chaos Engineering

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/08-chaos`](poc/08-chaos/README.md) |
| **Purpose** | Prove fault tolerance and recovery behavior under various failure scenarios including crashes, data loss, state corruption, and timing anomalies. |
| **Dependencies** | Phases 1–6 (all components under test) |
| **Expected Outputs** | Evidence of correct recovery from each fault scenario, adherence to recovery order, dirty worktree quarantine, silent completion failure handling. |
| **Acceptance Criteria** | - Crash before event append → event not accepted |
|  | - Crash after append before projection → replay projects event |
|  | - Crash during merge → actual Git ref determines outcome |
|  | - Dirty worktrees quarantined, never auto-deleted |
|  | - Lost resume IDs → fresh reconstruction succeeds |
|  | - Silent completion failures → reconciliation runs, no inferred completion |
|  | - 11-step recovery order followed correctly |
| **Estimated Complexity** | High — Fault injection, timing, state inspection |
| **Spec References** | Chapters 20, 23 — Testing, Recovery and Fault Tolerance |
| **Invariants Validated** | INV-01 through INV-08 (comprehensive) |

---

## Phase 9 — Performance and Token Budgets

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/09-performance`](poc/09-performance/README.md) |
| **Purpose** | Establish baseline performance measurements and validate token budget enforcement per V2.2 benchmark dimensions. |
| **Dependencies** | Phases 1–8 (infrastructure and components measured) |
| **Expected Outputs** | Latency measurements, token budget validation, concurrent capacity data, Event Store growth rates, comparison of session modes. |
| **Acceptance Criteria** | - Event accept latency measured and recorded |
|  | - Packet sizes validated against V2.2 budget table |
|  | - Oversized packets rejected with visible reason |
|  | - Concurrent features operate without interference |
|  | - Cold/persistent/reconstruction modes compared quantitatively |
|  | - Benchmark report generated with hardware and configuration context |
| **Estimated Complexity** | Medium — Timing, measurement, report generation |
| **Spec References** | Chapters 9, 20, 22 — Cache, Testing, Performance |
| **Invariants Validated** | INV-10 (privacy-safe telemetry in measurement) |

---

## Phase 10 — End-to-End Integration

| Attribute | Value |
| --- | --- |
| **PoC** | [`poc/10-end-to-end`](poc/10-end-to-end/README.md) |
| **Purpose** | Prove the complete V2.2 workflow from feature request through merge completion and knowledge synchronization, validating all components work together as an integrated system. |
| **Dependencies** | All prior phases (1–9) |
| **Expected Outputs** | Complete feature workflow evidence, all invariants verified, event correlation chain, session lineage graph, knowledge evolution result, cleanup verification. |
| **Acceptance Criteria** | - Complete lifecycle traversal: requested → completed |
|  | - All 10 architectural invariants hold throughout workflow |
|  | - Event Store contains complete audit trail with causation chain |
|  | - Session Lineage Graph correctly tracks all edges |
|  | - Knowledge Evolution produces valid snapshot post-merge |
|  | - Feature sessions cleaned up at terminal state |
|  | - Git remains canonical throughout (INV-01) |
|  | - tmux sessions created, used, destroyed correctly |
|  | - Capability Registry consulted before adapter operations |
| **Estimated Complexity** | High — Full integration, multi-component coordination |
| **Spec References** | All chapters — Architecture Overview key execution path |
| **Invariants Validated** | INV-01 through INV-10 (all) |

---

## Execution Timeline

| Phase | PoC | Est. Duration | Cumulative |
| ---: | --- | ---: | ---: |
| 1 | tmux Runtime | 2 hours | 2 hours |
| 2 | Event Protocol | 4 hours | 6 hours |
| 3 | Session Resume | 3 hours | 9 hours |
| 4 | Capability Registry | 2 hours | 11 hours |
| 5 | Knowledge Runtime | 6 hours | 17 hours |
| 6 | Review Loop | 4 hours | 21 hours |
| 7 | Scheduler | 3 hours | 24 hours |
| 8 | Chaos | 6 hours | 30 hours |
| 9 | Performance | 4 hours | 34 hours |
| 10 | End-to-End | 8 hours | 42 hours |

> **Note:** Estimates assume one engineer with knowledge of the V2.2 spec. Phases 7/8 can execute in parallel. Phases 3/4 can execute in parallel.

---

## Completion Criteria

The validation roadmap is complete when:

1. Every phase has a filled `RESULT.md` with pass/fail evidence
2. Every `ISSUES.md` documents discovered concerns
3. All 10 phase reports are written in `reports/`
4. The `experiment-log.md` contains entries for every experiment
5. A final summary identifies what remains before production implementation
