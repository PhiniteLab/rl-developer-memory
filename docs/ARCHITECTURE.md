# Architecture

`rl-developer-memory` is a local-first MCP service that turns recurring debugging and operational knowledge into a structured, queryable store.

## High-level flow

1. normalize a failure or query into a profile
2. retrieve lexical, structural, and optional dense candidates
3. rank and decide between match / ambiguous / abstain
4. surface guardrails, preferences, and review information
5. store verified fixes and feedback
6. expose operational state through CLI and lifecycle surfaces

## Core runtime modules

| Path | Responsibility |
| --- | --- |
| `src/rl_developer_memory/server.py` | MCP tool registration and process entrypoint |
| `src/rl_developer_memory/app.py` | application facade used by MCP and direct Python calls |
| `src/rl_developer_memory/settings.py` | environment-driven runtime settings |
| `src/rl_developer_memory/lifecycle.py` | owner-key, slot, duplicate exit, and lifecycle status tracking |
| `src/rl_developer_memory/storage.py` | SQLite persistence, retrieval telemetry, metrics, reports, and review queue |
| `src/rl_developer_memory/migrations.py` | packaged SQL migration discovery and application |
| `src/rl_developer_memory/backup.py` | backup, verification, restore, and retention helpers |
| `src/rl_developer_memory/maintenance.py` | operational CLI |
| `src/rl_developer_memory/security.py` | sanitization and redaction helpers |
| `src/rl_developer_memory/normalization/` | query normalization and signature extraction |
| `src/rl_developer_memory/retrieval/` | candidate retrieval, features, ranker, and decision policy |
| `src/rl_developer_memory/services/` | record, feedback, preferences, guardrails, session, and RL audit services |
| `src/rl_developer_memory/domains/rl_control/` | RL/control taxonomy, validators, reporting, and promotion helpers |
| `src/rl_developer_memory/{algorithms,agents,envs,networks,buffers,trainers,evaluation,experiments,theory,callbacks,utils}/` | config-driven RL development backbone (skeleton interfaces, theorem-to-code mappings, stabilization hooks, evaluation + checkpoint orchestration) |
| `src/rl_developer_memory/benchmarks/` | diagnostics, calibration, and benchmark datasets |

## Data model

The store separates stable reusable knowledge from operational telemetry.

### Core issue memory
- `issue_patterns`
- `issue_variants`
- `issue_episodes`
- `issue_examples`

### Retrieval and feedback state
- `retrieval_events`
- `retrieval_candidates`
- `feedback_events`
- `session_memory`
- `embeddings`

### Review and prevention state
- `preference_rules`
- `review_queue`

### Support state
- schema migrations and FTS structures
- reports saved under the state directory

## Request flow details

### 1. Query normalization
The normalization layer builds a profile from:
- `error_text`
- `context`
- `command`
- `file_path`
- `stack_excerpt`
- `env_json`
- repo and scope metadata

### 2. Candidate retrieval
Retrieval combines:
- SQLite FTS
- variant-aware fingerprints
- taxonomy shortcuts
- optional dense retrieval

### 3. Ranking and decision
Ranking considers:
- text overlap
- scope alignment
- root-cause and family alignment
- command/path/environment similarity
- feedback priors
- session memory
- optional strategy overlays

### 4. RL/control audit layer
When RL mode is enabled, the runtime can add:
- query/candidate domain profiling
- read-only audit summaries
- validation tier and promotion reporting
- review-gated promotion semantics

## Operational surfaces

The architecture intentionally exposes operational checks as first-class features:
- `smoke`
- `doctor`
- `server-status`
- `backup` / `verify-backup` / `restore-backup`
- `e2e-mcp-reuse-harness`
- calibration and reporting benchmarks
