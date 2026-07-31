# PoC 03: 03-session-resume

## Objective
Validate that the runtime can recover from session loss through both vendor resume and fresh reconstruction, proving that resume is an optimization and never a correctness dependency (INV-06).

## Scope
- Reattach to existing processes.
- Fresh reconstruction from Git-derived packets (without resume IDs).
- Quarantine behavior for dirty worktrees during feature recovery.
- Root recovery cache validation.

## Success Criteria
- [ ] Session recovery cleanly attempts reattach -> resume -> fresh reconstruction.
- [ ] Fresh reconstruction successfully loads agent context solely from Git and the cache, without requiring vendor-specific resume features.
- [ ] Dirty feature worktrees are safely quarantined.
- [ ] Root session accurately validates cache against the integration branch HEAD.

## Architecture Assumptions Validated
- Recovery decision tree: reattach -> resume -> fresh reconstruction
- Resume is exceptional only (INV-06)
- Fresh reconstruction from Git-derived packets works without resume IDs
- Reconstruction packet contains required fields (role contract, repository identity, Knowledge Cache, Git state)
- Recovery order from V2.2 spec Chapter 23
- Capability Registry must declare `resume=true` before resume attempt
- Feature recovery handles dirty worktrees by quarantine
- Root recovery validates cache against integration HEAD

## Relevant V2.2 Spec
- Chapters 7, 8, 23
- INV-06: Normal execution does not use resume
- Test scenarios T-08, T-09, T-10
