# Persistent tmux Session Supervisor

## Decision

**The Session Supervisor and its integration boundary are implemented and
deterministically validated, but persistent model transport is not yet
production-ready.**

The runtime now owns durable tmux lifecycle, identity, readiness, bounded turn
delivery, acknowledgement recovery, reconstruction, and cleanup. The minimal
vertical slice no longer lets a production CLI adapter silently fall back to a
direct subprocess. Its explicit transport mode is
`tmux_supervised_noninteractive_v1`.

That mode keeps a feature-scoped runtime worker alive in a dedicated tmux
server and executes each structured model turn as a bounded non-interactive
child. It gives the runtime a persistent supervised transport and eliminates
unsupervised invocation, but it does **not** preserve interactive model context
between turns. Treating it as equivalent to a persistent Claude/Codex root
would overstate the result.

## Implemented surface

`SessionSupervisor` implements:

- `start`: records `STARTING` before launch, creates a collision-resistant tmux
  name, launches on a runtime-private socket, and fails closed on launch or
  readiness failure;
- `observe`: checks tmux presence and the runtime identity digest without using
  pane prose as workflow authority;
- `send_turn`: injects only a fixed generated turn reference and waits for a
  correlated structured spool response;
- `resume_or_reconstruct`: reattaches a verified live session, permits declared
  resume, or selects explicit synthetic reconstruction on a clean worktree;
- `terminate`: performs graceful-stop-then-kill and idempotently confirms an
  already absent terminal;
- `reconcile`: handles live reattachment, adapter drift, stale identity,
  completed-response acknowledgement windows, ambiguous in-flight requests,
  absent sessions, and termination acknowledgement loss.

The durable lifecycle is:

```text
STARTING -> READY -> BUSY -> READY
    |         |       |
    v         v       v
UNAVAILABLE / RECOVERY_REQUIRED
    |                 |
    +----> STARTING <-+

READY/BUSY/UNAVAILABLE/RECOVERY_REQUIRED
    -> TERMINATING -> TERMINATED
```

Invalid transitions are rejected. Session records contain identity and launch
digests, adapter/version, role, feature scope, lifecycle revision, timestamps,
transport mode, and bounded diagnostics. They do not contain pane captures,
prompts, stdout, stderr, or a model transcript.

## Adapter declarations and authority

| Adapter | Baseline role | Fork/recovery declaration | Structured channel | Authority |
| --- | --- | --- | --- | --- |
| Claude | production planner/reviewer default | native fork; resume declared | JSON stdout | only agent adapter allowed to declare merge authority |
| Antigravity 1.1.10 | temporary planner/review advisor | synthetic reconstruction; resume declared | JSON stdout | advisory only; `temporary=True`; exact-head human gate required |
| Codex | feature implementer | native fork; resume declared | JSONL stdout | workspace write only; no merge authority |

All three declare launch command, readiness detector, trust-prompt policy,
resume/fork behavior, structured-output channel, and termination behavior.
Antigravity-specific behavior remains isolated in its adapter: plan-mode
sandboxing, disabled CLI logging, JSON Schema adaptations, temporary embedded
review patch, and synthetic reconstruction.

Codex sessions are bound to the generated feature worktree. The supervisor
rejects a turn whose working directory differs from the registered session
scope. Existing lease fencing, protected-ref snapshots, Git-config digest,
clean-worktree checks, and Git-derived implementation evidence remain in force.

Claude remains the only adapter whose non-temporary capability document can
claim merge authority. Antigravity cannot turn an advisory verdict into
`merge.approved`; the existing human exact-head override remains mandatory and
no auto-merge path was added.

## Structured-result and acknowledgement boundary

The persistent worker receives only `TURN <generated-id>` through tmux. The
prompt, schema, and CLI command are not sent as terminal keystrokes. A
permission-restricted spool entry carries the bounded request to the worker.

After completion:

1. the supervisor checks the turn identity and prompt digest;
2. the adapter validates the task-specific structured result;
3. the coordinator appends that result and transport evidence to the Event
   Store;
4. only after durable append does it acknowledge and delete the response.

If the response exists but the event acknowledgement is missing after restart,
reconcile moves the session to `RECOVERY_REQUIRED`. A retry with the same
deterministic turn ID consumes the existing result and does not call the model
again. If Event Store already contains the turn ID, startup reconciliation
acknowledges and removes the stale spool response.

Nonzero, timed-out, or schema-invalid output is removed immediately after
retaining only hashes, byte counts, duration, exit status, and a non-content
diagnostic shape. It cannot enter Event Store as a successful structured
result.

Event Store replay remains a pure fold. It does not call an adapter, send tmux
keys, retry a prompt, or mutate Git. Repeated state replay was tested without
changing event count or session lifecycle revision.

## Recovery coverage

| Failure | Implemented response |
| --- | --- |
| runtime restart, session alive | reattach only after registry/tmux identity match |
| tmux session lost, Git clean | declared resume or explicit reconstruction |
| agent failure, worktree dirty | preserve worktree and writer lease; require recovery |
| response complete before event acknowledgement | recover same correlated result without resend |
| stale tmux identity | `RECOVERY_REQUIRED`; never trust session name alone |
| adapter version drift | fence on start and startup reconcile |
| trust prompt | accept only when adapter policy and disposable fixture both allow it |
| readiness timeout | `RECOVERY_REQUIRED`; no guessed readiness or subprocess fallback |
| terminate acknowledgement lost | terminal absence confirms idempotent termination |
| merge or cleanup acknowledgement lost | existing Git-first reconciliation remains authoritative |

Git remains the source of truth throughout. A model-declared commit is retained
as an observation and compared with the actual worktree `HEAD`; it never
selects the merge candidate.

## Privacy and evidence

No raw tmux pane or model transcript is retained by the new runtime or its v2
evidence package. Pane data used during readiness is held only in memory; the
record stores its hash and byte count when a timeout needs diagnostics.

Portable evidence:

`ai-runtime-validation/artifacts/20260803T100500Z-session-supervisor-v2/`

The package uses `ai-runtime-evidence/v2`, has a SHA-256 manifest, and records
zero live model calls. Its privacy scan confirms absence of local absolute
paths, email probes, credential patterns, and raw pane/model sentinels.

## Verification

Validated against implementation commit `37c36a2335f3c202a8bba1ab139e9ae641fa1962`:

- runtime tests: **32/32 passed**;
- deterministic tmux supervisor and lifecycle integration: passed;
- Event Store/Git/worktree/lease/review-gate/cleanup E2E: passed;
- restart, reconcile, dirty preservation, stale identity, version drift,
  trust/readiness timeout, and acknowledgement-window tests: passed;
- non-Claude merge-authority rejection: passed;
- contract validation: **82/82 assertions passed**;
- clean-clone runtime tests: **32/32 passed**;
- clean-clone contract validation: **82/82 passed**;
- v2 evidence manifest and privacy scan: passed;
- normative `docs/` diff from `ddd6ffe`: empty.

The real CLIs were discovery-probed only in this increment:

| CLI | Observed version | Model calls |
| --- | --- | ---: |
| Antigravity | 1.1.10 | 0 |
| Claude Code | 2.1.197 | 0 |
| Codex | 0.146.0 | 0 |

No normative contract conflict was found, so `docs/` was not changed. The
remaining differences are implementation gaps against the full V2 target, not
contradictions requiring a normative edit.

## Production-readiness conclusion

The lifecycle supervisor is suitable as the production implementation base for
local tmux supervision. The **persistent model transport is not production-ready**
because the integrated mode still starts a bounded non-interactive CLI child
for each turn and no persistent Claude/Codex root or native feature fork is yet
used by the vertical slice.

Before enabling the Claude production workflow, the runtime still needs:

1. a live disposable-fixture contract run for Claude 2.1.197 covering root
   readiness, trust behavior, native fork, exceptional resume, structured
   terminal-event return, and graceful stop;
2. a stable structured result/event channel independent of pane scraping for
   the persistent interactive process;
3. persistent read-only Claude and Codex root provisioning plus bounded feature
   fork packets and lineage records;
4. adapter capability revalidation bound to the deployed CLI build and an
   explicit model-inference permission;
5. a live Claude authoritative review proving that the accepted structured
   approval binds the Git-derived base/head and still passes the mechanical
   merge gate;
6. operational soak testing for memory growth, stale modal state, readiness
   drift, and controlled root replacement.

## Next increment

The next increment should implement **Persistent Root and Native Feature Fork
Transport** on top of this supervisor: provision read-only Claude/Codex roots,
deliver immutable event references through a runtime client, return validated
structured terminal events, record lineage, and validate Claude's real
authority path on a disposable repository. Durable asynchronous delivery and
changes-requested retry scheduling should follow without turning replay into
prompt resend or sessions into a generic worker pool.
