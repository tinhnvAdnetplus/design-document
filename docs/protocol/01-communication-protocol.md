# 11 — Communication Protocol

## Purpose

This chapter defines asynchronous event communication between agents, the V2
Event Store, Dispatcher, Eligibility Scheduler, and deterministic runtime
actors. It replaces synchronous agent-to-agent calls with durable event handoff.

## Core rule

A sender emits an event, receives acceptance or rejection from the control
plane, then returns to its own work or idle state. It MUST NOT wait for a
receiver’s result. A receiver processes the event when its role, session state,
and policy permit, then emits a successor event or explicit deferral.

## Event flow

~~~mermaid
flowchart LR
    P[Producer] --> V[Validate]
    V -->|valid| L[Append Event Store]
    V -->|invalid| R[event.rejected]
    L --> S[Project aggregate]
    S --> Q[Durable Delivery Queue]
    Q --> E[Eligibility Scheduler]
    E --> D[Dispatcher]
    D --> A[Adapter notify]
    A --> K[Consumer acknowledgement]
    K --> C[Consumer process]
    C --> N[Successor event or idle]
~~~

The Event Store append and projection order is deliberately before notification. A terminal
notice can be lost; the event record remains available to retry or reconcile.

## Delivery semantics

The protocol provides at-least-once notice delivery and exactly-once effect
through idempotent event processing and deterministic command intents. It does
not promise exactly-once terminal keystrokes.

| Concern | Protocol rule |
| --- | --- |
| producer retry | same idempotency key returns existing accepted event |
| duplicate notice | consumer acknowledgement is idempotent |
| duplicate event | projection compares event ID and content digest |
| ordering | ordered per aggregate; cross-feature order is not meaningful |
| out-of-order causal event | hold or reject pending predecessor resolution |
| unavailable consumer | retain pending delivery with deadline |
| expired delivery | escalate event; do not discard durable source event |
| fan-out | one delivery record per target |
| terminal ambiguity | mark adapter unavailable; preserve event |

## Event streams

Events belong to a primary aggregate stream and may be indexed by session,
feature, root, merge, or policy revision. The primary feature stream serializes
workflow decisions for one feature. Separate feature streams may progress in
parallel if their leases and merge constraints do not conflict.

| Stream | Ordering guarantee | Example |
| --- | --- | --- |
| feature | strict logical sequence | plan, implementation, review |
| session | lifecycle sequence | ready, unavailable, recovered |
| root | cache synchronization sequence | sync requested/completed |
| runtime | global operational record | config loaded, recovery started |
| policy | revision history | policy changed, capability revoked |
| lineage | derived session-parent projection | fork/reconstruction evidence |
| knowledge | snapshot publication lifecycle | candidate/validated/published |

## Acknowledgement model

A notification acknowledgement means the target runtime client resolved and
accepted the event reference. A processing acknowledgement means the agent
emitted a correlated workflow result or explicit defer. The two states are
different and are separately recorded.

The orchestrator SHOULD remind a consumer of unprocessed high-priority events
after a configured delay, but it must not inject repeated prompts indefinitely.
A consumer can emit a deferral with a reason and estimated availability; policy
sets the maximum deferral interval.

## Priority classes

| Priority | Use | Delivery policy |
| --- | --- | --- |
| critical | lease revocation, cancellation, security stop | interrupt-compatible adapter path |
| high | review decision, merge outcome, recovery action | prompt delivery before normal queue |
| normal | planning and implementation work | FIFO per session |
| low | cache refresh hints, metrics notices | coalesce where safe |

Priority does not override authorization. A critical event to a terminated
session is recorded and handled by recovery or cleanup, not forced into a
nonexistent terminal.

## Causation and correlation

Every event has a unique event ID, a correlation ID shared by one feature
workflow, and an optional causation ID naming the immediate predecessor. A
reviewer response caused by an implementation-ready event carries that event
ID. A root synchronization request is caused by merge completion but shares
the feature correlation ID.

A root-cause event such as a human feature request has no causation ID. An
operator override must use a new correlation or explicit override link rather
than pretending to be a normal successor.

## Delivery deadlines

| Event category | Ack deadline | Processing expectation | Escalation |
| --- | ---: | ---: | --- |
| cancellation/revocation | 30 s | immediate state change | revoke externally |
| implementation notice | 2 min | configurable task SLA | session health check |
| review request | 5 min | configurable review SLA | maintainer visibility |
| merge approval | 2 min | mechanical validation | invalidate if stale |
| root sync | 10 min | bounded cache update | degrade root planning |
| telemetry | best effort | none | coalesce/drop under policy |

The deadlines measure runtime handling, not model cognitive performance. An
agent can remain busy for a long task provided it emits progress or lease
renewal events under configured policy.

## Message routing

The Dispatcher routes by explicit target role or session. Eligibility Scheduler
selects delivery only after policy, priority, retry deadline, session capacity,
and lease state permit it. It MUST resolve a role to a current eligible session
at delivery time. A sender cannot select an arbitrary terminal by string. If two
reviewer sessions exist for separate attempts, the feature aggregate identifies
the valid target.

## Protocol invariants

1. Event acceptance is separate from event delivery.
2. Delivery is separate from task completion.
3. Event payloads contain facts and references, not hidden terminal commands.
4. Unstructured terminal prose cannot change workflow state.
5. Every delivery attempt is attributable to an immutable event.
6. A consumer cannot grant itself a new capability by emitting an event.
7. A valid event remains inspectable after its target session is destroyed.
8. Transport substitution must preserve these semantics.
9. Event Store replay rebuilds projections and reconciles effects; it never
   replays terminal input or Git mutation blindly.
10. Session Lineage Graph is not a delivery route or authorization input.

## Trade-offs

Events create eventual visibility and require status tooling. The alternative,
blocking RPC, is deceptively simple until a CLI is unavailable or waits for
human input. This protocol favors recoverable handoffs and explicit evidence
over conversational immediacy.

See [Message Format and JSON Events](02-message-json-event-protocol.md) for the
envelope and [Protocol Error Handling](03-protocol-error-handling.md) for
rejection and retry behavior.
