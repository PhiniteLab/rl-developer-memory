# Professional RL quality gate

This document defines the **minimum acceptance gate** for RL work in this repository.

The goal is to lift every RL code delivery from “seems to run” to **validated, defensible engineering quality**.

It complements, but does not replace:
- `docs/VALIDATION_MATRIX.md`
- `docs/ROLLOUT.md`
- `docs/MCP_RL_INTEGRATION_POLICY.md`
- `docs/THEORY_TO_CODE.md`

## Checklist

The repository-level RL quality gate requires all of the following categories to be evaluated:

1. repository structure compliance
2. import/compile safety
3. typing discipline
4. lint discipline
5. unit tests
6. smoke tests
7. short runtime tests
8. deterministic behavior checks
9. checkpoint/reload checks
10. config validation
11. logging and metrics minimum standards
12. docs sync
13. theorem-to-code sync
14. MCP memory write-back hygiene
15. rollout safety checks

## Command evidence

Use `docs/VALIDATION_MATRIX.md` as the canonical command matrix for both the core gate and the RL/runtime extension checks.

For the scripted summary report, run:

```bash
python scripts/rl_quality_gate.py --json
```

## Acceptance principles

- **No hidden red flags:** lint, typing, test, smoke, and build must pass.
- **No import ambiguity:** representative package imports must succeed.
- **No RL-specific blind spots:** determinism, checkpoint/reload, config validation, theorem/code sync, and rollout safety must be covered.
- **No low-hygiene memory writes:** durable MCP write-back must remain redacted, scoped, and verified-only.
- **No weak rollout promotion:** active rollout is not implied by a passing codebase gate; live shadow soak and review-backlog signoff are still required.
