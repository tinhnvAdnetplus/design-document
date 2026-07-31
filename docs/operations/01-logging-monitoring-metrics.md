# 21 — Logging, Monitoring, and Metrics

## Purpose

This chapter defines operational telemetry, privacy boundaries, dashboards, and
alerts for the runtime.

## Logging principles

Logs describe control-plane action and safe operational evidence. They do not
default to full prompts, raw terminal captures, source snapshots, credentials,
or unrestricted command output. Every record has timestamp, severity, component,
runtime/session/feature correlation where applicable, and policy revision.

| Log class | Contents | Retention |
| --- | --- | --- |
| audit | event acceptance, approval, merge, override | longest policy period |
| operational | lifecycle, delivery, Git gateway result | operational period |
| security | authorization denial, path escape, secret signal | incident policy |
| diagnostic | bounded redacted capture | short, restricted |
| access | operator read/mutate requests | audit period |

## Structured log example

~~~json
{
  "time": "2026-07-31T10:24:00Z",
  "level": "INFO",
  "component": "scheduler",
  "message": "delivery acknowledged",
  "event_id": "evt_01J",
  "feature_id": "feat-0042",
  "session_id": "ses_codex_1",
  "attempt": 1,
  "policy_revision": "policy-2026-07-31.1"
}
~~~

## Metrics

| Metric | Type | Labels | Interpretation |
| --- | --- | --- | --- |
| runtime_events_accepted_total | counter | type, result | protocol load/errors |
| runtime_event_accept_seconds | histogram | type | event-store latency |
| runtime_delivery_seconds | histogram | target role, result | notice latency |
| runtime_pending_deliveries | gauge | session, priority | backpressure |
| runtime_sessions | gauge | adapter, role, lifecycle | availability |
| runtime_leases | gauge | resource type, state | concurrency |
| runtime_feature_state | gauge | state | workflow flow |
| runtime_recovery_total | counter | kind, outcome | resilience |
| runtime_merge_total | counter | outcome, strategy | integration health |
| runtime_root_cache_age_seconds | gauge | root | sync freshness |
| runtime_packet_bytes | histogram | role | context budget |
| runtime_token_usage_total | counter | adapter, role | cost trend |

Labels must avoid feature text, path names, user content, or high-cardinality
unbounded IDs in metrics backends. Detailed association stays in logs/events.

## Dashboards

A production dashboard should show runtime readiness, root availability,
features by state, pending and expired deliveries, active/expired leases, merge
outcomes, cache freshness, recovery rate, event-store health, and packet/token
trend. It should link to safe aggregate status rather than terminal transcripts.

## Alerts

| Condition | Severity | Initial action |
| --- | --- | --- |
| event store unavailable | critical | stop state changes |
| integration lock stuck | high | reconcile Git and lock owner |
| root unavailable past SLO | high | recovery procedure |
| expired writer lease with live process | high | revoke/fence |
| repeated authorization denial | security | suspend and investigate |
| dirty worktree quarantine | high | maintainer review |
| Knowledge Cache stale | warning | synchronize/rebuild |
| packet budget breach | warning | inspect selection policy |

## Tracing

A correlation ID traces one feature workflow; an event ID traces one action;
a command intent ID traces an external side effect. OpenTelemetry or equivalent
may export these identifiers if access controls prevent source/task leakage.

## Retention and access

Event audit retention is configured separately from debug logs. Restricted
diagnostics must be encrypted at rest where available, access-logged, and
purged by policy. Metrics may be retained longer because they are aggregated
and redacted.

## Trade-offs

Detailed observability can become a sensitive transcript system. This design
prioritizes structured evidence and aggregate metrics, enabling incident
response without making routine telemetry an uncontrolled prompt archive.

## V2 component telemetry

| Component | Required telemetry | Limitation |
| --- | --- | --- |
| Event Store | append latency, replay outcome, projection lag | never emit raw event payload by default |
| Eligibility Scheduler | queue depth, eligible age, priority, retry count | no feature text labels |
| Dispatcher | notice latency, target availability, acknowledgement | delivery is not task completion |
| Knowledge Runtime | evolution stage, snapshot age, candidate rejection | no snapshot content in metrics |
| Cache Registry | artifact count, invalidation, eviction, layer bytes | Conversation Cache access is restricted |
| Session Lineage Graph | node/edge count, orphan/reconstruction count | no authority inference from graph |

Alerting on Knowledge Evolution must distinguish an unavailable cache from a
failed merge. The former degrades context quality but cannot invalidate a
verified Git integration commit.
