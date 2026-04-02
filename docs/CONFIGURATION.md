# Configuration

## Source of truth

For live Codex usage, the single authoritative runtime registration is:

- `~/.codex/config.toml`

Repository templates and helper files are examples; they are not the live control plane.

## Important runtime paths

- `RL_DEVELOPER_MEMORY_HOME`
- `RL_DEVELOPER_MEMORY_DB_PATH`
- `RL_DEVELOPER_MEMORY_STATE_DIR`
- `RL_DEVELOPER_MEMORY_BACKUP_DIR`
- `RL_DEVELOPER_MEMORY_LOG_DIR`
- `RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH`
- `RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR`

## Lifecycle and owner-key settings

These are the most important live lifecycle env values:

- `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY`
- `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV`
- `RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY`
- `RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE`
- `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES`
- `RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE`

Recommended posture:
- require owner key
- prefer `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`
- use duplicate exit code `75`
- leave global cap disabled by setting max instances to `0`

Synthetic fallback does not replace the preferred posture. `RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY=1` is a compatibility and recovery valve for runtimes that cannot yet inject the main conversation key consistently; operators should still prefer explicit main-conversation ownership whenever possible.

## Ranking and safety settings

- `RL_DEVELOPER_MEMORY_MATCH_ACCEPT_THRESHOLD`
- `RL_DEVELOPER_MEMORY_MATCH_WEAK_THRESHOLD`
- `RL_DEVELOPER_MEMORY_AMBIGUITY_MARGIN`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE`
- `RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES`
- `RL_DEVELOPER_MEMORY_ENABLE_REDACTION`
- `RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE`

## RL/control extension settings

RL features are optional and should be rolled out deliberately.

Key env values:
- `RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL`
- `RL_DEVELOPER_MEMORY_DOMAIN_MODE`
- `RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT`
- `RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT`
- `RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION`
- `RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION`
- `RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET`
- `RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT`
- `RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT`
- `RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS`

## Recommended runtime generation

Use the maintenance CLI to render the current recommended env block:

```bash
rl-developer-memory-maint recommended-config --mode shadow --format toml
rl-developer-memory-maint recommended-config --mode shadow --profile rl-control-shadow --format toml
```

## Registration helper

The Codex registration helper writes the MCP block and AGENTS guidance:

```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex
```

RL shadow example:
```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex \
  --enable-rl-control \
  --rl-rollout-mode shadow
```
