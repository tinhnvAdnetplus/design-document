# 07 — Persistent Sessions and Resume

## Purpose

This chapter specifies why roots remain alive, when resume is permitted, and
how the runtime recovers when it cannot resume. It establishes the rule that
resume is an optimization, never a correctness dependency.

## Persistent-session policy and Resume Lifecycle

Normal development follows this policy:

| Operation | Root session | Feature session |
| --- | --- | --- |
| start runtime | create or attach once | not created |
| receive work | stay running | fork as needed |
| finish work | remain idle | terminate at feature terminal state |
| agent is busy | queue notice asynchronously | queue notice asynchronously |
| normal next feature | reuse same root | create a new fork |
| crash or reboot | recover; resume optional | recover; resume optional |
| merge complete | sync knowledge | destroy |

Restarting an otherwise healthy root merely to refresh context is prohibited.
Context refresh is achieved by a root-owned Git-derived synchronization, not by
discarding the process. Restarting a feature session to avoid a difficult task
is also prohibited; a new fork requires an explicit recovery or abandonment
transition.

## Resume lifetime by scope

Resume Cache entries are opaque adapter metadata with a policy-bounded
lifetime. They are valid only while the runtime Session Lifecycle permits a
recovery attempt; they are not long-lived agent memory.

| Scope | Cache owner | Eligible interval | Terminal invalidation | Fresh path |
| --- | --- | --- | --- | --- |
| Root | root adapter | unavailable to root replacement | root drain/disable/replacement | root reconstruction packet |
| Planner | feature adapter | unavailable to plan outcome | plan accepted/rejected/cancelled | plan packet |
| Implementer | feature adapter | unavailable while feature can continue | review/cancel/cleanup | worktree/Git packet |
| Reviewer | feature adapter | unavailable while decision is pending | approval/rejection/expiry/cancellation | immutable review packet |

The runtime deletes or makes unusable a Resume Cache entry at its terminal
invalidation event under retention policy. A retained diagnostic reference does
not re-enable resume. Resume metadata cannot substitute for a current Registry
declaration; absent `resume=true`, recovery selects reconstruction.

## Why persistence matters

A persistent root avoids repeating stable project instructions, repository
orientation, conventions, and recent integrated changes. It also keeps CLI tool
state available. The runtime does not equate this convenience with durability:
the Knowledge Cache is written independently and can be reconstructed.

Persistence has a cost. A long-lived CLI can leak memory, hold stale terminal
state, or continue after a policy change. Health checks, bounded Knowledge Caches,
configuration revision checks, and explicit state transitions control that cost.

## Exceptional-resume preconditions

The runtime MAY attempt resume only when all conditions are true:

1. a prior session was marked unavailable due to abnormal loss;
2. the Capability Registry currently declares `resume=true` for the adapter;
3. the adapter provides a stored opaque resume reference;
4. resume is enabled by configuration;
5. the session role is still valid under current policy;
6. Git base and assigned worktree satisfy recovery checks;
7. no newer runtime session holds the same exclusive resource;
8. the adapter can produce readiness evidence after resume.

Failure of any condition selects fresh-session reconstruction. Resume never
runs during ordinary idle, task handoff, or root knowledge synchronization.

## Recovery decision tree

~~~mermaid
flowchart TD
    A[Session unavailable] --> B{Prior process alive?}
    B -->|yes| C[Reattach and validate identity]
    B -->|no| D{Resume reference allowed and present?}
    C --> E{Git and policy match?}
    D -->|yes| F[Attempt vendor resume]
    D -->|no| G[Create fresh session]
    F --> H{Readiness and state validation pass?}
    H -->|yes| E
    H -->|no| G
    E -->|yes| I[Mark ready]
    E -->|no| G
    G --> J[Build Git-derived reconstruction packet]
    J --> I
~~~

The decision is deliberately conservative. Reattaching a wrong terminal or
resuming a stale role is more dangerous than spending a bounded reconstruction
prompt.

## Reconstruction packet

A fresh root packet contains stable role instructions, configuration revision,
repository identity, integration head, Knowledge Cache if valid, recent integrated
ranges, known project constraints, and links to event evidence. A fresh feature
packet additionally contains feature ID, plan, worktree status, writer lease
status, review cycle, and target Git base.

| Field | Root reconstruction | Feature reconstruction |
| --- | ---: | ---: |
| runtime and policy revision | required | required |
| role contract | required | required |
| repository and integration HEAD | required | required |
| Knowledge Cache provenance | required | selected |
| feature plan | no | required |
| worktree path and branch | no | required |
| active lease and fencing token | no | if still valid |
| commits and diff digest | recent range | required |
| pending event references | selected | required |
| raw transcript | never required | never required |

The packet must state that it is a reconstruction, identify unknowns, and tell
the agent to verify Git before acting. It must not claim continuity that cannot
be proven. It identifies the Knowledge Snapshot version and Session Lineage
Graph parentage so recovery remains auditable without a transcript.

## Root recovery

A recovered root receives no authority to edit code. It validates its cache
against current integration HEAD. If the cache base is stale, it schedules a
normal synchronization before accepting project-wide planning. A root that
cannot load cache may still operate using Git inspection; token efficiency
degrades but correctness remains.

## Feature recovery

A feature recovery is more constrained because it may own mutable state.

| Worktree finding | Required action |
| --- | --- |
| clean, head matches recorded commit | reconstruct and continue |
| clean, head advanced by known event | rebuild projection then continue |
| dirty, owned session absent | quarantine and require policy/human resolution |
| branch missing, commit reachable | recreate worktree from commit |
| branch missing, commit unreachable | block and preserve forensic copy |
| lease expired | do not write; request a new lease |
| approval exists but base/head changed | invalidate approval and review again |

A runtime must never auto-stage, auto-commit, reset, or delete a dirty feature
worktree during recovery.

## Resume verification

After a vendor resume, the adapter verifies terminal session name, process
identity where possible, current working directory, expected repository, role
banner or sentinel, and ability to read the assigned event inbox. The
orchestrator verifies session metadata, policy revision, feature projection,
leases, and Git state. Both layers are required.

## Operational controls

| Setting | Default | Meaning |
| --- | ---: | --- |
| resume enabled | true | allow exceptional resume attempt |
| maximum resume attempts | 1 | avoid loops and duplicate state |
| root recovery deadline | 5 min | time before degraded alert |
| feature recovery deadline | 15 min | time before escalation |
| stale cache tolerance | 0 integrated commits | require sync before root planning |
| dirty worktree action | quarantine | never discard by default |
| reconstruction packet limit | 128 KiB | preserve prompt budget |

## Capability revalidation

Capability revalidation occurs at Runtime startup, Runtime restart, adapter
upgrade, and a manual CLI upgrade declared by an operator. The Runtime obtains
a new document only through the Adapter's `capabilities()` operation and
compares its version and supported operations with the Capability Registry. It
does not scrape CLI output or probe an interactive session to infer support.
Until revalidation succeeds, affected sessions are unavailable and resume,
fork, and delivery paths that depend on the adapter remain blocked. This
prevents a retained Resume Cache from reviving a session against stale adapter
metadata.

## Trade-offs

Native resume may preserve tool-specific conversational continuity and save
tokens. It can also revive stale assumptions or fail across CLI upgrades. The
Git-derived fresh path is slower but portable, inspectable, and reliable. The
runtime prefers resume when verified and otherwise treats it as unavailable.

A zero-restart normal policy may surface CLI memory leaks. Operators may
explicitly drain and replace a root during a maintenance window, but this is a
controlled recovery event with a reconstruction packet, not ordinary workflow
behavior.

## Cache and lineage restrictions

Resume Cache is one layer in the V2 Cache Taxonomy. It cannot promote terminal
text or conversational material into Knowledge Cache. If a recovered session
has no valid lineage parent, its reconstruction is marked root-cause recovery,
not a synthetic fork. Both cases remain compatible with Git-first recovery.

## Future improvements

Future adapters may cryptographically attest a resumed session, checkpoint a
sanitized local context, or support transactional session snapshots. These
features can reduce reconstruction cost but cannot alter the Git-first recovery
requirement.
