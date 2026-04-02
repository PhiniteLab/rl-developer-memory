# Installation

This guide covers the supported installation paths for `rl-developer-memory`.

## Requirements

- Linux or WSL 2
- Python 3.10+
- a writable local filesystem for the active database and state directories
- Codex when you want live MCP registration

## Recommended install

```bash
git clone https://github.com/<your-user-or-org>/rl-developer-memory.git
cd rl-developer-memory
bash install.sh
bash scripts/install_skill.sh --mode copy
bash scripts/verify_install.sh
```

## What `install.sh` does

1. creates install, data, state, backup, and Codex-home directories
2. copies the repository into the install root
3. creates a virtualenv
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
- `CODEX_HOME` — Codex home for config registration
- `PYTHON_BIN` — Python interpreter to use
- `SKIP_DEP_INSTALL=1` — install editable package without resolving deps
- `VENV_SYSTEM_SITE_PACKAGES=1` — create the venv with system packages visible
- `SKIP_CRON_INSTALL=1` — skip cron setup
- `REQUIRE_CRON_INSTALL=1` — fail install if cron setup does not succeed
- `ENABLE_RL_CONTROL=1` — register RL-control flags in the live Codex block
- `RL_ROLLOUT_MODE=shadow|active` — choose RL rollout mode when RL is enabled

Example RL shadow install:
```bash
ENABLE_RL_CONTROL=1 RL_ROLLOUT_MODE=shadow bash install.sh
bash scripts/install_skill.sh --mode copy
bash scripts/verify_install.sh
```

## Skill install/sync to global surfaces

Use the skill installer after runtime install to expose canonical skill content to global discovery surfaces.
This does not replace runtime authority; `~/.codex/config.toml` remains authoritative.

```bash
bash scripts/install_skill.sh --mode copy
```

- `--mode copy` (default): public-share friendly and robust
- `--mode symlink`: local-dev convenience
- `--mode generated`: smaller generated discovery bundle
- `--dry-run --json`: inspect resolved targets without writing

See `docs/SKILL_INSTALL_SYNC.md` for details.

## Manual development install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
python -m rl_developer_memory.maintenance init-db
```

## After install

Recommended first checks:
```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
python scripts/release_acceptance.py --json
python scripts/rl_quality_gate.py --json
```

## Verification script

`scripts/verify_install.sh` validates:
- smoke path
- benchmark-user-domains execution
- standard doctor
- RL doctor when RL flags are active
- Codex config block presence and required env values
- calibration profile existence
- backup availability
- AGENTS snippet presence
- end-to-end reuse harness when the MCP runtime is importable

## RL rollout registration semantics

- `--enable-rl-control --rl-rollout-mode shadow` keeps the RL domain in a conservative shadow posture.
- `--enable-rl-control --rl-rollout-mode active` writes the stricter active domain mode.
- In both cases, the preferred owner-key env remains `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`.
- Verification should still start from shadow-oriented doctor checks unless live active signoff is explicitly intended.
