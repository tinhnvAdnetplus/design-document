# 09 — Fork, Knowledge, and Prompt Cache

## Purpose

This chapter specifies feature forking, root knowledge cache structure, and
prompt cache controls. These mechanisms reduce token use without becoming a
durable system of record.

## Fork strategy

A feature fork captures a bounded contextual starting point from its parent
root. It is not a copy of all conversation history and not a database backup.

A fork packet contains stable role instructions, feature request, approved plan
when available, relevant root knowledge records, Git base, target paths, known
constraints, event references, and explicit non-goals. It should contain
pointers to repository files rather than large source excerpts.

| Input | Include in fork? | Reason |
| --- | --- | --- |
| role contract | always | protects authority boundary |
| repository identity | always | prevents wrong-workspace action |
| root cache version | always | provenance |
| full transcript | never by default | context inflation and privacy |
| relevant ADRs | selected | durable rationale |
| plan | implementation/review | task definition |
| Git diff | review; selective implementation | evidence, not broad context |
| unrelated feature detail | never | isolation |
| stale or unverified cache fact | no | avoid propagating assumption |

## Knowledge cache purpose

A root cache is a compact, derived model of integrated repository knowledge.
It helps roots orient quickly, choose relevant references for forks, and avoid
repeating stable context. It is maintained by the root itself after a successful
merge and must cite Git provenance for every mutable fact.

The cache is not a conversational memory dump. It MUST NOT be required to build
or recover the repository, authorize a merge, or determine source correctness.

## Cache schema

~~~yaml
cache_version: 12
root_id: claude-root
repository:
  remote_identity: sha256:...
  integration_ref: main
  integration_head: 9f17...
generated_at: 2026-07-31T10:24:00Z
source_ranges:
  - from: 62a1...
    to: 9f17...
facts:
  architecture:
    - statement: "Job dispatch is event-driven."
      evidence:
        commits: ["9f17..."]
        paths: ["docs/architecture/01-architecture-overview.md"]
  dependencies:
    - name: sqlite
      version: "3.x"
      evidence:
        commits: ["9f17..."]
  interfaces:
    - name: FeatureEventV1
      change: added field policy_revision
      evidence:
        commits: ["9f17..."]
open_questions:
  - id: q-014
    statement: "Remote worker policy not implemented."
    evidence:
      commits: ["9f17..."]
limits:
  max_bytes: 262144
  max_facts: 500
~~~

Facts must distinguish observed behavior, design decision, open question, and
inference. An inference identifies its evidence and confidence; it must not be
presented as a repository fact.

## Knowledge synchronization input

After merge, a root reads only evidence relevant to the integrated range:

1. Git merge commit and parent relationship;
2. changed files and rename detection;
3. migration files and schema changes;
4. dependency manifests and lockfile changes;
5. generated code and generator inputs;
6. public API, configuration, and documentation changes;
7. linked plan, review, test, and merge events;
8. unresolved findings or rollout constraints.

The root does not replay prior conversations. If the range is too large, it
breaks synchronization into bounded chunks while preserving the same Git range
and provenance.

## Prompt-cache strategy

There are three cache levels.

| Cache | Location | Lifetime | Validation |
| --- | --- | --- | --- |
| adapter prompt fragments | local runtime state | adapter deployment | config digest |
| root knowledge cache | root-owned state | across normal features | Git base and provenance |
| feature packet | feature data directory | one feature attempt | plan/base/lease binding |

The runtime SHOULD hash every injected packet and record the hash in the
session record. It SHOULD not persist the raw packet when it can reconstruct it
from Git, configuration, and cache facts. Sensitive fragments require explicit
retention policy.

## Cache invalidation

A cache is invalid for planning when integration HEAD differs from its recorded
head. It is invalid for a feature when policy revision, plan version, target
base, or protected path rules differ from the packet binding. Invalidation does
not delete cache automatically; it marks it stale and requires update or
reconstruction.

| Trigger | Required action |
| --- | --- |
| merged commit | schedule root synchronization |
| force update of integration ref | full cache validation |
| policy revision changes | re-evaluate packet permissions |
| dependency lockfile change | refresh dependency facts |
| migration change | add migration fact and review marker |
| adapter upgrade | retain cache but revalidate prompt fragments |
| cache hash mismatch | quarantine and rebuild |
| missing provenance | discard derived fact |

## Token budget

Token control is an engineering requirement, not only an optimization.

| Packet component | Default budget | Oversize response |
| --- | ---: | --- |
| stable instructions | 4 KiB | configuration review |
| root cache selection | 32 KiB | rank and summarize evidence |
| plan artifact | 24 KiB | split plan sections |
| changed diff for review | 64 KiB | reference file and commit ranges |
| task event | 16 KiB | attach external artifact |
| total feature packet | 128 KiB | reject/defer with visible reason |

Budgets are byte-oriented at the transport boundary and token-estimated at
adapter boundaries. The runtime records observed model token usage if the
adapter provides it, but never relies on a vendor estimate for correctness.

## Cache update pseudocode

~~~text
function synchronize_root(root, merge):
  assert merge integration commit is reachable
  gather changed paths, manifests, migrations, generated markers
  gather linked plan, review, and test evidence
  ask root to derive concise facts with source citations
  validate every mutable fact references the integrated range
  write new cache by atomic rename
  emit knowledge.synchronized(cache version, range, digest)
~~~

If cache generation fails, the merged code remains valid. The orchestrator
records sync pending and retries under policy or presents a human operation.

## Trade-offs

Caching concise knowledge lowers repeated prompt cost but risks stale or
overconfident summaries. Git provenance and invalidation make that risk visible.
No-cache operation is safer against stale memory but has high recurring
orientation cost. The design selects derived, bounded caches because they can
be rebuilt and audited.

## Future improvements

Semantic code indexes, embedding search, and dependency graph extraction may
help select relevant facts. They remain derived caches and must expose commit
provenance, invalidation behavior, retention scope, and cost limits before use
in a root packet.

