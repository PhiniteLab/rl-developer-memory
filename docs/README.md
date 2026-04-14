# Documentation map

This directory contains the main documentation set for `rl-developer-memory`.

## Start here

- [../README.md](../README.md) — project overview and quick start
- [INSTALLATION.md](INSTALLATION.md) — installation, verification, and first-run workflow
- [USAGE.md](USAGE.md) — MCP, CLI, and Python usage patterns
- [CONFIGURATION.md](CONFIGURATION.md) — runtime configuration model and important environment variables
- [OPERATIONS.md](OPERATIONS.md) — health, lifecycle, backup, restore, and diagnostics commands
- [operations/AUTO_TRIGGER_PROOF_PROTOCOL.md](operations/AUTO_TRIGGER_PROOF_PROTOCOL.md) — recommended first-test runbook for proving auto-trigger, MCP, and runtime effects
- [ROLLOUT.md](ROLLOUT.md) — recommended shadow/active rollout posture
- [../examples/README.md](../examples/README.md) — runnable RL/control example scenarios

## Architecture and engineering

- [ARCHITECTURE.md](ARCHITECTURE.md) — modules, data flow, and storage model
- [DEPENDENCIES.md](DEPENDENCIES.md) — runtime, development, and optional dependency guidance
- [DEVELOPMENT.md](DEVELOPMENT.md) — contributor workflow and validation expectations
- [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) — validation matrix and rollout rubric
- [RL_QUALITY_GATE.md](RL_QUALITY_GATE.md) — minimum professional RL acceptance gate
- [THEORY_TO_CODE.md](THEORY_TO_CODE.md) — theorem/assumption/objective mappings to class.method targets

## RL and Codex workflow references

- [RL_BACKBONE.md](RL_BACKBONE.md) — scalable RL development backbone layout and contracts
- [RL_CODING_STANDARDS.md](RL_CODING_STANDARDS.md) — coding, validation, and delivery standards for RL contributions
- [MCP_RL_INTEGRATION_POLICY.md](MCP_RL_INTEGRATION_POLICY.md) — RL lifecycle policy for MCP scope, decision, feedback, and write-back
- [MEMORY_SCOPE_OPERATIONS_NOTE.md](MEMORY_SCOPE_OPERATIONS_NOTE.md) — scope-selection and verified write-back notes
- [CODEX_MAIN_CONVERSATION_OWNERSHIP.md](CODEX_MAIN_CONVERSATION_OWNERSHIP.md) — owner-key and conversation reuse model
- [CODEX_RL_AGENT_OPERATING_MODEL.md](CODEX_RL_AGENT_OPERATING_MODEL.md) — agent roles, orchestration flow, and safe RL workflow contract
- [ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md](ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md) — reuse validation checklist
- [SKILL_INSTALL_SYNC.md](SKILL_INSTALL_SYNC.md) — portable global skill sync for `.codex` and `.agents`
