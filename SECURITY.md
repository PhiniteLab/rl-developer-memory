# Security Policy

## Scope

`rl-developer-memory` is a local-first developer tool that:
- stores structured issue data in local SQLite
- modifies local Codex configuration
- can schedule local backup automation
- may store environment excerpts, verification output, and operational metadata

Security-sensitive surfaces include:
- `~/.codex/config.toml`
- local database and backup paths
- lifecycle lock/state files
- installation and verification scripts
- redaction behavior for stored payloads

## Reporting a vulnerability

Do **not** open a public issue containing exploit details, secrets, or unsafe reproduction steps.

Preferred route:
1. use GitHub private vulnerability reporting if enabled
2. otherwise contact the maintainer privately before disclosure

## What helps a report

Please include:
- affected version or commit
- operating environment (Linux / WSL)
- exact command or workflow involved
- impact summary
- minimal reproduction steps
- whether the issue touches config mutation, SQLite data, backups, or stored sensitive values

## Current security posture

- the project is documented for Linux and WSL workflows
- redaction is configurable and enabled in the recommended runtime posture
- active data should stay on the local Linux or WSL filesystem
- mirrored backup targets should be copies, not the live database path
