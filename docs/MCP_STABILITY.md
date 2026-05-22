# MCP stability and data-safety contract

This document records the stability posture for the `rl-developer-memory` MCP runtime. It focuses on SQLite data safety, lifecycle reads, backup/restore behavior, and read-like MCP tool side effects.

It is an operator/developer contract. The live runtime authority remains `~/.codex/config.toml`.

## Goals

The MCP runtime should be safe under normal Codex stdio lifecycle behavior:

- migrations should not leave partially-applied schema changes behind
- destructive migrations should be explicitly guarded and auditable
- status/health reads should not mutate lifecycle state unless requested
- read-like retrieval calls should be able to run without dense-cache or telemetry writes
- backup filenames should stay unique even under concurrent backup requests
- restore should refuse to run while an MCP server is active

## Migration safety

`MigrationRunner` applies each migration as a separate atomic unit:

1. open an explicit `BEGIN IMMEDIATE` transaction
2. run the migration statements
3. insert the `schema_migrations` marker
4. commit
5. roll back on any error before the marker is committed

If a migration fails after creating or modifying schema objects, the failed migration's changes are rolled back and no `schema_migrations` marker is written. Earlier successfully committed migrations remain applied.

### Transaction contract

`MigrationRunner.apply_all()` expects a connection with no active caller transaction. It refuses to run when `conn.in_transaction` is already true, avoiding implicit-commit behavior and ambiguous rollback semantics.

### SQL execution contract

Packaged migration SQL is executed statement-by-statement inside the explicit transaction. The executor supports multiple SQL statements on the same physical line and uses `sqlite3.complete_statement` to preserve SQLite statement boundaries.

## Destructive migration policy

Migration SQL is scanned for destructive `DROP TABLE`, `DROP TRIGGER`, `DROP INDEX`, and `DROP VIEW` statements.

Before a DROP executes, the runner writes a DB-local archive manifest to `migration_archive_manifests` with:

- migration version and name
- object type and object name
- whether the object existed
- the object's `sqlite_master.sql` text when available
- table row count for dropped tables when available
- archive timestamp

### DROP TABLE allowlist

Ordinary `DROP TABLE` is rejected unless explicitly allowed. Current allowlisted retired learning-state tables are:

- `ranker_state`
- `contextual_bandit_state`

FTS virtual tables with an `_fts` suffix are also allowed for controlled FTS rebuilds when the existing object is a virtual table.

Unknown ordinary table drops raise `MigrationError`. Add a deliberate policy entry or redesign the migration before dropping new data tables.

### Archive limitation

The archive manifest is an audit record, not a filesystem restore backup. If a migration requires recoverable data snapshots, create and verify a regular backup before running it.

## Lifecycle status reads

`read_server_lifecycle_status(settings)` is pure-read by default.

Default behavior:

- does not rewrite aggregate status JSON
- does not reap stale slot files
- only reads current slot/status snapshots

Use `read_server_lifecycle_status(settings, refresh_files=True)` when you intentionally want the legacy refresh behavior:

- stale slot cleanup
- aggregate status rewrite with `status-read`

### MCP health and restore guard

`issue_health` and backup restore guards use pure-read lifecycle status. Health checks should not mutate lifecycle state, and restore safety checks should not write status files as a side effect.

## Strict read-only retrieval mode

The default runtime remains backward compatible: dense cache writes and telemetry writes are enabled unless explicitly disabled.

Read-like retrieval paths can be made stricter with these settings:

| Setting | Default | Effect |
| --- | --- | --- |
| `RL_DEVELOPER_MEMORY_ENABLE_DENSE_CACHE_WRITES` | `1` | Allows dense retrieval to cache missing embeddings in SQLite. |
| `RL_DEVELOPER_MEMORY_ENABLE_TELEMETRY_WRITES` | `1` | Allows `issue_match` / `issue_search` to write retrieval telemetry. |
| `RL_DEVELOPER_MEMORY_STRICT_READ_ONLY` | `0` | Forces dense cache writes and telemetry writes off, and skips session penalty application that can trigger session cleanup writes. |

### Strict mode behavior

When `RL_DEVELOPER_MEMORY_STRICT_READ_ONLY=1`:

- dense vectors may still be computed in memory
- missing embeddings are not inserted or updated
- retrieval telemetry rows are not written
- `retrieval_event_id` may be absent from match/search responses
- session-memory reranking is skipped to avoid hidden purge writes

`issue_feedback`, `issue_record_resolution`, preference writes, review resolution, backup, restore, and migration commands remain real write operations. Strict read-only mode is intended for read-like retrieval paths, not for turning the whole application into a read-only database process.

## Backup and restore safety

### Concurrent backup uniqueness

Backup path reservation uses atomic exclusive file creation. Same-second backups keep readable names and add suffixes as needed:

```text
rl_developer_memory_<stamp>.sqlite3
rl_developer_memory_<stamp>_0001.sqlite3
rl_developer_memory_<stamp>_0002.sqlite3
```

Concurrent processes cannot reserve the same backup path. If backup or manifest writing fails, partial `.sqlite3` and `.json` artifacts are cleaned up.

Backup manifests are written atomically and remain paired with the reserved SQLite backup path.

### Restore guard

`restore_backup()` refuses to restore when lifecycle status reports an active MCP server slot. Stop the active MCP process before restore, then verify the selected backup and restore deliberately.

Recommended restore posture:

1. stop active MCP users/processes
2. run `rl-developer-memory-maint server-status`
3. run `rl-developer-memory-maint verify-backup <backup.sqlite3>`
4. run `rl-developer-memory-maint restore-backup <backup.sqlite3>`
5. run `rl-developer-memory-maint smoke`

## Validation checklist

Run focused checks after changing this surface:

```bash
python -m pytest tests/unit/memory/test_migrations.py
python -m pytest tests/unit/test_backup.py tests/unit/test_backup_filename_collision.py
python -m pytest tests/unit/test_server_issue_health.py tests/integration/operations/test_phase6_server_lifecycle.py
python -m pytest tests/unit/memory/test_dense_retrieval_bandit.py tests/unit/memory/test_feedback_learning.py
```

Run the full quality gate before release or rollout:

```bash
python -m compileall -q src scripts examples tests
ruff check .
pyright
python -m pytest
python -m rl_developer_memory.maintenance smoke
python scripts/release_readiness.py --json
```

A passed codebase readiness report does not imply active rollout. Active rollout still requires live shadow soak evidence and explicit review-backlog signoff.

## Residual risks and operator notes

- The migration archive manifest is DB-local. Keep regular backups for recoverability.
- Backup filename reservation is concurrency-safe, but backup pruning is not a global cross-process lock. Avoid very small retention counts under heavy concurrent backup schedules.
- Strict read-only mode disables session-memory personalization on read-like paths to avoid hidden writes.
- Runtime authority stays in `~/.codex/config.toml`; repository templates are examples unless explicitly synced into the live Codex home.
