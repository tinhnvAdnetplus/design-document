# 29 — Glossary and Reference

## Glossary

| Term | Definition |
| --- | --- |
| Adapter | Component that maps one AI CLI or worker to runtime contract. |
| Aggregate | Event-sourced workflow entity such as feature or session. |
| Approval binding | Immutable evidence tuple authorizing one merge candidate. |
| Cache | Derived, disposable knowledge or prompt artifact. |
| Causation ID | Identifier of the direct predecessor event. |
| Correlation ID | Identifier shared by one logical workflow. |
| Feature session | Disposable forked session assigned to one feature role. |
| Fencing token | Monotonically increasing value that rejects stale writers. |
| Git gateway | Controlled component for Git worktree and merge operations. |
| Integration worktree | Protected checkout used only by merger. |
| Lease | Time-bound, scoped grant to a resource. |
| Merger | Deterministic actor that validates and updates integration ref. |
| Policy revision | Immutable configuration version used for authorization. |
| Projection | Rebuildable current state derived from events. |
| Root cache | Per-root Git-derived project knowledge. |
| Root session | Persistent agent session owning project-wide context. |
| Runtime client | Small command invoked through terminal event notice. |
| Session ID | Runtime-generated identity for one process instance. |
| Synthetic fork | Fresh session created from a bounded packet when native fork is absent. |
| Terminal notice | Short tmux-injected reference to a durable event. |
| Worktree lease | Exclusive writer authorization for one feature worktree. |

## Normative requirement checklist

| Area | Required rule |
| --- | --- |
| Source of truth | Git is canonical; session state is cache. |
| Roots | one persistent root per enabled AI; no feature code writes. |
| Features | forked, isolated, and destroyed after terminal state. |
| Communication | asynchronous events; no blocking agent RPC. |
| Review | Claude emits merge approval in v1. |
| Merge | deterministic merger validates exact evidence. |
| Synchronization | only roots update own knowledge after merge. |
| Resume | exceptional recovery only; fresh path must work. |
| Transport | tmux notices reference durable events. |
| Security | capabilities, path validation, least privilege, audit. |
| Recovery | preserve dirty work; never infer unsafe side effects. |

## Error-code reference

| Code | Meaning | Usual action |
| --- | --- | --- |
| SCHEMA_INVALID | event cannot be parsed/validated | correct producer |
| PROTOCOL_UNSUPPORTED | incompatible protocol version | upgrade/migrate |
| AUTHORIZATION_DENIED | role/scope lacks capability | use authorized role |
| TRANSITION_INVALID | event not valid in current state | inspect aggregate |
| IDEMPOTENCY_CONFLICT | same key, different contents | create correct action |
| LEASE_STALE | token expired/superseded | recover/reacquire |
| DELIVERY_EXPIRED | target did not acknowledge | reconcile/escalate |
| ADAPTER_UNAVAILABLE | CLI/terminal cannot be trusted | recover session |
| GIT_PRECONDITION_FAILED | refs/worktree differ from evidence | inspect/rebase |
| APPROVAL_STALE | head/base/policy/check changed | re-review |
| WORKTREE_DIRTY | cleanup/recovery cannot proceed | human decision |
| CACHE_PROVENANCE_INVALID | derived fact lacks evidence | rebuild cache |
| SECURITY_VIOLATION | unsafe path/input/secret condition | contain/investigate |

## Reference map

| Topic | Primary chapter |
| --- | --- |
| system structure | Architecture Overview |
| roles and authority | Agent Model |
| states and diagrams | State Model |
| CLI behavior | Claude and Codex Runtimes |
| recovery | Persistent Sessions and Fault Tolerance |
| event schema | Message Format and JSON Events |
| workflow | Feature and Review Lifecycle |
| Git | Merge Strategy and Git Workflow |
| cache | Knowledge Synchronization |
| implementation | Reference Implementation |
| operations | Logging and Performance |
| security | Security Architecture and Permission Model |

## Document maintenance checklist

When changing an interface, update its schema, state transition, authorization,
examples, tests, observability, recovery behavior, and ADR where required. When
adding an adapter, update capability matrix, adapter contract, configuration,
security review, test fixtures, and roadmap status.

