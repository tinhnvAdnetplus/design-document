# Experiment Design: 01-tmux-runtime

## Architecture Mapping
In the AI Multi-Agent Runtime V2.2, the **Orchestrator** utilizes tmux as a robust execution substrate. 
- **Root session**: Dedicated tmux sessions (e.g., `claude-root`) running long-lived agents that manage cross-feature context.
- **Feature session**: Disposable tmux sessions for ephemeral tasks (e.g., `codex-feature-{id}-1`).
- **Adapter**: Interfaces with the agent's environment, executing inside the tmux session.

## Runtime Topology
1. A single tmux server bound to socket `-L ai-runtime`.
2. Multiple isolated sessions within this server.
3. Event delivery mechanism executing `tmux -L ai-runtime send-keys -t <session> "<command>" Enter`.

## Expected Behavior
- Creating a session using `-c /path` accurately sets the CWD for that runtime.
- Sessions exist independently; closing or killing one does not affect others.
- The `send-keys` mechanism operates asynchronously, guaranteeing INV-07 (Event producers do not block on consumers).
- Feature sessions can be terminated safely, adhering to INV-08 (Feature sessions are disposable).
