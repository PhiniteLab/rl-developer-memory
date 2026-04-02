# Professional RL quality gate

This document defines the **minimum acceptance gate** for RL work in this repository.

The goal is to lift every RL code delivery from “seems to run” to **validated, defensible engineering quality**.

It complements, but does not replace:
- `docs/VALIDATION_MATRIX.md`
- `docs/ROLLOUT.md`
- `docs/MCP_RL_INTEGRATION_POLICY.md`
- `docs/theory_to_code.md`

## Checklist

The repository-level RL quality gate requires all of the following categories to be evaluated:

1. repository structure compliance
2. import/compile safety
3. typing discipline
4. lint discipline
5. unit tests
6. smoke tests
7. kısa runtime tests
8. deterministic behavior checks
9. checkpoint/reload checks
10. config validation
11. logging/metrics minimum standardı
12. docs sync
13. theorem-to-code sync
14. MCP memory write-back hygiene
15. rollout safety checks

## Standard command evidence

The core command matrix is:

```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m build
```

The RL/runtime extension matrix is:

```bash
python -m rl_developer_memory.maintenance smoke-learning
python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
python -m rl_developer_memory.maintenance benchmark-rl-control-reporting
python scripts/validate_theory_code_sync.py
python scripts/run_rl_backbone_smoke.py
python scripts/rl_quality_gate.py --json
```

## Acceptance principles

- **No hidden red flags:** lint, typing, test, smoke, and build must pass.
- **No import ambiguity:** representative package imports must succeed.
- **No RL-specific blind spots:** determinism, checkpoint/reload, config validation, theorem/code sync, and rollout safety must be covered.
- **No low-hygiene memory writes:** durable MCP write-back must remain redacted, scoped, and verified-only.
- **No weak rollout promotion:** active rollout is not implied by a passing codebase gate; live shadow soak and review-backlog signoff are still required.

## Scripted report

Use:

```bash
python scripts/rl_quality_gate.py --json
```

The report includes:
- category-by-category pass/fail status
- command evidence
- failed items
- rollout readiness summary
- active rollout go/no-go state
