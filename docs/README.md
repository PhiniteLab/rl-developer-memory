# Documentation

This directory expands on the root [`README.md`](../README.md) with setup, configuration, usage, operations, architecture, and contributor guidance.

## Public repository positioning

This documentation set is written for the standalone public `rl-developer-memory` repository.

- Keep naming consistent across package and runtime assets.
- Treat RL/control memory workflows as first-class behavior, not optional branding.
- Keep coexistence guidance with other MCP memory servers optional and policy-driven.

## Authoritative public surfaces

For public users, read the documentation with these rules in mind:

- the authoritative MCP registration lives in `~/.codex/config.toml`
- keep exactly one `[mcp_servers.rl_developer_memory]` block there
- the live custom plugin / skill root is `~/.codex/local-plugins/**`
- bundled skill content in this repository is reference-only; any live custom wrapper should live under `~/.codex/local-plugins/**`
- example files in `templates/` are reference snippets, not live configuration
- repo content under `skills/` is bundled reference material, not the authoritative runtime root

## Start here

- [`INSTALLATION.md`](INSTALLATION.md): setup, verification, manual registration, and path guidance
- [`CONFIGURATION.md`](CONFIGURATION.md): runtime variables, defaults, and public configuration model
- [`CODEX_MAIN_CONVERSATION_OWNERSHIP.md`](CODEX_MAIN_CONVERSATION_OWNERSHIP.md): owner-key contract for one MCP per main Codex conversation
- [`ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md`](ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md): live launcher checklist for proving true stdio reuse
- [`USAGE.md`](USAGE.md): MCP tools, direct Python usage, preferences, guardrails, metrics, and CLI commands
- [`OPERATIONS.md`](OPERATIONS.md): backups, restore, logs, health checks, and troubleshooting
- [`ROLLOUT.md`](ROLLOUT.md): recommended default runtime posture and alternative configuration choices
- [`ARCHITECTURE.md`](ARCHITECTURE.md): module responsibilities, request flow, ranking, storage, and safety controls
- [`DEVELOPMENT.md`](DEVELOPMENT.md): local setup, validation, and contributor expectations
- [`DEPENDENCIES.md`](DEPENDENCIES.md): Python and system dependencies
- [`COMPATIBILITY.md`](COMPATIBILITY.md): platform support and WSL guidance

## Suggested reading order

1. Read the root [`README.md`](../README.md) for the project overview.
2. Use [`INSTALLATION.md`](INSTALLATION.md) and [`CONFIGURATION.md`](CONFIGURATION.md) to get a correct live setup.
3. Use [`USAGE.md`](USAGE.md) and [`OPERATIONS.md`](OPERATIONS.md) for day-to-day usage.
4. Use [`ROLLOUT.md`](ROLLOUT.md) to choose a configuration posture.
5. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`DEVELOPMENT.md`](DEVELOPMENT.md) before changing code.

## Scope

These docs are grounded in the repository as it exists today:

- `src/rl_developer_memory/` for the MCP server, retrieval logic, storage, safety, and maintenance CLI
- `scripts/` for registration, verification, cron, and backup helpers
- `templates/` for example config snippets
- `tests/` for regression and benchmark coverage
- `skills/rl-developer-memory-self-learning/` for bundled reference content related to the rl-developer-memory workflow; any live custom wrapper belongs under `~/.codex/local-plugins/**`
