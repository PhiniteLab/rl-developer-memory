# Development

This guide is for contributors working from a source checkout.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
```

## Core validation

```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m build
```

## Additional useful checks

```bash
python -m rl_developer_memory.maintenance smoke-learning
python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
python -m rl_developer_memory.maintenance benchmark-rl-control-reporting
```

## Repository structure

- `src/rl_developer_memory/` — runtime package
- `tests/` — regression and behavior tests
- `docs/` — documentation set
- `scripts/` — installer and helper scripts
- `templates/` — example config and wrapper artifacts
- `.github/workflows/ci.yml` — CI quality gate

## Source of truth rules

- code and scripts define behavior
- README/docs describe the current behavior
- `~/.codex/config.toml` is the live runtime registration source of truth
- repository templates are examples, not live runtime authority

## Docs maintenance checklist

When touching docs, verify:
- MCP tool names still match `server.py`
- CLI commands still match `maintenance.py`
- install flow still matches `install.sh`
- verify flow still matches `scripts/verify_install.sh`
- rollout guidance still matches `register_codex.py` and `doctor`
