# Contributing

Thanks for contributing to `rl-developer-memory`.

This project is a local-first Python MCP service. Strong contributions improve **correctness, install reliability, retrieval quality, rollout safety, and documentation clarity** without bloating the dependency or runtime surface.

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
- documentation kept in sync with code and scripts
- public-facing changes reflected in `CHANGELOG.md` when appropriate

## Validation expectations

Use [`docs/VALIDATION_MATRIX.md`](docs/VALIDATION_MATRIX.md) as the canonical command matrix.

Minimum contributor check:

```bash
ruff check .
pyright
python -m pytest
```

When release-impacting behavior changes, also run:

```bash
python scripts/release_readiness.py --json
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
- keep example paths in sync with `examples/`

## Pull request checklist

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
