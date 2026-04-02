# Repo delta: RL MCP workflow contract

This repository treats `rl_developer_memory` as a **local-first MCP memory and audit surface**
for RL/control development, not as a replacement for normal debugging discipline.

## Live runtime authority

- Treat `~/.codex/config.toml` as the **only live runtime authority**.
- Repository configs under `configs/` and helper scripts are examples, not live authority.

## Runtime posture invariants

- Prefer `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` for main-conversation ownership.
- Keep **owner-key required** posture.
- Treat duplicate exit code **`75`** as a **reuse signal**, not a crash.
- Keep global max instance cap semantics aligned with **`0`**.
- Default rollout posture is **shadow**.
- Keep active DB paths on the local Linux/WSL filesystem; do **not** use `/mnt/c/...`.
- Preserve redaction hygiene for secrets, tokens, env excerpts, and sensitive local paths.

## Agent-oriented orchestration guidance

- For the recommended Codex RL work model, see `docs/CODEX_RL_AGENT_OPERATING_MODEL.md`.
- Keep `AGENTS.md` as a short delta contract; put longer role/orchestration guidance in docs.

Additional operator-facing policy notes:
- For portable skill install/sync across global `.codex` and `.agents`, see `docs/SKILL_INSTALL_SYNC.md`.
- `docs/MEMORY_SCOPE_OPERATIONS_NOTE.md` for scope and verified write-back hygiene
- `docs/RL_CODING_STANDARDS.md` for RL coding and delivery expectations

## RL development MCP flow

1. **Before coding or triage expansion**
   - Use `issue_match` with the shortest stable symptom, command, file path, and `project_scope`.
   - If ambiguous, inspect only the top one or two candidates with `issue_get`.
   - Use `issue_guardrails` when you need prevention rules, preference overlays, or policy reminders.

2. **During implementation and validation**
   - Use normal repo-native validation first.
   - After a meaningful accepted/rejected attempt, use `issue_feedback`.
   - Use `session_id` to keep in-turn ranking memory local to the active debugging session.

3. **Only after verification**
   - Write durable fixes with `issue_record_resolution` only for reusable, verified resolutions.
   - Never store raw secrets, unredacted env dumps, or one-off noisy workarounds.

## Scope contract

- `project_scope`: repo-specific RL workflows, config, import, rollout, theorem/code, checkpoint, benchmark, or validator issues
- `global`: broad reusable engineering fixes not tied to this repo
- `user_scope`: user-specific coding style, review preferences, tuning habits, or preference overlays

## Preference and session contract

- Use `issue_set_preference` for stable user/team preferences.
- Use `issue_list_preferences` to inspect active preference overlays.
- Use `session_id` on `issue_match` and `issue_feedback` for temporary within-session ranking memory.
- Do not promote transient session reactions directly into durable pattern memory.

## Write-back rule

Persist a resolution only when all of the following are true:
- the symptom is real and non-hypothetical
- the fix is specific and reusable
- the fix passed relevant validation
- the stored summary is redacted and compact
- the chosen scope is explicit and justified

