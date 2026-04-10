# Repo delta: RL MCP workflow contract

This file is a **short delta contract**. Detailed guidance lives in `docs/`.

## Runtime authority

- `~/.codex/config.toml` is the **only live runtime authority**.
- Repository configs under `configs/` and helper scripts are examples, not live authority.

## Runtime posture invariants

- Prefer `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` for main-conversation ownership.
- Keep **owner-key required** posture.
- Treat duplicate exit code **`75`** as a **reuse signal**, not a crash.
- Global max instance cap: **`0`**. Default rollout posture: **shadow**.
- Active DB must stay on local Linux/WSL filesystem (not `/mnt/c/...`).
- Redact secrets, tokens, env excerpts, and sensitive paths before durable storage.

## MCP flow (short form)

1. `issue_match` → `issue_get` (top 1–2) → `issue_guardrails` as needed
2. `issue_feedback` after accepted/rejected attempts
3. `issue_record_resolution` only after verification — redacted, scoped, reusable

Scope: `project_scope` for repo-specific, `global` for cross-repo, `user_scope` for personal preferences.

## Detailed guidance (see docs/)

| Topic | Document |
| --- | --- |
| Codex RL orchestration model | [`docs/CODEX_RL_AGENT_OPERATING_MODEL.md`](docs/CODEX_RL_AGENT_OPERATING_MODEL.md) |
| MCP lifecycle & write-back policy | [`docs/MCP_RL_INTEGRATION_POLICY.md`](docs/MCP_RL_INTEGRATION_POLICY.md) |
| Scope & write-back quick reference | [`docs/MEMORY_SCOPE_OPERATIONS_NOTE.md`](docs/MEMORY_SCOPE_OPERATIONS_NOTE.md) |
| RL coding & delivery standards | [`docs/RL_CODING_STANDARDS.md`](docs/RL_CODING_STANDARDS.md) |
| Skill install/sync | [`docs/SKILL_INSTALL_SYNC.md`](docs/SKILL_INSTALL_SYNC.md) |
| Owner-key model | [`docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md`](docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md) |

