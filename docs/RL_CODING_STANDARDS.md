# RL coding standards

This document defines the **minimum coding and delivery standards** for RL work added to this repository.

It is a contributor-facing engineering contract, not a separate runtime authority.
The live runtime authority remains `~/.codex/config.toml`.

## Goals

- keep RL additions modular, typed, testable, and reviewable
- keep theorem, loss, stabilization, evaluation, and rollout evidence connected
- prevent prototype-only habits from leaking into accepted repository code

## Required structure alignment

RL additions should land in the existing backbone layout:
- `algorithms/`
- `agents/`
- `envs/`
- `networks/`
- `buffers/`
- `trainers/`
- `evaluation/`
- `experiments/`
- `theory/`
- `callbacks/`
- `utils/`

Do not bypass these layers with ad-hoc monolithic scripts unless the change is explicitly experimental and isolated.

## Code standards

- use Python type hints on public functions, dataclasses, and interfaces
- write docstrings for public classes, protocols, and important methods
- prefer small composable abstractions over one large trainer or one large script
- keep imports deterministic and lint-clean
- avoid adding heavy runtime dependencies without a strong justification
- keep config-driven execution where the repo already exposes config schemas

## RL-specific engineering rules

### 1. Theory-to-code traceability

If a change affects objectives, assumptions, theorem claims, stabilization, or evaluation:
- update `docs/THEORY_TO_CODE.md` when the public mapping changes
- preserve class/method anchors used by the theorem sync surface
- keep hidden assumptions explicit when they affect correctness or safety

### 2. Stabilization and runtime safety

When a change touches training behavior, preserve or update:
- deterministic seed discipline
- normalization hooks
- NaN/Inf and exploding-update guards
- checkpoint/save/load behavior
- rollback/recovery semantics
- diagnostics and anomaly capture

### 3. Evaluation and metrics

At minimum, RL-facing changes should not regress:
- training summary metrics
- evaluation summary metrics
- theory/audit payloads when relevant
- rollout benchmark completeness

## Validation expectations

For accepted RL work, run the repository quality gate appropriate to the change.

- Use `docs/VALIDATION_MATRIX.md` as the canonical command matrix.
- Use `python scripts/rl_quality_gate.py --json` for the higher-level RL acceptance report.
- Keep theorem, rollout, and MCP-policy checks aligned with `docs/THEORY_TO_CODE.md`, `docs/ROLLOUT.md`, and `docs/MCP_RL_INTEGRATION_POLICY.md`.

## Delivery standard

A change is not ready to present as professional RL work unless:
- code is lint/type clean
- relevant tests pass
- docs stay synchronized with the behavior users will see
- theorem/code drift is resolved when applicable
- rollout posture and MCP memory policy remain consistent with repo contracts

## Related documents

- `docs/RL_BACKBONE.md`
- `docs/THEORY_TO_CODE.md`
- `docs/RL_QUALITY_GATE.md`
- `docs/MCP_RL_INTEGRATION_POLICY.md`
- `docs/CODEX_RL_AGENT_OPERATING_MODEL.md`
