# Operations

This guide covers health checks, backup and restore, lifecycle inspection, metrics, and review-queue operations.

## Core health checks

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint smoke-learning
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint server-status
rl-developer-memory-maint e2e-mcp-reuse-harness --json
python scripts/release_readiness.py --json
python scripts/rl_quality_gate.py --json
```

For a fuller first-run proof that combines prompt routing, MCP usage, runtime effects, and negative controls, use:

- [`operations/AUTO_TRIGGER_PROOF_PROTOCOL.md`](operations/AUTO_TRIGGER_PROOF_PROTOCOL.md)

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
- same-second and concurrent backup requests reserve unique SQLite paths atomically
- backup manifests are written atomically and paired with the reserved SQLite path

Backup names keep a readable timestamp and add suffixes only when needed:

```text
rl_developer_memory_<stamp>.sqlite3
rl_developer_memory_<stamp>_0001.sqlite3
```

If backup or manifest writing fails, partial local backup artifacts are cleaned up.

## Restore safety

Restore operations are intentionally conservative:

- `restore-backup` verifies the manifest before restoring
- a safety backup is created by default when the active DB exists
- restore refuses to run while lifecycle status reports an active MCP server slot
- lifecycle status is read in pure-read mode during the guard check

Recommended restore runbook:

```bash
rl-developer-memory-maint server-status
rl-developer-memory-maint verify-backup /path/to/backup.sqlite3
rl-developer-memory-maint restore-backup /path/to/backup.sqlite3
rl-developer-memory-maint smoke
```

If `restore-backup` reports an active MCP server, stop the active MCP session/process first. Do not restore over a live MCP process.

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
rl-developer-memory-maint resolve-review 17 approve --note "confirmed"
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

`server-status` can be used as a pure inspection command. Programmatic lifecycle reads are pure-read by default; callers that intentionally want stale-slot cleanup and aggregate status refresh must opt in with `refresh_files=True`.

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


## Memory operations policy

For scope and write-back hygiene, use:
- `docs/MCP_RL_INTEGRATION_POLICY.md`
- `docs/MEMORY_SCOPE_OPERATIONS_NOTE.md`
