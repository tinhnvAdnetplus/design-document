# 06 — Claude and Codex Runtimes

## Purpose

This chapter specifies the adapter contract for the initial Claude CLI and
Codex CLI runtimes. It separates common required behavior from CLI-specific
invocation details that can change with vendor releases.

## Common adapter contract

Each adapter MUST declare capabilities, launch a named terminal session, emit
structured observations, support a fork operation, and support exceptional
recovery. It MUST isolate vendor syntax inside the adapter and must not expose
vendor-specific commands as runtime event types.

| Capability | Claude adapter | Codex adapter | Runtime use |
| --- | --- | --- | --- |
| persistent root | required | required | project context |
| feature fork | required or compatible equivalent | required or compatible equivalent | short-lived task context |
| resume hint | optional | optional | abnormal recovery only |
| event notice injection | required | required | asynchronous delivery |
| readiness evidence | required | required | supervision |
| bounded diagnostic capture | required | required | incident support |
| graceful stop | required | required | feature cleanup |
| session metadata | required | required | reconciliation |
| lineage metadata | required | required | fork/reconstruction provenance |
| resume scope | required | required | exceptional recovery lifetime |

## Claude runtime profile

The Claude adapter owns one session named claude-root and creates a clearly
named feature terminal for each planner or reviewer fork. Its root prompt
contains only stable runtime instructions, project identity, cache location,
read-only role boundaries, and event-handling convention. Feature scope enters
through a fork packet rather than mutating root instructions permanently.

The adapter SHOULD use the CLI’s native fork command where offered. It records:

| Field | Meaning |
| --- | --- |
| parent runtime session | root session that supplied context |
| vendor fork reference | opaque vendor value, if present |
| Knowledge Cache version | derived cache used for the fork |
| feature ID and role | planner or reviewer responsibility |
| Git base | immutable starting commit |
| terminal session | assigned terminal identity |

Claude planning and review output is not an authorization by itself. The adapter
must require the agent to write or emit the structured event artifact that the
orchestrator validates.

## Codex runtime profile

The Codex adapter owns codex-root and a distinct terminal for each feature
implementer fork. The root is read-only and may advise on implementation
constraints; it does not receive a write lease. The implementer receives a
worktree path, branch, writer lease token, plan artifact reference, test command
policy, and event-return convention.

A Codex implementation event MUST include:

- feature branch and exact head commit;
- expected integration base and merge-base calculation;
- changed path list and diff digest;
- test commands, outcomes, and relevant output references;
- generated files or migration declarations;
- declared unresolved risks;
- writer lease token and session identity.

The adapter MUST treat an uncommitted result as incomplete. It can send an
intermediate status event, but must not create implementation-ready evidence.

## Terminal layout

~~~text
tmux server: ai-runtime

claude-root
  window 0: Claude root CLI

codex-root
  window 0: Codex root CLI

claude-feature-feat-0042-plan
  window 0: Claude planner fork

codex-feature-feat-0042
  window 0: Codex implementer fork and feature worktree

claude-feature-feat-0042-review-1
  window 0: Claude reviewer fork
~~~

A feature session name includes its feature ID and attempt or role to prevent
ambiguous recovery. Names are runtime-generated, not trusted from agent output.

## Prompt construction

The adapter assembles a prompt from bounded sources:

| Source | Root | Feature | Review |
| --- | ---: | ---: | ---: |
| stable role contract | yes | yes | yes |
| runtime event handling convention | yes | yes | yes |
| current Knowledge Cache | yes | selected | selected |
| full prior transcript | no | no | no |
| plan artifact | no | yes | yes |
| current Git diff | no | implementation only | yes |
| writer lease | no | implementation only | no |
| review policy | no | no | yes |

Prompt content SHOULD reference files and Git ranges instead of inlining large
source trees. An adapter must make the packet available on disk under the
runtime state directory and inject only an immutable reference plus concise
instructions where possible.

## Readiness and completion

Vendor CLIs can change screen prompts. The adapter therefore uses a layered
readiness strategy:

1. successful process launch under the expected terminal session;
2. explicit adapter sentinel, structured file write, or supported CLI status;
3. bounded pane capture only as diagnostic fallback;
4. configured timeout that marks the session unavailable rather than guessing.

Likewise, task completion is proven by a structured runtime event, not by a
phrase such as “done” in terminal output. This protects against hallucinated
completion and UI variations.

## Sending an event notice

A notice says that an event exists and where its immutable envelope can be read.
It must be short enough for terminal injection and must not put secrets or large
diffs into the command line.

~~~sh
tmux send-keys -t codex-feature-feat-0042:0.0   'ai-runtime event --inbox codex-feature-feat-0042 --event evt_01J...' Enter
~~~

The invoked client validates the event reference, acknowledges receipt, and
allows the CLI to process its contents. The terminal text is transport
convenience, not the source of the event.

## Fork procedure

~~~text
function fork_feature(adapter, root, feature, role, packet):
  assert root is Ready and packet Git base is reachable
  create terminal name from adapter, feature, role, attempt
  ask adapter to create native or compatible fork
  persist vendor metadata and parent/snapshot lineage as opaque/provenance data
  validate child readiness
  create child session record
  emit session.ready and feature role assignment
~~~

If a native fork is unavailable, the adapter may start a new session with a
compact root snapshot. It MUST label this synthetic, record the cache revision,
and preserve the same feature disposal behavior. It MUST NOT imply that the
new session has an exact vendor conversational parent.

## Resume procedure

Resume exists only for a terminal loss, host reboot, or adapter crash. An
adapter first proves that its prior process cannot be used. It then attempts a
vendor resume only if a stored opaque ID is present, policy allows it, and the
resume can be verified against expected repository state. Otherwise it starts
a fresh root or feature session from a reconstruction packet.

A successful vendor resume does not bypass state validation. The runtime checks
role, lease, feature state, Git base, and policy revision before marking it
ready.

## Resume scopes

The adapter MUST report the Resume Scope and deadline assigned by runtime
policy. Root scope ends when the configured root is replaced; Planner,
Implementer, and Reviewer scopes end with their feature-role terminal state.
“Feature Resume” groups these three feature roles. A generic Worker Resume does
not exist in V2 because persistent CLI sessions are not a worker pool.

| Scope | Allowed only after | Required recovery evidence | Expiry |
| --- | --- | --- | --- |
| Root | abnormal root loss | repository identity and snapshot validity | root replacement/disable |
| Planner | abnormal feature loss | feature request and current plan state | plan terminal state |
| Implementer | abnormal feature loss | clean/handled worktree and current lease | review/cancel/cleanup |
| Reviewer | abnormal feature loss | current immutable review packet | decision/cancel/expiry |

## CLI upgrade safety

Adapter versions and detected CLI versions are recorded in session metadata.
A runtime upgrade MUST perform a compatibility check before reattaching roots.
Unknown command syntax, changed fork behavior, or ambiguous readiness results
in unavailable state, not blind command execution.

## Limitations

The specification does not assert exact Claude or Codex command syntax because
those CLIs evolve. An adapter implementation owns its tested command mappings
and exposes capability flags. This avoids requiring every document user to
modify the protocol when a vendor renames a local flag.

See [Persistent Sessions and Resume](03-persistent-sessions-resume.md) for
recovery and [tmux Runtime and Orchestrator](06-tmux-orchestrator.md) for
terminal supervision.
