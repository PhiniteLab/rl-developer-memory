# Configuration

`rl-developer-memory` is configured through environment variables plus one live Codex MCP registration.

## Public configuration model

The live public model is:

- the authoritative MCP registration is the single `rl_developer_memory` block in `~/.codex/config.toml`
- the live custom plugin / skill root is `~/.codex/local-plugins/**`
- example files under `templates/` are reference snippets only
- runtime defaults come from `src/rl_developer_memory/settings.py`

## Live Codex registration

The repository's registration helper writes a block like this into `~/.codex/config.toml`:

```toml
[mcp_servers.rl_developer_memory]
command = "/path/to/install/.venv/bin/python"
args = ["-m", "rl_developer_memory.server"]
cwd = "/path/to/install"
startup_timeout_sec = 15
tool_timeout_sec = 25
enabled = true
required = false

[mcp_servers.rl_developer_memory.env]
RL_DEVELOPER_MEMORY_HOME = "/path/to/data"
RL_DEVELOPER_MEMORY_DB_PATH = "/path/to/data/rl_developer_memory.sqlite3"
RL_DEVELOPER_MEMORY_STATE_DIR = "/path/to/state"
RL_DEVELOPER_MEMORY_BACKUP_DIR = "/path/to/data/backups"
RL_DEVELOPER_MEMORY_LOG_DIR = "/path/to/state/log"
RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR = "/path/to/state/run"
RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE = "75"
RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"
RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"
RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE = "0"
RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"
RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"
RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"
RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES = "1"
RL_DEVELOPER_MEMORY_ENABLE_REDACTION = "1"
RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE = "1"
RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH = "/path/to/state/calibration_profile.json"
# Optional RL/control scaffold:
# RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"
# RL_DEVELOPER_MEMORY_DOMAIN_MODE = "hybrid"
# RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT = "1"
# RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT = "1"
# RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION = "1"
# RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT = "3"
# RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS = "12"
```

Keep exactly one `[mcp_servers.rl_developer_memory]` block in `~/.codex/config.toml`.

## Install-time configuration

These variables are read by `install.sh`.

| Variable | Purpose | Default | Notes |
| --- | --- | --- | --- |
| `INSTALL_ROOT` | Installed bundle location | `~/infra/rl-developer-memory` | Editable installed copy used by the generated MCP block |
| `DATA_ROOT` | Runtime data home | `~/.local/share/rl-developer-memory` | Holds the live SQLite database |
| `STATE_ROOT` | State and log home | `~/.local/state/rl-developer-memory` | Holds state files and logs |
| `BACKUP_ROOT` | Local snapshot directory | `DATA_ROOT/backups` | Local backup destination |
| `WINDOWS_BACKUP_TARGET` | Optional mirrored backup destination | unset | Mirror only; do not use as the live writable DB |
| `CODEX_HOME` | Codex home directory | `~/.codex` | Live config block is written here |
| `PYTHON_BIN` | Python executable used to create the virtualenv | `python3` | Installer helper |
| `SKIP_DEP_INSTALL` | Install with `--no-deps` | `0` | Installer helper |
| `SKIP_CRON_INSTALL` | Skip cron installation | `0` | Installer helper |

### Generated artifacts

After installation, the main generated artifacts are:

- `INSTALL_ROOT/config/install.env`
- `DATA_ROOT/rl_developer_memory.sqlite3`
- `BACKUP_ROOT/`
- `STATE_ROOT/log/`
- `~/.codex/config.toml`
- `~/.codex/AGENTS.md`

If you rely on a custom plugin or skill wrapper, keep the live asset under `~/.codex/local-plugins/**`.

## Runtime source of truth

`Settings.from_env()` in `src/rl_developer_memory/settings.py` is the runtime source of truth. It:

- expands `~`
- applies defaults
- creates required directories
- resolves the current owner-key requirement and any optional compatibility cap
- enables or disables optional overlays and safety controls

## Core paths

| Variable | Purpose | Default |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_HOME` | Root directory for runtime data | `~/.local/share/rl-developer-memory` |
| `RL_DEVELOPER_MEMORY_DB_PATH` | SQLite database file | `RL_DEVELOPER_MEMORY_HOME/rl_developer_memory.sqlite3` |
| `RL_DEVELOPER_MEMORY_STATE_DIR` | State directory | `~/.local/state/rl-developer-memory` |
| `RL_DEVELOPER_MEMORY_LOG_DIR` | Log directory | `RL_DEVELOPER_MEMORY_STATE_DIR/log` |
| `RL_DEVELOPER_MEMORY_BACKUP_DIR` | Local backup directory | `RL_DEVELOPER_MEMORY_HOME/backups` |
| `RL_DEVELOPER_MEMORY_WINDOWS_BACKUP_TARGET` | Optional mirrored backup path | unset |
| `RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH` | Saved calibration profile | `RL_DEVELOPER_MEMORY_STATE_DIR/calibration_profile.json` |

## MCP process lifecycle

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY` | runtime default `0`, recommended registration `1` | Refuse startup unless the launcher provides an owner key |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` | empty | Preferred launcher-facing owner key for one main conversation |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY_ENV` | empty | Optional indirection alias for the preferred main-conversation key |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY` | empty | Secondary compatibility direct owner key |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY_ENV` | empty | Secondary compatibility indirection alias |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE` | empty | Preferred launcher-facing diagnostics label such as `main` or `subagent` |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY` | empty | Low-level compatibility alias for a direct owner key |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV` | empty | Low-level compatibility alias: name of another env var that contains the owner key |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_ROLE` | empty | Low-level compatibility alias for owner-role diagnostics |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_ROLE` | empty | Secondary compatibility role diagnostic alias |
| `RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY` | `0` | Allow a generated process-scoped owner key when no explicit/derived key is available; diagnostics label it as `RL_DEVELOPER_MEMORY_SYNTHETIC_OWNER_KEY` |
| `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES` | compatibility fallback; recommended value `0` | Optional global ceiling for concurrently alive MCP stdio processes; `0` disables the global cap |
| `RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE` | compatibility fallback | Legacy single-instance behavior when you intentionally want one total process |
| `RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR` | `RL_DEVELOPER_MEMORY_STATE_DIR/run` | Lock directory for owner-key dedup |
| `RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE` | `75` | Exit code used when a duplicate launch is rejected for an already-owned conversation |

The recommended invariant is:

- every main Codex conversation gets one stable owner key
- the first process for that owner key starts normally
- a second process for the same owner key is rejected with exit code `75`
- different owner keys may coexist without a global total cap

## Conversation-owner integration

The recommended setup is **one server per main Codex conversation** with no global total cap.

Current repository resolution order is:

1. explicit owner vars: `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`, `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY`, `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY`
2. alias vars: `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY_ENV`, `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV`, `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY_ENV`
3. `CODEX_THREAD_ID` lineage root resolution
4. parent-process lineage scan (environment + session lineage inheritance)
5. recent-session inference (safe single-owner inference from newest local sessions)
6. optional synthetic fallback (`RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY=1`)

If explicit injection is unavailable, allow Codex/launcher-derived lineage to flow through `CODEX_THREAD_ID`.

Public launch-time variables:

| Variable | Purpose |
| --- | --- |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` | Preferred launcher-facing owner key. All launches for one main conversation, including subagents, should use the same value. |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY_ENV` | Optional indirection alias for the preferred main-conversation key. |
| `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE` | Preferred launcher-facing role label such as `main` or `subagent`. |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY` | Low-level compatibility alias for a direct owner key. |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV` | Low-level compatibility alias for owner-key indirection. |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY` | Secondary compatibility direct owner key. |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY_ENV` | Secondary compatibility indirection alias. |
| `RL_DEVELOPER_MEMORY_SERVER_OWNER_ROLE` | Low-level compatibility alias for role diagnostics. |
| `RL_DEVELOPER_MEMORY_MCP_OWNER_ROLE` | Secondary compatibility alias for role diagnostics. |
| `RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY` | Optional synthetic fallback switch (`0` or `1`). |

Preferred launcher contract:

- preferably inject `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` into every MCP child launch
- if explicit injection is unavailable, let the runtime derive the root main-conversation key from `CODEX_THREAD_ID` session lineage / parent inference chain
- make sure subagents resolve to the same main-conversation owner key
- optionally inject `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE=main|subagent` for diagnostics
- for synthetic fallback cases, the runtime derives a process-scoped fallback key as `synthetic-process-<ppid>-<pid>` and reports its source label as `RL_DEVELOPER_MEMORY_SYNTHETIC_OWNER_KEY`

How the current repo behaves when a main-conversation owner key is present:

- the first launch for that owner key is allowed
- a second concurrent launch with the **same** owner key is rejected before consuming another process slot
- the rejecting process exits with `RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE` (default `75`)
- `rl-developer-memory-maint server-status` exposes the active slot `owner_key` and `owner_role`
- when `CODEX_THREAD_ID` lineage is available, inferred role is `main` for root conversations and `subagent` for non-root threads; synthetic fallback roles are `anonymous`

What this repo does **not** do by itself:

- invent a reliable conversation key
- map subagents to their parent conversation automatically
- attach a new stdio client to an already-running process

So the required Codex-side contract is:

1. resolve one stable owner key per main conversation, using the same resolution chain (explicit, aliases, lineage, parent, recent sessions, optional synthetic)
2. make sure any subagent launch resolves to that same main-conversation key
3. treat duplicate exit code `75` as a **reuse / dedup signal**, not as an uncontrolled crash
4. route the subagent through the already-owned conversation MCP instead of retrying new launches

If you still want a bounded total-process ceiling for a specific deployment, you may set `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES` to a positive integer. That global cap is now a compatibility option rather than the recommended default.

## Lifecycle status fields to observe

`rl-developer-memory-maint server-status` returns structured lifecycle state:

- aggregate fields: `running`, `active_count`, `active_slots`, `status_path`, `lock_path`, `max_instances`, `launch_count`, `enforce_single_instance`, `db_path`, `state_dir`
- additional aggregate diagnostics: `assigned_slot`, `pid`, `parent_pid`, `command`, `process_alive`
- each `active_slots[]` item includes:
  - `slot`, `pid`, `parent_pid`, `process_alive`
  - `lock_path`, `status_path`, `command`
  - `owner_key`, `owner_key_env`, `owner_role`
  - `started_at`, `initialized_at`


## Matching and decision thresholds

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_MATCH_ACCEPT_THRESHOLD` | `0.68` | Threshold for a confident `match` |
| `RL_DEVELOPER_MEMORY_MATCH_WEAK_THRESHOLD` | `0.40` | Threshold for `ambiguous` vs `abstain` |
| `RL_DEVELOPER_MEMORY_AMBIGUITY_MARGIN` | `0.09` | Required score gap before accepting a clear winner |
| `RL_DEVELOPER_MEMORY_SESSION_TTL_SECONDS` | `21600` | TTL for session-local acceptance and rejection memory |
| `RL_DEVELOPER_MEMORY_TELEMETRY_ENABLED` | enabled | Store retrieval events and candidate snapshots |

## Dense retrieval

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_DENSE_RETRIEVAL` | enabled | Turn dense retrieval on or off |
| `RL_DEVELOPER_MEMORY_DENSE_EMBEDDING_DIM` | `192` | Dense embedding dimension |
| `RL_DEVELOPER_MEMORY_DENSE_CANDIDATE_LIMIT` | `16` | Dense candidate shortlist size |
| `RL_DEVELOPER_MEMORY_DENSE_SIMILARITY_FLOOR` | `0.12` | Minimum similarity required for a dense hit |
| `RL_DEVELOPER_MEMORY_DENSE_MODEL_NAME` | `hash-ngrams-v1` | Stored embedding model label |

## Strategy overlay and live-override safety

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT` | disabled by runtime default, enabled by the installer | Enable the strategy-based ranking overlay |
| `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE` | disabled by runtime default, enabled by the installer | Keep the strategy overlay observational-only rather than allowing live reordering |
| `RL_DEVELOPER_MEMORY_STRATEGY_OVERLAY_SCALE` | `0.20` | Strategy-level contribution |
| `RL_DEVELOPER_MEMORY_VARIANT_OVERLAY_SCALE` | `0.08` | Variant-level contribution |
| `RL_DEVELOPER_MEMORY_SAFE_OVERRIDE_MARGIN` | `0.03` | Required margin before a live override is allowed |
| `RL_DEVELOPER_MEMORY_MINIMUM_STRATEGY_EVIDENCE` | `3` | Minimum evidence required before strategy data can promote a candidate |
| `RL_DEVELOPER_MEMORY_STRATEGY_HALF_LIFE_DAYS` | `75` | Decay half-life for strategy statistics |
| `RL_DEVELOPER_MEMORY_VARIANT_HALF_LIFE_DAYS` | `35` | Decay half-life for variant statistics |

## Preferences and guardrails

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES` | enabled | Apply prompt-driven user / repo / global preference overlays |
| `RL_DEVELOPER_MEMORY_PREFERENCE_OVERLAY_SCALE` | `1.0` | Preference-rule scoring multiplier |
| `RL_DEVELOPER_MEMORY_MAX_PREFERENCE_ADJUSTMENT` | `0.18` | Maximum absolute preference adjustment applied to one candidate |
| `RL_DEVELOPER_MEMORY_GUARDRAIL_LIMIT` | `5` | Maximum number of guardrail items returned by `issue_guardrails` |
| `RL_DEVELOPER_MEMORY_DEFAULT_USER_SCOPE` | empty | Default user-scope overlay key when not supplied per call |

## RL-control domain extension

These flags now drive the active RL/control extension: retrieval-time audit, persisted experiment/theory audit hardening, and review-gated promotion.

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL` | disabled | Turn on RL/control domain-aware normalization, retrieval, and storage behavior |
| `RL_DEVELOPER_MEMORY_DOMAIN_MODE` | `generic` | Domain mode: `generic`, `hybrid`, or `rl_control` |
| `RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT` | disabled | Enable theory-oriented audit hardening for stored and retrieved RL/control candidates |
| `RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT` | disabled | Enable experiment/runtime audit hardening for stored and retrieved RL/control candidates |
| `RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION` | enabled | Keep validation-tier decisions conservative when audit findings are present |
| `RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION` | enabled | Require review-queue approval before promoting to `validated`, `theory_reviewed`, or `production_validated` |
| `RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET` | `2` | Maximum warning count allowed before a candidate-tier write is downgraded to observed |
| `RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT` | `3` | Minimum seed count expected before `validated` promotion is considered |
| `RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT` | `5` | Stronger minimum seed count expected before `production_validated` promotion is considered |
| `RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS` | `12` | Max artifact reference count accepted by RL metadata validators |

Recommended first opt-in for shadow use:

- `RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"`
- `RL_DEVELOPER_MEMORY_DOMAIN_MODE = "hybrid"`
- `RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT = "1"`
- keep `RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION = "1"`


## Backups, metrics, retention, and review queue

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_LOCAL_BACKUP_KEEP` | `30` | Number of local snapshots to retain |
| `RL_DEVELOPER_MEMORY_MIRROR_BACKUP_KEEP` | `15` | Number of mirrored snapshots to retain |
| `RL_DEVELOPER_MEMORY_TELEMETRY_RETENTION_DAYS` | `90` | Retention window for retrieval telemetry |
| `RL_DEVELOPER_MEMORY_RESOLVED_REVIEW_RETENTION_DAYS` | `120` | Retention window for resolved review queue items |

`issue_metrics` summarizes the operational state of:

- retrieval and verification behavior
- preference rule hits
- strategy overlay behavior
- review queue size
- backup freshness
- calibration profile status

## Safety and redaction

| Variable | Default | Purpose |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_REDACTION` | enabled | Redact secrets from env JSON, notes, and verification output |
| `RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE` | enabled | Load a saved calibration profile if present |
| `RL_DEVELOPER_MEMORY_ENV_JSON_MAX_CHARS` | `4000` | Max stored chars from `env_json` |
| `RL_DEVELOPER_MEMORY_VERIFICATION_OUTPUT_MAX_CHARS` | `4000` | Max stored chars from verification output |
| `RL_DEVELOPER_MEMORY_NOTE_MAX_CHARS` | `2000` | Max stored chars from notes |

## Recommended public default

The current recommended default configuration is:

- one `rl_developer_memory` MCP block in `~/.codex/config.toml`
- `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"`
- `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"`
- `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"`
- `RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE = "0"`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_REDACTION = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE = "1"`
- leave RL/control scaffold flags disabled unless you are explicitly testing the domain extension

## Example runtime override

```bash
export RL_DEVELOPER_MEMORY_HOME="$HOME/.local/share/rl-developer-memory"
export RL_DEVELOPER_MEMORY_DB_PATH="$RL_DEVELOPER_MEMORY_HOME/rl_developer_memory.sqlite3"
export RL_DEVELOPER_MEMORY_STATE_DIR="$HOME/.local/state/rl-developer-memory"
export RL_DEVELOPER_MEMORY_BACKUP_DIR="$HOME/.local/share/rl-developer-memory/backups"
export RL_DEVELOPER_MEMORY_LOG_DIR="$RL_DEVELOPER_MEMORY_STATE_DIR/log"
export RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR="$RL_DEVELOPER_MEMORY_STATE_DIR/run"
export RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE=75
export RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY=1
export RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV=RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY
export RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES=0
export RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT=1
export RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE=1
export RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES=1
export RL_DEVELOPER_MEMORY_ENABLE_REDACTION=1
# Optional RL/control scaffold (shadow-only in PR-2):
# export RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL=1
# export RL_DEVELOPER_MEMORY_DOMAIN_MODE=hybrid
# export RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT=0
# export RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT=0

# Dynamic launch-time wiring from Codex:
# export RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY="$STABLE_MAIN_CONVERSATION_KEY"
# export RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE="main"
```

## Path behavior

The runtime path model is intentionally cwd-independent.

That means:

- the live database path does not depend on shell cwd
- backups and logs do not depend on shell cwd
- install-time path decisions can be propagated into the live MCP block without editing Python code

For SQLite safety, keep the live database inside the Linux or WSL filesystem. Use Windows or cloud locations only as backup mirrors, not as the active writable database.

## RL/control rollout profiles

The maintenance helper now supports explicit rollout profiles:

- `default`
- `rl-control-shadow`
- `rl-control-active`

Examples:

```bash
rl-developer-memory-maint recommended-config --mode shadow --profile rl-control-shadow
rl-developer-memory-maint doctor --mode shadow --profile rl-control-shadow
```

`rl-control-shadow` injects the conservative RL/control flag set:

- `RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"`
- `RL_DEVELOPER_MEMORY_DOMAIN_MODE = "hybrid"`
- `RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT = "1"`
- `RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION = "1"`

`rl-control-active` switches the domain mode to `rl_control` while keeping the same audit and review-gated promotion posture.

## Registration helper RL flags

`scripts/register_codex.py` now supports:

- `--enable-rl-control`
- `--rl-rollout-mode shadow|active`

This writes the RL/control env block directly into the live `rl_developer_memory` registration instead of leaving RL enablement as a manual post-edit step.
