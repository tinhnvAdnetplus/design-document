# Phase 2C Real CLI Decision

- Decision: **PHASE_3_BLOCKED**
- Run: `20260803T074021Z-0e6ffc`
- Git revision: `97a895160a6fe71232e419005454608f504b67c1`
- Calls: agy `3/3`, Codex `3/3`

## Gates

| Gate | Antigravity | Codex |
| --- | --- | --- |
| Available | True | True |
| Structured event | True | True |
| Resume memory | True | True |
| tmux response | False | False |

## Required adaptations

- Replace the Claude adapter with a version-bound Antigravity adapter for Phase 2C.
- Use synthetic Git-derived reconstruction because agy 1.1.10 exposes no native fork flag.
- Prefer JSON Schema output channels over terminal scraping for protocol events.
