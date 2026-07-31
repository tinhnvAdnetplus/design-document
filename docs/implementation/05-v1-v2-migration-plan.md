# V1 → V2 Migration Guide

## Purpose

This plan evolves a compatible V1 deployment into V2 without changing Git
history, replaying conversations, or requiring loss of active work.

## Compatibility principles

V2 is additive at the control-plane boundary. Existing event envelopes remain
valid. Existing root caches remain usable after a one-time provenance/schema
validation. Existing vendor resume IDs stay opaque. No migration creates a new
source of truth or grants new session authority.

## Migration phases

| Phase | Change | Compatibility gate | Rollback |
| --- | --- | --- | --- |
| 0 | inventory V1 state/configuration | clean Git and state backup | none needed |
| 1 | introduce V2 vocabulary/projections | Event Store reads V1 log | disable V2 projections |
| 2 | register existing cache artifacts | cache digest/provenance check | retain V1 cache mode |
| 3 | enable session lineage projection | all active sessions resolve | rebuild projection |
| 4 | enable scheduler metrics/queues | no pending delivery loss | retain legacy scheduler path |
| 5 | enable knowledge evolution pipeline | candidate snapshot validation | event-only sync fallback |
| 6 | enable optional metadata commits | dedicated branch protections | set event-only mode |
| 7 | enforce V2 policies and remove deprecated labels | full test/chaos pass | retain data readers |

## Phase 0 — Inventory and backup

Record runtime configuration digest, adapter versions, policy revision, active
features, worktree manifests, leases, Event Store location, root cache versions,
and terminal observations. Back up Git, configuration, Event Store, and
sanitized cache artifacts. Do not back up or migrate raw conversation content
unless existing retention policy expressly permits it.

## Phase 1 — Event Store and projection compatibility

Rename interfaces and dashboards from event log/state store to Event Store and
projections without changing persistent record format. Add a schema version and
replay test that rebuilds V2 projections from a V1 event stream. Do not execute
command intents during migration replay.

## Phase 2 — Cache registry

For each existing prompt, resume, or knowledge cache artifact, create registry
metadata: layer, owner, root/feature/session scope, base commit, digest,
retention class, and reconstruction method. Unknown cache artifacts are
quarantined rather than classified as knowledge. Conversation material remains
unregistered and unavailable by default.

## Phase 3 — Session lineage

Derive parent-child relationships from root/fork/session events. Where V1 lacks
a parent reference, mark the lineage edge unknown; do not infer one from
terminal naming alone. Active sessions can continue; new forks must include
explicit parent and cache-version metadata.

## Phase 4 — Scheduler decomposition

Expose existing delivery queues through Dispatcher, Eligibility Scheduler, Retry
Schedule, and Session Registry interfaces. Preserve delivery IDs and
idempotency keys. Activate priority/fairness metrics before changing scheduling
policy. Do not introduce a worker pool for existing persistent adapters.

## Phase 5 — Knowledge Evolution

Run Knowledge Evolution in shadow mode for at least one configured integration
range: collect evidence, derive a candidate snapshot, validate provenance and
budget, compare it with the current root cache, and publish only after policy
acceptance. If validation fails, retain V1 event-driven synchronization and
record the candidate failure.

## Phase 6 — Optional root update commit

Default V2 remains event-only. A deployment that needs auditable shared cache
metadata creates a protected runtime knowledge branch, verifies no application
paths are writable there, and enables metadata-only commits. This phase is
optional and independently reversible by returning to event-only checkpoints.

## Phase 7 — Enforcement and deprecation

After migration tests pass, require cache layer metadata on new artifacts,
explicit resume scopes, lineage edges for forks, and scheduler metrics. Retain
V1 readers for configured deprecation period. Remove legacy terminology only
after all active features and adapters report V2 capability.

## Active-feature handling

Do not migrate a feature while it holds an uncertain write lease or while an
integration merge is in progress. Let it reach a stable checkpoint, then attach
V2 metadata. A feature can complete using V1 delivery semantics because V2
preserves the event contract.

## Validation matrix

| Check | Evidence |
| --- | --- |
| Git truth unchanged | object/ref comparison before and after |
| event replay deterministic | V1 stream projects V2 state |
| cache registry safe | unknown/transcript artifacts quarantined |
| lineage correct | fork fixture and known V1 sessions |
| scheduler lossless | pending deliveries retain IDs/order class |
| evolution safe | every published fact has provenance |
| resume safe | all resume IDs removed still recovers |
| metadata commit safe | no application path changes |
| rollback safe | V1 event-only sync can continue |

## Rollback policy

Rollback disables V2 projections, cache registry enforcement, new scheduler
policy, and metadata branch writes while preserving appended evidence. It never
deletes Event Store records, cache artifacts, branches, or worktrees as a
rollback shortcut. Git remains independently recoverable at every phase.

## Migration completion

Migration is complete when every enabled adapter declares V2 compatibility,
existing artifacts are registered or quarantined, V2 replay/chaos tests pass,
the terminology is reflected in operating procedures, and maintainers approve
the selected metadata checkpoint mode.
