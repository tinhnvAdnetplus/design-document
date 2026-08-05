# Issues

Every iteration is retained. Where a failure was the probe's own integration
defect, it is labelled as such: none of these is a vendor incompatibility unless
it says so explicitly.

## Harness iterations `20260805T155910Z-52067a`, `20260805T160410Z-1b2f3f`

Discovery-only runs with no model call. The first proved fixture construction,
the runtime imports, evidence assembly, redaction checks, and
`verify-evidence.sh` compatibility. The second confirmed each gate can run
standalone after `ensure_adapters` was added, so a failed gate can be retried
without re-spending the quota of the gates that already passed.

## Probe iteration `20260805T160420Z-3af6a8` — first full live run, 10 calls

Passed: G1 for all three roles plus one turn through the real
`SessionSupervisor`; G3 Claude native fork with the root transcript
byte-identical across two children; G4 Claude resume recalling the root nonce
through a forked child; G6 with usage recorded for every turn.

Three failures, all reported only as `session readiness timed out`, which is not
a mechanism:

- the Claude root never reached its declared readiness;
- the `codex fork` TUI never reached its declared readiness, so Q1 concluded that
  no forked session was discoverable;
- the Claude feature session never printed the identity handshake, so G5 could
  not even attempt delivery.

**Correction.** The probe recorded no pane diagnostics on failure, so a timeout
was indistinguishable from a wrong detector, a blocking dialog, and a dead
process. A bounded allowlist of session-shaped marker lines was added, redacted
and capped, together with `pane_dead` and per-pattern match booleans.

The Q1 conclusion from this run is **withdrawn**. It attributed a probe-side
integration gap to the vendor, which is exactly the mistake this file exists to
prevent.

## Probe iteration `20260805T161436Z-8db913` — G2 diagnostics, 0 calls

The markers immediately explained both root failures:

- Claude 2.1.222 asks `❯ 1. Yes, I trust this folder` / `2. No, exit`. The
  declared `trust_pattern` is `Do you trust the contents`, which does not match
  it, so `SessionSupervisor._wait_ready` never saw a trust prompt to act on and
  simply waited out its deadline.
- Codex 0.146.0 was sitting at `Press enter to continue`, a one-time notice the
  declared trust pattern also cannot see.

This run also **invalidated the Codex root pass from the first run**. Codex only
reached readiness there because the earlier `codex exec` turn in G1 had already
cleared that notice and trusted the directory. Promoting `persistent_root` on the
strength of the first run alone would have promoted it on a false premise.

**Correction.** A disposable-fixture-only `clear_interactive_gates` step was
added. It launches a throwaway session, dismisses recognised gates, records each
one verbatim together with whether the declared trust pattern could see it, and
kills the session. It consumes no model call.

## Probe iteration `20260805T161822Z-7ee83d` — gate clearing, 0 calls

With the notice dismissed, Codex revealed a real trust dialog —
`Do you trust the contents of this directory?` — which the declared pattern
**does** match. Because this run still used the declared
`TrustPromptBehavior.REJECT`, `_wait_ready` correctly refused it:
`trust prompt requires an authorized disposable fixture`. That is the intended
fail-closed behaviour, not a defect.

Claude, after its trust dialog was dismissed, settled into a prompt box rendering
`❯ Try "how do I log an error?"`. The declared ready pattern requires the glyph
at end of line, so it still did not match.

**Correction.** G2 was split into two recorded variants so the declared
production path and the readiness measurement are never conflated.

## Probe iteration `20260805T162330Z-c84384` — G2 authoritative, 0 calls

- **Codex passed on the declared production path.** With the directory already
  trusted and the notice cleared, the declared spec — `trust_prompt=REJECT`,
  no disposable authorization — reached `READY` with no trust prompt observed.
  Readiness line verbatim: `│ model:     gpt-5.4-mini medium   /model to change │`.
  Runtime identity held across six samples over twelve seconds, and the root
  stayed `READY` after a child session terminated.
- **Claude failed on both variants**, with two independent declaration defects
  now proven verbatim: the trust pattern does not match its dialog, and the ready
  pattern does not match its idle prompt box, whose placeholder hint rotates
  (`Try "how do I log an error?"`, then `Try "fix lint errors"`) and always
  follows the glyph.

## Probe iteration `20260805T162830Z-b2ca48` — G5 authoritative, Q1 defect, 4 calls

**G5 succeeded at the vendor boundary.** With the folder trust gate cleared
first, the forked Claude feature session printed its identity handshake, the
runtime sent exactly `EVENT ref-0ba6de340f2a4238b0a454aa9c3a9eab` through
`send-keys`, the live CLI resolved that reference under its bound session inbox,
and an identity- and digest-correlated structured event reached the runtime
outbox and was durably acknowledged. `raw_output_retained` stayed `false` and
`cleanup_session` reported `cleaned` with one durable ack.

The gate is still recorded as failed, for one reason: the declared feature
readiness detector `^AI_RUNTIME_EVENT_READY {session_identity}$` did not match,
while the unanchored form did. The Claude TUI prefixes assistant output, so the
`^` anchor cannot hold.

That defect must **not** be fixed by dropping the anchor. The launch command
carries the bootstrap prompt, which itself contains the literal marker and the
substituted identity, so an unanchored detector could be satisfied by the echoed
instruction instead of the model's reply. Readiness would then be false. This is
recorded as a design problem for the next increment rather than papered over.

**Q1 failed on a probe defect.** `codex fork` reached readiness this time, but
the probe snapshotted the rollout directory *before* `clear_interactive_gates`
ran — and the throwaway prewarm session forks the parent too, leaving its own
rollout behind. Two rollouts therefore looked new, the "exactly one candidate"
rule rejected both, and a working fork was reported as undiscoverable.

**Correction.** The snapshot moved to after gate clearing, and the newest
candidate by mtime wins instead of requiring exactly one.

## Probe iteration `20260805T163202Z-03f6c1` — Q1 stdin hang, 1 call

The re-run failed differently. `codex exec` emitted
`Reading additional input from stdin...` and blocked for 210 seconds until the
probe's own timeout, producing no output and no session identifier.

Cause: `subprocess.run` left the child's stdin inherited, so `codex exec` waited
for an EOF that never arrived.

**Correction.** Every live invocation now passes `stdin=subprocess.DEVNULL`.

This is not only a probe defect. `src/ai_runtime/runtime/_session_worker.py`
launches each supervised turn with the same unconstrained `subprocess.run`, and
that worker is itself reading `sys.stdin` from its tmux pane. A Codex child can
therefore block on, or compete for, the pane input the supervisor's `send-keys`
intended for the worker. It is reported in
`reports/phase-4/live-persistent-adapter-contract.md` rather than patched here,
because changing the worker's process contract needs its own regression test.

## Probe iteration `20260805T163624Z-d5cd00` — Q1 authoritative, 2 calls

Q1 answered **yes**. `codex fork <parent>` created a session, exactly one new
rollout was discovered, and `codex exec resume <forked>` exited 0 and recalled
the nonce seeded in the parent, proving inherited context. The parent rollout was
byte-identical before and after, so root immutability holds for Codex too.

## Quota

17 of 30 authorized live calls: Claude 12, Codex 5. Thirteen remained unspent.
Every zero-call iteration above was deliberate — pane diagnostics, gate
clearing, and detector binding cost no quota, which is why three consecutive
corrections were affordable.
