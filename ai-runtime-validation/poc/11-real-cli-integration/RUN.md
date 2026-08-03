# Run

## Prerequisites

- Authenticated `agy` and `codex` commands.
- `tmux`, `git`, and Python 3.11+.
- Explicit authorization to consume model quota.

## Command

```bash
./scripts/run_all.sh --live
```

Optional controls:

```bash
AGY_PROBE_MODEL=gemini-3.6-flash-low \
CLI_PROBE_TIMEOUT_SECONDS=60 \
./scripts/run_all.sh --live
```

Use `--discovery-only` to collect help/version evidence without model calls.
