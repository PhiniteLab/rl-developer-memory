# Support

## Supported environments

Primary supported targets:
- Linux
- WSL 2

The project is aimed at:
- Codex users
- MCP-based local tooling workflows
- local SQLite-backed memory and RL/control audit workflows

## Before opening an issue

Read:
- [README.md](README.md)
- [docs/INSTALLATION.md](docs/INSTALLATION.md)
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)
- [docs/ROLLOUT.md](docs/ROLLOUT.md)

Then run the relevant checks:

### Installed bundle
```bash
bash /path/to/install/scripts/verify_install.sh
```

### Source checkout
```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
```

## When asking for help

Include:
- Linux or WSL version
- Python version
- how you installed the project
- exact command that failed
- shortest meaningful error excerpt
- whether the problem is install, runtime, backup, migration, lifecycle, rollout, or matching-related

## What to expect

The easiest problems to diagnose are:
- install failures
- Codex registration problems
- WSL path mistakes
- smoke or doctor failures
- backup/restore issues
- matching regressions backed by tests or reproduction cases
