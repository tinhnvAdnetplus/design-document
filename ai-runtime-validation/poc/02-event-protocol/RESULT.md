# Results: 02-event-protocol

## Validation Run Date
*TBD*

## Environment Details
- jq version:

## Criteria Checklist
- [ ] Events matching the schema are successfully appended.
- [ ] Invalid events (missing fields, bad schema, wrong protocol) are rejected with appropriate error codes (SCHEMA_INVALID).
- [ ] Duplicate events based on `idempotency_key` are rejected (IDEMPOTENCY_CONFLICT).
- [ ] Projection is correctly rebuilt in deterministic order during event replay.

## Observations
*Record actual outcomes and any discrepancies from EXPECTED.md here.*
