# 27 — Protocol and tmux Examples

## Purpose

This appendix provides normative-compatible examples of a feature exchange,
terminal operations, configuration, and recovery. Values are illustrative.

## Example feature flow

~~~json
{
  "type": "feature.requested",
  "aggregate": {"feature_id": "feat-0042", "stream": "feature/feat-0042", "sequence": 1},
  "payload": {
    "title": "Add lease fencing to worktree gateway",
    "target_ref": "main",
    "risk": "medium",
    "acceptance_criteria": [
      "Reject stale fencing token",
      "Expose a structured denial",
      "Add concurrent-writer test"
    ]
  }
}
~~~

Claude Planner produces a plan artifact and emits a plan-ready event. The
approved plan reference is delivered to Codex Implementer in a fork packet.
Codex commits implementation and emits implementation-ready with base/head,
tests, and diff digest. Claude Reviewer emits either findings or immutable
approval. The merger verifies and integrates exact head, then roots synchronize.

## Example terminal commands

~~~sh
# Inspect runtime sessions.
tmux -L ai-runtime list-sessions

# Create a root terminal in a controlled worktree.
tmux -L ai-runtime new-session -d -s claude-root   -c /srv/ai-runtime/integration-readonly

# Deliver a reference, never task text or a raw JSON event.
tmux -L ai-runtime send-keys -t codex-feature-0042-1:0.0   'ai-runtime event consume --session ses_codex_0042_1 --event evt_01J' Enter

# Obtain bounded diagnostics for an incident.
tmux -L ai-runtime capture-pane -p -t codex-feature-0042-1:0.0 -S -80
~~~

An implementation must execute process arguments safely rather than copy these
strings into a shell. It validates session and path values before invocation.

## Example review finding

~~~json
{
  "type": "changes.requested",
  "payload": {
    "reviewed_head": "ab12cd34...",
    "findings": [
      {
        "id": "rev-01",
        "severity": "high",
        "path": "src/git/gateway.ts",
        "summary": "Fencing token is read but not checked before commit.",
        "required_outcome": "Reject stale token at every write gateway entry point."
      }
    ],
    "requires_rereview": true
  }
}
~~~

The implementer cannot interpret this as a general prompt change. It is a
structured state transition from review back to implementation.

## Example approval

~~~json
{
  "type": "merge.approved",
  "producer": {
    "session_id": "ses_claude_review_0042_2",
    "role": "claude_reviewer",
    "adapter": "claude"
  },
  "payload": {
    "reviewed_head": "cd34ef56...",
    "reviewed_base": "091e4d9c...",
    "target_ref": "main",
    "plan_digest": "31fd...",
    "check_evidence_digest": "eac1...",
    "policy_revision": "policy-2026-07-31.1",
    "expires_at": "2026-07-31T11:24:00Z"
  }
}
~~~

## Example Knowledge Cache fact

~~~yaml
kind: concurrency
statement: "Feature worktree writes require a current fencing token."
confidence: confirmed
source:
  integration_range: "091e4d9c..de45fa67"
  commits: ["de45fa67"]
  paths: ["src/git/gateway.ts", "test/gateway.test.ts"]
  events: ["evt_merge_01J"]
~~~

## Recovery example

A host reboots after implementation-ready but before review delivery. On
startup, the runtime rebuilds projections, sees a reachable clean feature head,
sees no active writer lease, and finds a pending review delivery. It starts a
fresh Claude review fork if the prior terminal is absent, builds a review
packet from Git and structured evidence, and delivers the existing request.
It does not restart the implementer or reconstruct full conversations.

## Implementation checklist

- Validate every terminal session name and worktree path.
- Persist event before terminal notice.
- Bind approval to immutable commits and policy revision.
- Reject raw prose as workflow authority.
- Fence stale writers.
- Preserve dirty worktrees on recovery.
- Update Knowledge Cache only after integration commit.
- Keep raw prompts out of default logs.

## V2 Knowledge Evolution example

After merge completion, Knowledge Runtime records an evolution-started event
for each root, detects affected snapshot domains from the Git diff, and builds
a bounded evidence packet. The named root publishes a validated Knowledge Cache
version and emits synchronization completion. If metadata checkpoints are
enabled, the Git gateway writes only the snapshot manifest to the protected
runtime knowledge branch. The implementer/reviewer feature terminals are then
destroyed and both roots return to idle.
