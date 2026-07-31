# PoC 04 — Capability Registry: Expected Results

## Pass Criteria

### CAP-01: Capability Document Registration
- Adapter `capabilities()` call returns a well-formed JSON document
- Document contains: adapter name, version, supported operations (start, fork, resume, stop)
- Registry stores document indexed by adapter name
- Registry rejects documents missing required fields

### CAP-02: Fork Gating
- When Registry declares `native_fork=true`: native fork path selected
- When Registry declares `synthetic_fork=true`, no native: synthetic fork selected
- When Registry declares neither: fork request rejected with `ADAPTER_UNAVAILABLE`
- Fork type never inferred from CLI output, probing, or model reasoning

### CAP-03: Resume Gating
- Resume attempt proceeds only when Registry declares `resume=true`
- When `resume=false` or absent: fresh reconstruction selected
- Resume cache is not consulted without Registry authorization

### CAP-04: Revalidation on Startup/Restart
- Runtime startup triggers `capabilities()` call for every enabled adapter
- Previous Registry entries cleared before new documents loaded
- Affected sessions marked unavailable until revalidation succeeds

### CAP-05: Revalidation on Adapter Upgrade
- Manual CLI upgrade declaration triggers revalidation
- Version mismatch between old and new document detected
- Operations dependent on changed capabilities re-evaluated

### CAP-06: Declaration/Observation Mismatch
- When adapter declares `resume=true` but resume fails consistently: `ADAPTER_UNAVAILABLE`
- When adapter declares `native_fork=true` but fork produces invalid session: `ADAPTER_UNAVAILABLE`
- Affected work fenced until mismatch resolved

### CAP-07: Stale Document Rejection
- Document with older version than currently registered is rejected
- Revalidation with stale document does not overwrite current state

## Fail Criteria
- Any operation proceeds without a current Capability Registry entry
- Runtime infers capabilities from CLI output or terminal probing
- Resume attempted without `resume=true` in Registry
- Fork type inferred from adapter name instead of capability declaration