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
python scripts/release_acceptance.py --json
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

Automated validation can prove codebase readiness, but it should still default to **no-go** for active rollout until live shadow soak and review-backlog signoff are complete.

Recommended evidence collection:
```bash
python scripts/release_acceptance.py --json
python scripts/rl_quality_gate.py --json
```

The matrix uses a temporary Linux/WSL runtime root, keeps the DB path off `/mnt/c`, verifies reuse semantics, checks docs/CLI/MCP sync, and returns a conservative active rollout gate. By default it treats a pending review backlog above `10` items as non-manageable. The RL quality gate adds repository-structure, theory/code, and memory-hygiene acceptance checks on top.

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

RL active registration:
```bash
python scripts/register_codex.py \
  --install-root ~/infra/rl-developer-memory \
  --data-root ~/.local/share/rl-developer-memory \
  --state-root ~/.local/state/rl-developer-memory \
  --codex-home ~/.codex \
  --enable-rl-control \
  --rl-rollout-mode active
```


## Shadow versus active: practical interpretation

- **Shadow**: use for default RL/control rollout, review-gated promotion, and conservative reporting/audit visibility.
- **Active**: use only when shadow health is already proven and your team explicitly accepts stronger RL domain behavior.
- A passing automated report means the codebase is ready for shadow operation; it does **not** automatically mean active rollout should be enabled.
