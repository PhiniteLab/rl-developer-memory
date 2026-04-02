# Skill install and sync

This repository is the **canonical source** for the RL-oriented skill bundle.

The bundle should not remain repo-local only:
- the canonical source lives in the repository
- global discovery copies live under the user's resolved `.codex` and `.agents` surfaces
- live MCP authority still remains **`~/.codex/config.toml`**

This document describes the portable sync strategy.

## Runtime authority

The live control plane remains:

```text
~/.codex/config.toml
```

Skill files, plugin metadata, and marketplace entries are **discovery/install surfaces**, not runtime authority.

## Canonical source

The repository canonical source includes:

- `.codex-plugin/plugin.json`
- `.mcp.json`
- `skills/`
- selected policy and workflow docs under `docs/`

Do not edit copied global bundles by hand. Update the repo source and re-run the sync command.

## Portable discovery rules

The sync script resolves targets in this order:

### Codex surface
1. `--codex-home` if provided
2. `CODEX_HOME` if set
3. otherwise `~/.codex`

### Agents bridge surface
1. `--agents-home` if provided
2. `AGENTS_HOME` if set
3. otherwise `~/.agents`

Portable examples should prefer:

```bash
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
```

Do **not** hardcode user-specific absolute paths into repo files.

## Global targets

The sync command installs or refreshes:

- Codex local-plugin bundle:
  - `${CODEX_HOME:-$HOME/.codex}/local-plugins/rl-developer-memory`
- Agents marketplace bridge bundle:
  - `${AGENTS_HOME:-$HOME/.agents}/plugins/plugins/rl-developer-memory`
- Agents marketplace manifest entry:
  - `${AGENTS_HOME:-$HOME/.agents}/plugins/marketplace.json`

## Install modes

### `--mode copy` (default, recommended)
- copies the canonical bundle subset into both global targets
- safest for public GitHub sharing
- avoids symlink surprises on other machines
- keeps docs and skill metadata bundled together

### `--mode symlink`
- creates **relative symlinks** from global targets back to the repo checkout
- useful for active local development
- best when you want global discovery to track repo edits immediately
- less portable across moved/deleted checkouts

### `--mode generated`
- writes a smaller generated bundle for discovery surfaces
- useful when you want only plugin/skill metadata plus policy docs
- keeps runtime authority separate from generated copies

## Recommended commands

Preview target discovery without writing:

```bash
.venv/bin/python scripts/install_skill.py --dry-run --json
```

Install the recommended copy-mode bundle:

```bash
.venv/bin/python scripts/install_skill.py --mode copy
```

Use symlink mode during local iteration:

```bash
.venv/bin/python scripts/install_skill.py --mode symlink
```

The shell wrapper is also available:

```bash
bash scripts/install_skill.sh --mode copy
```

## Idempotency

Re-running the sync command is expected and safe:
- target bundle is refreshed
- marketplace entry is updated in place
- duplicate plugin entries are not added

## What the sync does **not** do

It does **not**:
- modify the repo canonical source
- replace runtime authority with helper files
- hardcode machine-specific usernames
- promote active rollout by default

## Related guidance

- `docs/MCP_RL_INTEGRATION_POLICY.md`
- `docs/MEMORY_SCOPE_OPERATIONS_NOTE.md`
- `docs/CODEX_RL_AGENT_OPERATING_MODEL.md`
- `docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md`
