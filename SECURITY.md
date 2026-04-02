# Security Policy

## Supported versions

Security fixes are prioritized for:
- the latest tagged release
- the `main` branch

Older commits and local forks may receive best-effort guidance only.

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

Do **not** open a public issue containing exploit details, secrets, tokens, or unsafe reproduction steps.

Preferred private reporting route:
1. Open a private report through GitHub Security Advisories:
   - <https://github.com/PhiniteLab/rl-developer-memory/security/advisories/new>
2. If that flow is unavailable in your environment, use the guidance in [SUPPORT.md](SUPPORT.md) only to request a private contact path and **do not include vulnerability details**.

## Response targets

The project aims to:
- acknowledge a new private report within **72 hours**
- provide an initial triage update within **7 calendar days**
- coordinate a remediation and disclosure plan before public release of details

These are targets, not legal guarantees, but they define the intended maintainer response posture.

## What helps a report

Please include:
- affected version or commit
- operating environment (Linux / WSL)
- exact command or workflow involved
- impact summary
- minimal reproduction steps
- whether the issue touches config mutation, SQLite data, backups, or stored sensitive values

## Disclosure expectations

Please give the maintainer reasonable time to validate, mitigate, and prepare a fix before public disclosure. Public proof-of-concept details should wait until a fix or safe mitigation is available.

## Current security posture

- the project is documented for Linux and WSL workflows
- redaction is configurable and enabled in the recommended runtime posture
- active data should stay on the local Linux or WSL filesystem
- mirrored backup targets should be copies, not the live database path
