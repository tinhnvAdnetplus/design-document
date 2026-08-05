# Run

## Prerequisites

- Authenticated `claude` and `codex` commands on PATH.
- `tmux`, `git`, and Python 3.11+.
- Explicit authorization to consume model quota. This PoC is opt-in and is
  excluded from `run-all.sh` and `ci.sh`.

## Commands

Harness check with no model call:

```bash
./scripts/run_all.sh --discovery-only
```

Full bounded live probe:

```bash
./scripts/run_all.sh --live
```

A single gate, for a bounded retry after a recorded failure:

```bash
./scripts/run_all.sh --live --gates G5
```

## Controls

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROBE_CLAUDE_MODEL` | `haiku` | cheapest viable Claude model |
| `PROBE_CODEX_MODEL` | `gpt-5.4-mini` | cheapest viable Codex model |
| `PROBE_MAX_LIVE_CALLS` | `30` | hard cap; the probe raises rather than exceeding it |
| `PROBE_TURN_TIMEOUT_SECONDS` | `180` | per-turn subprocess bound |
| `PROBE_READINESS_TIMEOUT_SECONDS` | `60` | per-session readiness bound |

Lowering `PROBE_MAX_LIVE_CALLS` is always safe. Raising it above 30 requires a
human decision, because 30 is the authorized ceiling for this increment.

## Evidence

Each run writes `artifacts/<run-id>/` containing
`live-contract-evidence.json`, `revision-evidence.json`,
`portable-git-evidence.json`, and `manifest.sha256`. Verify with:

```bash
../../scripts/verify-evidence.sh artifacts/<run-id>
```

The probe prints the value to use for `validation_provenance_sha256`. It is the
SHA-256 of `manifest.sha256`, so it covers every recorded byte and anyone with
the package can recompute it:

```bash
sha256sum artifacts/<run-id>/manifest.sha256
```

## Residue

The probe deletes the fixture, kills every tmux server it started, removes the
Claude project transcript directory it created for the fixture path, and removes
only the Codex rollout files whose names contain a session identifier it created.
Counts are recorded under `session_residue` in the evidence. Claude's
workspace-trust record for the fixture path is left in place; the path itself no
longer exists.
