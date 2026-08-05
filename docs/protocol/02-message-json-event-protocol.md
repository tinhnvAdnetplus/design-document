# 12 — Message Format and JSON Events

## Purpose

This chapter defines the V2 JSON event envelope, event catalog, payload rules,
and examples. The envelope is the authoritative communication artifact; a
terminal notice carries only a reference to it.

## Envelope

~~~json
{
  "event_id": "evt_01J9Z4P2W5Y7",
  "protocol": "ai-runtime.events/v1",
  "type": "implementation.ready",
  "occurred_at": "2026-07-31T10:24:00Z",
  "producer": {
    "session_id": "ses_codex_0042_1",
    "role": "codex_implementer",
    "adapter": "codex",
    "adapter_version": "1.4.0"
  },
  "lineage": {
    "parent_session_id": "ses_codex_root",
    "knowledge_snapshot_version": 42,
    "edge_type": "fork"
  },
  "aggregate": {
    "feature_id": "feat-0042",
    "stream": "feature/feat-0042",
    "sequence": 12
  },
  "correlation_id": "cor_01J9Z4...",
  "causation_id": "evt_01J9Z3...",
  "idempotency_key": "impl-ready/feat-0042/ab12cd",
  "policy_revision": "policy-2026-07-31.1",
  "payload": {},
  "attachments": [],
  "integrity": {
    "content_sha256": "hex",
    "signature_ref": null
  }
}
~~~

All fields except causation ID, lineage, attachments, and signature reference are
required. Timestamps use UTC RFC 3339. IDs use configured opaque stable
formats. The event hash is calculated over a canonical representation excluding
the hash field itself.

## Common payload fields

| Field | Rule |
| --- | --- |
| feature ID | required for feature workflow events |
| session ID | must match producer identity |
| commit IDs | full reachable object IDs, not branch names alone |
| path list | repository-relative and policy-filtered |
| policy revision | must resolve in policy store |
| reason code | stable machine-readable enum |
| human summary | bounded, optional explanatory text |
| evidence references | immutable event, Git, file, or check references |

Payload text must be small. Large diffs, reports, plans, or captures are stored
as attachments with content digest and access-controlled URI.

## Event catalog

| Type | Producer role | Required payload facts | Transition |
| --- | --- | --- | --- |
| feature.requested | human/policy | request, target, risk | requested |
| plan.ready | Claude planner | plan digest, base, acceptance criteria | planning to plan-ready |
| plan.approved | authorized approver | plan digest, policy evidence | plan-ready to implementation |
| implementation.progress | Codex implementer | lease, checkpoint, summary | no stage change |
| implementation.ready | Codex implementer | head, base, tests, diff digest | implementation to review |
| review.requested | orchestrator | review packet digest | notify reviewer |
| changes.requested | Claude reviewer | findings, reviewed head, severity | review to implementation |
| feature.blocked | orchestrator | reason, blocked stage, cycle/round counts, heads, evidence | blocked overlay; dispatch stops |
| feature.unblocked | authorized maintainer | reason, justification, new bounded allowance | overlay cleared; stage unchanged |
| merge.approved | Claude reviewer | immutable approval binding | review to approved |
| merge.started | merger | integration lock, candidate | approved to merging |
| merge.completed | merger | result, integration commit, checks | merging to merged/failed |
| knowledge.sync.requested | orchestrator | merge range, root ID | notify root |
| knowledge.synchronized | root | cache digest, provenance | sync progress |
| knowledge.evolution.started | Knowledge Runtime | root, merge range, candidate domains | evolution started |
| knowledge.snapshot.published | root | snapshot/cache digest, domains, provenance | snapshot current |
| cache.invalidated | Knowledge Runtime | layer, scope, trigger | cache unavailable |
| session.lineage.recorded | adapter/orchestrator | parent, child, edge type | lineage projection |
| session.unavailable | adapter/orchestrator | observation and reason | session overlay |
| lease.granted | orchestrator | resource, token, expiry | writer enabled |
| lease.revoked | orchestrator | reason, token | writer disabled |
| event.rejected | orchestrator | rejected ID, code, detail | no business transition |

## Implementation-ready example

~~~json
{
  "type": "implementation.ready",
  "payload": {
    "feature_branch": "ai/feat-0042",
    "base_commit": "091e4d9c...",
    "head_commit": "ab12cd34...",
    "merge_base": "091e4d9c...",
    "changed_paths": ["src/runtime/lease.ts", "test/lease.test.ts"],
    "diff_sha256": "a291...",
    "tests": [
      {"command": "npm test -- lease", "status": "passed", "report_ref": "artifact://check/01"}
    ],
    "generated_artifacts": [],
    "migrations": [],
    "known_risks": [],
    "writer_lease": {"lease_id": "lea_01", "fencing_token": 17}
  }
}
~~~

The merge base must be recomputed by the merger. The implementer’s claim is
evidence, not a substitute for Git verification.

## Merge approval example

~~~json
{
  "type": "merge.approved",
  "payload": {
    "feature_id": "feat-0042",
    "reviewed_head": "ab12cd34...",
    "reviewed_base": "091e4d9c...",
    "target_ref": "main",
    "plan_digest": "31fd...",
    "review_packet_digest": "cabe...",
    "check_evidence_digest": "eac1...",
    "policy_revision": "policy-2026-07-31.1",
    "expires_at": "2026-07-31T11:24:00Z",
    "approval_scope": "merge"
  }
}
~~~

Only the configured Claude reviewer identity can emit this type in the baseline role profile. The
merger must reject it if any binding fact differs at merge time.

## Validation

Schema validation occurs before authorization. Semantic validation occurs before
projection and again before a side effect. Unknown top-level required fields
should be rejected in strict mode; unknown optional extension fields may be
preserved under a namespaced extension object.

~~~text
validate event:
  parse JSON with size limit
  require supported protocol version and known type
  validate producer session and role
  validate aggregate sequence/idempotency semantics
  validate type-specific schema
  resolve referenced Git objects and policy revision where required
  check content digest
  authorize transition
~~~

## Versioning

The protocol version has major compatibility semantics. A consumer of protocol
major version 1 rejects an incompatible major version 2 event rather than interpreting it best-effort. Additive
fields use the extensions namespace and must not change existing meaning.
Breaking changes require a parallel event type or major version migration.

## Event Store replay rule

Event Store replay reconstructs aggregate, delivery, cache, and lineage
projections from accepted events. A replayed command intent MUST first use its
confirmation query; it MUST NOT replay terminal keys, merges, commits, or
cleanup merely because a historical event appears in the stream.

## Attachments

An attachment contains URI, media type, byte size, digest, retention class, and
access classification. Attachments are immutable once referenced. A consumer
must verify digest before use and must not fetch a remote attachment unless
policy permits its location and network access.

## Privacy and redaction

Events must avoid secrets, raw prompts, complete source snapshots, and
unbounded terminal output. A summary that contains a credential-like token must
be redacted before append. Security-sensitive evidence can be referenced through
a restricted artifact URI while public event metadata remains inspectable.

## Trade-offs

A strict envelope adds structure compared with free-text messages, but it makes
recovery, authorization, and metrics possible. It also lets future adapters
participate without teaching every agent vendor-specific conversation syntax.
