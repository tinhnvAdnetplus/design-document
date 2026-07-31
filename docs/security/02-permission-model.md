# 26 — Permission Model

## Purpose

This chapter defines policy evaluation, capabilities, resource scopes, and
audit requirements. Permission is explicit, contextual, and short-lived where
mutation is involved.

## Policy decision model

~~~text
allow(subject, action, resource, context) when:
  subject session is registered and active
  role includes action capability
  policy revision is current
  resource matches allowed scope
  feature state permits action
  required lease/approval is valid
  no security or recovery block applies
~~~

The policy engine returns allow, deny, or require-human. It never returns an
implicit allow because an event was well-formed.

## Capability catalog

| Capability | Resource scope | Holder in baseline role profile |
| --- | --- | --- |
| read_repository | configured repo | all defined roles |
| fork_session | own adapter/root | root adapters |
| write_feature | assigned worktree and branch | Codex implementer |
| commit_feature | assigned branch | Codex implementer |
| request_review | feature aggregate | planner/implementer |
| review_feature | immutable review snapshot | Claude reviewer |
| approve_merge | exact reviewed candidate | Claude reviewer |
| merge_integration | configured integration ref | merger |
| sync_knowledge | own Knowledge Cache | corresponding root |
| use_model_inference | configured adapter inference endpoint | adapter with explicit network permission |
| alter_policy | configuration | administrator |
| recover_quarantine | named artifact | restricted maintainer |

A capability is narrower than a role. The implementation must check branch,
worktree, feature state, token, and policy revision as context.

`use_model_inference` is a network permission evaluated for the adapter, not a
claim inferred from a model response or terminal text. It is independent of
repository and merge permissions and is denied unless configuration explicitly
allows it.

## Permission matrix

| Action | Root | Planner | Implementer | Reviewer | Merger | Human admin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| read Git | yes | yes | yes | yes | yes | policy |
| edit app code | no | no | assigned | no | no | policy |
| create commit | no | no | assigned | no | no | policy |
| approve | no | no | no | yes | no | override |
| merge main | no | no | no | no | yes | emergency |
| update Knowledge Cache | own only | no | no | no | no | no |
| change policy | no | no | no | no | no | yes |
| delete quarantine | no | no | no | no | no | restricted |

## Writer lease

A writer permission is a lease with an expiry and fencing token. Every
write-sensitive gateway call includes feature ID, session ID, worktree manifest,
branch, and token. The gateway checks all fields before action. A process
without a valid current token may read but cannot write through managed paths.

## Approval binding

Merge approval is not a broad permission. It authorizes one exact candidate:
reviewed head, base, target ref, plan digest, check digest, policy revision, and
expiration. The merger reevaluates those facts and protected-path policy under
an integration lock.

## Policy change effects

A policy revision change takes effect for new side effects immediately. It does
not rewrite historical accepted events. Active leases may be revoked; queued
deliveries may be canceled; pending approvals may be invalidated. Every such
effect is logged with both old and new revision identifiers.

## Audit requirements

Permission decisions must record subject, role, capability, resource identifier,
feature/session context, policy revision, result, denial reason, and causation
event. Successful decisions that cause Git or terminal side effects also record
the command-intent and postcondition reference.

## Human overrides

Human overrides are separate capabilities with narrower issuer lists and
stronger audit. They may not be embedded in agent prompts. A policy may require
two humans or external approval for protected branches and secret-related
actions.

## Trade-offs

Contextual permission checks are more work than one broad token per agent, but
they confine compromised or mistaken sessions. Short leases add renewals yet
make recovery and stale-process fencing reliable.

## V2 non-authority metadata

Knowledge Snapshot version, cache layer, lineage parent, queue priority, and
retry attempt are operational metadata. None grants a capability. Permission
evaluation MUST continue to rely on authenticated session, role, resource,
current policy, feature state, and required lease/approval. A Session Lineage
Graph edge or Knowledge Cache citation cannot authorize dispatch, write, review,
or merge.
