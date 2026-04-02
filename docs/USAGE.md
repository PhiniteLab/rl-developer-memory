# Usage

You can use `rl-developer-memory` through MCP or directly from Python.

## Through MCP

The MCP server is exposed as `rl_developer_memory`.

Typical retrieval flow:
1. call `issue_match`
2. inspect details with `issue_get` when needed
3. record outcomes with `issue_feedback`
4. store reusable fixes with `issue_record_resolution`

For the RL/control workflow contract, see:
- [MCP_RL_INTEGRATION_POLICY.md](MCP_RL_INTEGRATION_POLICY.md)
- [MEMORY_SCOPE_OPERATIONS_NOTE.md](MEMORY_SCOPE_OPERATIONS_NOTE.md)
- [RL_CODING_STANDARDS.md](RL_CODING_STANDARDS.md)

### Example: find a prior fix
```python
issue_match(
    error_text="ModuleNotFoundError: No module named requests",
    command="python cli.py",
    file_path="cli.py",
    project_scope="global",
)
```

### Example: store a verified fix
```python
issue_record_resolution(
    title="CLI import fails under wrong interpreter",
    raw_error="ModuleNotFoundError: No module named requests",
    canonical_fix="Run the CLI inside the project virtualenv.",
    prevention_rule="Pin the launcher to the intended interpreter.",
    verification_steps="Re-run the CLI under the project virtualenv.",
    project_scope="global",
)
```

## Through Python

```python
from rl_developer_memory.app import RLDeveloperMemoryApp

app = RLDeveloperMemoryApp()
result = app.issue_match(
    error_text="sqlite3.OperationalError: database is locked",
    command="python train.py",
    file_path="tracking/sqlite_index.py",
    project_scope="rl-lab",
)
print(result["decision"])
```

## Common maintenance commands

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint metrics --window-days 30
rl-developer-memory-maint backup
rl-developer-memory-maint review-queue --status pending --limit 20
```

## RL/control reporting commands

```bash
rl-developer-memory-maint benchmark-rl-control-reporting
rl-developer-memory-maint rl-audit-health --window-days 30 --limit 10
```

## Scope guidance

Use compact, stable scopes:
- repo-specific issues → repo-scoped `project_scope`
- broad reusable engineering issues → `global`
- user-specific tuning → `user_scope`

## Preference and session guidance

- use `issue_set_preference` for stable user or team preferences
- use `issue_list_preferences` to inspect active preference overlays
- use `session_id` on `issue_match` and `issue_feedback` for within-session reranking memory
- keep session reactions temporary; promote only verified reusable fixes with `issue_record_resolution`

## Expected next actions from `issue_match`

- `match` → inspect the top result and try the suggested fix
- `ambiguous` → compare the top one or two results and use `issue_guardrails`
- `abstain` → continue fresh debugging and record only a verified reusable fix later

## Skill installation/sync

For portable global skill sync (`.codex` and `.agents`) see `docs/SKILL_INSTALL_SYNC.md`.
Use `bash scripts/install_skill.sh --mode copy` as the default public-safe path.
