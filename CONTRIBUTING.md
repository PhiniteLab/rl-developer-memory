# Contributing

Thanks for contributing to `rl-developer-memory`.

## Before you start

Read these first:
- [README.md](README.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — local setup, validation, repo structure
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for extended setup and validation details.

## What makes a strong contribution

- Scoped, reviewable changes with validation evidence
- No surprise behavior in backup, migration, lifecycle, or rollout paths
- Documentation kept in sync with code and scripts
- Public-facing changes reflected in `CHANGELOG.md`

## Validation

Use [`docs/VALIDATION_MATRIX.md`](docs/VALIDATION_MATRIX.md) as the canonical reference.

Minimum check:

```bash
ruff check .
pyright
python -m pytest
```

For release-impacting changes, also run:

```bash
python scripts/release_readiness.py --json
```

## Documentation changes

If you touch README or docs:
- Update the docs index in `docs/README.md`
- Keep command names in sync with `maintenance.py`
- Keep MCP tool names in sync with `server.py`
- Keep install steps in sync with `install.sh`, `register_codex.py`, and `verify_install.sh`

## Pull request checklist

Include:
- what changed
- why it changed
- how you validated it
- any residual risks or follow-up work

## Branch policy

- `main` is the only long-lived branch.
- Use short-lived topic branches only when needed for review, then delete them immediately after merge.
- Do not keep standing automation branches alive in the repository.
- If you are preparing a release or hotfix, make sure `main` is clean, validated, and changelog-aligned before tagging.

## Areas where extra care matters

- SQLite schema and migrations
- lifecycle locking and owner-key behavior
- rollout flags and RL-control promotion semantics
- backup/restore safety
- docs that can mislead install or live operations
