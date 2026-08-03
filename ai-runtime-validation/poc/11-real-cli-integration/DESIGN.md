# Design

## Safety boundary

- Maximum three model calls per CLI.
- Default Antigravity model: `gemini-3.6-flash-low`.
- Every live subprocess has a 60-second timeout.
- Antigravity runs with `--sandbox --mode plan` and a disabled CLI log.
- Codex runs with read-only sandboxing and approval policy `never`.
- The workspace is a disposable minimal repository with no project secrets.
- Raw stdout/stderr are never written. Evidence retains hashes, byte counts,
  exit status, timings, and a redacted bounded excerpt.

## Probe sequence

```text
discovery
   ├─ agy structured event ─ agy resume
   └─ codex structured event ─ codex resume
                                  │
                                  └─ codex native fork in tmux
agy interactive tmux ─────────────┘
                  concurrent readiness + cleanup
```

Antigravity 1.1 exposes resume/conversation controls but no native fork flag.
That is treated as an adapter requirement for synthetic reconstruction, not as
a failed process integration probe.
