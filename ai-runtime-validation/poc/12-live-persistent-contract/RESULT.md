# PoC 12 — Live Persistent Adapter Contract Result

- Decision: **PARTIAL_CONTRACT_ESTABLISHED**
- Executed at: `2026-08-05T16:04:20Z` through `2026-08-05T16:36:24Z`
- Adapter versions: Claude `2.1.222 (Claude Code)`, Codex `codex-cli 0.146.0`
- Models: Claude `haiku`, Codex `gpt-5.4-mini` with `model_reasoning_effort="low"`
- Live calls: **17 / 30** (Claude 12, Codex 5)
- Consolidated evidence:
  [`artifacts/consolidated-live-persistent-contract/`](artifacts/consolidated-live-persistent-contract/)
- `validation_provenance_sha256`:
  `db6a6b4febf6b671e9773125f1c2dba50c162ed1c3c0a41b42b592fcff585dd5`
  (`sha256sum artifacts/consolidated-live-persistent-contract/manifest.sha256`)

## Gate results

| ID | Gate | Result | Authoritative iteration |
| --- | --- | --- | --- |
| G1 | structured result under the exact adapter argv | **pass** | `20260805T160420Z-3af6a8` |
| G2 | persistent root readiness/identity/survival — Codex | **pass** | `20260805T162330Z-c84384` |
| G2 | persistent root readiness — Claude, declared detectors | **fail** | `20260805T162330Z-c84384` |
| G2 | persistent root readiness/identity/survival — Claude, rebound detectors | **pass** | `20260805T172349Z-34303d` |
| G3 | native fork, root unmutated — Claude | **pass** | `20260805T160420Z-3af6a8` |
| G3 | native fork, parent unmutated — Codex | **pass** | `20260805T163624Z-d5cd00` |
| G4 | resume recalls root context — Claude | **pass** | `20260805T160420Z-3af6a8` |
| G4 | resume recalls parent context — Codex | **pass** | `20260805T163624Z-d5cd00` |
| G5 | structured terminal events | **partial** | `20260805T162830Z-b2ca48` |
| G6 | prompt-cache measurement | **pass, measured** | `20260805T160420Z-3af6a8` |
| Q1 | `codex fork` composes with `codex exec` | **yes** | `20260805T163624Z-d5cd00` |
| Q2 | runtime-assigned session identifier | **Claude yes, Codex no** | `20260805T160420Z-3af6a8` |

## Measured prompt cache

Claude `haiku`, identical downstream prompt on every compared turn:

| Turn | cache write | cache read | cost USD |
| --- | ---: | ---: | ---: |
| root seed | 46,667 | 70,886 | 0.3723 |
| fork A | 1,395 | **46,667** | 0.0226 |
| fork B | 0 | **48,062** | 0.0146 |
| fresh, non-forked | 2,679 | 28,623 | 0.0446 |

Fork A's cache read equals the root seed's cache write exactly. The forked child
read the prefix the root paid to write, and the second fork wrote nothing at all.

## Detector rebind — follow-up increment, 0 live calls

Two further iterations rebound the Claude detectors to what 2.1.222 actually
renders, chosen by candidate-pattern trials against both the live trust dialog and
the live idle prompt rather than by reading the rendering:

- `ready_pattern`: `(?:^|\n).*?[❯>]\s*$` → `^\s*[❯>]\s+(?!\d+\.)\S`
- `trust_pattern`: `Do you trust the contents` → `Yes, I trust this folder`

The negative lookahead is load-bearing: the trust dialog draws the same glyph as a
selection cursor, and a pattern matching there would report `READY` with the
dialog still up.

- Consolidated evidence:
  [`artifacts/consolidated-claude-detector-rebind/`](artifacts/consolidated-claude-detector-rebind/)
- `validation_provenance_sha256`:
  `9281bf459ab9f5e4631c3f7984795f4426cfc5861b5eb014ea6714c38b337f6b`
- Live calls: **0 / 30** — both iterations are readiness measurements

## Promotion

`codex.persistent_root` and `claude.persistent_root` are `VALIDATED`, each against
the package that earned it. Every other field on every adapter stays
`FAIL_CLOSED`, each for a stated reason. Antigravity was not touched. See
`reports/phase-4/live-persistent-adapter-contract.md` and
`reports/phase-4/claude-detector-rebind.md`.

Raw prompts, pane captures, stdout, and model transcripts were not retained. Pane
data is limited to redacted detector-matching and allowlisted diagnostic lines,
capped at 200 characters each and 16 lines per session. Eleven iterations are
preserved, including five failures and their corrections, in
[ISSUES.md](ISSUES.md).
