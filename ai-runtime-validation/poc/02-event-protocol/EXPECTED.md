# Measurable Pass Criteria: 02-event-protocol

## 1. Schema Validation
- `missing_fields.json` fails validation.
- `bad_schema.json` fails validation.
- `wrong_protocol.json` fails validation.

## 2. Event Store Append
- Valid events are appended to `store.ndjson`.
- The store maintains strict append-only ordering.

## 3. Idempotency
- Appending the same valid event twice fails the second time with an idempotency error.

## 4. Replay & Projection
- Projection script reads `store.ndjson` and outputs the correct sequence of states matching the aggregate events.
