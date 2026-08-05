# Live Persistent Adapter Contract

## Decision

**The first live model calls in this project's history are recorded, and exactly
one capability field was earned.** `codex.persistent_root` moves to
`VALIDATED`. Every other field on Claude, Codex, and Antigravity stays
`FAIL_CLOSED`.

That is a smaller promotion than the evidence might suggest, and deliberately so.
Claude's vendor primitives all worked: `--print --resume <id> --fork-session`
produced distinct children while leaving the root transcript byte-identical,
resume recalled root context through a forked child, and the child read the exact
prefix the root paid to cache. What blocks Claude promotion is the runtime's own
side of the contract. Neither of Claude's declared detectors matches 2.1.222, so
any promoted field would route the runtime into a session it cannot verify —
strictly worse than the declared synthetic path it uses today. Fail-closed is not
a placeholder here; it is the correct answer given a broken detector.

Live model calls: Claude `12`, Codex `5`, Antigravity `0`. Total `17` of the `30`
authorized. Thirteen were left unspent.

## Method

Nine bounded iterations against a disposable Git fixture under a temporary
directory, on the runtime-private tmux socket. Cheapest viable configuration:
Claude `--model haiku`, Codex `--model gpt-5.4-mini` with
`model_reasoning_effort="low"`.

Help and version output was used for discovery only. No capability was inferred
from it; every promotion below rests on observed behaviour.

Evidence:
`ai-runtime-validation/poc/12-live-persistent-contract/artifacts/consolidated-live-persistent-contract/`

`index.json` in that package names the authoritative iteration for each gate, and
every claim in this report traces to an `iteration-<run-id>-evidence.json` file
inside it. `validation_provenance_sha256` is the SHA-256 of the package's
`manifest.sha256`, so it covers every recorded byte and any reader can recompute
it:

```text
db6a6b4febf6b671e9773125f1c2dba50c162ed1c3c0a41b42b592fcff585dd5
```

Raw prompts, pane captures, stdout, stderr, and model transcripts were never
persisted. Retained pane data is limited to redacted detector-matching and
diagnostic lines capped at 200 characters — which the brief required, because a
detector cannot be bound to reality without the marker it must match.

## Per-gate result

### G1 — live structured result under the real command line: **pass**

Claude PLAN, Claude REVIEW, and Codex IMPLEMENT each ran under the exact argv
`ClaudeCLIAdapter._command()` and `CodexCLIAdapter._command()` build today. All
three produced a result that `_extract_structured` located and `_validate_result`
accepted. The Codex implementer committed in its generated worktree and reported a
40-character object ID that satisfied `IMPLEMENTATION_SCHEMA`.

One Claude plan turn additionally completed through the real `SessionSupervisor`
under `tmux_supervised_noninteractive_v1` and was acknowledged, so the transport
still works against a live CLI and not only against fixtures.

**The parser is compensating for an unstable contract in both adapters.** Every
one of the three roles required a JSON-in-string decode:

| Adapter | where the structured object was found | depth |
| --- | --- | ---: |
| Claude | `.result<json-string>` | 2 |
| Codex | `.item.text<json-string>` in JSONL line 10 | 3 |

For Claude this is avoidable and worth fixing: the same root object also carries a
dedicated `structured_output` key next to the human-facing `result` string, and
the runtime's walk simply reaches the stringified `result` first. The adapter
should read the declared structured channel instead of parsing prose that happens
to contain JSON. For Codex the structured result is only available as text inside
an `agent_message` item, so the decode is unavoidable at this version and the
dependency should be recorded rather than hidden.

### G2 — persistent root readiness and identity: **Codex pass, Claude fail**

**Codex passed on the declared production path.** With `trust_prompt=REJECT` and
no disposable authorization, the root reached `READY`, the declared detector
`model:\s+(?!loading)\S+` matched the observed line
`│ model:     gpt-5.4-mini medium   /model to change │`, runtime identity held
across six samples over a twelve-second window, and the root remained `READY`
after a child session terminated.

Two preconditions are now explicit, and neither is expressed by the declaration:
the directory must already be trusted, and Codex's one-time
`Press enter to continue` notice must already be cleared. In the first full run
the Codex root appeared to pass only because the earlier `codex exec` turn had
already satisfied both. **That pass was confounded**, and promoting on it would
have promoted on a false premise. The isolated re-run is the authoritative one.

**Claude failed, with two independent declaration defects proven verbatim:**

1. The declared `trust_pattern` `Do you trust the contents` does not match
   Claude 2.1.222's dialog, which reads `❯ 1. Yes, I trust this folder` /
   `2. No, exit`. `_wait_ready` therefore never sees a trust prompt to act on and
   waits out its deadline. The recorded evidence field
   `seen_by_declared_trust_pattern` is `false` against the observed line.
2. Even with trust granted, the declared ready pattern
   `(?:^|\n).*?[❯>]\s*$` does not match Claude's idle prompt box. The glyph is
   always followed by a rotating placeholder hint — `Try "how do I log an
   error?"` in one iteration, `Try "fix lint errors"` in the next — so the
   end-of-line anchor can never hold.

Defect 2 also makes the current pattern hazardous in the other direction: the
trust dialog's own first option line begins with the same glyph, so a pane where
that glyph landed at end of line would satisfy "ready" while the CLI was still at
a dialog.

### G3 — native fork: **pass for both adapters**

Claude, two successive forks from one root:

- both children returned session IDs distinct from the root and from each other;
- the root transcript digest was byte-identical before and after each child turn.

Codex: `codex fork <parent>` created a session, and the parent rollout was
byte-identical before and after — same digest, same byte count.

Root immutability holds. No fork advanced its parent.

### G4 — resume: **pass for both adapters**

Claude: resuming the forked child returned the nonce that had been seeded only in
the root, which proves resume and fork inheritance in one observation. The
returned session ID equalled the resumed one, so resume correctly does not mint a
new identity.

Codex: `codex exec resume <forked>` exited 0 and recalled the parent's nonce.

### G5 — structured terminal events: **partial**

The channel worked end to end against the live Claude CLI. The forked feature
session printed its identity handshake; the runtime sent exactly

```text
EVENT ref-0ba6de340f2a4238b0a454aa9c3a9eab
```

through `send-keys` and nothing else; the live CLI resolved that reference under
its bound session inbox; an identity- and digest-correlated structured event
reached the runtime outbox; the runtime validated it, appended, and wrote a
durable acknowledgement. `raw_output_retained` stayed `false`, and
`cleanup_session` reported `cleaned` with one durable ack. The assertion that no
prompt text, path, schema, or secret crosses `send-keys` held: the payload is
fixed-form and machine-checked.

The gate is nonetheless recorded as failed, for one reason. The declared feature
detector `^AI_RUNTIME_EVENT_READY {session_identity}$` did not match; the
unanchored form did. The Claude TUI prefixes assistant output, so the `^` anchor
cannot hold.

**That defect must not be fixed by dropping the anchor.** The launch command
carries the bootstrap prompt, and that prompt contains the literal marker with
the substituted identity. An unanchored detector could be satisfied by the echoed
instruction rather than by the model's reply, and readiness would be false. The
fix is a marker the launch text does not itself contain, or an anchor bound to the
TUI's assistant prefix. Either is a design decision this increment did not make,
so `structured_terminal_events` stays fail-closed.

### G6 — prompt-cache measurement: **measured**

Claude `haiku`, identical downstream prompt on every compared turn:

| Turn | cache write | cache read | input | cost USD |
| --- | ---: | ---: | ---: | ---: |
| root seed | 46,667 | 70,886 | 6 | 0.3723 |
| fork A | 1,395 | **46,667** | 2 | 0.0226 |
| fork B | 0 | **48,062** | 2 | 0.0146 |
| fresh, non-forked | 2,679 | 28,623 | 2 | 0.0446 |

Fork A read 46,667 cached tokens — exactly the number the root seed wrote. Fork B
wrote nothing and read 48,062. Against the fresh turn carrying the same downstream
prompt, the forked turn read 18,044 more cached tokens and cost roughly half.

Two honest qualifications. The Claude Code system prompt is part of every prefix,
so a fresh turn also reports cache activity; only the delta is attributable to the
forked conversation prefix. And the absolute numbers are Haiku-scoped and
fixture-scoped, so they bound the shape of the saving, not its size for a real
root.

Chapter 09's claim that only a native fork turns the shared prefix into a cache
read is now **measured rather than assumed**, and the exact-equality between fork
A's read and the root's write is the cleanest form that evidence could take.

For Codex, `codex exec --json` exposes `cached_input_tokens` (52,096 on the
implementer turn) but no cost field. This probe's extractor did not capture
`cache_write_input_tokens`, so no Codex write-side figure is reported; that is a
gap in the probe, not a vendor limitation.

## What was promoted

| Adapter | Field | Result |
| --- | --- | --- |
| Codex | `persistent_root` | `VALIDATED`, provenance `db6a6b4f…` |
| Codex | `native_fork`, `resume`, `structured_terminal_events` | `FAIL_CLOSED` |
| Claude | all four fields | `FAIL_CLOSED` |
| Antigravity | all four fields | `FAIL_CLOSED`, untouched |

Reasons for each field that stayed closed:

- **Codex `native_fork` and `resume`.** Both are live-validated at the vendor
  boundary, and both fail the second half of the promotion test: a validated field
  requires a command mapping, and Codex exposes no way to assign a session
  identifier. Neither template renders from data the runtime owns. A validated
  field with no renderable mapping is unusable, so it would be a false claim.
- **Codex `structured_terminal_events`.** Not attempted; the Claude path consumed
  the G5 budget. Untested is untested.
- **Claude `persistent_root`.** G2 failed on two proven detector defects.
- **Claude `native_fork` and `resume`.** The vendor primitives passed G3, G4, and
  G6, but every consumer path is blocked downstream. `native_fork()` additionally
  requires a validated terminal-event channel, which G5 withheld; `resume_command`
  would relaunch into the root detector that G2 proved does not match. Promoting
  `resume` would actively make recovery worse: today `resume_or_reconstruct`
  selects synthetic reconstruction, which works, and a validated resume would
  divert it into a session whose readiness can never be confirmed.
- **Claude `structured_terminal_events`.** The channel is live-validated; the
  runtime's readiness detector for a forked feature session is not, and cannot be
  repaired by relaxing an anchor. See G5.

Antigravity's invariant still holds: `native_fork != FAIL_CLOSED` remains
rejected by `PersistentAdapterDeclaration.__post_init__`, and nothing in this
increment touched its declaration.

Claude merge authority remains disabled and was not part of any gate.

## Q1 — does `codex fork` compose with `codex exec`?

**Yes.** `codex fork <parent_session_id>` creates a session that
`codex exec resume <forked_session_id>` then drives non-interactively, with the
parent's context inherited — the resumed turn recalled a nonce seeded only in the
parent — and with the parent rollout left byte-identical.

Two qualifications matter more than the answer:

1. `codex fork` is a TUI. It reaches readiness only after its one-time
   `Press enter to continue` notice and the directory trust dialog are cleared.
   The runtime cannot answer either under its declared `REJECT` behaviour, so both
   are operational preconditions.
2. The forked session's identifier is not returned on any machine-readable
   channel. This probe recovered it by taking the newest rollout file created
   after the fork, which is discovery from vendor-private state — acceptable in a
   probe, not acceptable as a runtime mechanism.

The first full run concluded the opposite, that no forked session was
discoverable. That conclusion was a probe defect: the rollout snapshot was taken
before the throwaway prewarm session ran, and the prewarm forks the parent too, so
a working fork looked undiscoverable. It is retained in `ISSUES.md` as a recorded
iteration and explicitly withdrawn rather than left standing as a vendor finding.

## Q2 — session-identifier binding

**Claude: solved.** `--session-id <uuid>` is accepted and honoured — the root seed
requested a runtime-generated UUID and the CLI returned that exact identifier.
A runtime-assigned identifier therefore makes a fork or resume template
renderable without discovering anything from vendor state.

**Codex: no equivalent exists.** Neither `codex exec` nor `codex fork` nor
`codex resume` accepts a caller-supplied session identifier. `resume` and `fork`
accept a "thread name", but nothing sets one non-interactively. The identifier can
only be read out of `codex exec --json` output after the fact, which would require
a new persisted `SessionRecord` field rather than a placeholder.

The minimal change for Claude — **proposed, not implemented**:

```python
# feature_sessions.py
VENDOR_SESSION_NAMESPACE = uuid.UUID("…")

def vendor_session_id(adapter: str, runtime_session_id: str) -> str:
    return str(uuid.uuid5(VENDOR_SESSION_NAMESPACE, f"{adapter}|{runtime_session_id}"))
```

then one key added to each of two placeholder maps: `vendor_session_id` in
`_root_spec`, and `parent_vendor_session_id` in `_feature_values`. The derivation
is deterministic, needs no new persisted field, and survives restart because root
generation is already encoded in the runtime session ID that `replace_root`
assigns.

The human authorized implementing this once the dependent gates passed. It is not
implemented, because the decision above leaves no consumer: the only fields that
would render these placeholders are the Claude fields kept fail-closed, so adding
them now would commit unused code and an unused public helper. The probe validated
the mechanism — it derived the root UUID exactly this way, adding a run-scoped
component so iterations stayed independent — and the diff is ready when a field
needs it. Say the word and it goes in.

## Defect found in the runtime, reported not patched

`src/ai_runtime/runtime/_session_worker.py` launches every supervised turn with
`subprocess.run(...)` and no `stdin` argument, so the child inherits the worker's
stdin — which is the tmux pane the supervisor drives with `send-keys`. A live
Codex turn hit exactly this: it printed `Reading additional input from stdin...`
and blocked for 210 seconds until the probe's timeout, producing nothing. Two
processes reading one pane also means a model child can consume a `TURN <id>`
notice intended for the worker.

The fix is `stdin=subprocess.DEVNULL` on that call. It is not applied here because
changing the worker's process contract deserves its own regression test — that a
child cannot consume the worker's pane input — and a probe increment is the wrong
place to add untested behaviour to the transport. It is the highest-priority item
below.

## Non-changes

The bounded review loop, merge binding and authority, lease fencing, worktree
isolation, Git-first truth, protected-ref snapshots, replay purity, exact-head
approval, and the fork abstraction are all unchanged. No Knowledge Cache, durable
delivery scheduler, concurrent feature support, `abandon`, or `replan` was
implemented. No frozen artifact, `phase3-artifacts/` file, or
`ai-runtime-validation/lib/validation_lab.py` was modified.

One CI change: the "Verify committed evidence packages" step globbed only
`ai-runtime-validation/artifacts/*/`, which never reached a package committed
under the PoC that produced it. A second glob for
`ai-runtime-validation/poc/*/artifacts/*/` was added so this increment's committed
package is actually verified rather than merely present.

## Verification

- live calls: **17 / 30** (Claude 12, Codex 5, Antigravity 0);
- evidence packages: **10 verified** by
  `ai-runtime-validation/scripts/verify-evidence.sh`, including the consolidated
  package;
- runtime tests: **52/52 passed**;
- contract validation `ci.sh 01 02 03 04 05 06 07 08 10`: **73/73 assertions**;
- `ruff check`, `ruff format --check`, and `mypy` clean across `src`, `tests`, and
  `benchmarks`;
- fixture clean after every live run; every tmux server removed; redaction checks
  passed on all nine iteration reports;
- probe-created session files removed: 7 Claude transcripts, 1 Codex rollout. The
  Claude workspace-trust record for the fixture path is retained by the CLI
  outside the fixture; the path itself no longer exists.

## Next increment

1. **Fix the session-worker stdin contract** with a regression test. It is a
   one-keyword change guarding a proven hang and a proven input-contention hazard,
   and it affects the transport every role already uses.
2. **Rebind the Claude detectors to 2.1.222 and re-run G2.** The trust pattern
   must match `Yes, I trust this folder`; the ready pattern must not assume the
   glyph ends the line. This costs no model quota, and it is the single gate
   blocking every other Claude field.
3. **Design a feature-readiness marker the launch prompt does not contain**, then
   re-run G5. Until then `structured_terminal_events` cannot be promoted for any
   adapter even though the channel demonstrably works.
4. **Decide the Codex identifier question.** Either persist the vendor session ID
   observed on `codex exec --json` in `SessionRecord`, or accept that Codex native
   fork stays unreachable. The capability is proven; only the binding is missing.
5. **Read Claude's `structured_output` channel** instead of parsing the `result`
   string, and record the Codex `agent_message.text` decode as a version-bound
   dependency.
6. **Then, and only then, reconsider Claude promotion** — and note that authority
   still needs soak and controlled-replacement coverage beyond these gates, per
   `reports/phase-3/persistent-root-native-fork.md`.
