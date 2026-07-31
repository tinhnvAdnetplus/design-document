# 10 — tmux Runtime and Orchestrator

## Purpose

This chapter defines the local terminal runtime, tmux naming, orchestration
loop, and constraints on terminal transport.

## Why tmux

tmux provides process persistence across terminal attachment, named sessions,
inspectable windows, server-scoped lifecycle, and a familiar operator surface.
It is appropriate for a local single-host runtime. It is not an event store,
identity provider, authorization mechanism, or distributed scheduler.

## Naming and topology

| Resource | Pattern | Example |
| --- | --- | --- |
| tmux server socket | runtime configured | ai-runtime |
| Claude root | claude-root | claude-root |
| Codex root | codex-root | codex-root |
| planner | claude-feature-feature-role-attempt | claude-feature-0042-plan-1 |
| implementer | codex-feature-feature-attempt | codex-feature-0042-1 |
| reviewer | claude-feature-feature-review-attempt | claude-feature-0042-review-1 |
| diagnostics | runtime-diagnostics | runtime-diagnostics |

Names use a restricted generated alphabet. Feature text never enters a shell
command as a raw terminal name.

## Session creation

~~~sh
tmux -L ai-runtime new-session -d -s claude-root -c /srv/repo/main
tmux -L ai-runtime new-session -d -s codex-feature-0042-1 -c /srv/worktrees/0042
tmux -L ai-runtime has-session -t claude-root
tmux -L ai-runtime list-sessions -F '#{session_name} #{session_created}'
~~~

The examples are illustrative. A production adapter invokes commands without a
shell where possible, validates names and paths, uses a controlled environment,
and records exit status.

## Event notification

The orchestrator persists the event before notifying a terminal. A terminal
receives a short command referring to the immutable event record.

~~~sh
tmux -L ai-runtime send-keys -t codex-feature-0042-1:0.0   'ai-runtime event consume --session ses_01J --event evt_01J' Enter
~~~

The invoked runtime client writes an acknowledgement record. It does not trust
the event identifier from keyboard input without checking session identity and
authorization.

## Orchestration loop

~~~text
while runtime is running:
  reconcile terminal and lease observations on schedule
  accept and validate submitted events
  append event before deriving command intents
  select pending delivery whose target is available
  invoke adapter notify without waiting for task completion
  record delivery result and backoff where required
  execute eligible deterministic Git or cleanup command intents
  project new evidence and publish metrics
~~~

The loop may be event-driven internally. It MUST NOT require polling agent
terminals for workflow state. Health reconciliation is allowed on a bounded
schedule because it observes process liveness, not agent conversation.

## send-keys safety

Terminal injection is risky because shell prompts, modal CLI state, and
unexpected terminal content can change how input is interpreted. Adapters MUST:

1. send only generated fixed-form commands;
2. validate all identifier and path components against strict patterns;
3. avoid interpolating user task text into terminal commands;
4. send payload through the event store or file reference, not keypresses;
5. use a dedicated working directory and runtime client executable;
6. cap retries and capture only bounded diagnostics;
7. stop notification after ambiguous terminal state and mark unavailable.

## Supervision

The orchestrator checks tmux session existence, process launch status, optional
adapter heartbeat, working directory, and session record consistency. It does
not inspect normal conversation text to infer activity.

| Observation | Meaning | Response |
| --- | --- | --- |
| tmux session present, adapter ready | available | deliver eligible notices |
| tmux session present, no readiness | starting/busy/ambiguous | wait or deadline |
| tmux session absent | unavailable | reconcile and recover |
| working directory mismatch | potential compromise | revoke lease and block |
| runtime client ack missing | delivery retry | backoff then escalate |
| pane capture has secret marker | diagnostic risk | redact and restrict access |

## Orchestrator command intents

External side effects are represented as persisted intents.

| Intent | Preconditions | Confirmation |
| --- | --- | --- |
| start-session | configuration and unique name | session.ready |
| notify-session | accepted target event | delivery accepted/ack |
| create-worktree | feature branch and no collision | worktree.created |
| grant-lease | session ready and policy allowed | lease.granted |
| merge | valid approval and integration lock | merge.completed |
| terminate-session | terminal feature state | session.terminated |
| synchronize-root | reachable integration commit | knowledge.synchronized |

An intent can be safely retried only if its execution is idempotent or its
confirmation query is deterministic. The merger checks Git ancestry before
repeating a merge; it never submits the same merge blindly.

## Operator commands

~~~sh
ai-runtime status
ai-runtime feature show feat-0042
ai-runtime session list
ai-runtime event tail --feature feat-0042
ai-runtime reconcile --dry-run
ai-runtime recover --session ses_01J
~~~

Operator commands SHOULD default to read-only. Mutating actions require an
explicit confirmation, recorded operator identity, and policy authorization.

## Limitations and future direction

A local tmux server shares one host failure domain and one Unix-account trust
boundary. Remote workers will require authenticated transport, remote
supervision, distributed lease fencing, and a durable multi-writer event store.
The protocol intentionally does not depend on tmux so that replacement remains
possible.

