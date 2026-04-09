# rl-developer-memory — 00_execution_trace

## Scope
This report reconstructs the exact launch and runtime path for `python -m rl_developer_memory.server`, then connects it to the installed upstream MCP stdio implementation that actually owns the blocking read loop.

## 1) MCP entrypoint chain

### Host registration
- `~/.codex/config.toml:243-283` defines `[mcp_servers.rl_developer_memory]`.
- `~/.codex/config.toml:244-245` launches `rl-developer-memory/.venv/bin/python -m rl_developer_memory.server`.
- `scripts/register_codex.py:61-93` writes the same registration posture into `~/.codex/config.toml`.
- `.mcp.json:7-14` carries the repo-local stdio template.

### First in-repo code that runs
When Python resolves `-m rl_developer_memory.server`, module import builds the FastMCP object and decorated tools; the module guard then calls `main()`.

- `src/rl_developer_memory/server.py:42` — `FastMCP("rl-developer-memory", json_response=True)`
- `src/rl_developer_memory/server.py:45-59` — cached settings/lifecycle/app helpers
- `src/rl_developer_memory/server.py:330-343` — `main()`
- `src/rl_developer_memory/server.py:346-347` — module guard invokes `main()`

### In-repo execution path
1. `main()` loads the cached lifecycle object.
2. `lifecycle.start()` runs before any MCP protocol work.
3. `mcp.run()` transfers control to the installed `mcp` package.
4. `finally: lifecycle.release()` runs only after `mcp.run()` returns.

Direct code path:

```python
# src/rl_developer_memory/server.py:330-343
lifecycle = get_lifecycle()
lifecycle.start()
try:
    mcp.run()
finally:
    lifecycle.release()
```

### Upstream MCP runtime path
The repo does not implement its own stdio loop; it hands off to the installed `mcp` package:

1. `...site-packages/mcp/server/fastmcp/server.py:279-296` — `FastMCP.run()` selects stdio transport and calls `anyio.run(self.run_stdio_async)`.
2. `...site-packages/mcp/server/fastmcp/server.py:753-760` — `run_stdio_async()` opens `stdio_server()` and awaits `self._mcp_server.run(...)`.
3. `...site-packages/mcp/server/stdio.py:33-88` — `stdio_server()` wraps `sys.stdin.buffer` / `sys.stdout.buffer`, then starts `stdin_reader()` and `stdout_writer()` tasks.
4. `...site-packages/mcp/server/lowlevel/server.py:640-675` — low-level server enters `ServerSession(...)` and iterates `async for message in session.incoming_messages`.
5. `...site-packages/mcp/shared/session.py:221-225, 351-357` — `BaseSession.__aenter__()` starts `_receive_loop()`, and `_receive_loop()` consumes `async for message in self._read_stream`.

## 2) Process lifecycle

### spawn
The host process is the Codex app-server:
- parent PID `11129`
- command: `/home/mehmet/.vscode-server/extensions/openai.chatgpt-26.5401.11717-linux-x64/bin/linux-x86_64/codex app-server --analytics-default-enabled`

That process launches many `rl_developer_memory` children; live process listings showed examples `14037, 14653, 14899, 14936, 16689, 16826, 17044, 17064, 17080, 17114, 17878, 17887, 21013, 21023` under the same parent.

### init
Repo-local init is **only** `lifecycle.start()`:
- owner-key-required check: `src/rl_developer_memory/lifecycle.py:336-343`
- owner lock acquisition: `src/rl_developer_memory/lifecycle.py:190-211`, then `src/rl_developer_memory/lifecycle.py:344-356`
- slot lock acquisition: `src/rl_developer_memory/lifecycle.py:168-188`, then `src/rl_developer_memory/lifecycle.py:357-379`
- slot + aggregate status writes: `src/rl_developer_memory/lifecycle.py:270-334`, then `src/rl_developer_memory/lifecycle.py:380-383`

### ready
There are two different readiness notions:

1. **Transport/session readiness** is inside upstream MCP runtime after `mcp.run()` begins.
2. **Repo app readiness** is only when `get_app()` is first called by a tool wrapper.

For this repo, `get_app()` calls `mark_initialized()` at `src/rl_developer_memory/server.py:55-59`. Therefore `initialized_at` in the lifecycle status file is **not** the MCP initialize-handshake timestamp.

### serve
Once `mcp.run()` is active, the process sits inside the upstream stdio/session receive loop and serves until the transport closes.

### shutdown
Normal shutdown path:
1. upstream stdio/session loop returns
2. `mcp.run()` returns
3. `lifecycle.release()` executes
4. owner/slot locks are released and aggregate status is rewritten

Relevant code:
- release path: `src/rl_developer_memory/lifecycle.py:393-408`
- fallback registration: `atexit.register(self.release)` at `src/rl_developer_memory/lifecycle.py:122-135`

## 3) Stdio communication model

### stdin
`.../mcp/server/stdio.py:60-71` reads:

```python
async def stdin_reader():
    async with read_stream_writer:
        async for line in stdin:
            ...
```

That is **async** I/O, but still transport-blocking in the practical sense: if stdin remains open and no EOF arrives, the loop keeps waiting.

### stdout
`.../mcp/server/stdio.py:75-81` serializes one JSON-RPC message per line and flushes stdout.

### EOF handling
EOF is implicit: when `async for line in stdin` ends, `stdio_server()` unwinds, then `FastMCP.run_stdio_async()` returns, then `lifecycle.release()` runs.

### Local proof
A direct local `subprocess.Popen(..., stdin=PIPE)` reproduction against this repo showed:
- before closing stdin: process alive, lifecycle status still running
- after `proc.stdin.close()`: exit code `0`, lifecycle status `running=false`, note `server-stopped`

So repo shutdown on stdin EOF is **confirmed**.

## 4) Parent relationship

### What the repo uses parent PID for
- owner-key lineage recovery: `src/rl_developer_memory/settings.py:244-304`, `src/rl_developer_memory/settings.py:351-407`
- synthetic owner key generation: `src/rl_developer_memory/settings.py:345-348`
- status metadata: `src/rl_developer_memory/lifecycle.py:282-296`, `src/rl_developer_memory/lifecycle.py:312-330`, `src/rl_developer_memory/lifecycle.py:432-449`

### What the repo does not do
There is **no** parent-death watchdog in:
- `src/rl_developer_memory/server.py`
- `src/rl_developer_memory/lifecycle.py`
- `src/rl_developer_memory/settings.py`

Parent PID is used as metadata and fallback input, not as an enforced liveness dependency.

## 5) Shutdown conditions and non-shutdown scenarios

### Confirmed shutdown conditions
- stdin EOF / transport closure
- explicit process death by external signal

### Confirmed non-shutdown scenario
If the host leaves the child's stdio pipes open, the repo has no independent reason to exit:
- upstream receive loop stays open
- `mcp.run()` never returns
- `release()` never executes
- locks remain held

## 6) Key evidence summary
- host launch source: `~/.codex/config.toml:244-245`
- repo main loop: `src/rl_developer_memory/server.py:330-343`
- stdio read loop: `mcp/server/stdio.py:60-71`
- low-level session loop: `mcp/shared/session.py:351-357`
- no watchdog: no matching shutdown logic anywhere in repo code
