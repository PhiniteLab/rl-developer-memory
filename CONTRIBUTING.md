# Contributing

Thanks for contributing to `rl-developer-memory`.

This project is a local-first Python MCP service. Good contributions improve **correctness, install reliability, retrieval quality, rollout safety, and documentation clarity** without bloating the dependency or runtime surface.

## Before you start

Read these first:
- [README.md](README.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
```

## What makes a strong contribution

- scoped, reviewable changes
- validation evidence
- explicit treatment of runtime/config side effects
- no surprise behavior in backup, migration, lifecycle, or rollout paths
- documentation kept in sync with code

## Validation expectations

For most code changes, run:

```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m build
```

Add these when relevant:

```bash
python -m rl_developer_memory.maintenance smoke-learning
python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
python -m rl_developer_memory.maintenance benchmark-rl-control-reporting
```

## Install / registration changes

If you change install, verification, Codex registration, calibration, or backup logic, also validate:

```bash
bash install.sh
bash scripts/verify_install.sh
```

Recommended RL shadow install check:

```bash
ENABLE_RL_CONTROL=1 RL_ROLLOUT_MODE=shadow bash install.sh
bash scripts/verify_install.sh
```

## Documentation changes

If you touch README or docs:
- update the docs index in `docs/README.md`
- keep command names in sync with `maintenance.py`
- keep MCP tool names in sync with `server.py`
- keep install steps in sync with `install.sh`, `register_codex.py`, and `verify_install.sh`

## PR checklist

Include:
- what changed
- why it changed
- how you validated it
- any residual risks or follow-up work

## Areas where extra care matters

- SQLite schema and migrations
- lifecycle locking and owner-key behavior
- rollout flags and RL-control promotion semantics
- backup/restore safety
- docs that can mislead install or live operations
