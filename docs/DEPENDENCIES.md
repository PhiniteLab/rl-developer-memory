# Dependencies

The canonical dependency source for this repository is [`pyproject.toml`](../pyproject.toml).
Use this page as a quick reference, not as a second package manifest.

## Runtime dependencies

Installed automatically with `python -m pip install -e .`:

- `mcp[cli]>=1.0.0,<2.0.0`
- `tomli>=2.0.1` on Python `<3.11`

## Development dependencies

Installed with `python -m pip install -e .[dev]`:

- `pytest>=8.0.0`
- `pyright>=1.1.380`
- `ruff>=0.6.0`
- `build>=1.2.2`

## External tools

Depending on workflow, you may also need:
- `git`
- `python3` with `venv`
- `bash`
- `rsync` (optional for installer copy behavior)
- `cron` / `crontab` (optional for scheduled backups)
- Codex (optional for live MCP registration)

For install examples and first-run verification, use [INSTALLATION.md](INSTALLATION.md).
