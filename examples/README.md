# Examples

This directory contains runnable RL/control scenarios that show how the MCP surface behaves in a realistic debugging workflow.

## What the example suite demonstrates

Each seeded buggy case follows this flow:

1. a deliberately broken RL/control script is executed,
2. the script fails with a real assertion,
3. the runner starts the real MCP server over stdio,
4. the example seeds a verified pattern into an isolated demo database,
5. `issue_match`, `issue_get`, `issue_guardrails`, and `issue_feedback` are called,
6. the suite measures whether the system routes the case toward the correct fix.

The suite also includes fixed control cases that should **not** trigger the MCP recovery path.

## Covered bug families

1. Q-learning terminal bootstrap leak
2. DQN target-network leakage
3. N-step return terminal masking bug
4. PPO clipped surrogate max-vs-min bug
5. GAE terminal mask omission
6. Actor-critic returns-vs-advantage bug
7. SAC alpha / temperature sign bug
8. TD3 target smoothing clip omission
9. TD3 policy-delay schedule bug
10. Off-policy importance-weight omission (V-trace style)

## Measured outputs

- `buggy_detection_recall`
- `routing_accuracy`
- `fixed_non_trigger_rate`
- `mean_issue_match_latency_ms`
- `mean_score_uplift_after_feedback`
- per-case top-match, fix, and guardrail outputs

## Important honesty note

- The suite seeds patterns into an isolated demo database before evaluation.
- It is therefore **not** a zero-shot generalization benchmark on an empty memory store.
- `fixed_non_trigger_rate` is not an abstention benchmark; it measures whether already-correct scripts avoid unnecessary MCP intervention.

## Run the examples

```bash
PYTHONPATH=src .venv/bin/python examples/run_rl_scenarios.py \
  --output-json /tmp/rl_scenarios_metrics.json \
  --output-markdown /tmp/rl_scenarios_summary.md
```

The committed files under `examples/results/` are reference snapshots for documentation and verification. Prefer writing local runs to temporary paths unless you intentionally want to refresh those snapshots.

## Run the example test

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/integration/test_examples_rl_scenarios.py
```

## Technical note

The demo uses the real MCP stdio path:

- `python -m rl_developer_memory.server`
- `mcp.client.stdio`
- `ClientSession.call_tool(...)`

This is a real end-to-end MCP path, not a local direct-call shortcut.
