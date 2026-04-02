# Validation matrix and rollout readiness

This document standardizes the validation and rollout-readiness contract for `rl-developer-memory`.

## Core validation matrix

These commands are the default compile-time, import-time, and runtime quality gate:

```bash
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python -m build
```

## Rollout and orchestration extensions

Run these when hardening rollout, owner-key reuse, RL reporting, or shadow-to-active promotion posture:

```bash
python -m rl_developer_memory.maintenance smoke-learning
python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow
python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json
python -m rl_developer_memory.maintenance benchmark-rl-control-reporting
python scripts/release_readiness.py --json
python scripts/rl_quality_gate.py --json
```

## What each extended check proves

- `smoke-learning`
  - session memory and feedback plumbing still works
- `doctor --mode shadow --max-instances 0`
  - owner-key-required shadow posture is configured correctly
  - the active DB path is not expected to live under `/mnt/c/...`
- `doctor --mode shadow --profile rl-control-shadow`
  - RL/control shadow posture, audits, and review-gated promotion flags are aligned
- `e2e-mcp-reuse-harness --json`
  - one main conversation maps to one owner slot
  - subagents resolve back to the same main owner
  - duplicate launch does not create a second stateful process
  - duplicate exit code `75` is emitted as a reuse signal
- `benchmark-rl-control-reporting`
  - RL reporting surfaces, audit summaries, review reports, and metrics remain complete
- `scripts/release_readiness.py --json`
  - emits a structured validation matrix
  - checks docs ↔ CLI ↔ MCP surface sync
  - evaluates automated rollout readiness without treating active rollout as the default

## Standard interpretation

## Minimum RL quality gate checklist

`scripts/release_readiness.py --json` now emits a `minimum_quality_gate` section that evaluates the
following checklist against command results and repository contracts:

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

The checklist is reported with per-item evidence and failed-item extraction.

### Codebase readiness

Automated codebase readiness is considered **passed** when all of the following hold:
- core validation matrix passes
- both shadow doctor checks are clean
- e2e reuse harness verifies owner/reuse semantics
- RL reporting benchmark is stable
- docs, CLI names, and MCP tool names stay synchronized

### Active rollout decision

Automated validation alone does **not** imply active rollout.

Default decision rule:
- **shadow rollout**: recommended when codebase readiness passes
- **active rollout**: only after
  - shadow doctor stays clean over time
  - RL reporting benchmarks remain stable across repeated runs
  - review backlog is explicitly assessed as manageable
  - promotion/review policy is accepted by the team operating the rollout

Because review backlog and shadow soak are operational signals, `scripts/release_readiness.py` intentionally keeps the default active decision at **no-go** unless those live signals are supplied outside the script.

## CI guidance

- CI should always run the core validation matrix.
- A separate rollout-readiness job should run the extended orchestration checks.
- Install and registration verification (`bash install.sh` and `bash scripts/verify_install.sh`) remain mandatory whenever installer or registration logic changes.


## Professional RL acceptance gate

For the higher-level acceptance checklist used in professional RL delivery, see `docs/RL_QUALITY_GATE.md` and `python scripts/rl_quality_gate.py --json`.
