# Codex main-conversation ownership

`rl-developer-memory` uses an owner-key model to prevent duplicate MCP processes from claiming the same conversation.

## Preferred model

The recommended live posture is:
- explicit `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` per main conversation
- subagents inheriting or resolving to the same main-conversation key
- duplicate exit code `75` interpreted as a reuse signal

## Resolution sources

The runtime can derive an owner key from several sources, in order:
1. explicit owner-key environment variables
2. configured owner-key env alias
3. `CODEX_THREAD_ID` lineage
4. parent-process lineage
5. recent-session inference
6. optional synthetic fallback

## Why this matters

Correct owner-key resolution ensures:
- one live server per main conversation
- subagents reuse the same conversation-owned server
- duplicate launches are rejected instead of creating extra stateful processes

## Diagnostics

Inspect lifecycle state with:
```bash
rl-developer-memory-maint server-status
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint e2e-mcp-reuse-harness --json
```
