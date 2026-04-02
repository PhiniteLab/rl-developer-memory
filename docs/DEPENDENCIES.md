# Dependencies

## Required runtime dependency

The project has a deliberately small runtime dependency surface.

Required package dependency:
- `mcp[cli]>=1.0.0,<2.0.0`

## Development dependencies

Installed through `.[dev]`:
- `pytest`
- `pyright`
- `ruff`

## Optional environment dependencies

Depending on workflow, you may also need:
- `crontab` support for scheduled backups
- standard Linux/WSL shell tooling
- Codex for live MCP registration and use

## Dependency posture

Project goals:
- keep runtime dependencies minimal
- avoid turning the package into a large framework bundle
- prefer local scripts and explicit operational surfaces over hidden services
