# Issues

## Probe iteration `20260803T072740Z-362f38`

- Antigravity structured output succeeded, but the initial argument order made
  `--sandbox` the effective prompt. Resume therefore could not recall the nonce.
- Codex started a real thread and resumed it successfully, but its strict
  structured-output validator rejected `const` properties without an explicit
  JSON Schema `type`.
- Both tmux panes were cleaned up, but response markers were not observed in the
  first iteration. Pane lifecycle diagnostics were added without retaining pane
  output.
- The fixture remained clean and every redaction check passed.

The CLI ordering and schema compatibility issues were corrected before the
decision run. The failed iteration is preserved as negative integration
evidence rather than being relabeled as a vendor incompatibility.

## Probe iteration `20260803T073147Z-cd0d46`

- Structured JSON and actual resume passed for both Antigravity and Codex.
- Both tmux processes remained alive, but neither produced a response marker.
- A no-model readiness inspection showed both CLIs were waiting at their
  workspace trust dialogs. Initial prompt arguments therefore had not reached
  the model.

The decision probe now accepts trust only for its disposable fixture and sends
the prompt afterward through tmux `send-keys`, matching the intended runtime
transport more closely.
