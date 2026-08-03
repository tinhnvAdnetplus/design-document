# PoC 10 — end-to-end: Execution Guide

## Prerequisites

Run from the validation workspace once:

```bash
../../scripts/validate_environment.sh
```

## Execute

From this PoC directory:

```bash
./scripts/run_all.sh
```

Or from the validation workspace:

```bash
../../run-selected.sh 10
```

The command exits zero only when every measurable assertion passes. Failures exit non-zero with diagnostics. Each run creates an isolated directory under `artifacts/`, writes JSON and JUnit-compatible evidence, updates `RESULT.md`, and appends `experiment-log.md`.

All other scripts in `scripts/` are compatibility entrypoints into the same complete PoC assertion set; they do not report unconditional success.
