# PoC 11 — Real Antigravity/Codex CLI Integration

This opt-in PoC validates the live vendor boundary that PoCs 01–10 deliberately
simulate. For Phase 2C, Antigravity CLI (`agy`) temporarily replaces Claude CLI.

The probe uses a disposable minimal Git repository, read-only/sandboxed agent
modes, bounded calls, 60-second subprocess timeouts, unique tmux sockets, and
redacted evidence. It does not run as part of `run-all.sh` because it consumes
authenticated model quota.

The tested boundary is:

1. CLI/version and declared capability discovery.
2. Native structured output validated against JSON Schema.
3. Conversation/session resume using a harmless nonce.
4. Concurrent tmux execution and captured response readiness.
5. Codex native fork behavior and Antigravity synthetic-fork adaptation.
6. Clean teardown and no writes to the fixture repository.

Run only after reviewing [RUN.md](RUN.md).
