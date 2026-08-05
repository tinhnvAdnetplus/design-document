# Expected Results

Each gate is independently pass/fail. A failed gate keeps its own declaration
field fail-closed and does not block the others.

| ID | Gate | Required evidence |
| --- | --- | --- |
| LPC-01 | G1 | Claude PLAN and REVIEW and Codex IMPLEMENT each return a result that `_extract_structured` finds and `_validate_result` accepts, under the exact adapter argv |
| LPC-02 | G1 | the structured-shape trace records the path, depth, and whether a JSON-string decode or code-fence strip was required |
| LPC-03 | G1 | one Claude plan turn completes through the real `SessionSupervisor` transport and is acknowledged |
| LPC-04 | G2 | each root reaches readiness against its **declared** `ReadinessDetector`, and the matching pane line is recorded verbatim and redacted |
| LPC-05 | G2 | readiness and tmux runtime identity hold across a 12-second observation window |
| LPC-06 | G2 | a child session terminating leaves the root live and ready |
| LPC-07 | G3 | a forked Claude turn returns a session ID distinct from the root and from the other fork |
| LPC-08 | G3 | the root transcript digest is byte-for-byte identical before and after every child turn |
| LPC-09 | G4 | a resumed session returns the nonce seeded in the root, proving both resume and fork inheritance |
| LPC-10 | G5 | `send-keys` carries exactly `EVENT ref-<32 hex>` and no prompt, path, schema, or secret |
| LPC-11 | G5 | an identity- and digest-correlated structured event reaches the runtime outbox and is durably acknowledged |
| LPC-12 | G6 | usage is recorded for the fresh turn, both forked turns, and the root seed, or the absence of usage data is recorded explicitly |
| LPC-13 | Q1 | `codex exec resume` either drives a `codex fork` session with inherited context, or the composition failure is recorded as the finding |
| LPC-14 | Q2 | a runtime-assigned root identifier renders the fork/resume template, or the absence of that surface is established per adapter |
| LPC-15 | — | the fixture is clean, every tmux server is removed, and no raw prompt, pane, home path, email, or credential text appears in the evidence |
| LPC-16 | — | the live call count is recorded and within the 30-call cap |
| LPC-17 | G2 | every candidate readiness pattern is trialled against both the live trust dialog and the live idle prompt, and a candidate that matches the dialog is recorded as unusable |
| LPC-18 | G2 | every candidate trust pattern is trialled against the live dialog, so a declared pattern that describes a dialog the CLI does not render is caught |

## Decisions

| Decision | Meaning |
| --- | --- |
| `LIVE_CONTRACT_ESTABLISHED` | every selected gate passed |
| `PARTIAL_CONTRACT_ESTABLISHED` | at least one gate passed; each failure keeps its own field fail-closed |
| `LIVE_CONTRACT_NOT_ESTABLISHED` | no gate passed; every declaration stays fail-closed |
| `BUDGET_STOPPED` | the 30-call cap was reached; the probe stopped and asked the human |
| `BLOCKED_PRIVACY` | a redaction check failed; the package must not be trusted |
| `DISCOVERY_ONLY` | harness run with no model call |

`PARTIAL_CONTRACT_ESTABLISHED` is an expected and acceptable outcome. Promotion is
per field, so a partial result promotes exactly what it earned.

## Non-goals

No Knowledge Cache, durable delivery scheduler, concurrent features, `abandon`,
or `replan`. Claude merge authority is not enabled by this PoC; it needs its own
validation beyond these gates.
