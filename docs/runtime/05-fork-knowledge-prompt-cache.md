# 09 — Knowledge Runtime, Fork, and Cache Strategy

## Purpose

This chapter is the owner specification for Knowledge Runtime, the V2 Cache
Taxonomy, Knowledge Compression, and their relationship to feature forks. It
defines bounded derived knowledge without creating a durable system of record.

## Knowledge Runtime

Knowledge Runtime is a logical control-plane component. Its responsibility is
to select eligible evidence, maintain Cache Registry metadata, construct and
validate Knowledge Snapshots, apply Knowledge Compression, and coordinate
publication to a named root. It has no independent model identity and cannot
write application code, approve a merge, mutate the integration ref, or decide
feature workflow state.

### Lifecycle

Knowledge Runtime starts with the control plane, loads Cache Registry metadata,
and validates root snapshot base commits. It is idle until a fork packet needs
selection, an invalidation trigger occurs, or a knowledge-synchronization event
invokes Knowledge Evolution. It publishes a snapshot atomically, records an
Event Store outcome, and remains available. Its failure marks knowledge work
pending but never rolls back a merged Git change.

### Interactions and limitations

Knowledge Runtime reads Git through the Git gateway, eligible Event Store
evidence, configuration, and root-owned artifacts. It provides selected
snapshot facts to adapters and accepts a root's candidate publication only
after validation. It does not read full conversations by default and cannot
turn a summary into an evidenced fact without provenance.

## Knowledge Snapshot domains

| Domain | Purpose | Evidence boundary | Limitation |
| --- | --- | --- | --- |
| Project | repository baseline and active constraints | Git/configuration | no task transcript |
| Architecture | components, interfaces, decisions | code/docs/ADRs | must cite paths/commits |
| Business | domain terms/rules represented in project artifacts | governed repository evidence | no external product-memory inference |
| Workspace | worktree, branch, lease status | Git and runtime observation | transient; not code truth |
| Dependency | manifests, locks, generator relationships | Git | no package-registry assumption |
| Convention | style, test, build and repository rules | Git/configuration | cannot override policy |

Each snapshot has a version, root owner, integration base, selected domains,
fact classifications, provenance, digest, and byte/fact budgets. A snapshot
fact is confirmed, inferred, open, or transient; only confirmed facts and
explicitly labelled inferences may enter a root Knowledge Cache.

## V2 Cache Taxonomy and Cache Registry

The Cache Registry records layer, owner, scope, creation/base evidence, digest,
retention class, invalidation state, and reconstruction method. It does not
retain cache content by default.

| Layer | Responsibility | Lifecycle | Interaction | Limitation |
| --- | --- | --- | --- | --- |
| Prompt Cache | reuse stable packet fragments | adapter/session ephemeral | packet assembler | no authority or durable truth |
| Conversation Cache | restricted diagnosis | disabled by default; short retention | security-approved diagnostic access | no automatic knowledge promotion |
| Resume Cache | opaque vendor recovery hint | abnormal-loss window only | adapter recovery path | fresh reconstruction must work |
| Knowledge Cache | root-owned snapshot artifact | across normal root work | fork selection and root orientation | Git/evidence rebuild required |

Conversation Cache is deliberately not a fifth form of root memory. It is a
restricted cache layer whose eviction or retention never deletes Event Store or
Git evidence.

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
| Knowledge Cache version | always | provenance |
| full transcript | never by default | context inflation and privacy |
| relevant ADRs | selected | durable rationale |
| plan | implementation/review | task definition |
| Git diff | review; selective implementation | evidence, not broad context |
| unrelated feature detail | never | isolation |
| stale or unverified cache fact | no | avoid propagating assumption |

## Knowledge Cache purpose

A root Knowledge Cache is a compact, derived model of integrated repository knowledge.
It helps roots orient quickly, choose relevant references for forks, and avoid
repeating stable context. It is maintained by the root itself after a successful
merge and must cite Git provenance for every mutable fact.

The cache is not a conversational memory dump. It MUST NOT be required to build
or recover the repository, authorize a merge, or determine source correctness.

## Knowledge Snapshot schema

~~~yaml
cache_version: 12
root_id: claude-root
snapshot_domains: [project, architecture, business, workspace, dependency, convention]
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

Facts must distinguish confirmed behavior, design decision, open question, and
inference. An inference identifies its evidence and confidence; it must not be
presented as a repository fact. The schema may retain a bounded transient
summary only inside a packet; transient summaries are not published facts.

## Knowledge Evolution input

After merge, a root reads only evidence relevant to the integrated range:

1. Git merge commit and parent relationship;
2. changed files and rename detection;
3. migration files and schema changes;
4. dependency manifests and lockfile changes;
5. generated code and generator inputs;
6. public API, configuration, and documentation changes;
7. linked plan, review, test, and merge events;
8. unresolved findings or rollout constraints.

The root does not replay prior conversations. If the range is too large,
Knowledge Runtime breaks evidence collection into bounded chunks while
preserving the same Git range and provenance.

## Knowledge Compression

Knowledge Compression is the bounded transformation inside Knowledge Evolution.
It retains understanding only when it can keep its evidence link, and lets
Conversation Cache material expire under policy.

~~~text
eligible evidence -> transient summary -> candidate fact/inference/open question
-> provenance and confidence validation -> bounded Knowledge Snapshot
-> Conversation Cache retention/eviction under policy
~~~

Compression MUST NOT delete Git history or Event Store audit evidence. It MUST
NOT promote raw conversation text directly to a confirmed fact. A candidate
that exceeds budget is partitioned or rejected with its provenance intact.

## Cache-layer strategy

There are four cache layers.

| Cache | Location | Lifetime | Validation |
| --- | --- | --- | --- |
| Prompt Cache | adapter/session state | packet/session lifetime | config and packet digest |
| Conversation Cache | restricted diagnostic artifact | policy-bounded and disabled by default | access/retention policy |
| Resume Cache | adapter-private state | Resume Scope only | role/lifecycle/Git validation |
| Knowledge Cache | root-owned state | across normal root work | Git base, snapshot provenance, digest |

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
| merged commit | invoke synchronization and Knowledge Evolution |
| force update of integration ref | full cache validation |
| policy revision changes | re-evaluate packet permissions |
| dependency lockfile change | refresh dependency facts |
| migration change | add migration fact and review marker |
| adapter upgrade | retain cache but revalidate prompt fragments |
| cache hash mismatch | quarantine Registry entry and rebuild |
| missing provenance | discard derived fact |

## Token budget

Token control is an engineering requirement, not only an optimization.

| Packet component | Default budget | Oversize response |
| --- | ---: | --- |
| stable instructions | 4 KiB | configuration review |
| Knowledge Cache selection | 32 KiB | rank and summarize evidence |
| plan artifact | 24 KiB | split plan sections |
| changed diff for review | 64 KiB | reference file and commit ranges |
| task event | 16 KiB | attach external artifact |
| total feature packet | 128 KiB | reject/defer with visible reason |

Budgets are byte-oriented at the transport boundary and token-estimated at
adapter boundaries. The runtime records observed model token usage if the
adapter provides it, but never relies on a vendor estimate for correctness.

## Knowledge Evolution pseudocode

~~~text
function evolve_knowledge(root, merge):
  assert merge integration commit is reachable
  detect snapshot domains affected by Git diff
  gather changed paths, manifests, migrations, generated markers
  gather linked plan, review, and test Event Store evidence
  construct bounded candidate facts with source citations
  validate domain, confidence, budget, and integrated-range provenance
  write new snapshot/cache by atomic rename
  emit knowledge.synchronized(snapshot version, range, digest)
~~~

If evolution fails, the merged code remains valid. The orchestrator records
evolution pending and retries under policy or presents a human operation.

## Trade-offs

Caching concise knowledge lowers repeated prompt cost but risks stale or
overconfident summaries. Git provenance and invalidation make that risk visible.
No-cache operation is safer against stale memory but has high recurring
orientation cost. The design selects derived, bounded caches because they can
be rebuilt and audited.

The V2 Cache Taxonomy adds Cache Registry metadata and retention policy work,
but it prevents Prompt, Conversation, Resume, and Knowledge artifacts from
being treated as interchangeable memory or accidental authority.

## Future improvements

Semantic code indexes, embedding search, and dependency graph extraction may
help select relevant facts. They remain derived caches and must expose commit
provenance, invalidation behavior, retention scope, and cost limits before use
in a root packet.
