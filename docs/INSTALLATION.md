# Installation

`rl-developer-memory` is documented for Linux and WSL environments with Python 3.10+.

## Before you start

Public users should keep these rules in mind:

- the authoritative MCP registration is the single `rl_developer_memory` block in `~/.codex/config.toml`
- the live custom plugin / skill root is `~/.codex/local-plugins/**`
- bundled skill content in this repository is reference-only; any live custom wrapper should live under `~/.codex/local-plugins/**`
- example files in this repository are reference material, not live registration
- this repository includes `~/.codex/local-plugins`-friendly wrapper files (`.codex-plugin/plugin.json` and `.mcp.json`) for distribution only

`README.md` documents two install modes:

- **Mode A:** standard MCP install (writes live `~/.codex/config.toml` registration)
- **Mode B:** plugin-wrapper/local plugin install (kept as distribution/reference assets)

Mode B alone does not create the live Python environment or authoritative MCP registration; keep using Mode A or the documented manual `config.toml` flow for the actual server runtime.

## Requirements

Required:

- `bash`
- `git`
- `python3`
- `python3-venv`
- `python3-pip`
- a working Codex installation if you want MCP integration

Optional but useful:

- `rsync` for cleaner install-root syncs
- `cron` for scheduled backups
- `sqlite3` for manual inspection

For Ubuntu-based Linux or WSL:

```bash
sudo apt update
sudo apt install -y git bash python3 python3-venv python3-pip
```

Optional extras:

```bash
sudo apt install -y rsync cron sqlite3
```

## Recommended installed setup

Replace `<your-user-or-org>` with your GitHub account or organization name for your public repository.

```bash
git clone https://github.com/<your-user-or-org>/rl-developer-memory.git
cd rl-developer-memory
bash install.sh
```

The repository installer prepares an installed bundle, database, and Codex-facing configuration files. After it runs, treat these as the live public surfaces:

- `~/.codex/config.toml` for MCP registration
- `~/.codex/AGENTS.md` for home-level instructions
- `~/.codex/local-plugins/**` for live custom plugin / skill assets

By default, the installer uses:

- install root: `~/infra/rl-developer-memory`
- data root: `~/.local/share/rl-developer-memory`
- state root: `~/.local/state/rl-developer-memory`
- backup root: `~/.local/share/rl-developer-memory/backups`
- Codex home: `~/.codex`

### What the installer prepares

1. an install root with a Python virtual environment
2. the SQLite database and state directories
3. a generated `config/install.env` inside the installed bundle
4. an `rl_developer_memory` MCP server registration in `~/.codex/config.toml`
5. rl-developer-memory workflow guidance in `~/.codex/AGENTS.md`
6. backup helpers and optional cron integration

The repository still contains bundled skill content under `skills/`, but public users should treat `~/.codex/local-plugins/**` as the live custom skill / plugin root.
The `.mcp.json` file is a template surface (`remote` + `local command`) and does **not** replace the authoritative `~/.codex/config.toml` MCP registration.

## Verify the live setup

After installation, restart Codex and verify the public surfaces:

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
rl-developer-memory-maint metrics --window-days 14
grep -n '^\[mcp_servers.rl_developer_memory\]' ~/.codex/config.toml
```

Check that:

- `~/.codex/config.toml` contains exactly one `[mcp_servers.rl_developer_memory]` block
- the block points at the installed Python entrypoint and current runtime paths
- the generated env sets `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"`
- the generated env sets `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"`
- the generated env sets `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"`
- the generated env includes `RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR` and duplicate exit code `75`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"`
- preference rules, redaction, and calibration are enabled
- any live custom plugin or skill asset you rely on is under `~/.codex/local-plugins/**`

The intended live integration is:

- Codex resolves one stable owner key per main conversation
- the preferred path is explicit `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` injection for main and subagent launches
- current Codex runtimes can also derive that key from `CODEX_THREAD_ID` session lineage
- `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`, `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY`, and `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY` are still supported aliases when needed
- fallback is attempted in this order when explicit injection is unavailable:
  - alias envs (`..._KEY_ENV`)
  - parent-process lineage
  - recent-session inference
  - optional synthetic fallback (`RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY`)
- subagents for the same conversation must resolve to the same owner key
- duplicate exit code `75` is treated as a reuse signal for the already-owned conversation MCP

## Common installer overrides

You can override installer defaults with environment variables:

```bash
INSTALL_ROOT="$HOME/infra/rl-developer-memory" \
DATA_ROOT="$HOME/.local/share/rl-developer-memory" \
STATE_ROOT="$HOME/.local/state/rl-developer-memory" \
CODEX_HOME="$HOME/.codex" \
SKIP_CRON_INSTALL=1 \
bash install.sh
```

Useful toggles:

- `SKIP_CRON_INSTALL=1`
  Skip cron setup.
- `SKIP_DEP_INSTALL=1`
  Install the package without resolving dependencies.
- `VENV_SYSTEM_SITE_PACKAGES=1`
  Create the install virtual environment with `--system-site-packages`. This is mainly useful for offline verification runs when the base interpreter already has the MCP runtime installed.
- `WINDOWS_BACKUP_TARGET=/mnt/c/...`
  Mirror backups to a Windows-visible path while keeping the live database inside Linux or WSL storage.

## Manual setup

Use this path if you want to run the package from a checkout without the opinionated installer.

### 1. Install the package

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
```

### 2. Configure runtime paths

```bash
export RL_DEVELOPER_MEMORY_HOME="$HOME/.local/share/rl-developer-memory"
export RL_DEVELOPER_MEMORY_DB_PATH="$RL_DEVELOPER_MEMORY_HOME/rl_developer_memory.sqlite3"
export RL_DEVELOPER_MEMORY_STATE_DIR="$HOME/.local/state/rl-developer-memory"
export RL_DEVELOPER_MEMORY_BACKUP_DIR="$RL_DEVELOPER_MEMORY_HOME/backups"
export RL_DEVELOPER_MEMORY_LOG_DIR="$RL_DEVELOPER_MEMORY_STATE_DIR/log"
```

### 3. Initialize the database

```bash
python -m rl_developer_memory.maintenance init-db
```

### 4. Run the server

```bash
python -m rl_developer_memory.server
```

### 5. Register one live MCP block in Codex

Add a single `rl_developer_memory` MCP block to `~/.codex/config.toml` that launches:

```bash
python -m rl_developer_memory.server
```

Use the example snippets in `templates/` only as references. The live source of truth remains `~/.codex/config.toml`.

### 6. Optional custom plugin / skill asset

If you want a live custom plugin or skill wrapper for Codex, install it under:

```text
~/.codex/local-plugins/**
```

The repository's `skills/rl-developer-memory-self-learning/` directory is bundled reference content. If you install a live custom wrapper, keep it under `~/.codex/local-plugins/**`.

## Path safety

Keep the live SQLite database inside the Linux or WSL filesystem:

- recommended: `~/.local/share/rl-developer-memory/rl_developer_memory.sqlite3`

Avoid these locations for the active writable database:

- `/mnt/c/...`
- cloud-synced live folders
- network-mounted directories

These are acceptable for backup mirrors, but not ideal for the main writable SQLite file.

## Common installation problems

### `config/install.env: No such file or directory`

- Cause: `scripts/verify_install.sh` was run from a fresh clone instead of the installed copy.
- Fix: run the script from `INSTALL_ROOT`, or use the public runtime checks shown above instead.

### `crontab not found`

- Cause: cron is not installed.
- Fix: install cron or use `SKIP_CRON_INSTALL=1`.

### Codex does not show `rl_developer_memory`

- Restart Codex after installation.
- Inspect `~/.codex/config.toml` and confirm there is exactly one `[mcp_servers.rl_developer_memory]` block.
- Run `rl-developer-memory-maint doctor --mode shadow --max-instances 0`.
- Confirm the configured command points to the correct Python environment.

### Custom plugin or skill content seems ignored

- Confirm you are using `~/.codex/local-plugins/**` for live custom assets.
- Restart Codex after changing plugin or MCP configuration.
