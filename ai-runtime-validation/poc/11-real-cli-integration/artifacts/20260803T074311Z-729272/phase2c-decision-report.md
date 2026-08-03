# Phase 2C Real CLI Decision

- Decision: **PHASE_3_APPROVED_WITH_ADAPTATIONS**
- Run: `20260803T074311Z-729272`
- Git revision: `5eff1f8a1b2d27c2c8be210b2e28b0a1df10dbb6`
- Calls: agy `3/3`, Codex `3/3`

## Gates

| Gate | Antigravity | Codex |
| --- | --- | --- |
| Available | True | True |
| Structured event | True | True |
| Resume memory | True | True |
| tmux response | True | True |

## Required adaptations

- Replace the Claude adapter with a version-bound Antigravity adapter for Phase 2C.
- Use synthetic Git-derived reconstruction because agy 1.1.10 exposes no native fork flag.
- Prefer JSON Schema output channels over terminal scraping for protocol events.
