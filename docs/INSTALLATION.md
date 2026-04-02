# Installation

This guide covers the supported installation paths for `rl-developer-memory`.

## Environment requirements

### Supported platforms

- Linux
- WSL 2

### Required tools

- `git`
- `python3` with `venv`
- `pip`
- `bash`

### Optional tools

- `rsync` for faster bundle copies during `install.sh`
- `cron` / `crontab` for scheduled backups
- Codex when you want live MCP registration in `~/.codex/config.toml`

## Python packages

### Runtime packages installed by this project

- `mcp[cli]>=1.0.0,<2.0.0`
- `tomli>=2.0.1` on Python `<3.11`

### Development packages installed by `.[dev]`

- `pytest>=8.0.0`
- `pyright>=1.1.380`
- `ruff>=0.6.0`
- `build>=1.2.2`

## Recommended install

```bash
git clone https://github.com/PhiniteLab/rl-developer-memory.git
cd rl-developer-memory
bash install.sh
bash scripts/install_skill.sh --mode copy
bash scripts/verify_install.sh
```

## What `install.sh` does

1. creates install, data, state, backup, and Codex-home directories
2. copies the repository bundle into the install root
3. creates a virtual environment
4. installs the package
5. initializes the database
6. writes a calibration profile
7. creates an initial backup
8. registers the live MCP block in `~/.codex/config.toml`
9. installs cron-based backup automation unless skipped

## Installer environment toggles

- `INSTALL_ROOT` — target install directory
- `DATA_ROOT` — runtime data directory
- `STATE_ROOT` — runtime state and log directory
- `BACKUP_ROOT` — backup directory
- `CODEX_HOME` — Codex home used for config registration
- `PYTHON_BIN` — Python interpreter to use
- `SKIP_DEP_INSTALL=1` — install the editable package without resolving dependencies
- `VENV_SYSTEM_SITE_PACKAGES=1` — create the virtual environment with system packages visible
- `SKIP_CRON_INSTALL=1` — skip cron setup
- `REQUIRE_CRON_INSTALL=1` — fail the install if cron setup does not succeed
- `ENABLE_RL_CONTROL=1` — register RL/control flags in the live Codex block
- `RL_ROLLOUT_MODE=shadow|active` — choose the RL rollout mode when RL is enabled

### Example: RL shadow install

```bash
ENABLE_RL_CONTROL=1 RL_ROLLOUT_MODE=shadow bash install.sh
bash scripts/install_skill.sh --mode copy
bash scripts/verify_install.sh
```

## Manual source install

Use this when you are developing directly in the repository.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
python -m rl_developer_memory.maintenance init-db
```

If you only want runtime dependencies without developer tooling:

```bash
python -m pip install -e .
```

## First verification commands

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
python scripts/release_readiness.py --json
python scripts/rl_quality_gate.py --json
```

## Skill installation and sync

Use the portable skill installer after runtime install to expose canonical skill content to global discovery surfaces.
This does not replace runtime authority; `~/.codex/config.toml` remains authoritative.

```bash
bash scripts/install_skill.sh --mode copy
python scripts/install_skill.py --mode copy
```

Use the shell wrapper for the simplest public-facing path, or call `python scripts/install_skill.py --mode copy` directly when you want the Python entrypoint.

Available modes:
- `--mode copy` — safest public-share option
- `--mode symlink` — local development convenience
- `--mode generated` — generated discovery bundle
- `--dry-run --json` — inspect resolved targets without writing

For details, see [SKILL_INSTALL_SYNC.md](SKILL_INSTALL_SYNC.md).
