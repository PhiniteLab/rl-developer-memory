# Operations

This guide covers health checks, backup and restore, lifecycle inspection, metrics, and review-queue operations.

## Core health checks

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint smoke-learning
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
```

## What these commands tell you

- `smoke` — the package starts, stores seed data, and returns a valid top match
- `smoke-learning` — feedback/session-memory plumbing still works
- `doctor` — config, rollout posture, paths, calibration profile, and backup freshness align
- `server-status` — current lifecycle slot and owner-key state
- `e2e-mcp-reuse-harness` — duplicate-owner reuse behavior still works

## Backup workflow

Create a backup:
```bash
rl-developer-memory-maint backup
```

List backups:
```bash
rl-developer-memory-maint list-backups --limit 10
```

Verify a backup:
```bash
rl-developer-memory-maint verify-backup /path/to/backup.sqlite3
```

Restore a backup:
```bash
rl-developer-memory-maint restore-backup /path/to/backup.sqlite3
```

Restore without creating a safety backup:
```bash
rl-developer-memory-maint restore-backup /path/to/backup.sqlite3 --no-safety-backup
```

## Backup expectations

Recommended live posture:
- keep the active DB on Linux/WSL local storage
- use backup verification before risky restore actions
- treat mirrored targets as copy destinations, not the active database path
- monitor backup freshness with `doctor`

## Metrics and reports

Inspect recent behavior:
```bash
rl-developer-memory-maint metrics --window-days 30
```

Export a dashboard snapshot:
```bash
rl-developer-memory-maint export-dashboard --output ~/rl-developer-memory-dashboard.json
```

Useful things to watch:
- decision mix (`match`, `ambiguous`, `abstain`)
- feedback outcomes
- review backlog
- calibration profile presence
- backup freshness
- strategy bandit shadow signals

## Review queue operations

```bash
rl-developer-memory-maint review-queue --status pending --limit 20
rl-developer-memory-maint resolve-review 17 accept --note "confirmed"
```

## Retention and cleanup

```bash
rl-developer-memory-maint prune-retention --telemetry-days 90 --review-days 120
```

## Logs and state

Primary runtime locations:
- state dir: `RL_DEVELOPER_MEMORY_STATE_DIR`
- log dir: `RL_DEVELOPER_MEMORY_LOG_DIR`
- backup dir: `RL_DEVELOPER_MEMORY_BACKUP_DIR`
- calibration profile: `RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH`

## Cron-based backups

The project ships `scripts/install_cron.sh` to install a backup schedule.

Default schedule:
```text
17 */2 * * *
```

Manual install:
```bash
bash ~/infra/rl-developer-memory/scripts/install_cron.sh
```

If your environment cannot support cron immediately, use `SKIP_CRON_INSTALL=1` during install and configure scheduling later.
