#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_ROOT="${INSTALL_ROOT:-$HOME/infra/rl-developer-memory}"
DATA_ROOT="${DATA_ROOT:-$HOME/.local/share/rl-developer-memory}"
STATE_ROOT="${STATE_ROOT:-$HOME/.local/state/rl-developer-memory}"
BACKUP_ROOT="${BACKUP_ROOT:-$DATA_ROOT/backups}"
WINDOWS_BACKUP_TARGET="${WINDOWS_BACKUP_TARGET:-}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_DEP_INSTALL="${SKIP_DEP_INSTALL:-0}"
SKIP_CRON_INSTALL="${SKIP_CRON_INSTALL:-0}"
VENV_SYSTEM_SITE_PACKAGES="${VENV_SYSTEM_SITE_PACKAGES:-0}"
ENABLE_RL_CONTROL="${ENABLE_RL_CONTROL:-0}"
RL_ROLLOUT_MODE="${RL_ROLLOUT_MODE:-shadow}"
REQUIRE_CRON_INSTALL="${REQUIRE_CRON_INSTALL:-0}"
SHADOW_MODE_FLAG="1"
if [[ "$RL_ROLLOUT_MODE" == "active" ]]; then
  SHADOW_MODE_FLAG="0"
fi

echo "[1/7] Creating directory layout..."
mkdir -p "$INSTALL_ROOT" "$DATA_ROOT" "$STATE_ROOT" "$BACKUP_ROOT" "$CODEX_HOME"

echo "[2/7] Copying bundle into install root..."
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude "dist" \
    --exclude "build" \
    "$SCRIPT_SOURCE_DIR"/ "$INSTALL_ROOT"/
else
  rm -rf "$INSTALL_ROOT"
  mkdir -p "$(dirname "$INSTALL_ROOT")"
  cp -a "$SCRIPT_SOURCE_DIR" "$INSTALL_ROOT"
fi

echo "[3/7] Creating Python environment..."
VENV_ARGS=()
if [[ "$VENV_SYSTEM_SITE_PACKAGES" == "1" ]]; then
  VENV_ARGS+=("--system-site-packages")
fi
"$PYTHON_BIN" -m venv "${VENV_ARGS[@]}" "$INSTALL_ROOT/.venv"
"$INSTALL_ROOT/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
if [[ "$SKIP_DEP_INSTALL" == "1" ]]; then
  "$INSTALL_ROOT/.venv/bin/python" -m pip install -e "$INSTALL_ROOT" --no-deps
else
  "$INSTALL_ROOT/.venv/bin/python" -m pip install -e "$INSTALL_ROOT"
fi

echo "[4/7] Writing install environment..."
mkdir -p "$INSTALL_ROOT/config"
cat > "$INSTALL_ROOT/config/install.env" <<EOF
export INSTALL_ROOT="$INSTALL_ROOT"
export DATA_ROOT="$DATA_ROOT"
export STATE_ROOT="$STATE_ROOT"
export BACKUP_ROOT="$BACKUP_ROOT"
export WINDOWS_BACKUP_TARGET="$WINDOWS_BACKUP_TARGET"
export CODEX_HOME="$CODEX_HOME"
export RL_DEVELOPER_MEMORY_HOME="$DATA_ROOT"
export RL_DEVELOPER_MEMORY_DB_PATH="$DATA_ROOT/rl_developer_memory.sqlite3"
export RL_DEVELOPER_MEMORY_STATE_DIR="$STATE_ROOT"
export RL_DEVELOPER_MEMORY_BACKUP_DIR="$BACKUP_ROOT"
export RL_DEVELOPER_MEMORY_WINDOWS_BACKUP_TARGET="$WINDOWS_BACKUP_TARGET"
export RL_DEVELOPER_MEMORY_LOCAL_BACKUP_KEEP="\${RL_DEVELOPER_MEMORY_LOCAL_BACKUP_KEEP:-30}"
export RL_DEVELOPER_MEMORY_MIRROR_BACKUP_KEEP="\${RL_DEVELOPER_MEMORY_MIRROR_BACKUP_KEEP:-15}"
export RL_DEVELOPER_MEMORY_LOG_DIR="$STATE_ROOT/log"
export RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE="\${RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE:-75}"
export RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY="\${RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY:-1}"
export RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV="\${RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV:-RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY}"
export RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY="\${RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY:-1}"
export RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE="${RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE:-0}"
export RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES="${RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES:-0}"
export RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON="${RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON:-1}"
export RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS="${RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS:-0}"
export RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS="${RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS:-1.0}"
export RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT="\${RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT:-1}"
export RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE="\${RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE:-$SHADOW_MODE_FLAG}"
export RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES="\${RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES:-1}"
export RL_DEVELOPER_MEMORY_ENABLE_REDACTION="\${RL_DEVELOPER_MEMORY_ENABLE_REDACTION:-1}"
export RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE="${RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE:-1}"
export RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH="$STATE_ROOT/calibration_profile.json"
export VENV_SYSTEM_SITE_PACKAGES="$VENV_SYSTEM_SITE_PACKAGES"
EOF

echo "[5/7] Initializing database..."
# shellcheck disable=SC1091
source "$INSTALL_ROOT/config/install.env"
"$INSTALL_ROOT/.venv/bin/python" -m rl_developer_memory.maintenance init-db

echo "[5a/7] Writing calibration profile..."
"$INSTALL_ROOT/.venv/bin/python" -m rl_developer_memory.maintenance calibrate-thresholds --write-profile >/dev/null

echo "[5b/7] Creating initial safety backup..."
"$INSTALL_ROOT/.venv/bin/python" -m rl_developer_memory.maintenance backup >/dev/null

echo "[6/7] Updating Codex config and global instructions..."
REGISTER_ARGS=(
  --install-root "$INSTALL_ROOT"
  --data-root "$DATA_ROOT"
  --state-root "$STATE_ROOT"
  --codex-home "$CODEX_HOME"
)
if [[ "$ENABLE_RL_CONTROL" == "1" ]]; then
  REGISTER_ARGS+=(--enable-rl-control --rl-rollout-mode "$RL_ROLLOUT_MODE")
fi
"$INSTALL_ROOT/.venv/bin/python" "$INSTALL_ROOT/scripts/register_codex.py" "${REGISTER_ARGS[@]}"

echo "[7/7] Installing cron backup..."
if [[ "$SKIP_CRON_INSTALL" == "1" ]]; then
  echo "Skipping cron installation because SKIP_CRON_INSTALL=1"
else
  if ! bash "$INSTALL_ROOT/scripts/install_cron.sh"; then
    if [[ "$REQUIRE_CRON_INSTALL" == "1" ]]; then
      echo "Cron installation failed and REQUIRE_CRON_INSTALL=1." >&2
      exit 1
    fi
    echo "Warning: cron installation failed; rerun bash $INSTALL_ROOT/scripts/install_cron.sh after fixing cron permissions." >&2
  fi
fi

cat <<EOF

Install complete.

Install root:        $INSTALL_ROOT
Data root:           $DATA_ROOT
State root:          $STATE_ROOT
Backup root:         $BACKUP_ROOT
Windows mirror root: ${WINDOWS_BACKUP_TARGET:-<not configured>}
Codex home:          $CODEX_HOME

Next:
  1. Restart Codex (or open a new Codex session).
  2. Run: bash $INSTALL_ROOT/scripts/verify_install.sh
  3. Optionally inspect: $CODEX_HOME/config.toml

Useful toggles:
  - SKIP_DEP_INSTALL=1              install editable package without resolving dependencies
  - VENV_SYSTEM_SITE_PACKAGES=1     inherit already-installed system/site packages into the install venv
  - ENABLE_RL_CONTROL=1             write RL-control rollout flags to Codex config
  - RL_ROLLOUT_MODE=shadow|active   choose the RL rollout profile when ENABLE_RL_CONTROL=1
  - REQUIRE_CRON_INSTALL=1          fail installation if cron setup does not succeed
EOF
