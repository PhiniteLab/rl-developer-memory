---
name: rl-developer-workflow
description: Use this skill for substantive RL/control engineering work that must stay theory-aware, validation-first, MCP-aware, and professionally structured rather than prototype-only.
---

# Purpose

Use this skill when the task is genuinely about **RL/control development quality** rather than casual discussion.

Its job is to pull work toward a professional RL backbone:
- repo-aware before abstract claims
- theorem-to-code explicit instead of implied
- assumptions and risks surfaced instead of hidden
- validation and rollout posture treated as first-class requirements
- MCP and durable memory used only where justified

This skill is a **workflow-and-architecture skill**, not just a bugfix skill.

## Trigger criteria

Trigger this skill when one or more of the following are true:

- the user asks for RL algorithm design or implementation
- the task involves actor-critic, DQN, PPO, A2C, DDPG, TD3, or SAC
- theorem-to-code, Bellman, TD, HJB, Lyapunov, ISS, UUB, MPC, or dynamic-programming alignment matters
- the task touches RL/control experiment design, reproducibility, seed discipline, checkpointing, rollout policy, or evaluation rigor
- the user wants Codex orchestration, agent design, MCP integration, or memory hygiene inside an RL workflow
- the task needs RL-oriented validation, stabilization, runtime safety, or quality-gate hardening
- the task needs academically careful technical guidance rather than informal heuristics

## Non-trigger criteria

Do **not** trigger this skill for:

- casual conversation
- generic text editing or rewriting
- surface-level project admin with no RL/control content
- tasks where “RL” is only mentioned in passing but no technical RL work is requested
- trivial formatting or renaming work that does not affect RL/control design, validation, or runtime behavior

## Task classification logic

Classify the task before implementation:

- **analysis-only**: inspection, audit, mapping, design review
- **feature / bounded refactor**: trainer, algorithm, theory, config, diagnostics, orchestration, install, or docs changes
- **validation-only**: lint/type/test/smoke/doctor/benchmark/theory sync
- **rollout / operations**: shadow-vs-active readiness, owner-key reuse, MCP orchestration

Then identify the RL slice:

- algorithm / policy / value / buffer / trainer
- theorem / assumption / objective / control audit
- experiment / checkpoint / diagnostics / reproducibility
- rollout / owner-key / MCP / memory hygiene

## Repo-first rule

Do not speak as if the repo already supports a behavior unless you inspected the relevant files.

Before claiming RL structure or workflow support, inspect the smallest relevant set of:
- `src/`
- `tests/`
- `configs/`
- `scripts/`
- `docs/`
- `AGENTS.md`

If the repo and the requested behavior diverge, say so explicitly.

## Professional RL backbone uplift

When the repo or patch is too prototype-like, guide it toward:
- algorithm-agnostic abstractions
- modular trainer/runtime surfaces
- config-driven execution
- reproducibility discipline
- checkpoint/resume/rollback support
- theorem-to-code traceability
- explicit diagnostics and failure signatures
- bounded, testable, documented changes

Do not introduce a redesign unless the task justifies it; prefer the smallest defensible uplift.

## Theory / assumptions / validation obligations

For substantive RL/control work:
- make assumptions explicit
- map equations/objectives to code anchors
- distinguish confirmed facts from inferences
- state theoretical risk if implementation evidence is weak
- connect metrics to the risks they are meant to observe

If theorem-to-code or control claims are involved, ensure the output mentions:
- assumptions
- objective/loss mapping
- validation/audit surface
- residual risks

## RL coding standards contract

Stay aligned with:
- `docs/RL_CODING_STANDARDS.md`
- `docs/RL_BACKBONE.md`
- `docs/theory_to_code.md`

This means:
- OOP-compatible, typed, docstring-backed Python
- modular responsibilities
- config-aware behavior
- explicit validation expectations
- no “works on my machine” delivery posture

## RL quality gate contract

Stay aligned with:
- `docs/RL_QUALITY_GATE.md`
- `docs/VALIDATION_MATRIX.md`

For Python/code changes, expect the relevant subset of:
- `ruff check .`
- `pyright`
- `python -m pytest`
- `python -m rl_developer_memory.maintenance smoke`
- `python -m build`

Add RL-specific validation when the task touches theorem sync, rollout, or diagnostics.

## MCP integration policy

Stay aligned with:
- `docs/MCP_RL_INTEGRATION_POLICY.md`

Use `rl_developer_memory` when there is:
- a real failure signal
- an ambiguity that benefits from guardrails
- a justified need for preference or memory policy
- a verified reusable fix

Do **not** turn every RL task into a memory query.

## Scope and write-back hygiene

Stay aligned with:
- `docs/MEMORY_SCOPE_OPERATIONS_NOTE.md`

Use:
- `project_scope` for repo-specific RL/control issues
- `global` for broadly reusable engineering lessons
- `user_scope` for stable user/team preferences

Only write durable memory after validation and only with redacted, compact summaries.

## Codex RL operating model

Stay aligned with:
- `docs/CODEX_RL_AGENT_OPERATING_MODEL.md`
- `docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md`

Respect:
- main-conversation ownership
- explicit or resolvable owner-key posture
- duplicate exit code `75` as reuse
- shadow-first rollout posture
- conservative active-rollout recommendations

## Token-efficient discipline

Keep context small:
- inspect only the needed files
- prefer short failure excerpts over long logs
- summarize repo deltas instead of dumping files
- use phase summaries for large tasks
- avoid repeating the whole architecture once it is already established

## Delivery format

For substantial work, return at least:
- task classification
- workflow used
- files changed, or `none`
- commands run
- validation status as passed / failed / skipped / not configured
- remaining risks / caveats

For analysis-only work, say so explicitly.
