# PoC 05 — Knowledge Runtime: Expected Results

## Pass Criteria

### KR-01: Knowledge Snapshot Schema (6 Domains)
- Knowledge Snapshot successfully generates with all 6 required domains populated
- Domains conform to V2.2 schema structure

### KR-02: Fact Classification
- Facts are accurately classified into `confirmed`, `inferred`, `open`, or `transient` states
- Fact state transitions operate as specified by validation logic

### KR-03: Provenance Validation against Git
- All `confirmed` and `inferred` facts possess valid provenance links to Git commits or codebase state
- Invalid provenance triggers rejection

### KR-04: Knowledge Compression Pipeline
- Active context exceeding 128 KiB triggers the Knowledge Compression pipeline
- Summarization reduces payload while retaining critical `confirmed` facts

### KR-05: Knowledge Evolution after Merge
- A `merge.completed` event triggers a `knowledge.evolution.started` event
- Old transient/open facts are purged; new facts are promoted to confirmed

### KR-06: Cache Taxonomy Isolation
- Knowledge Cache is strictly isolated from Prompt Cache, Conversation Cache, and Resume Cache
- Read/write ops to Knowledge Cache do not pollute Conversation Cache

### KR-07: Token Budget Enforcement (128 KiB)
- Strict rejection of Knowledge Snapshot payloads exceeding 128 KiB token equivalent
- Event `SCHEMA_INVALID` or `PROTOCOL_UNSUPPORTED` emitted if budget is breached

### KR-08: Unproven Fact Rejection
- Attempting to inject `confirmed` facts without Git provenance results in demotion to `inferred` or immediate rejection

## Fail Criteria
- Facts stored without classification
- No provenance check against Git for `confirmed` facts
- Token budgets ignored, leading to bloat