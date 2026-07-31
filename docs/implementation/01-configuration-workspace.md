# 18 — Configuration and Workspace Layout

## Purpose

This chapter defines configuration structure, directory ownership, validation,
and a reference workspace layout for local deployment.

## Configuration principles

Configuration is versioned, reviewed, least-privilege, and separate from
runtime-derived state. Agent task text must not change policy. A configuration
reload creates a new policy revision; active side effects are reauthorized
before execution.

## Example configuration

~~~yaml
runtime:
  name: ai-runtime
  repository: /srv/ai-runtime/repo.git
  integration_ref: main
  state_dir: /srv/ai-runtime/state
  worktree_root: /srv/ai-runtime/worktrees
  tmux_socket: ai-runtime
  event_store:
    kind: sqlite
    path: /srv/ai-runtime/state/runtime.db
  limits:
    inline_event_bytes: 16384
    feature_packet_bytes: 131072
    root_cache_bytes: 262144
    pending_deliveries_per_session: 32
  scheduler:
    priority_classes: [critical, high, normal, low]
    max_delivery_attempts: 5
    fairness: per_feature_fifo
  knowledge_runtime:
    snapshot_domains: [project, architecture, business, workspace, dependency, convention]
    conversation_cache: disabled
    knowledge_cache_retention_days: 30
    resume_cache_retention_hours: 24

agents:
  claude:
    enabled: true
    root:
      role: claude_root
      tmux_session: claude-root
      worktree: /srv/ai-runtime/integration-readonly
    allowed_actions: [plan, review, approve_merge, synchronize_knowledge]
  codex:
    enabled: true
    root:
      role: codex_root
      tmux_session: codex-root
      worktree: /srv/ai-runtime/integration-readonly
    allowed_actions: [implement, synchronize_knowledge]

policy:
  approval:
    merge_role: claude_reviewer
    expiration_minutes: 60
  review:
    max_fix_cycles: 3
    escalation: require_human
  protected_paths:
    - migrations/**
    - infra/**
    - .github/**
  required_checks:
    - unit
    - lint
  resume:
    enabled: true
    max_attempts: 1
  retention:
    transcript_mode: disabled
    feature_metadata_days: 30
    event_days: 365
  knowledge_audit:
    mode: event_only # event_only | metadata_branch
    branch: runtime/knowledge

security:
  allowed_worktree_roots:
    - /srv/ai-runtime/worktrees
  network:
    default: deny
    allow_for: [adapter_update, configured_mcp]
    model_inference:
      claude: allow
      codex: allow
  secrets:
    provider: environment_reference
~~~

This example is a policy artifact. Absolute paths, command mappings, and secret
provider names are deployment-specific. Secrets are referenced, never included.

## Configuration schema

| Section | Required fields | Validation |
| --- | --- | --- |
| runtime | repository, integration ref, state/worktree dirs | paths exist or safely creatable |
| agents | adapter ID, root role, enabled flag | unique roots and policy-authorized actions |
| policy | merge role, protected paths, checks, review escalation | role resolves; patterns and bounded fix cycles valid |
| limits | bounded sizes and counts | positive, safe maximums |
| security | path roots, egress, model-inference permission, secret references | no broad unsafe allowance |
| retention | event/cache/transcript rules | privacy and storage constraints |
| observability | log level, metrics endpoint | secret redaction enabled |
| scheduler | priority/retry/fairness limits | bounded classes and attempts |
| knowledge runtime | snapshot/cache/retention policy | Conversation Cache disabled by default |

`allowed_actions` is policy authorization, not Capability Discovery. The
Runtime obtains adapter capabilities only from `Adapter.capabilities()` and
builds Capability Registry metadata from that result. The loader must reject
unknown critical fields in strict mode and reject a configuration that grants a
role inconsistent actions such as root code write or implementer merge approval.
It must also reject an enabled adapter that cannot provide a current Capability
Document at startup.

## Directory structure

~~~text
/srv/ai-runtime/
  repo.git/                         Git object database or primary checkout
  integration/                      merger-only integration worktree
  integration-readonly/             root/read-only view
  worktrees/
    feat-0042/
    review-feat-0042-1/
  state/
    runtime.db                      Event Store and projection
    events/                         optional NDJSON export
    sessions/
      ses_claude_root.json
    leases/
    deliveries/
    caches/
      claude-root.yaml
      codex-root.yaml
    cache-registry/
    lineage/
    packets/
      feat-0042/
    artifacts/
    quarantine/
  config/
    runtime.yaml
    adapters/
    policy/
  logs/
  run/
    ai-runtime.sock
~~~

Runtime state is not committed to the application repository unless a separate
repository policy explicitly tracks sanitized design metadata. Application code
worktrees do not contain caches, event files, or vendor resume IDs.

## V2 runtime state ownership

| State | Owner | Lifecycle | Restriction |
| --- | --- | --- | --- |
| Event Store | control plane | retention policy | runtime evidence, not code truth |
| Cache Registry | Knowledge Runtime | cache artifact lifetime | metadata, not unrestricted contents |
| Knowledge Cache | named root | root lifecycle | provenance-linked and rebuildable |
| Conversation Cache | restricted diagnostics | short policy lifetime | disabled by default |
| Resume Cache | adapter | Resume Scope | opaque and exceptional only |
| Capability Registry | Runtime | adapter/runtime lifecycle | version-bound Adapter capability documents only |
| Lineage projection | Session Registry | event retention | no authority/transport semantics |

## File permissions

| Path | Owner | Mode guidance | Reason |
| --- | --- | --- | --- |
| config policy | runtime administrator | read-only to agents | prevent policy self-modification |
| state database | runtime account | owner read/write | event integrity |
| Knowledge Cache | corresponding root/runtime | owner read/write | derived context confidentiality |
| packets | feature role/runtime | restrictive temporary | task content |
| worktrees | assigned writer | controlled write | isolation |
| logs | observability/runtime | restrictive read | may contain paths/summaries |
| quarantine | maintainer only | no agent write | forensic preservation |

A hardened deployment should map roles to separate Unix users or containers.
At minimum, the gateway and policy engine must reject path and capability misuse
even when filesystem permissions are coarse.

## Workspace creation

~~~text
function create_feature_workspace(feature):
  validate generated feature ID
  create branch from recorded integration base
  create worktree under canonical root
  write immutable workspace manifest
  set controlled environment and Git configuration
  grant no write lease until session readiness
  return path and manifest digest
~~~

The manifest records feature ID, branch, base commit, creation event, expected
owner, and allowed root. It is used during cleanup and recovery to distinguish a
runtime worktree from an arbitrary directory.

## Environment contract

Adapters receive a minimal environment: repository path, assigned worktree,
runtime client path, session ID, role, cache/packet reference, and configured
safe variables. They do not receive database credentials, policy write keys, or
other agents’ secrets. Shell initialization files should be controlled or
disabled for runtime CLI invocation.

## Change management

A configuration change is a reviewed Git change or equivalent immutable
configuration revision. The orchestrator logs its digest and uses it for event
authorization. Revoking a capability applies immediately to new side effects;
existing sessions become unable to renew denied leases.

The review escalation policy bounds review/fix cycles per feature. When the
configured maximum is reached, the Runtime applies the configured
`require_human` action: it blocks automatic further implementation/review
dispatch and records the cycle count and evidence. A maintainer may abandon,
replan, or issue an auditable policy override; the setting never turns a review
finding into approval.

Model inference egress is separate from adapter-update and MCP egress. Each
enabled networked model adapter requires an explicit `model_inference` allow
entry; absence means deny. This permission only permits the configured adapter
to contact its configured inference endpoint and grants no repository, shell,
policy, or merge authority.

V2 configuration MUST reject a Conversation Cache enabled without explicit
retention/access policy, a scheduler class that bypasses authorization, or a
Root Update Commit branch that permits application paths.

## Trade-offs

A detailed configuration schema increases initial setup but makes policy
reviewable and reproducible. Splitting state, configuration, and worktrees
reduces accidental coupling, at the cost of more paths to manage.
