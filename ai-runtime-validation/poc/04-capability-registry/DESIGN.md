# Experiment Design: Capability Registry

## Architecture Mapping
- **Component**: Capability Registry (Orchestrator)
- **Role**: Validates and gates adapter operations.
- **Protocol**: ai-runtime.events/v1

## Expected Behavior
1. **Registration**: Store capabilities.
2. **Gating**: Reject operations not supported.
3. **Revalidation**: Fetch capabilities on trigger.
4. **Mismatch**: Mark unavailable.\n