# Rollout

This document describes the recommended runtime posture for `rl-developer-memory`.

## Recommended default posture

Use **shadow mode** first.

Recommended characteristics:
- owner-key-required startup
- no global total cap (`MAX_MCP_INSTANCES=0`)
- redaction enabled
- calibration enabled
- strategy bandit enabled in shadow mode
- preference rules enabled

Typical checks:
```bash
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint metrics --window-days 14
```

## Owner-key guidance

Prefer explicit main-conversation key injection with:
- `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`

Keep these invariants:
1. one stable owner key per main conversation
2. subagents should resolve to the same main-conversation key
3. duplicate exit code `75` means reuse the existing server
4. do not treat duplicate exit as a generic crash

## RL/control rollout order

### Step 1 — RL shadow
Turn on RL support conservatively:
```bash
rl-developer-memory-maint recommended-config --mode shadow --profile rl-control-shadow
rl-developer-memory-maint doctor --mode shadow --profile rl-control-shadow
rl-developer-memory-maint benchmark-rl-control-reporting
rl-developer-memory-maint rl-audit-health --window-days 30 --limit 10
```

Shadow profile semantics:
- RL/control domain logic enabled
- theory and experiment audit enabled
- promotion remains review-gated
- reporting surfaces are visible
- rollout stays conservative

### Step 2 — RL active
Only after shadow health looks stable:
```bash
rl-developer-memory-maint recommended-config --mode active --profile rl-control-active
rl-developer-memory-maint doctor --mode active --profile rl-control-active
```

Use active mode only when:
- shadow doctor is clean
- reporting benchmarks are stable
- review backlog is manageable
- your team accepts the stricter RL posture

## Registration helper examples

Standard runtime registration:
```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex
```

RL shadow registration:
```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex \
  --enable-rl-control \
  --rl-rollout-mode shadow
```
