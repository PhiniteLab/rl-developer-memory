# Operations

This guide covers health checks, backups, restore, review operations, metrics, and troubleshooting.

## Live invariants

For a running Codex installation:

- keep exactly one `[mcp_servers.rl_developer_memory]` block in `~/.codex/config.toml`
- keep the active database on the local Linux or WSL filesystem
- require a stable owner key for each main conversation
- resolve owner key via explicit -> alias -> `CODEX_THREAD_ID` lineage -> parent-process lineage -> recent-session inference -> optional synthetic fallback
- keep live custom skill or plugin assets under `~/.codex/local-plugins/**`
- treat repository templates as examples, not live configuration

## Core health checks

Useful routine commands:

```bash
rl-developer-memory-maint smoke
rl-developer-memory-maint server-status
rl-developer-memory-maint doctor --mode shadow --max-instances 0
rl-developer-memory-maint e2e-mcp-reuse-harness --json
rl-developer-memory-maint metrics --window-days 14
```

What they help answer:

- does the local package still start correctly?
- is the live MCP entry present and unique?
- how many MCP processes are alive right now?
- is the service running with the intended safety settings?
- is the repo-side MCP reuse contract healthy before testing a live launcher?
- are retrieval quality and review backlog trending in the right direction?

## Backup workflow

### Create a backup

```bash
rl-developer-memory-maint backup
```

From a checkout:

```bash
PYTHONPATH=src python3 -m rl_developer_memory.maintenance backup
```

The service uses the SQLite backup API rather than raw file copies.

### List backups

```bash
rl-developer-memory-maint list-backups --limit 20
```

### Verify a backup

```bash
rl-developer-memory-maint verify-backup /path/to/rl_developer_memory_YYYYMMDD_HHMMSS.sqlite3
```

### Restore a backup

```bash
rl-developer-memory-maint restore-backup /path/to/rl_developer_memory_YYYYMMDD_HHMMSS.sqlite3
```

By default, restore creates a safety backup of the current live database before replacing it.

To disable that extra safety snapshot explicitly:

```bash
rl-developer-memory-maint restore-backup /path/to/backup.sqlite3 --no-safety-backup
```

## What a backup contains

Each backup run creates:

- a snapshot file named like `rl_developer_memory_YYYYMMDD_HHMMSS.sqlite3`
- a sibling JSON manifest containing creation time, source DB path, digest, size, and host information

If `RL_DEVELOPER_MEMORY_WINDOWS_BACKUP_TARGET` is set, the snapshot and manifest are mirrored there as well.

## Metrics and dashboards

Inspect recent operational behavior:

```bash
rl-developer-memory-maint metrics --window-days 14
```

Export a dashboard snapshot:

```bash
rl-developer-memory-maint export-dashboard --output ~/rl-developer-memory-dashboard.json
```

Key things to watch:

- retrieval decision mix (`match`, `ambiguous`, `abstain`)
- feedback outcomes and verified conversions
- strategy signals such as observation-only promotions and safe overrides
- preference rule hits
- pending review count
- backup freshness
- calibration profile state

## Review queue operations

List pending review items:

```bash
rl-developer-memory-maint review-queue --status pending --limit 20
```

Resolve one item:

```bash
rl-developer-memory-maint resolve-review 17 accept --note "Confirmed after manual inspection"
```

Use the review queue when the service intentionally holds a consolidation decision for explicit approval instead of silently merging a risky variant.

## Recommended config inspection

Print a recommended env block for the current machine:

```bash
rl-developer-memory-maint recommended-config --mode shadow --format toml
```

Validate the live installation against that operating mode:

```bash
rl-developer-memory-maint doctor --mode shadow --max-instances 0
```

Validate the repository-side reuse contract before a live launcher test:

```bash
rl-developer-memory-maint e2e-mcp-reuse-harness --json
```

Inspect current process slots and owner metadata:

```bash
rl-developer-memory-maint server-status
```

If you are using conversation-owner integration, inspect returned lifecycle metadata:

- `owner_key`, `owner_key_env`, `owner_role`
- `active_slots[].pid`, `active_slots[].parent_pid`
- `active_count`, `launch_count`, `assigned_slot`, `status_path`, `lock_path`
- per-slot status metadata: `slot`, `command`, `process_alive`, `started_at`, `initialized_at`

Duplicate launch behavior is expected when:

- the resolved owner key already has a live slot
- the launch exits through duplicate rejection with the configured owner-key exit code (`75` by default)

For the separate live launcher procedure that tries to prove real shared stdio reuse, see [`ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md`](ORCHESTRATION_STDLIO_REUSE_CHECKLIST.md).

## Retention and cleanup

Prune telemetry and resolved review items:

```bash
rl-developer-memory-maint prune-retention --telemetry-days 90 --review-days 120
```

Backups are pruned automatically after each snapshot according to:

- `RL_DEVELOPER_MEMORY_LOCAL_BACKUP_KEEP`
- `RL_DEVELOPER_MEMORY_MIRROR_BACKUP_KEEP`

## Logs

Important log paths:

- runtime log directory: `RL_DEVELOPER_MEMORY_LOG_DIR`
- default state log directory: `~/.local/state/rl-developer-memory/log`
- cron backup stderr log: `~/.local/state/rl-developer-memory/log/backup.cron.log`

If scheduled backups appear idle, start with the cron log file.

## Scheduled backups

The repository includes `scripts/install_cron.sh`, which installs a cron entry that runs the bundled backup helper.

Default schedule:

```text
17 */2 * * *
```

Install or reinstall it manually:

```bash
bash ~/infra/rl-developer-memory/scripts/install_cron.sh
```

Override the schedule while installing:

```bash
CRON_SCHEDULE="0 * * * *" bash ~/infra/rl-developer-memory/scripts/install_cron.sh
```

## Troubleshooting

### Codex does not show `rl_developer_memory`

- Restart Codex after editing `~/.codex/config.toml`.
- Confirm there is exactly one `[mcp_servers.rl_developer_memory]` block.
- Confirm `command`, `args`, and `cwd` point to a real installation.
- Run `rl-developer-memory-maint doctor --mode shadow --max-instances 0`.

### The service starts too many times

- Check `RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY` and either confirm explicit `RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY` injection or confirm that `CODEX_THREAD_ID` session lineage is available to the runtime.
- If lineage is unavailable, confirm whether synthetic fallback is expected (`RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY`) and that synthetic owner semantics are acceptable.
- Use `rl-developer-memory-maint server-status` to inspect active slots.
- Avoid duplicate `rl_developer_memory` registrations in alternate config surfaces.
- Confirm the runtime resolves the same owner key for the main conversation and its subagents, whether by explicit injection or by `CODEX_THREAD_ID` lineage.
- If you intentionally use a compatibility cap, also confirm `RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES` matches that policy.

### A launch exits with code `75`

- This is the controlled duplicate exit used by conversation-owner dedup.
- It means another live MCP process already owns that conversation key.
- The correct caller behavior is to reuse the already-owned conversation MCP instead of retrying new launches with the same owner key.
- Use the orchestration checklist to confirm that subagents still get successful `rl_developer_memory` tool calls after that dedup signal.

### Restore failed or looked unsafe

- Verify the target backup first with `rl-developer-memory-maint verify-backup ...`.
- Restore again without `--no-safety-backup` unless you have a very specific reason.
- Confirm the active DB path is on the local filesystem.

### Backups work locally but not to the mirror target

- Check that `RL_DEVELOPER_MEMORY_WINDOWS_BACKUP_TARGET` points to a writable path.
- Keep the live DB local and use the mirror path only for copies.

### SQLite behaves badly on `/mnt/c/...`

- Move the active database back under `~/.local/share/rl-developer-memory`.
- Keep Windows or cloud locations for mirrored backups only.

## RL/control audit health and reporting

For RL/control deployments, the most useful extra maintenance commands are:

```bash
rl-developer-memory-maint rl-audit-health --window-days 30 --limit 10
rl-developer-memory-maint benchmark-rl-control-reporting
rl-developer-memory-maint recommended-config --mode shadow --profile rl-control-shadow
rl-developer-memory-maint doctor --mode shadow --profile rl-control-shadow
```

### `rl-audit-health`

This command summarizes:

- RL/control pattern counts by `memory_kind`
- validation-tier mix
- audit findings by severity and audit type
- pending review items by review mode
- promotion backlog by requested tier
- highest-risk stored patterns

Use it before switching from shadow RL rollout to a stronger active posture.

### `benchmark-rl-control-reporting`

This benchmark checks that the reporting surface is actually live:

- `issue_search` exposes retrieval-time audit summaries
- `issue_get` exposes persisted audit summaries
- `issue_review_queue` exposes reviewer-facing summaries
- `issue_metrics` exports the RL/control health section

Treat this as a regression gate for the reporting surface rather than a retrieval-only benchmark.
