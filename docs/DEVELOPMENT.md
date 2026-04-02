# Development

This guide is for contributors working from a source checkout.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
```

This gives you:

- the package in editable mode
- the MCP dependency stack
- `pytest`
- `ruff`
- `pyright`
- `build`

The repository also includes `pyrightconfig.json`. The default development extra now installs both `ruff` and `pyright` so local checks and CI can use the same toolchain.

## Useful commands

Run the test suite:

```bash
python -m pytest
```

Run fast static checks:

```bash
ruff check .
pyright
```


Run smoke checks:

```bash
python -m rl_developer_memory.maintenance smoke
python -m rl_developer_memory.maintenance smoke-learning
```

Inspect operations and diagnostics:

```bash
python -m rl_developer_memory.maintenance server-status
python -m rl_developer_memory.maintenance metrics --window-days 14
python -m rl_developer_memory.maintenance runtime-diagnostics
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
python -m rl_developer_memory.maintenance benchmark-real-world
python -m rl_developer_memory.maintenance benchmark-hard-negatives
python -m rl_developer_memory.maintenance benchmark-merge-stress
```

Run the MCP server directly:

```bash
python -m rl_developer_memory.server
```

Show local tool help:

```bash
python -m rl_developer_memory.maintenance --help
python scripts/register_codex.py --help
python scripts/e2e_mcp_reuse_harness.py --json
```

## Repository layout

Top-level responsibilities:

- `pyproject.toml`: package metadata, console entrypoints, and pytest configuration
- `install.sh`: convenience installer for local Codex-oriented setups
- `src/rl_developer_memory/`: runtime package and maintenance CLI
- `scripts/`: setup and helper scripts
- `docs/`: public and contributor documentation
- `skills/`: bundled reference skill content shipped with the repository
- `templates/`: example config and helper templates
- `tests/`: regression, lifecycle, diagnostics, and benchmark coverage

## Source-of-truth guidance

When you touch install, configuration, or docs surfaces, keep these distinctions clear:

- the live MCP registration is the single `[mcp_servers.rl_developer_memory]` block in `~/.codex/config.toml`
- live custom skill or plugin assets belong under `~/.codex/local-plugins/**`
- bundled skill content in this repository is reference-only; any live custom wrapper should live under `~/.codex/local-plugins/**`
- repository templates are examples
- repository `skills/` content is bundled source material, not the live Codex bootstrap state

Do not edit the bundled `skills/rl-developer-memory-self-learning/` copy as though it were the live runtime source of truth.

## Validation expectations

For most code changes, run:

1. `python -m pytest`
2. `python -m rl_developer_memory.maintenance smoke`

Recommended additional checks when relevant:

- `python -m rl_developer_memory.maintenance smoke-learning`
- `python -m rl_developer_memory.maintenance server-status`
- `python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json`
- `python -m rl_developer_memory.maintenance metrics --window-days 14`
- `pyright`
- `build`
- targeted benchmark commands if you changed retrieval, learning, or consolidation behavior

For public-facing documentation updates:

- verify `README.md` reflects the same MCP/Maintenance surfaces as code
- run at least:
  - `python -m rl_developer_memory.maintenance server-status`
  - `python -m rl_developer_memory.maintenance smoke`
  - `python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json`
- confirm the installed `~/.codex/config.toml` MCP block matches the documented launch model

If you changed installation, registration, backup, or path logic:

1. test `bash install.sh` in a temporary directory
2. inspect the generated `~/.codex/config.toml`-equivalent output in the temp Codex home
3. run the installed `scripts/verify_install.sh`
4. confirm the docs still describe the public live surfaces correctly

## Temporary install check

```bash
tmpdir="$(mktemp -d)"

INSTALL_ROOT="$tmpdir/install" DATA_ROOT="$tmpdir/data" STATE_ROOT="$tmpdir/state" CODEX_HOME="$tmpdir/codex-home" SKIP_CRON_INSTALL=1 PYTHON_BIN=python3 bash install.sh

bash "$tmpdir/install/scripts/verify_install.sh"
```


## Documentation maintenance tips

When updating public docs, verify that:

- tool counts and tool names match `src/rl_developer_memory/server.py`
- maintenance command lists match `src/rl_developer_memory/maintenance.py`
- backup and restore guidance matches `src/rl_developer_memory/backup.py`
- configuration examples still describe the single live `~/.codex/config.toml` MCP entry

## PR guidance

Good pull requests are:

- narrow in scope
- validated
- honest about tradeoffs
- careful with SQLite path behavior and Codex integration
- consistent with the public documentation

Please include:

- what changed
- why it changed
- how you validated it
- any remaining risks or follow-up work

For live launcher validation of parent/subagent MCP reuse, keep the separate orchestration checklist up to date: [`ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md`](ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md).

For the broader project contribution guide, see [`../CONTRIBUTING.md`](../CONTRIBUTING.md).


## CI and installed-bundle validation

The end-to-end MCP reuse harness launches the real server process. That check requires the `mcp` runtime dependency to be importable in the interpreter running the test.

- local source checkout without dependencies: `tests/test_e2e_mcp_reuse_harness.py` is skipped
- editable or installed environment with dependencies: the test must pass

Recommended PR validation sequence:

```bash
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m rl_developer_memory.maintenance benchmark-user-domains
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
```

Recommended install validation sequence:

```bash
tmpdir="$(mktemp -d)"
INSTALL_ROOT="$tmpdir/install" DATA_ROOT="$tmpdir/data" STATE_ROOT="$tmpdir/state" CODEX_HOME="$tmpdir/codex-home" SKIP_CRON_INSTALL=1 PYTHON_BIN=python3 bash install.sh
bash "$tmpdir/install/scripts/verify_install.sh"
```

Offline-friendly installed-bundle validation, when the base interpreter already has the MCP runtime:

```bash
tmpdir="$(mktemp -d)"
INSTALL_ROOT="$tmpdir/install" DATA_ROOT="$tmpdir/data" STATE_ROOT="$tmpdir/state" CODEX_HOME="$tmpdir/codex-home" \
SKIP_CRON_INSTALL=1 SKIP_DEP_INSTALL=1 VENV_SYSTEM_SITE_PACKAGES=1 PYTHON_BIN=python3 bash install.sh
bash "$tmpdir/install/scripts/verify_install.sh"
```

