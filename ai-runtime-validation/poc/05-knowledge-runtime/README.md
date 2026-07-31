# PoC 05: Knowledge Runtime

## Objective
Validate Knowledge Snapshots (6 domains), Knowledge Compression, and Knowledge Evolution.

## Architecture Assumptions Validated
- Knowledge Snapshot schema with 6 domains (Project, Architecture, Business, Workspace, Dependency, Convention).
- Facts classified as: confirmed, inferred, open, transient.
- Provenance linking to Git commits and paths.
- Knowledge Compression pipeline: eligible evidence -> transient summary -> candidate fact -> validation -> bounded snapshot.
- Knowledge Evolution triggered by merge evidence.
- Cache Registry metadata tracking.
- V2 Cache Taxonomy: Prompt Cache, Conversation Cache (disabled), Resume Cache, Knowledge Cache.
- Token budget enforcement (128 KiB total feature packet).
- Unproven facts rejected.
- Conversation Cache material cannot promote to Knowledge Cache.

## Relevant V2.2 spec
- Chapters 9, 16
- INV-01, INV-05
- Test scenarios T-13, T-16, T-17\n