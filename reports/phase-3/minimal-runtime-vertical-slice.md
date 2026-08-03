# Minimal Runtime Vertical Slice

## Decision

**Implemented and validated with documented Antigravity adaptations.** The
slice is suitable as the next production implementation baseline, but it is not
the complete multi-agent runtime.

Claude CLI is the production planner/reviewer default. The Antigravity adapter
is temporary, version-bound, advisory-only, and cannot emit an authoritative
merge approval. Codex remains the only baseline implementation adapter.

## Implemented path

```text
feature.requested
  -> structured plan -> human plan approval
  -> isolated worktree + fenced writer lease
  -> Codex change + Git commit -> implementation.ready
  -> read-only review
  -> Claude approval OR Antigravity recommendation + human exact-head approval
  -> merge preflight -> merge -> merge.completed -> safe worktree cleanup
```

The runtime includes:

- a vendor-neutral adapter contract and version-bound Claude, Antigravity, and
  Codex subprocess adapters;
- strict structured plan, implementation, and review result validation;
- append-only Event Store integration and a pure replay projection;
- isolated branch/worktree creation beneath a generated safe feature path;
- file-backed exclusive writer leases with monotonic fencing tokens;
- Git-derived base, head, changed paths, and diff digest evidence;
- protected branch/tag snapshots around Codex execution;
- exact reviewed-head/base approval binding and merge conflict preflight;
- explicit implementation and merge reconciliation entry points;
- a CLI with separate request, plan approval, temporary review approval,
  merge, status, and reconciliation commands.

## Claude-first authority model

The runtime rejects any non-Claude adapter that declares agent merge authority.
With the default profile, a valid Claude review may emit `merge.approved`. With
the temporary Antigravity profile, an `approve` result is stored as an advisory
`implementation.progress` observation. The feature remains at
`AWAITING_HUMAN_APPROVAL` until a maintainer explicitly binds approval to the
exact implementation head. The temporary override is disabled by default.

This prevents the current `agy` substitution from silently changing the frozen
Claude/Codex governance model.

## Recovery behavior

Replay only folds durable events; it never invokes a model or performs a Git
operation. The runtime fails closed in the following ambiguity windows:

- dirty worktree after an implementer exits: preserve worktree and lease;
- clean commit without `implementation.ready`: require explicit maintainer
  reconciliation;
- adapter name/version drift: stop before invoking the changed adapter;
- protected ref change during implementation: require repository inspection;
- base/head drift or merge conflict: stop before `merge.started`;
- merge completed before event acknowledgement: inspect clean Git ancestry,
  append a reconciled `merge.completed`, then clean up.

## Automated verification

The deterministic suite contains 21 runtime/Event Store tests. It covers the
complete advisory and Claude-authoritative paths, pure replay, dirty-worktree
preservation, lease conflicts, adapter drift, forged merge authority, stale
head/base binding, model-declared commit mismatch, commit/event reconciliation,
and merge/event reconciliation.

Run it with:

```bash
PYTHONPATH=src python3 -m unittest discover -v
```

## Live CLI observations — 2026-08-03

Tested in disposable repositories with no project content or secrets:

| Component | Observed version | Result |
| --- | --- | --- |
| Antigravity | `1.1.10` | Structured planning passed; bounded patch review passed after adapter adaptations. |
| Codex | `codex-cli 0.146.0` | Workspace write and native Git commit passed. |
| Claude Code | `2.1.197` | Adapter discovery/command contract implemented; not invoked because this phase was explicitly run with Antigravity. |

The full Antigravity/Codex fixture completed with 11 correlated events:

- base `18a31b2f143b376492473e243e652584169c18ba`;
- reviewed head `366a4fb76b8d337d0c187e60c249be1bd58fe4b6`;
- merge head `fcabb5891a3d74abd0929f17ed612a35a43061cf`;
- Antigravity review remained advisory;
- human approval bound the exact reviewed head;
- feature worktree and branch were removed only after a clean merge.

That first live fixture exercised the explicit reconciliation path because
Codex wrote the correct file but did not commit before returning. A follow-up
Codex probe proved the linked-worktree permission adaptation: Codex produced a
clean native commit and the runtime reached `AWAITING_HUMAN_APPROVAL` with
`reconciled=false`.

Codex also returned a non-existent commit hash in its structured narrative on
two probes. The runtime correctly treats this field as an observation and binds
`implementation.ready` to the actual verified Git HEAD, recording
`declared_commit_matches=false`. This is a concrete validation of the Git-first
source-of-truth invariant.

Antigravity 1.1.10 required two additional temporary adaptations:

1. review receives a runtime-generated, digest-bound patch capped at 64 KiB and
   is instructed not to use tools; otherwise print-mode may return a successful
   but empty response after attempting Git access;
2. the verdict schema uses a string plus runtime enum validation, and the prompt
   states the two exact tokens; its structured-output implementation was not
   reliable with the enum expressed directly in JSON Schema.

No raw model transcript is retained. Runtime evidence stores structured bounded
results, output hashes/byte counts, durations, versions, and prompt hashes.

## Deliberate non-goals

This slice does not yet implement the full scheduler, long-lived knowledge
evolution, distributed locks, multi-host operation, autonomous merge, or GUI.
The adapter calls are bounded non-interactive CLI invocations; persistent tmux
session supervision remains the next integration increment, building on the
already-approved PoC 11 transport evidence.

## Next increment

The next implementation checkpoint should replace bounded subprocess calls with
the persistent session supervisor while preserving the adapter/result contract,
then add changes-requested retry/replan and durable delivery scheduling. Claude
CLI should be exercised on a disposable fixture before enabling its
merge-authority profile outside validation.
