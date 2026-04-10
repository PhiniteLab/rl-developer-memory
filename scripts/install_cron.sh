#!/usr/bin/env bash
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(cd "$THIS_DIR/.." && pwd)"

# shellcheck disable=SC1091
source "$INSTALL_ROOT/config/install.env"

CRON_SCHEDULE="${CRON_SCHEDULE:-17 */2 * * *}"

# Validate cron schedule format (5 fields, each with digits/wildcards/ranges/steps)
CRON_FIELD='[0-9*,/\-]+'
if ! printf '%s' "$CRON_SCHEDULE" | grep -Eq "^${CRON_FIELD}[[:space:]]+${CRON_FIELD}[[:space:]]+${CRON_FIELD}[[:space:]]+${CRON_FIELD}[[:space:]]+${CRON_FIELD}$"; then
  echo "Invalid CRON_SCHEDULE format: '$CRON_SCHEDULE'" >&2
  echo "Expected 5-field cron expression (e.g., '17 */2 * * *')" >&2
  exit 1
fi

CRON_TAG="# rl-developer-memory backup"
CRON_COMMAND="bash \"$INSTALL_ROOT/scripts/run_backup.sh\" >/dev/null 2>>\"$STATE_ROOT/log/backup.cron.log\" $CRON_TAG"

mkdir -p "$STATE_ROOT/log"

if ! command -v crontab >/dev/null 2>&1; then
  echo "crontab not found. Install cron first, then rerun: bash scripts/install_cron.sh" >&2
  exit 1
fi

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -v 'rl-developer-memory backup' || true)"
new_cron="$(printf '%s\n%s %s\n' "$filtered" "$CRON_SCHEDULE" "$CRON_COMMAND")"

printf '%s\n' "$new_cron" | crontab -

if command -v systemctl >/dev/null 2>&1 && systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^cron\.service'; then
    sudo systemctl enable --now cron >/dev/null 2>&1 || true
  fi
elif command -v service >/dev/null 2>&1; then
  sudo service cron start >/dev/null 2>&1 || true
fi

echo "Installed cron entry:"
echo "$CRON_SCHEDULE $CRON_COMMAND"
