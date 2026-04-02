# rl-developer-memory Plugin Wrapper Examples

## 1) Portable local plugin install (reference)

```bash
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"

git clone https://github.com/<your-user-or-org>/rl-developer-memory.git
cd rl-developer-memory

python scripts/install_skill.py --mode copy --codex-home "$CODEX_HOME" --agents-home "$AGENTS_HOME"

# keep ~/.codex/config.toml as the MCP authority
# restart Codex after MCP/runtime changes
```

## 2) `.mcp.json` remote/local templates

```json
{
  "mcpServers": {
    "rl-developer-memory-remote-template": {
      "type": "http",
      "url": "https://example.invalid/mcp/rl-developer-memory"
    },
    "rl-developer-memory-local-command-template": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "rl_developer_memory.server"]
    }
  }
}
```

## 3) Optional marketplace-style mapping

Use a marketplace entry that points to the local plugin folder only when your environment uses a marketplace bridge.

```json
{
  "plugins": [
    {
      "name": "rl-developer-memory",
      "source": {
        "source": "local",
        "path": "./plugins/rl-developer-memory"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```
