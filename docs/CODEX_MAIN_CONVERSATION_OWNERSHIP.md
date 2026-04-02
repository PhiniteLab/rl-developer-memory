# Codex Main-Conversation Ownership Integration

This document defines the **owner-key contract** for running exactly one
`rl_developer_memory` MCP process per main Codex conversation.

## Preferred integration contract

Use the following for normal operation:

- `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` (preferred direct env var)
- `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE` (`main` or `subagent`, optional)

`RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` must identify the stable **main conversation**
identifier, not a per-subagent thread id.

## Full owner-key resolution chain in this repo

On startup, `Settings.from_env()` resolves `server_owner_key` in this order:

1. **Explicit envs (direct, highest priority)**
   - `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`
   - `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY`
   - `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY`
2. **Explicit alias envs**
   - `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY_ENV`
   - `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV`
   - `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY_ENV`
3. **Current process `CODEX_THREAD_ID` lineage**
   - resolves thread lineage to root via `forked_from_id`/session ancestry metadata
4. **Parent-process lineage fallback**
   - scans ancestor process environments for any of the owner envs and/or
     `CODEX_THREAD_ID` lineage when the child env is incomplete
5. **Recent-session inference**
   - uses newest local Codex session files; only picks a key when all observed
     candidates collapse to a single root
6. **Optional synthetic fallback**
   - if `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY=1` and
     `RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY=1`, generates the
     process-scoped key `synthetic-process-<ppid>-<pid>` and marks its
     diagnostics source label as `RL_DEVELOPER_MEMORY_SYNTHETIC_OWNER_KEY`

The first resolved key becomes both:

- `server_owner_key`
- `server_owner_key_env` (the source label shown by diagnostics)

Role inference occurs after owner-key resolution:

- if explicit role envs are passed, that value is used directly
- otherwise, when resolved via `CODEX_THREAD_ID`, role is inferred as:
  - `main` when current thread equals resolved owner thread id
  - `subagent` otherwise
- synthetic fallback uses role `anonymous`

## Lifecycle behavior tied to the resolved owner key

When `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY=1` and an owner key resolves:

- first launch for that owner acquires owner lock and starts normally
- duplicate same-owner launches are rejected **before** consuming a global slot
- rejection exits with `RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE`
  (default `75`) via `MCPServerOwnerConflict`
- lifecycle status exposes `owner_key`, `owner_key_env`, `owner_role` in:
  - aggregate `server-status`
  - each `active_slots` entry

Repo default values in a recommended live configuration are:

- `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"`
- `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"`
- `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` injected per launch
- `RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE = "75"`
- `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"` (no global cap requirement)

## Reuse contract (Codex orchestration layer responsibility)

`rl_developer_memory` is a stdio MCP server:

- the repo can prevent duplicate same-owner launches and emit the controlled exit code
- it cannot attach a second stdio client to an existing process

So orchestrator-level behavior must interpret duplicate exit `75` as a
**reuse/dedup signal** and route subagent tool calls through the already-running
conversation-owned MCP.

For a production-ready verification flow, use:

- repo-side proof: `rl-developer-memory-maint e2e-mcp-reuse-harness --json`
- orchestration proof: [`ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md`](ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md)
