#!/usr/bin/env bash
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(cd "$THIS_DIR/.." && pwd)"
INSTALL_ENV="$INSTALL_ROOT/config/install.env"

if [[ -f "$INSTALL_ENV" ]]; then
  # shellcheck disable=SC1091
  source "$INSTALL_ENV"
  VERIFY_MODE="installed-bundle"
else
  VERIFY_MODE="source-checkout"
  echo "[verify] Missing install environment: $INSTALL_ENV"
  echo "[verify] Falling back to source-checkout defaults."
  export INSTALL_ROOT
  export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
  export RL_DEVELOPER_MEMORY_HOME="${RL_DEVELOPER_MEMORY_HOME:-$HOME/.local/share/rl-developer-memory}"
  export RL_DEVELOPER_MEMORY_DB_PATH="${RL_DEVELOPER_MEMORY_DB_PATH:-$RL_DEVELOPER_MEMORY_HOME/rl_developer_memory.sqlite3}"
  export RL_DEVELOPER_MEMORY_STATE_DIR="${RL_DEVELOPER_MEMORY_STATE_DIR:-$HOME/.local/state/rl-developer-memory}"
  export RL_DEVELOPER_MEMORY_BACKUP_DIR="${RL_DEVELOPER_MEMORY_BACKUP_DIR:-$RL_DEVELOPER_MEMORY_HOME/backups}"
  export RL_DEVELOPER_MEMORY_LOG_DIR="${RL_DEVELOPER_MEMORY_LOG_DIR:-$RL_DEVELOPER_MEMORY_STATE_DIR/log}"
  export RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR="${RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR:-$RL_DEVELOPER_MEMORY_STATE_DIR/run}"
  export RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH="${RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH:-$RL_DEVELOPER_MEMORY_STATE_DIR/calibration_profile.json}"
fi

if [[ -x "$INSTALL_ROOT/.venv/bin/python" ]]; then
  VERIFY_PYTHON="$INSTALL_ROOT/.venv/bin/python"
else
  VERIFY_PYTHON="${VERIFY_PYTHON:-python3}"
fi


python_has_mcp_runtime() {
  PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
    "$VERIFY_PYTHON" - <<'PY' >/dev/null 2>&1
import importlib
import sys

try:
    importlib.import_module("mcp.server.fastmcp")
except Exception:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

if [[ ! -f "$CODEX_HOME/config.toml" ]]; then
  echo "Expected Codex config at $CODEX_HOME/config.toml" >&2
  exit 1
fi

PYTHONPATH_PREFIX="$INSTALL_ROOT"
if [[ -d "$INSTALL_ROOT/src" ]]; then
  PYTHONPATH_PREFIX="$INSTALL_ROOT/src:$PYTHONPATH_PREFIX"
fi

echo "[verify] Mode: $VERIFY_MODE"
echo "[verify] Running local smoke test..."
PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
  "$VERIFY_PYTHON" -m rl_developer_memory.maintenance smoke

echo "[verify] Running benchmark-user-domains..."
PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
  "$VERIFY_PYTHON" -m rl_developer_memory.maintenance benchmark-user-domains >/dev/null

echo "[verify] Running rollout doctor..."
PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
  "$VERIFY_PYTHON" -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0 --codex-home "$CODEX_HOME"

if grep -q 'RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"' "$CODEX_HOME/config.toml"; then
  RL_PROFILE="rl-control-shadow"
  if grep -q 'RL_DEVELOPER_MEMORY_DOMAIN_MODE = "rl_control"' "$CODEX_HOME/config.toml"; then
    RL_PROFILE="rl-control-active"
  fi
  echo "[verify] Running RL rollout doctor for profile: $RL_PROFILE..."
  PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
    "$VERIFY_PYTHON" -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0 --codex-home "$CODEX_HOME" --profile "$RL_PROFILE"
fi

echo "[verify] Checking Codex config..."
CONFIG_MATCHES="$(grep -c "^\[mcp_servers.rl_developer_memory\]" "$CODEX_HOME/config.toml")"
if [[ "$CONFIG_MATCHES" != "1" ]]; then
  echo "Expected exactly one [mcp_servers.rl_developer_memory] block, found: $CONFIG_MATCHES" >&2
  exit 1
fi
grep -n 'RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY = "1"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR = "' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE = "75"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON = "1"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS = "0"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS = "1.0"' "$CODEX_HOME/config.toml"
grep -n 'RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"' "$CODEX_HOME/config.toml"
if grep -q 'RL_DEVELOPER_MEMORY_DOMAIN_MODE = "rl_control"' "$CODEX_HOME/config.toml"; then
  grep -n 'RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "0"' "$CODEX_HOME/config.toml"
else
  grep -n 'RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "1"' "$CODEX_HOME/config.toml"
fi

echo "[verify] Checking calibration profile..."
test -f "${RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH:-$RL_DEVELOPER_MEMORY_STATE_DIR/calibration_profile.json}"

echo "[verify] Checking backup availability..."
backup_count="$(
  PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
    "$VERIFY_PYTHON" -m rl_developer_memory.maintenance list-backups --limit 1 | \
    "$VERIFY_PYTHON" -c 'import json,sys; print(len(json.load(sys.stdin).get("backups", [])))'
)"
if [[ "$backup_count" -lt 1 ]]; then
  echo "[verify] Expected at least one backup." >&2
  exit 1
fi

echo "[verify] Checking AGENTS snippet..."
grep -n "RL Developer Memory workflow" "$CODEX_HOME/AGENTS.md"

echo "[verify] Checking bundled reference skill content..."
test -f "$INSTALL_ROOT/skills/rl-developer-memory-self-learning/SKILL.md"

if python_has_mcp_runtime; then
  echo "[verify] Running end-to-end MCP reuse harness..."
  PYTHONPATH="$PYTHONPATH_PREFIX${PYTHONPATH:+:$PYTHONPATH}" \
    "$VERIFY_PYTHON" -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json >/dev/null
else
  if [[ "$VERIFY_MODE" == "installed-bundle" ]]; then
    echo "[verify] Missing required MCP runtime dependency in installed bundle." >&2
    exit 1
  fi
  echo "[verify] Skipping end-to-end MCP reuse harness because the MCP runtime is unavailable for $VERIFY_PYTHON."
fi

echo "[verify] All local checks passed."
