# Orchestration stdio reuse checklist

Use this checklist when validating conversation-owned stdio MCP reuse.

## Preconditions

- the package is installed and importable
- the runtime config is written to `~/.codex/config.toml`
- owner-key-required posture is enabled

## Checklist

1. `rl-developer-memory-maint server-status`
   - confirm the server can report slot and owner metadata

2. `rl-developer-memory-maint doctor --mode shadow --max-instances 0`
   - confirm config and lifecycle posture align

3. `rl-developer-memory-maint e2e-mcp-reuse-harness --json`
   - confirm the main conversation starts
   - confirm a duplicate launch is rejected with exit code `75`
   - confirm the duplicate does not create a second slot for the same owner
   - confirm two distinct main conversations can coexist
   - confirm a subagent thread resolves back to the main owner key

## Pass criteria

The harness verdict should report:
- `main_started = true`
- `subagent_resolved_to_main = true`
- `duplicate_launch_rejected = true`
- `duplicate_preserved_single_owner_slot = true`
- `distinct_main_conversations_coexist = true`
- `reuse_signal_emitted = true`
