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

When working from a source checkout, prefer the repo-native virtualenv tools (`.venv/bin/python`, `.venv/bin/ruff`, `.venv/bin/pyright`) or an activated `.venv` to avoid import drift in script entrypoints.

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
python scripts/release_readiness.py --json
python scripts/rl_quality_gate.py --json
python scripts/train_rl_backbone.py --config configs/rl_backbone.shadow.json
python scripts/eval_rl_backbone.py --config configs/rl_backbone.shadow.json
python scripts/run_rl_backbone_smoke.py
python scripts/validate_theory_code_sync.py
```

## Repository structure

- `src/rl_developer_memory/` — runtime package
- `src/rl_developer_memory/maintenance_cli/` — split maintenance CLI internals behind the stable `maintenance.py` façade
- `tests/unit/` — focused unit contracts, including `tests/unit/memory/` for core memory behavior
- `tests/integration/` — multi-module flow checks, grouped into `operations/`, `rl_control/`, and `benchmarks/` where helpful
- `tests/smoke/` — lightweight runtime smoke checks
- `tests/regression/` — regression guards (checkpoint, docs/code sync, theorem/code sync)
- `docs/` — documentation set
- `examples/` — runnable RL/control scenarios and outputs
- `scripts/` — installer and helper scripts
- `templates/` — example config and wrapper artifacts
- `.github/workflows/ci.yml` — CI quality gate
- `.github/workflows/release.yml` — tag-based release workflow

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
- RL MCP lifecycle guidance still matches `docs/MCP_RL_INTEGRATION_POLICY.md`
- rollout validation matrix still matches `.github/workflows/ci.yml` and `scripts/release_readiness.py`
- Codex agent workflow guidance still matches `docs/CODEX_RL_AGENT_OPERATING_MODEL.md` and repo `AGENTS.md`
- RL quality gate guidance still matches `docs/RL_QUALITY_GATE.md` and `scripts/rl_quality_gate.py`

## Agent-oriented orchestration policy

Use [CODEX_RL_AGENT_OPERATING_MODEL.md](CODEX_RL_AGENT_OPERATING_MODEL.md) as the standard role-and-phase execution model for Codex RL tasks.

## Skill surface sync sanity check

Use the portable installer in dry-run mode to verify target discovery:

```bash
python scripts/install_skill.py --dry-run --json
```
