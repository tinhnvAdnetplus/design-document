# Design

## Safety boundary

- Hard cap of **30 authenticated model calls** for the whole increment, enforced
  by `Budget.spend`, which raises before the 31st call and logs a running count.
- Cheapest viable configuration: Claude `--model haiku`, Codex
  `--model gpt-5.4-mini` with `model_reasoning_effort="low"`.
- Every live subprocess is bounded by `PROBE_TURN_TIMEOUT_SECONDS` (default 180).
- All live work runs against a disposable Git repository under a temporary
  directory. The probe never touches this repository or any real project.
- Claude root and probe turns run `--permission-mode plan`; the G5 feature
  session needs `acceptEdits` because the protocol under test requires the model
  to write one file into the runtime state directory, which is itself inside the
  disposable fixture.
- Codex root runs `--sandbox read-only`; the Codex implementer turn runs
  `--sandbox workspace-write` bound to the generated feature worktree, exactly as
  `CodexCLIAdapter._command()` declares.
- Interactive workspace trust is accepted only for the disposable fixture, via
  `TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY` with `disposable=True`. The
  declared production behaviour (`REJECT`) is recorded unchanged.
- Raw prompts, pane captures, stdout, stderr, and model transcripts are never
  persisted. Evidence retains digests, byte counts, timings, exit status,
  booleans, and one redacted detector-matching pane line per session capped at
  200 characters.

## Fixture layout

```text
$FIXTURE/                       mktemp -d, prefix airv-live-persistent-, 0700
├── repo/                       disposable Git repo, branch main, one commit
│   ├── README.md
│   └── src/module.py
├── runtime-state/              SessionSupervisor state_dir per gate
│   ├── g1-supervised/ g2-claude/ g2-codex/ q1-codex/ g5-claude/
│   └── <state>/terminal-events/<session>/{inbox,outbox,acks,diagnostics}
└── worktrees/probe/            generated feature worktree for the Codex writer
```

`git config user.email probe@example.invalid` is repository-local and redacted in
every artifact. tmux runs on the supervisor's own derived socket and the server
is killed in a `finally` block for every gate.

## Gate sequence

```text
G1 direct argv ──┬─ claude plan ── claude review
                 └─ codex implement (seeds the Codex nonce/session)
G1 supervised ──── claude plan through SessionSupervisor + _session_worker
G2 ──────────────┬─ claude root readiness/identity/child-survival
                 └─ codex root readiness/identity/child-survival
G3/G4/G6 ───────── root seed (--session-id) ── fork a ── fork b ── fresh baseline
                                             └─ resume forked child (nonce)
Q1 ─────────────── codex fork <parent> in tmux ── codex exec resume <forked>
G5 ─────────────── claude feature session ── EVENT ref-<id> ── outbox collect
```

G1 runs before Q1 because Q1 forks the session that the Codex implementer turn
creates. G2 runs before G5 so the fixture's workspace trust is already recorded
and the feature session is not blocked by a dialog the feature detector does not
watch for.

## Why the argv is invoked directly and once through the supervisor

The brief requires the exact argv `_command()` builds today. The supervised path
hardens away the very data three gates need: `_session_worker` persists only a
validated structured candidate plus output metrics, so vendor `session_id` and
`usage` are gone by the time the adapter sees the turn. The probe therefore runs
each role's argv directly to observe the raw contract, and additionally runs one
Claude plan turn through `SessionSupervisor` to prove the transport still works
against a live CLI. Both results are recorded separately.

## Structured-shape tracing

`_extract_structured` digs through nesting, JSON-in-string, and code fences. The
probe re-implements that walk with path tracking (`trace_structured`) and records
where the required-key object was found, at what depth, and whether a JSON-string
decode or a fence strip was needed. A parser compensating for an unstable vendor
contract is a finding, not a convenience.

## Session-identifier binding

`FeatureSessionFactory._feature_values()` renders `{parent_session_id}` as the
runtime registry session ID, so a fork template naming a vendor UUID would not
render. The probe evaluates the candidate answer: derive the vendor identifier
from data the runtime already owns,

```text
uuid5(runtime_namespace, "<adapter>|<runtime_session_id>|<root_generation>")
```

launch the root with Claude's `--session-id <uuid>`, and render the same value
into the fork/resume template. Nothing is discovered from vendor state and no new
persisted field is required. The Codex equivalent is searched for and, if absent,
recorded as absent.

## Root immutability

Native fork is only useful if the child does not advance the parent. Claude
stores a session as `~/.claude/projects/<slug>/<session-id>.jsonl` and Codex as
`~/.codex/sessions/<date>/rollout-*-<uuid>.jsonl`. The probe digests the parent
file before and after each child turn. A fork that changes the parent digest is a
failed gate, not a partial pass. Only files whose names contain a session
identifier the probe itself created are ever read or removed.

## Interactive gates and diagnostic markers

Three mechanisms were added during the run, each because an iteration produced a
bare `session readiness timed out` that explained nothing. All three cost no
model quota, which is why three consecutive corrections were affordable.

- **`failure_markers`** records, on any readiness failure, a bounded allowlist of
  session-shaped lines (`MARKER_PATTERNS`), each redacted and capped at 200
  characters, plus `pane_dead` and per-pattern match booleans. A raw pane capture
  is still never retained; without the matching line a detector cannot be bound
  to reality, which is what the increment exists to do.
- **`clear_interactive_gates`** launches a throwaway session, dismisses recognised
  one-time gates (`INTERACTIVE_GATES`) for the disposable fixture only, records
  each dismissal verbatim together with whether the adapter's declared trust
  pattern could see it, and kills the session. `_wait_ready` can only act on a
  gate its declared `trust_pattern` matches; anything else is invisible to it.
- **`stdin=subprocess.DEVNULL`** on every live invocation. `codex exec` prints
  `Reading additional input from stdin...` and blocks until EOF when it inherits
  an open stdin, which one iteration observed as a 210-second timeout instead of
  a turn.

G2 therefore runs two recorded variants per adapter so they are never conflated:
the **declared production path** keeps `TrustPromptBehavior.REJECT`, where a
fresh fixture correctly fails closed at a trust dialog; the readiness measurement
then runs on the disposable-authorized path. Trust is an operational
precondition, not something the declaration may answer for itself.

## Candidate-pattern trials

Recording *why* a detector failed is not enough to choose a replacement, and the
wrong way to choose one is to read the vendor's rendering and write a regex that
looks right. Each candidate is instead evaluated against two live panes and
recorded as match/no-match with the redacted line that matched:

- the **settled idle pane**, which a readiness pattern must match;
- the **trust-dialog pane**, which it must **not** match.

The second requirement is not hypothetical. `_wait_ready` evaluates readiness
against the same capture in which it has just answered a trust prompt, so a
pattern that fires on the dialog reports `READY` while the dialog is still up. The
trials rejected the most obvious Claude candidate on exactly that basis:
`^\s*[❯>](?:\s|$)` matched the idle prompt *and* `❯ 1. Yes, I trust this folder`.

`READY_PATTERN_TRIALS` is keyed by adapter and `TRUST_PATTERN_TRIALS` is shared.
Trials are recorded in three places: on the pane that still shows a one-time gate,
on the settled pane after every known gate is cleared, and on any pane where a
declared detector timed out. A declaration change then cites a recorded match
rather than a reading.

## Negative evidence

Every failed attempt is retained through `record_iteration` with its correction,
following `poc/11-real-cli-integration/ISSUES.md`. An integration mistake is
never relabelled as a vendor incompatibility. Two conclusions from the first full
run were withdrawn on that basis and are documented as withdrawn in
[ISSUES.md](ISSUES.md): a confounded Codex root pass, and a Q1 "no forked session"
finding that was the probe's own snapshot defect.
