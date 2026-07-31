# PoC 04: Capability Registry

## Objective
Validate that the Capability Registry correctly gates adapter operations (startup, fork, resume, scheduling) based on declarative Capability Documents, and properly handles revalidation and mismatch scenarios.

## Architecture Assumptions Validated
- Adapter `capabilities()` provides version-bound Capability Document
- Registry populated only from adapter declarations, never from CLI probing or LLM reasoning
- Registry gates: startup, scheduling, fork, resume
- Revalidation triggers: runtime startup, restart, adapter upgrade, manual CLI upgrade
- Mismatch handling: `ADAPTER_UNAVAILABLE` status
- Resume gated by `resume=true` declaration
- Fork gated by `native_fork` or `synthetic_fork` declaration

## Relevant V2.2 spec
- Chapters 5, 6, 10
- Test scenarios T-22 through T-27\n