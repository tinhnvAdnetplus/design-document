# PoC 06: Review Loop

## Objective
Validate the feature and review lifecycle from plan through merge, including the review/fix escalation mechanism and approval binding verification.

## Architecture Assumptions Validated
- Feature lifecycle state machine: requested -> planning -> implementing -> reviewing -> approved -> merging -> synchronizing -> completed.
- Approval binding immutability (reviewed_head, reviewed_base, plan_digest, policy_revision, check_evidence_digest).
- Stale approval invalidation when head/base/policy change.
- Review/fix escalation at configured cycle limit.
- Writer lease grant/revocation.
- Changes requested returns feature to implementation with absent approval state.
- Forged approval rejection.
- Only Claude reviewer can emit merge.approved in baseline role profile (INV-04).

## Relevant V2.2 spec
- Chapters 14, 8
- INV-04, INV-03
- Test scenarios T-04, T-05, T-06, T-26\n