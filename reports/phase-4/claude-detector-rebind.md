# Claude Detector Rebind and the Session-Worker Stdin Contract

Increment scope: the first two items of the next-increment list in
[`live-persistent-adapter-contract.md`](live-persistent-adapter-contract.md).
Everything else on that list is unchanged and is specified for execution at the
end of this report.

## Decision

Two changes, both earned:

1. `src/ai_runtime/runtime/_session_worker.py` no longer hands its tmux pane to
   the model child. The defect is now covered by a regression test that fails
   without the fix.
2. `claude.persistent_root` is promoted to `CapabilityValidation.VALIDATED` with
   `validation_provenance_sha256 =`
   `9281bf459ab9f5e4631c3f7984795f4426cfc5861b5eb014ea6714c38b337f6b`, after the
   Claude readiness and trust detectors were rebound to what CLI 2.1.222 actually
   renders and G2 was re-run to a pass on the declared production path.

Every other capability field on every adapter stays `FAIL_CLOSED`, each for a
reason stated below. **This increment spent 0 live model calls.** Both G2 runs are
readiness measurements: they launch the vendor CLIs and watch their panes, and
never send a turn.

Consequence for the persistent architecture: Claude now has a complete chain of
*vendor* primitives — persistent root, native fork, resume, and a measured cache
read — and one missing piece of *runtime* plumbing, the session-identifier
binding that would let the fork and resume templates render. That is the next
increment, and it is now the only thing between this design and an end-to-end
persistent root for the planner/reviewer role.

## Step 1 — the session-worker stdin contract

`_session_worker` reads its `TURN <id>` notices from `sys.stdin`, which is the
tmux pane the supervisor drives with `send-keys`. It launched every turn with
`subprocess.run(...)` and no `stdin` argument, so the model child inherited that
same pane.

The fix is `stdin=subprocess.DEVNULL` on that call. The value of the increment is
the test, not the keyword.

`tests/runtime/test_session_supervisor.py::test_turn_child_never_inherits_the_worker_pane_stdin`
runs a real supervised session and sends a turn whose command reads all of stdin
and reports what it saw. It asserts four things:

- the turn did not time out;
- it exited 0;
- the child observed `{"stdin_bytes": 0, "stdin_isatty": false}` — immediate EOF
  on something that is not a terminal;
- a *subsequent* turn still completes without reconciliation, so the worker still
  owns the pane.

Against the unfixed worker the test fails in **10.4 s** with `timed_out: True`:
the child blocked on a tty that never sends EOF, exactly as the live Codex turn
did for 210 s during the previous increment. Against the fixed worker it passes
in **0.43 s**. A hang that was previously only reproducible by spending model
quota is now a deterministic 0.4-second assertion.

The second half of the assertion matters as much as the first. Two processes
reading one pane is not only a hang risk: a model child that wins the read
consumes a `TURN <id>` notice intended for the worker, and the supervisor then
waits out its deadline on a turn that will never be answered. The follow-up turn
in the test is what pins that property.

## Step 2 — rebinding the Claude detectors

### Method: candidate patterns are trialled against live panes, not chosen by eye

The previous increment proved that the declared Claude detectors do not match
2.1.222, and recorded the marker lines that explain why. It did not record enough
of the pane to *choose* a replacement, and the honest way to choose one is not to
read the vendor's rendering and write a regex that looks right.

The probe therefore gained a **candidate-pattern trial table**. Each candidate is
evaluated against two live panes — the workspace-trust dialog and the settled
idle prompt — and the result is recorded as match/no-match together with the
redacted line that matched. Two properties are required of a readiness pattern,
and the two panes measure exactly one each:

- it must match the idle prompt;
- it must **not** match the trust dialog.

The second is not hypothetical. `SessionSupervisor._wait_ready` evaluates
readiness against the same pane capture in which it has just answered a trust
prompt, so a readiness pattern that fires on the dialog reports `READY` while the
dialog is still up, and the session is then driven in a state the runtime has
misread.

### Recorded trials — readiness

Claude 2.1.222, `ai-runtime-validation/poc/12-live-persistent-contract/artifacts/`
`20260805T172349Z-34303d`:

| candidate | idle prompt | trust dialog | verdict |
| --- | --- | --- | --- |
| `(?:^\|\n).*?[❯>]\s*$` (declared) | no | no | matched nothing; the glyph is never last on its line |
| `^\s*[❯>](?:\s\|$)` | yes | **yes** | **rejected** — matched `❯ 1. Yes, I trust this folder` |
| `^\s*[❯>]\s+(?!\d+\.)\S` | yes | no | **chosen** |
| `^\s*[❯>]\s+Try\s` | yes | no | viable; depends on the rotating placeholder hint |
| `(?i)\(shift\+tab to cycle\)` | yes | no | viable alternate, footer-based |
| `(?i)plan mode on` | yes | no | viable but couples readiness to the permission mode |

The obvious pattern is the rejected one. Without the trust-pane column it would
have looked like the best of the three matches.

`^\s*[❯>]\s+(?!\d+\.)\S` was chosen over the two footer candidates because the
prompt box is the input surface the transport actually depends on, and over
`Try\s` because the placeholder hint is content: it rotates between renders and
disappears the moment anything is typed. The three recorded idle panes show three
different hints — `Try "how do I log an error?"`, `Try "edit <filepath> to..."`,
and `Try "refactor <filepath>"` — which is itself the evidence that the chosen
pattern does not depend on hint text.

### Recorded trials — trust

| candidate | trust dialog | verdict |
| --- | --- | --- |
| `Do you trust the contents` (declared) | no | never observed on any Claude version |
| `(?i)do you trust` | no | the phrase is absent from the dialog entirely |
| `Yes, I trust this folder` | yes | **chosen** |
| `^\s*[❯>]?\s*1\.\s*Yes\b` | yes | viable but would match any first-option-yes dialog |

The broad `(?i)do you trust` candidate failing is the useful result: the declared
pattern was not merely too narrow, it was describing a dialog Claude does not
render. It came into the declaration without evidence, which is the failure mode
the trial table exists to prevent.

### G2 after the rebind

Both adapters pass. Decision `LIVE_CONTRACT_ESTABLISHED`, 0 live model calls.

| observation | Claude 2.1.222 | Codex 0.146.1 |
| --- | --- | --- |
| declared production path | `READY`, not fail-closed | `READY`, not fail-closed |
| readiness line (redacted) | `❯ Try "refactor <filepath>"` | `│ model:     gpt-5.4-mini medium   /model to change  │` |
| identity stable | 6/6 samples over 12 s | 6/6 samples over 12 s |
| root survived child termination | yes, `READY` after | yes, `READY` after |
| declared trust pattern saw its own dialog | yes (was no) | yes |

Trust remains an operational precondition on both adapters. The declaration
rejects the prompt rather than answering it; the disposable fixture authorizes it
explicitly. What changed is that the prompt is now *visible* to the supervisor,
so an untrusted directory fails closed with a trust diagnostic instead of an
uninformative readiness timeout. That is a real operational improvement
independent of the promotion: the previous behaviour told an operator nothing.

### A newly reachable branch, so it gets a test

Making the trust pattern match its dialog activates the
`TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY` path in `_wait_ready` for Claude for
the first time. Activating an untested branch is the thing this increment is
supposed to stop doing, so
`test_trust_prompt_is_answered_only_for_an_authorized_disposable_fixture` covers
both halves: an authorized disposable spec reaches `READY` through the answered
prompt, and the same spec with `disposable=False` fails closed with
`trust prompt requires an authorized disposable fixture`.

`test_claude_readiness_pattern_cannot_fire_on_its_own_trust_dialog` pins the two
recorded panes as literals and asserts the three properties the trials
established. It exists so that a later simplification of the negative lookahead
fails a test instead of silently reintroducing the premature-`READY` bug.

## What was promoted, and what was not

| adapter | field | before | after | why |
| --- | --- | --- | --- | --- |
| claude | `persistent_root` | fail-closed | **validated** | declared production path reached `READY` on the observed prompt line; identity stable 6/6 over 12 s; root survived child termination |
| claude | `native_fork` | fail-closed | fail-closed | vendor primitive validated, but `native_fork_command` is `None`; nothing renders it |
| claude | `resume` | fail-closed | fail-closed | same — `resume_command` is `None` |
| claude | `structured_terminal_events` | fail-closed | fail-closed | the readiness marker is carried inside the launch prompt that asks for it |
| codex | all four | unchanged | unchanged | `persistent_root` stays validated on its own package; G2 re-passed with no regression |
| antigravity | all four | unchanged | unchanged | out of scope |

`native_fork` and `resume` are the interesting pair. Both were validated at the
vendor boundary in the previous increment, and the detector defect that was the
*other* blocker is now gone. What remains is one piece of runtime plumbing: the
fork and resume templates cannot render because the runtime has no vendor session
identifier to substitute. That is step 4a below, it has a proven mechanism, and
it is small.

## A provenance-field conflict that had to be resolved

`PersistentAdapterDeclaration` has one `validation_provenance_sha256`, and two
different invariants require it: a validated capability field, and
`merge_authority`. While every Claude capability field was fail-closed the value
was unconstrained, so the declaration carried the *merge-authority* digest passed
to `ClaudeCLIAdapter(authority_validation_sha256=...)`.

A validated `persistent_root` pins that field to the evidence that earned it, so
it now carries the rebind package digest unconditionally. Those are two different
claims and one digest cannot honestly cover both.

The consequence is stated plainly rather than hidden: when
`merge_authority=True`, the authority digest is still validated for shape at
construction and is then **no longer persisted anywhere**. Before this change its
only persistence was the field it has now lost. Nothing in the runtime grants
merge authority today — the combination is exercised only in tests, and
`reports/phase-3/persistent-root-native-fork.md` already requires soak and
controlled-replacement coverage before authority is considered — so this is a
traceability gap, not a live one. Closing it means giving authority its own
field, which is a schema change with contract-validation consequences and belongs
in the increment that actually takes up authority. It is listed as step 6.

## Evidence

A **new** package, `artifacts/consolidated-claude-detector-rebind/`, rather than a
regeneration of the existing one. The existing package's digest
(`db6a6b4f…`) is pinned in `adapters/cli.py` as Codex's provenance, and
regenerating it to add iterations would invalidate that pin. The new package
names the old one in `depends_on`, with the reason, so the full G2 lineage stays
traceable without copying iterations or counting their live calls twice.

`consolidate_evidence.py` now refuses to overwrite an existing package unless
`--force` is passed, for exactly that reason. It was verified by running it: the
default name is refused, the new name builds, and
`sha256sum consolidated-live-persistent-contract/manifest.sha256` still reports
`db6a6b4f…`.

| run | role | live calls |
| --- | --- | ---: |
| `20260805T171837Z-bc92cc` | G2 with candidate trials; declared Claude detectors still failed | 0 |
| `20260805T172349Z-34303d` | G2 authoritative after the rebind; both adapters `READY` | 0 |

Privacy checks passed on both: no home path, no repository path, no fixture
email, no raw stdout or pane field. The `retained_pane_data` statement in the
evidence was corrected — it described only the readiness line and understated the
diagnostic allowlist, which retains up to 16 redacted lines when a detector
fails. Fixtures were clean after both runs and every tmux server was removed.

## Non-changes

The bounded review loop, merge binding and authority, lease fencing, worktree
isolation, Git-first truth, protected-ref snapshots, replay purity, exact-head
approval, and the fork abstraction are unchanged. No Knowledge Cache, durable
delivery scheduler, concurrent feature support, `abandon`, or `replan`. No frozen
artifact, `phase3-artifacts/` file, or `ai-runtime-validation/lib/validation_lab.py`
was modified. Codex's declaration is untouched apart from re-verification.

## Verification

- live model calls: **0**;
- `python3 -m unittest discover -s tests`: **55 passed** (52 before, plus the
  three added here);
- `ai-runtime-validation/ci.sh 01 02 03 04 05 06 07 08 10`: **73/73 assertions**;
- `ruff check`, `ruff format --check`, `mypy`: clean across `src`, `tests`,
  `benchmarks`;
- `verify-evidence.sh` on the new package: **PASS**;
- `consolidated-live-persistent-contract/manifest.sha256` digest unchanged at
  `db6a6b4f…`;
- the regression test was confirmed to fail before the fix (10.4 s, `timed_out`)
  and pass after it (0.43 s).

## Next increment — specification

Steps 3 to 6, in dependency order. Quota estimates assume the same cheapest
configuration: Claude `--model haiku`, Codex `--model gpt-5.4-mini` with
`model_reasoning_effort="low"`.

### Step 3 — a feature-readiness marker the launch prompt does not contain

**Blocks:** `structured_terminal_events` on every adapter.

The channel works. G5 proved a live CLI resolves an `EVENT ref-<id>` notice under
its bound inbox and returns an identity- and digest-correlated structured event
that the runtime durably acknowledges. The defect is readiness: the feature
session is launched with a bootstrap prompt *in its argv*, and that prompt
contains the literal marker and the substituted identity. The declared detector
`^AI_RUNTIME_EVENT_READY {session_identity}$` did not match because the TUI
prefixes assistant output; the unanchored form did match — but it can be
satisfied by the echoed instruction rather than the model's reply, so readiness
would be false.

Do **not** fix this by relaxing the anchor. Fix it by removing the marker from
everything the pane can echo:

1. Write the bootstrap prompt to
   `<state_dir>/terminal-events/<session>/bootstrap.json`, mode `0600`, through
   the same atomic-replace helper the spool uses.
2. Launch the feature session with an argv that names only that **path**. Nothing
   in the launch command then contains the marker.
3. Keep the anchored detector exactly as declared.

Acceptance criteria:

- the feature session reaches readiness under the **anchored** detector;
- the probe records `marker_present_in_pane_before_reply: false`, sampled after
  launch and before the model's first output — this is the assertion that makes
  the fix meaningful rather than incidental;
- G5 delivery and durable ack still pass, `raw_output_retained` stays `false`;
- a unit test asserts the launch argv contains neither the marker literal nor the
  session identity.

Cost: 2–4 live calls. Trap: the model must be able to read that path under the
session's sandbox — with `--permission-mode plan` a read is allowed, but confirm
it rather than assume it, and keep the file inside the state directory the session
is already scoped to.

### Step 4a — bind a vendor session identifier for Claude

**Blocks:** `claude.native_fork`, `claude.resume`. This is the highest-leverage
item on the list: it is the last piece of plumbing between the design and an
end-to-end native-fork persistent root, and the vendor half is already validated.

`FeatureSessionFactory._feature_values()` renders `{parent_session_id}` as the
runtime registry session ID, not a vendor UUID, so a fork template naming a vendor
session would not render. The probe validated the answer: derive the identifier
from data the runtime already owns, and tell the vendor to use it.

In `src/ai_runtime/runtime/feature_sessions.py`:

```python
VENDOR_SESSION_NAMESPACE = uuid.UUID("9f2c1d54-6b3a-5f7e-9c48-1a2b3c4d5e6f")


def vendor_session_id(adapter: str, runtime_session_id: str, root_generation: int = 0) -> str:
    """Vendor-facing UUID derived only from data the runtime already owns."""
    return str(
        uuid.uuid5(
            VENDOR_SESSION_NAMESPACE,
            f"{adapter}|{runtime_session_id}|{root_generation}",
        )
    )
```

Then one key each into the placeholder maps: `vendor_session_id` in `_root_spec`,
and `parent_vendor_session_id` in `_feature_values`. Nothing is discovered from
vendor state and no new persisted field is required.

In `ClaudeCLIAdapter`, the root launch command gains
`"--session-id", "{vendor_session_id}"`, and the two mappings become renderable:

```python
native_fork_command=(
    self.path, "--resume", "{parent_vendor_session_id}", "--fork-session",
    "--session-id", "{vendor_session_id}", ...,
),
resume_command=(self.path, "--resume", "{vendor_session_id}", ...),
```

Then re-run G3 and G4 **through the supervisor**, not only against raw argv. The
previous increment measured them as direct invocations; promotion needs the forked
child to reach declared readiness under `SessionSupervisor` and the root
transcript to stay byte-identical across the child's turn.

Acceptance criteria:

- root launches with the derived `--session-id` and reaches `READY`;
- a forked feature session reaches `READY` under the supervisor;
- the root transcript digest is unchanged before and after the child's turn — a
  fork that advances the parent is a failed gate, not a partial pass;
- resume of a killed root recalls a nonce seeded before the kill, and
  `recovery_kind` records `resume` rather than `synthetic_reconstruction`;
- only then promote `native_fork` and `resume`, with a new evidence package.

Cost: 4–6 live calls. Three traps, all avoidable:

- **Declaration digest churn.** Changing the root launch command changes
  `declaration_revision` and `digest`, and `CapabilityRegistry.register` rejects a
  changed declaration for a running adapter by design. This is a restart, not a
  hot reload. Say so in the report rather than working around the registry.
- **`--session-id` is not idempotent.** Passing it for a session the vendor
  already knows is an error. The first start assigns it; every later attach must
  go through `--resume`. `resume_or_reconstruct` is the right place for that
  branch, and it needs its own test.
- **G2 must be re-run.** The root launch command changes, so the previous
  readiness measurement no longer describes the command being launched.

### Step 4b — decide the Codex identifier question

**Blocks:** `codex.native_fork`, `codex.resume`. This needs a decision, not more
evidence. The capability is proven; only the binding is missing.

*Design A — persist the observed vendor identifier.* `codex exec --json` emits a
session id on its first event. `SessionRecord` would gain
`vendor_session_id: str | None`, populated from a declared, version-bound field
that `_session_worker` persists alongside the structured candidate. This gets you
fork-by-parent, but not the child: `codex fork` is a TUI, and the forked session's
id was only discoverable from the rollout **filename**. The probe called that out
as acceptable for a probe and not a runtime mechanism, and that judgement should
hold — a runtime that reads vendor rollout filenames has taken a dependency it
cannot verify.

*Design B — accept synthetic fork for Codex.* Keep `ForkCapability.SYNTHETIC` and
record the reason in the declaration.

**Recommendation: B.** The measured cache economics are what justify native fork,
and they apply to a long-lived root with a large shared prefix — the
planner/reviewer role, which is Claude. Codex is the implementer: it gets a fresh
worktree per feature and has little root context to inherit, so native fork buys
least exactly where the binding is hardest. Choosing B costs nothing that was
measured and removes an unverifiable dependency from the roadmap.

If A is chosen anyway, the blocking requirement is on the vendor, not on this
codebase: Codex must expose the forked session identifier on a machine-readable
channel. Until it does, the field stays fail-closed regardless of implementation
effort.

### Step 5 — read the declared structured-output channel

**Blocks:** nothing, but it removes a silent dependency, and silent is the
problem.

`_extract_structured` walks nesting, JSON-in-string, and code fences to find the
required-key object. That walk is compensation for an unstable vendor contract,
and it succeeds quietly, so a vendor changing its envelope degrades the runtime
without any signal.

Claude already emits a first-class `structured_output` object —
`_shape_diagnostic` inspects it today purely for error messages. Prefer it:

1. If the root JSON has a `structured_output` mapping, validate that and return.
2. Only fall back to the walk when it is absent, and when the fallback fires,
   record `structured_extraction_fallback: true` in the turn evidence.
3. Record the Codex `agent_message.text` decode as a version-bound dependency on
   the declaration rather than as parser behaviour.

Acceptance criteria: unit tests over recorded envelope shapes for both adapters;
the fallback flag present in evidence and asserted; no change in what the adapter
returns for a well-formed envelope. Cost: 0–2 live calls — this can be built from
recorded shapes, with an optional 2 calls to confirm against live envelopes.

### Step 6 — separate authority provenance from capability provenance

Give merge authority its own field on `PersistentAdapterDeclaration` so a
declaration can carry both claims, and restore the authority digest that this
increment dropped. Fold it into the increment that actually takes up merge
authority, which per `reports/phase-3/persistent-root-native-fork.md` still needs
soak and controlled-replacement coverage first. Cost: 0 live calls.

### Order and budget

| step | blocks | live calls | note |
| --- | --- | ---: | --- |
| 4a Claude identifier binding | `native_fork`, `resume` | 4–6 | highest leverage; vendor half already validated |
| 3 feature-readiness marker | `structured_terminal_events` | 2–4 | independent of 4a; can run in parallel |
| 5 structured-output channel | nothing | 0–2 | mostly buildable from recorded shapes |
| 4b Codex decision | `codex.native_fork` | 0 | a decision, not an implementation |
| 6 authority provenance field | authority traceability | 0 | with the authority increment |

Total 6–12 live calls, comfortably inside a 30-call bound. Note that the 13 calls
left over from the previous increment do **not** carry forward: that bound was
authorized for that increment, and a new one needs its own authorization.

After steps 3 and 4a, Claude has a complete persistent chain and the remaining
question is no longer capability but durability — soak, controlled replacement,
and behaviour across a vendor upgrade, since every detector in this report is
bound to 2.1.222 by construction.
