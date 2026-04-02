# RL backbone

`rl-developer-memory` already had a strong MCP/runtime control plane. This additive backbone adds a
**typed execution/data plane** that is still dependency-light and centered on the existing RL/control
memory and audit surface.

## Folder responsibilities

| Path | Responsibility |
| --- | --- |
| `src/rl_developer_memory/algorithms/` | Algorithm blueprints for DQN/PPO/A2C/DDPG/TD3/SAC and shared algorithm contracts |
| `src/rl_developer_memory/agents/` | Policy/value agent composition and objective hooks |
| `src/rl_developer_memory/envs/` | Environment interfaces and deterministic test envs/wrappers |
| `src/rl_developer_memory/networks/` | Framework-agnostic network specs and scalar smoke models |
| `src/rl_developer_memory/buffers/` | Replay and rollout abstractions |
| `src/rl_developer_memory/trainers/` | 10-stage trainer pipeline and stabilization policy |
| `src/rl_developer_memory/evaluation/` | Evaluator and failure-aware metrics aggregation |
| `src/rl_developer_memory/experiments/` | Config schemas, checkpoints, manifests, memory bridge, and experiment runner |
| `src/rl_developer_memory/theory/` | Assumptions, notation, theorem mappings, and sync validation |
| `src/rl_developer_memory/callbacks/` | Checkpoint, anomaly, and early-stop callbacks |
| `src/rl_developer_memory/utils/` | Reproducibility, numeric guards, and safe serialization |
| `configs/` | Example experiment configs; not live runtime authority |
| `scripts/` | Config-driven train/eval entrypoints plus smoke and theorem/code sync utilities |
| `tests/unit/` | Narrow contract tests |
| `tests/integration/` | End-to-end manifest and resume tests |
| `tests/smoke/` | Import and smoke path tests |
| `tests/regression/` | Determinism, checkpoint, and rollout-hardening regressions |
| `docs/` | Architecture, theorem/code, and operator guidance |

## Backbone flow

1. define the problem and env contract
2. freeze observation/action interfaces
3. build network roles from the algorithm blueprint
4. define loss/objective terms
5. bind theory mappings and assumptions
6. run the training loop
7. apply stabilization guards
8. evaluate and summarize
9. capture failure signatures and anomalies
10. feed the improvement loop and MCP memory surface

## Theory blueprint layer

The backbone now exposes a reusable theorem-to-code and training-blueprint layer for every
supported RL algorithm family:

- `theory/registry.py` keeps assumptions, notation, objective terms, theorem mappings, and risk metrics
- `theory/blueprint.py` builds per-algorithm training blueprints with:
  - 10 canonical stages
  - loss decomposition
  - update-equation anchors
  - control/stability audit hooks
  - failure modes
  - ablation hooks
  - reporting and artifact templates
- `theory/validators.py` binds the blueprint to runtime checks:
  - experiment assumption validation
  - hidden-assumption audit
  - seed/variance audit
  - result artifact validation

This is intentionally stronger than a narrative-only document. The runtime emits blueprint-aware
`theory_sync`, `artifact_refs`, and reporting payloads so the same contract can be checked by tests,
smoke scripts, and the RL control audit surface.

## Rollout posture

- Default rollout posture stays **shadow**.
- Active RL/control mode should be considered only when:
  - shadow health is clean,
  - reporting/benchmark signals are stable,
  - review backlog is manageable.
- Example configs in `configs/` are helpers only. The live Codex runtime authority is still `~/.codex/config.toml`.

## Why no heavy ML dependency?

This phase is about **compile-time, import-time, runtime, and theory-traceable structure**.
The backbone therefore stays backend-agnostic, so it can be tested and audited in isolation while
still producing payloads compatible with `domains/rl_control/validators.py` and the MCP memory layer.


## Contributor standards

For contributor-facing RL coding and delivery expectations, see `docs/RL_CODING_STANDARDS.md`.
