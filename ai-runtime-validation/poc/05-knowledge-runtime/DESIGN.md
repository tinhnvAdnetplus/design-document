# PoC 05 — Knowledge Runtime: Design

## Objective
Validate the Knowledge Runtime architecture, specifically the creation, validation, compression, and evolution of the Knowledge Snapshot and its integration with the V2 Cache Taxonomy.

## Experiment Design
- Simulate Git context containing various fact states.
- Emit a `knowledge.sync.requested` event to trigger Snapshot creation.
- Validate that the Snapshot populates 6 distinct domains.
- Inject facts without provenance to test rejection/demotion mechanisms.
- Feed a synthetic 200 KiB context to trigger the Knowledge Compression pipeline.
- Simulate a `merge.completed` event to test the Knowledge Evolution lifecycle.

## Architecture Mapping
- **Knowledge Runtime**: Central processing unit for facts and snapshots.
- **Cache Registry**: Stores the resulting Knowledge Cache, isolated from Prompt/Conversation Caches.
- **Knowledge Evolution**: Triggered on merge to update the knowledge baseline.

## Runtime Topology
Git → Knowledge Runtime → Snapshot → Root Notification → Cache Registry

## Expected Behavior
- **Snapshot Generation**: Emits `knowledge.snapshot.published` upon success.
- **Compression**: The pipeline truncates and summarizes to respect the 128 KiB token budget, prioritizing `confirmed` facts.
- **Evolution**: Post-merge, the system emits `knowledge.evolution.started`, synchronizes Git state, and demotes/purges stale transient facts.