# 16 — Knowledge Synchronization

## Purpose

This chapter defines how roots update durable derived knowledge after merge.
Synchronization maintains useful long-term context without replaying feature
conversations.

## Trigger and authority

A merge-completed event triggers one synchronization request per enabled root.
Only the named root session can write its cache. A feature session, reviewer,
merger, or orchestrator may request synchronization but cannot write root
knowledge.

The trigger must cite an integrated commit range. A feature branch head that
has not merged is not eligible for root cache update.

## Required inspection

Each root inspects the following evidence for its assigned integration range:

| Evidence | Required interpretation |
| --- | --- |
| merge parents and commit messages | causal feature boundary |
| changed paths and renames | component impact |
| dependency manifests/lockfiles | dependency graph change |
| migration/schema files | data compatibility impact |
| generated files and sources | regeneration relationship |
| public APIs/configuration | contract change |
| tests and CI links | verification scope |
| plan/review/merge events | intent and accepted risks |

The root records concise facts and provenance. It must distinguish a confirmed
repository fact from a hypothesis or open question.

## Synchronization flow

~~~mermaid
flowchart TD
    A[merge.completed] --> B[Build evidence packet]
    B --> C[Deliver to root]
    C --> D[Read Git range and linked artifacts]
    D --> E[Derive concise cache facts]
    E --> F[Validate provenance and size]
    F --> G[Atomically write root cache]
    G --> H[knowledge.synchronized]
~~~

The evidence packet is a cue, not a replacement for Git inspection. A root must
compare the reported integration head with Git before cache write.

## Cache changes

A synchronization updates only facts affected by the integrated range. It may
add or revise architecture, dependency, interface, migration, operational, and
domain facts. It removes a fact only when Git evidence demonstrates removal or
replacement. It should avoid rewriting unrelated cache sections because broad
rewrites make provenance and diff review harder.

## Root update commit

The workflow's Root Update Commit is an optional, auditable checkpoint for
sanitized cache metadata. When enabled, the root writes only a cache manifest,
provenance digest, and integration range to a dedicated metadata branch such as
runtime/knowledge. It MUST NOT write application source, alter the integration
ref, or include prompt transcripts. The merger's integration commit remains the
canonical code change.

| Mode | Durable checkpoint | Use when |
| --- | --- | --- |
| event-only | synchronization event and cache digest | local/private cache deployment |
| metadata branch | event plus metadata-only Git commit | shared audit of cache evolution |
| external audit store | event plus signed snapshot reference | regulated deployment |

The metadata commit contains a direct parent relation to the prior metadata
commit and cites the integration commit it summarizes. Failure to create this
optional commit does not roll back a merged feature; it leaves synchronization
pending or records an event-only result according to policy.

## Provenance format

~~~yaml
fact:
  kind: interface
  statement: "Merge approval now includes policy revision."
  confidence: confirmed
  source:
    integration_range: "091e..ab12"
    commits: ["ab12..."]
    paths: ["docs/protocol/02-message-json-event-protocol.md"]
    events: ["evt_merge_01"]
  updated_at: "2026-07-31T10:24:00Z"
~~~

A cache writer must retain enough source information for a later agent or human
to find the evidence without relying on the original conversation.

## Failure and retry

A cache synchronization failure does not roll back the merge. The runtime marks
the root cache stale, retains the merge evidence, and schedules retry or human
operation. The root remains available for narrowly scoped work only if policy
permits; broad planning should wait for current cache or use direct Git
inspection.

| Failure | Response |
| --- | --- |
| Git range unreachable | block sync and alert |
| cache size limit | summarize/partition with same provenance |
| root unavailable | retain pending request and recover root |
| invalid derived fact | reject cache write; ask root to correct |
| atomic write failure | retain old cache, retry safely |
| linked artifact unavailable | record unknown, do not invent fact |

## No transcript replay

The runtime does not ask a root to read all planner, implementer, reviewer, and
terminal transcripts after each merge. Instead it supplies Git range, structured
artifacts, and selected event evidence. This preserves durable decision context
while limiting token growth and privacy exposure.

## Completion criteria

A root emits synchronization complete only after cache digest, source range,
and changed fact counts are recorded. The orchestrator verifies that the cache
base equals integration head and that all mutable facts have provenance. It may
mark a feature completed when required roots finish or when a configured
deferred-sync policy explicitly records the outstanding obligation.

## Future improvements

A semantic index can assist root analysis but must produce evidence-linked
facts. Multiple roots may share a read-only generated index, but they must
retain independent cache ownership and cannot overwrite each other’s summaries.
