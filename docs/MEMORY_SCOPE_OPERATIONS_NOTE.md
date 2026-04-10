# Memory scope and write-back operations note

> **Quick-reference summary** of [MCP_RL_INTEGRATION_POLICY.md](MCP_RL_INTEGRATION_POLICY.md) §3–5.
> See that document for full scope, write-back, and redaction guidance.

This short note is for operators and contributors who use `rl_developer_memory` during RL development.

## Scope policy

Choose scope deliberately:

- `project_scope`
  - repo-specific config, import, rollout, theorem/code, checkpoint, benchmark, validator, and RL workflow issues
- `global`
  - broad reusable engineering lessons not tied to this repository
- `user_scope`
  - stable user/team coding preferences, validation order, review strictness, or tuning habits

## Write-back policy

Durable memory write-back should happen only when all are true:
- the symptom is real
- the fix is specific
- the fix passed validation
- the lesson is reusable
- the stored content is compact and redacted
- the selected scope is explicit

## Never write back

Do not store:
- secrets
- tokens
- raw `.env` excerpts
- long unredacted logs
- sensitive local paths when avoidable
- speculative hypotheses
- temporary hacks
- single-run unexplained flakes

## Preferred lifecycle

1. `issue_match`
2. `issue_get` for top 1-2 only when needed
3. `issue_guardrails` when prevention rules or scope reminders matter
4. `issue_feedback` after a meaningful accepted/rejected attempt
5. `issue_record_resolution` only after verification

## Runtime posture reminders

- treat `~/.codex/config.toml` as the only live runtime authority
- prefer `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`
- treat duplicate exit code `75` as reuse
- keep active DB paths off `/mnt/c/...`
- default rollout posture is shadow
