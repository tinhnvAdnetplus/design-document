# 20 — Testing and Benchmark Strategy

## Purpose

This chapter defines verification required before a runtime release. Tests
cover correctness, protocol contracts, recovery, security, performance, and
token efficiency.

## Test pyramid

| Layer | Scope | Examples |
| --- | --- | --- |
| unit | pure domain and policy | state transition, schema, cache invalidation |
| contract | adapters and gateways | fork, notify, resume, Git command behavior |
| integration | local runtime components | event-to-delivery, worktree lease, merge |
| end-to-end | mock CLIs and real Git | plan to sync workflow |
| chaos | failure injection | killed terminal, lost resume ID, disk error |
| benchmark | measured behavior | latency, token budget, throughput |
| security | adversarial boundaries | path escape, forged approval, secret logging |

Mock adapters are mandatory for deterministic continuous integration. A small
manual compatibility suite validates the real installed CLIs on supported
versions.

## Required scenarios

| ID | Scenario | Pass criterion |
| --- | --- | --- |
| T-01 | root startup | one ready root per enabled adapter |
| T-02 | feature fork | child has unique identity and bounded packet |
| T-03 | writer collision | second writer lease denied |
| T-04 | normal review loop | fixes require re-review |
| T-05 | forged approval | rejected by policy |
| T-06 | stale approval | invalidated before merge |
| T-07 | merge crash | Git outcome accurately reconciled |
| T-08 | terminal killed | affected session recovers, others continue |
| T-09 | all resume IDs erased | fresh reconstruction succeeds |
| T-10 | dirty feature worktree | quarantined, never auto-deleted |
| T-11 | duplicate event | no duplicate side effect |
| T-12 | adapter timeout | bounded retry then visibility |
| T-13 | cache loss | rebuild from Git and evidence |
| T-14 | path traversal event | rejected and audited |
| T-15 | raw prompt sentinel | absent from default logs |
| T-16 | Cache Taxonomy | Conversation Cache disabled; every layer registered |
| T-17 | Knowledge Evolution | published facts cite Git/Event Store evidence |
| T-18 | Session Lineage Graph | fork/reconstruction DAG has no authority edge |
| T-19 | Scheduler fairness | priority and retry preserve bounded eligible delivery |
| T-20 | Event Store replay | projections rebuild; no blind side effect replay |
| T-21 | terminal-event obligation | missing terminal event never advances workflow; observable reconciliation runs |
| T-22 | Capability Registry startup | every enabled adapter supplies a current Capability Document |
| T-23 | capability revalidation | startup/restart, adapter upgrade, and manual CLI upgrade refresh Registry |
| T-24 | capability misreporting | declaration/observation mismatch becomes `ADAPTER_UNAVAILABLE` |
| T-25 | resume declaration | resume is attempted only when Registry says `resume=true` |
| T-26 | review/fix escalation | configured cycle limit blocks automatic dispatch and surfaces maintainer action |
| T-27 | model inference permission | adapter inference is denied without explicit configured permission |

## Property tests

State-machine property tests generate valid and invalid event sequences. They
verify that an implementation cannot reach merged without implementation-ready
and valid approval, cannot grant overlapping writers, and cannot complete root
sync without a reachable integration commit.

Projection replay tests apply an event stream twice and assert identical final
state. Idempotency tests submit the same event and command intent repeatedly,
then confirm only one Git or terminal side effect occurs.

Knowledge property tests reject unproven facts, oversized candidates, and
Conversation Cache promotion. Lineage tests reject cycles and verify that a
lineage edge cannot affect capability resolution or dispatch target selection.

## Adapter contract tests

Each adapter must pass a common fixture set:

- create named root and report readiness;
- create a feature fork with parent/cache provenance;
- receive a bounded event reference;
- acknowledge without treating terminal text as authority;
- detect absent terminal;
- attempt exceptional resume once;
- declare `resume=true` before any resume attempt;
- provide a version-bound Capability Document and revalidate it on required triggers;
- start fresh reconstruction when resume fails;
- gracefully stop and report terminal absence;
- redact diagnostics according to policy.

Vendor CLI release upgrades require re-running the suite and recording
supported version range.

## Chaos tests

Fault injection should occur before and after each durable boundary:

| Fault | Required assertion |
| --- | --- |
| crash before event append | event not accepted |
| crash after append before projection | replay projects event |
| crash after intent before execution | reconcile executes/observes once |
| crash during tmux notify | duplicate-safe delivery |
| crash during worktree creation | orphan detected and cleaned safely |
| crash during merge | actual ref determines outcome |
| disk-full cache write | old cache preserved |
| event database lock | bounded retry/no data corruption |
| lost network CI lookup | merge blocks by policy |
| clock jump | lease uses safe expiration handling |
| Event Store replay after intent | confirmation query prevents duplicate effect |
| corrupt cache artifact | Registry quarantines and rebuilds |
| lineage parent missing | reconstruction marked root-cause, not fork |
| terminal task deadline with no event | no inferred completion; reconcile then recover/block |
| adapter behavior contradicts Capability Registry | `ADAPTER_UNAVAILABLE`; no undeclared fallback |

Chaos runs must use disposable repositories and never point at production
remotes.

## Benchmark dimensions

| Metric | Definition | Target use |
| --- | --- | --- |
| event accept latency | submit to durable acceptance | control-plane sizing |
| notify latency | accepted event to adapter notice | interaction quality |
| workflow latency | request to merge completion | process bottleneck |
| recovery time | failure detection to ready state | SLO |
| cache rebuild time | Git range to cache write | root readiness |
| prompt bytes | packet size by role | token control |
| vendor token usage | adapter-reported usage | cost trend |
| concurrent features | active non-conflicting flows | capacity |
| event-store growth | bytes/event and retention | storage planning |

Benchmarks compare a cold fresh session, persistent root plus fork, and
reconstruction after resume loss. Results must state repository size, commit
history size, CLI versions, hardware, cache policy, test workload, and whether
model usage is simulated or live.

## Release gates

A release requires schema compatibility tests, all required scenarios, no
critical security failures, a documented real-adapter compatibility run, and
benchmark comparison against the prior release. Regression thresholds are
configuration-driven but should include event acceptance, recovery time, and
packet-size growth.

## Test data handling

Fixtures use synthetic repositories and secret sentinels, not production source
or credentials. Logs and artifacts from live adapter tests follow retention
policy. Benchmark reports publish aggregate metrics and configuration, not raw
prompts unless a secure opt-in process authorizes it.

## Future improvements

Future work may add formal model checking for the state machines, fuzzing for
event parsers and path handling, and replay of anonymized production Event Store records
in an isolated environment.
