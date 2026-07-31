# PoC 02: 02-event-protocol

## Objective
Validate the V2.2 JSON event envelope schema, event catalog, validation pipeline, idempotency, and Event Store append-only semantics.

## Scope
- Validation of JSON envelope structure and fields
- Event types (feature.requested, plan.ready, etc.)
- Strict schema validation
- Idempotency key duplication rejection
- Content integrity validation via SHA-256 hash
- Projection rebuild from event replay

## Success Criteria
- [ ] Events matching the schema are successfully appended.
- [ ] Invalid events (missing fields, bad schema, wrong protocol) are rejected with appropriate error codes (SCHEMA_INVALID).
- [ ] Duplicate events based on `idempotency_key` are rejected (IDEMPOTENCY_CONFLICT).
- [ ] Projection is correctly rebuilt in deterministic order during event replay.

## Architecture Assumptions Validated
- JSON envelope structure with all required fields (event_id, protocol, type, occurred_at, producer, aggregate, correlation_id, idempotency_key, policy_revision, payload, integrity)
- Schema validation before authorization
- Idempotency key deduplication
- Content integrity via SHA-256 hash
- Append-only Event Store semantics
- Projection rebuild from event replay
- Event ordering via aggregate sequence numbers

## Relevant V2.2 Spec
- Chapters 11-13 — Communication Protocol, Message Format, Protocol Error Handling
- INV-09: Every state change has correlation and provenance
