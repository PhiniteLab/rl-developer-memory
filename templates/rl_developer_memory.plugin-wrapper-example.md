# rl-developer-memory Plugin Wrapper Examples

## 1) Local plugin install (reference)

```bash
mkdir -p ~/.codex/local-plugins
cd ~/.codex/local-plugins

git clone https://github.com/<your-user-or-org>/rl-developer-memory.git rl-developer-memory

# keep ~/.codex/config.toml as the MCP authority
# restart Codex
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
