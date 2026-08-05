# PoC 12 — Live Persistent Adapter Contract

This opt-in PoC establishes, against the installed Claude and Codex CLIs, whether
the persistent-adapter contract in `src/ai_runtime/runtime/feature_sessions.py`
can be satisfied by a live model transport. Every adapter declaration is
`FAIL_CLOSED` for `persistent_root`, `native_fork`, `resume`, and
`structured_terminal_events` because no live model call had ever been recorded.
This PoC is the probe that can legitimately promote individual fields — and only
the fields its evidence supports.

It does not run as part of `run-all.sh` or `ci.sh` because it consumes
authenticated model quota. `validation_lab.py` registers PoCs `01`–`10` only, so
this directory is invisible to both entrypoints by construction.

The tested boundary is:

1. **G1** — a schema-valid structured result under the exact argv
   `ClaudeCLIAdapter._command()` and `CodexCLIAdapter._command()` build today,
   for every role the adapter owns, plus one turn through the real
   `SessionSupervisor` transport.
2. **G2** — persistent root readiness against the *declared* `ReadinessDetector`,
   identity stability across an observation window, and root survival when a
   child session terminates.
3. **G3** — native fork producing a distinct child session with the root left
   byte-for-byte unmutated.
4. **G4** — resume recalling a harmless nonce seeded in the root.
5. **G5** — the `AI_RUNTIME_EVENT_READY` / `EVENT ref-<id>` channel end to end
   with the live CLI acting as the event client.
6. **G6** — measured prompt-cache behaviour of a forked turn against a fresh
   turn carrying the identical downstream prompt.

Two open questions are answered by behaviour, not by help text:

- **Q1** — does `codex fork` compose with `codex exec resume`?
- **Q2** — can a root be launched with a runtime-assigned session identifier so a
  fork/resume command template stays renderable?

Help and version output is discovery, never Capability Registry evidence. A gate
that fails keeps its own declaration field fail-closed and blocks nothing else.

G2 also serves a second purpose after the first live run: it is the gate that
rebinds a declared `ReadinessDetector` to a new CLI version. Candidate patterns are
trialled against both the live trust dialog and the live idle prompt, and a pattern
that matches the dialog is unusable no matter how well it matches the prompt —
`_wait_ready` checks readiness on the same capture in which it just answered a
trust prompt. Because G2 sends no turn, that rebinding costs no model quota.

Run only after reading [RUN.md](RUN.md).
