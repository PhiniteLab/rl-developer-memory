# rl-developer-memory

![rl-developer-memory cover](assets/cover.png)

`rl-developer-memory` is a **local-first MCP server for Codex** that stores reusable debugging and operational knowledge in SQLite, ranks prior fixes for recurring failures, and adds an **optional RL/control-aware audit layer** for experiment-heavy workflows.

It ships three things together:

1. a Python MCP server exposed as `rl_developer_memory`
2. a maintenance CLI named `rl-developer-memory-maint`
3. an installation and verification workflow for Codex-centered local deployments

## What the project does

- stores reusable issue patterns, variants, episodes, feedback, preferences, and review items in local SQLite
- returns compact ranked matches for recurring failures through MCP tools
- supports lifecycle, backup, restore, calibration, dashboard export, and rollout verification commands
- can operate in a generic debugging mode or in an **RL/control shadow or active posture**
- stays local-first: the runtime database, state, logs, and backups are yours

## Current public surface

- **Runtime identity:** `rl_developer_memory`
- **Package identity:** `rl-developer-memory`
- **Primary entrypoint:** `python -m rl_developer_memory.server`
- **MCP surface:** **12 tools**
- **Maintenance surface:** **28 CLI subcommands** via `rl-developer-memory-maint`
- **Live MCP authority:** `~/.codex/config.toml`

## Public MCP tools

### Retrieval and inspection
- `issue_match`
- `issue_get`
- `issue_search`
- `issue_recent`

### Write-back and feedback
- `issue_record_resolution`
- `issue_feedback`

### Preferences and prevention
- `issue_set_preference`
- `issue_list_preferences`
- `issue_guardrails`

### Operations and review
- `issue_metrics`
- `issue_review_queue`
- `issue_review_resolve`

## Maintenance CLI surface

The maintenance CLI is the operational control plane for local installs.

### Schema and bootstrap
- `init-db`
- `migrate-v2`
- `schema-version`

### Backups
- `backup`
- `list-backups`
- `verify-backup`
- `restore-backup`

### Health and lifecycle
- `smoke`
- `smoke-learning`
- `server-status`
- `runtime-diagnostics`
- `recommended-config`
- `doctor`
- `e2e-mcp-reuse-harness`

### Operations telemetry
- `metrics`
- `export-dashboard`
- `prune-retention`

### Review queue
- `review-queue`
- `resolve-review`

### Benchmarks and calibration
- `benchmark-user-domains`
- `benchmark-rl-control-reporting`
- `benchmark-failure-taxonomy`
- `benchmark-dense-bandit`
- `benchmark-real-world`
- `benchmark-hard-negatives`
- `benchmark-merge-stress`
- `calibrate-thresholds`

## Quick start

### Recommended install
```bash
git clone https://github.com/<your-user-or-org>/rl-developer-memory.git
cd rl-developer-memory
bash install.sh
bash scripts/verify_install.sh
```

That flow:
- creates the Python environment
- initializes the SQLite store
- writes a calibration profile
- creates an initial backup
- registers the live MCP block in `~/.codex/config.toml`
- verifies smoke, doctor, config, backup, calibration, and reuse behavior

### Recommended first checks
```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
```

## Install modes

### Mode A — Standard MCP install
Use `install.sh` when you want the real MCP runtime available in Codex.

Important installer toggles:
- `SKIP_DEP_INSTALL=1`
- `VENV_SYSTEM_SITE_PACKAGES=1`
- `ENABLE_RL_CONTROL=1`
- `RL_ROLLOUT_MODE=shadow|active`
- `REQUIRE_CRON_INSTALL=1`
- `SKIP_CRON_INSTALL=1`

Example RL shadow install:
```bash
ENABLE_RL_CONTROL=1 RL_ROLLOUT_MODE=shadow bash install.sh
bash scripts/verify_install.sh
```

### Mode B — Manual / source-checkout workflow
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
python -m rl_developer_memory.maintenance init-db
python -m rl_developer_memory.server
```

If you choose the manual path, you must still create exactly one live `[mcp_servers.rl_developer_memory]` block in `~/.codex/config.toml`.

## RL/control support

The repository can operate in two practical modes:

- **generic mode** for broad engineering failures
- **RL/control mode** for experiment, theory, sim2real, and control-audit-heavy workflows

Recommended rollout order:
1. install in normal shadow posture
2. enable RL shadow profile
3. verify `doctor --profile rl-control-shadow`
4. verify `benchmark-rl-control-reporting`
5. inspect `rl-audit-health`
6. only then consider an active RL rollout

## Live runtime rules

- keep exactly one live `[mcp_servers.rl_developer_memory]` block in `~/.codex/config.toml`
- keep the active database on the local Linux or WSL filesystem
- prefer explicit `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` injection per main conversation
- treat duplicate exit code `75` as a reuse signal, not as a generic failure
- keep calibration profiles and backups current

## Validation and quality

Current repository expectations:
```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m build
```

The repository also ships a CI workflow that runs these core gates automatically on push and pull request.

## Documentation map

- [docs/README.md](docs/README.md) — documentation index
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — install and first-run workflow
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) — runtime configuration model
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — health, backup, restore, and lifecycle operations
- [docs/ROLLOUT.md](docs/ROLLOUT.md) — shadow/active rollout guidance
- [docs/USAGE.md](docs/USAGE.md) — MCP and Python usage patterns
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — runtime/data-flow overview
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — contributor workflow
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — supported environments
- [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) — dependency posture
- [docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md](docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md) — owner-key model
- [docs/ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md](docs/ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md) — reuse validation checklist

## Contributing and support

- Contributor guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Support guidance: [SUPPORT.md](SUPPORT.md)
- Security policy: [SECURITY.md](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
