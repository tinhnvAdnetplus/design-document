# PoC 01: 01-tmux-runtime

## Objective
Validate that tmux provides a viable runtime substrate for managing persistent agent sessions with proper naming, lifecycle, and event notification delivery in the AI Multi-Agent Runtime V2.2 specification.

## Scope
- tmux server persistence and detachment
- Controlled session naming based on roles and features
- Event delivery via `send-keys`
- Process isolation and session validation

## Success Criteria
- [ ] tmux server persists detached across terminal boundaries.
- [ ] Named sessions are successfully created mapping to root and feature concepts.
- [ ] `send-keys` reliably delivers commands directly to target sessions.
- [ ] Sessions can be accurately enumerated and verified.

## Architecture Assumptions Validated
- tmux server persistence across terminal detachment
- Named session creation with controlled naming (claude-root, codex-root, claude-feature-{id}-plan-{attempt}, codex-feature-{id}-{attempt}, claude-feature-{id}-review-{attempt})
- Event notification via `send-keys` to specific session/window/pane targets
- Session existence checking via `has-session`
- Session enumeration via `list-sessions`
- Process isolation between sessions
- Socket naming (`-L ai-runtime`)
- Working directory assignment at session creation (`-c /path`)

## Relevant V2.2 Spec
- Chapter 10 — tmux Runtime and Orchestrator
- INV-07: Event producers do not block on consumers
- INV-08: Feature sessions are disposable
