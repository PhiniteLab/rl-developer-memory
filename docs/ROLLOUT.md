# Runtime posture

This guide describes the recommended live operating posture for `rl-developer-memory` in Codex.

## Live configuration rule

All live MCP changes belong in the single `[mcp_servers.rl_developer_memory]` block inside `~/.codex/config.toml`.

Do not create duplicate `rl_developer_memory` registrations in alternate config files, plugin manifests, or helper snippets.

## Recommended default posture

For most installations, use owner-key-required startup with no global total cap:

- `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"`
- `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"`
- `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"`
- `RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE = "0"`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_REDACTION = "1"`
- `RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE = "1"`

Operational meaning:

- the deterministic baseline remains in control
- strategy recommendations are collected and measured without reordering live results by default
- preference rules and guardrails stay available
- redaction and calibration remain on
- the same main conversation cannot claim a second MCP process
- subagents should reuse the same owner key as their main conversation
- there is no required global total cap in the recommended setup

## Owner-key routing requirement

The recommended posture prefers an explicit `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` per main conversation.

When explicit injection is not present, this repo still attempts owner-key resolution by:

- explicit owner vars (`RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`, `RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY`, `RL_DEVELOPER_MEMORY_MCP_OWNER_KEY`)
- alias vars (`..._ENV` forms)
- `CODEX_THREAD_ID` session lineage
- parent-process lineage
- recent-session inference
- optional synthetic fallback (`RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY`)

Required caller behavior:

1. use one stable main-conversation owner key, either explicitly or via the chain above
2. make sure subagents resolve to that same main-conversation owner key
3. treat duplicate exit code `75` as a reuse signal
4. reuse the already-owned conversation MCP instead of launching another process for the same key

## When to enable live strategy promotions

Switch `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE` from `"1"` to `"0"` only after you are satisfied with the current behavior.

Before making that change, check:

- recent metrics look healthy
- false positives are controlled
- verified conversions are acceptable
- the pending review queue is manageable
- the service is not producing an unexpected number of safe overrides

Useful commands:

```bash
rl-developer-memory-maint metrics --window-days 14
rl-developer-memory-maint export-dashboard --output ~/rl-developer-memory-dashboard.json
rl-developer-memory-maint review-queue --status pending --limit 20
rl-developer-memory-maint doctor --mode active --max-instances 0
```

## Compatibility fallback: bounded total cap

If your runtime cannot yet provide a stable owner key, you can temporarily fall back to a bounded total-cap model instead:

- `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "0"`
- `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "2"` for a small shared cap, or `"1"` for a strict singleton
- `RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE = "0"` or `"1"` to match the cap you chose

Use this only as a compatibility path when owner-key routing is unavailable.

## Returning to observation-only strategy mode

If you want to stop live strategy promotions:

1. set `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"`
2. keep `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"` if you still want to collect strategy observations
3. set `RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "0"` only if you want to disable the strategy overlay completely

## Health commands

Recommended checks for the live posture:

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint server-status
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint metrics --window-days 14
```

Things worth monitoring:

- active process ownership and duplicate rejection behavior
- retrieval decision mix
- false positives and verified conversions
- safe overrides and observation-only promotions
- preference-rule hits
- pending review queue size
- backup freshness
- calibration profile presence

Before enabling non-observation strategy behavior (`shadow_mode=0`), also run:

```bash
rl-developer-memory-maint runtime-diagnostics
rl-developer-memory-maint export-dashboard --output ~/rl-developer-memory-dashboard.json
rl-developer-memory-maint e2e-mcp-reuse-harness --json
```

This confirms:

- benchmark / diagnostics output is structurally stable
- dashboard snapshots capture current policy and review state
- conversation-owner reuse is represented as a controlled duplicate signal (`75`) rather than repeated process launches

## RL/control rollout posture

The recommended RL/control rollout order is:

1. `--profile rl-control-shadow`
2. validate with `benchmark-rl-control-reporting`
3. inspect `rl-audit-health`
4. only then move to `--profile rl-control-active`

### Shadow profile

Use shadow RL rollout first:

```bash
rl-developer-memory-maint recommended-config --mode shadow --profile rl-control-shadow
rl-developer-memory-maint doctor --mode shadow --profile rl-control-shadow
```

Shadow profile semantics:

- RL/control domain logic enabled
- theory and experiment audit enabled
- review-gated promotion still enforced
- retrieval audit visible, but rollout remains conservative
- suitable for validating reporting and review burden

### Active profile

After shadow health looks stable, use:

```bash
rl-developer-memory-maint recommended-config --mode active --profile rl-control-active
rl-developer-memory-maint doctor --mode active --profile rl-control-active
```

Active profile semantics:

- RL/control mode is no longer just a hybrid hint path
- the runtime expects RL/control env flags to be present in the live block
- audit summaries and promotion review become part of the normal reviewer workflow

### Registration helper

The Codex registration helper now accepts optional RL rollout flags:

```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex \
  --enable-rl-control \
  --rl-rollout-mode shadow
```

Switch `shadow` to `active` only after the RL audit-health and reporting benchmarks remain healthy.
