# Experiment Design: 02-event-protocol

## Architecture Mapping
The AI Multi-Agent Runtime relies heavily on an event-driven architecture governed by the `ai-runtime.events/v1` protocol. 
- **Event Store**: Append-only log of all events.
- **Derived State Store**: Projections rebuilt by replaying the Event Store.
- **Validation Pipeline**: Rejects invalid schemas prior to domain logic.

## Runtime Topology
1. A mock validation script representing the schema validator.
2. A flat NDJSON file representing the Event Store.
3. A bash script simulating the Event Store appender with deduplication logic.
4. A projection engine replaying the NDJSON file.

## Expected Behavior
- Any event not conforming to the envelope schema yields `SCHEMA_INVALID`.
- Duplicate `idempotency_key` yields `IDEMPOTENCY_CONFLICT`.
- Events pass validation if the hash matches the payload and envelope structure is intact.
- Replaying the events accurately reconstructs the sequence of actions.
