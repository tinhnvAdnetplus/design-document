# 25 — Security Architecture

## Purpose

This chapter defines the security objectives, threat model, trust boundaries,
and baseline controls for the local runtime.

## Security objectives

The runtime must prevent unauthorized repository mutation, merge approval,
policy change, terminal command injection, secret disclosure, and cross-feature
workspace access. It must preserve enough evidence to investigate misuse
without retaining unrestricted prompts or terminal transcripts.

## Threat model

| Threat | Example | Primary control |
| --- | --- | --- |
| malicious event | forged merge approval | authenticated producer and capability check |
| confused agent | root edits feature code | role policy and no writer lease |
| stale process | old implementer resumes | lease fencing token |
| terminal injection | task text interpreted as shell | fixed-form notification command |
| path traversal | event selects arbitrary worktree | generated paths and canonical validation |
| secret exposure | token in prompt/log | redaction and restricted retention |
| supply-chain change | altered CLI behavior | adapter version contract tests |
| capability misreporting | declared adapter behavior differs from observation | mark `ADAPTER_UNAVAILABLE`, fence, and revalidate |
| Git ref race | merge against changed base | lock and approval binding |
| event tamper | edited local record | digest, access controls, optional signatures |
| privilege escalation | agent changes policy | read-only configuration and separate admin role |

The local threat model assumes the host runtime account and local kernel are
trusted enough to run agents. A compromised host can defeat local file controls;
hardened deployments should use OS accounts, containers, and remote audit sinks.

## Trust boundaries

~~~mermaid
flowchart LR
    U[Human / external request] --> C[Control plane]
    C --> A[Agent adapters]
    A --> T[tmux terminals]
    C --> G[Git gateway]
    C --> S[State and cache]
    A --> N[Vendor and approved network]
    T --> W[Feature worktrees]
    G --> I[Integration worktree]
~~~

Every arrow is a boundary at which input is validated, identity is checked, and
output is constrained. Terminal output is particularly untrusted: it may be
model-generated, affected by shell state, or include adversarial repository
content.

## Baseline controls

| Area | Control |
| --- | --- |
| identity | runtime-issued session IDs bound to terminal/adapters |
| authorization | role and capability policy evaluated twice |
| Git | gateway allow-list, clean integration check, immutable approvals |
| files | canonical allowed roots, manifests, restrictive modes |
| terminal | fixed-form send-keys, no prompt text injection |
| events | schema, digest, idempotency, append-only access |
| secrets | references only, redaction, restricted diagnostics |
| network | deny by default; adapter/MCP allow-list and explicit model-inference permission |
| dependencies | pinned/validated adapter versions, contract tests |
| audit | accepted/rejected actions and override records |

## Secret handling

Secrets are supplied by a configured provider reference, scoped to the minimum
agent/session that needs them, and never inserted into an event envelope or
Knowledge Cache. The runtime masks known secret values from logs where feasible and
treats a suspected exposure as a security incident: stop sharing artifact,
revoke credential, redact retained copies where policy permits, and record
response.

## Repository-content attacks

Agents read untrusted repository text, including instructions embedded in source,
issues, and generated files. Adapters must treat repository content as data,
not authority. Only runtime configuration and validated events prescribe role,
permissions, terminal command format, or merge action.

## Secure defaults

Raw transcript retention is disabled. Network access is denied unless needed.
Model inference traffic is denied unless the specific adapter has an explicit
model-inference permission; adapter updates and MCP access do not imply it.
Root sessions lack write leases. Feature sessions lack integration access.
Unknown events and policy revisions are rejected. Dirty worktrees are preserved
rather than automatically cleaned. These defaults favor containment over
frictionless automation.

## Incident response

1. Freeze affected leases and block state-changing intents.
2. Preserve event/log/Git evidence with controlled access.
3. Identify scope: session, feature, worktree, policy, credentials, remote.
4. Rotate exposed credentials and invalidate suspicious approvals.
5. Reconstruct from known-good Git/configuration if necessary.
6. Record corrective action and add regression test.

## Limitations and future work

Local controls cannot fully isolate a powerful CLI running under one Unix user.
Future hardening may add per-agent containers, seccomp, filesystem namespaces,
network proxies, signed events, hardware-backed credentials, and remote
append-only audit storage.

## V2 knowledge and scheduler controls

Knowledge Runtime accepts only Git/configuration/governed Event Store evidence.
Conversation Cache is disabled by default, access-logged when enabled, and
cannot be promoted directly into Knowledge Cache. Cache Registry metadata and
Session Lineage Graph are sensitive operational metadata; they require the same
access control as event audit records. Scheduler and Dispatcher accept only
validated event references and cannot interpret terminal text as a queue command.

## Capability Registry trust boundary

Capability Discovery is Adapter-owned. Capability Registry is Runtime-owned and
contains only version-bound results returned by `Adapter.capabilities()`. The
Runtime MUST NOT populate it from CLI output, runtime probing, or LLM reasoning.
Declared capabilities are claims subject to observed behavior: if a fork,
resume, notification, or lifecycle observation contradicts the current
declaration, the Runtime treats the adapter as `ADAPTER_UNAVAILABLE`, fences
dependent leases/intents, and requires revalidation. It never silently trusts a
misreporting adapter or falls back to an undeclared behavior.
