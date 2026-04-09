# 08_runtime_proof

## Controlled duplicate-proof run
Command class: isolated runtime launch using the live interpreter and config-derived env, but repo-local temp state dirs.

Observed result:
```json
{
  "rl_duplicate_returncode": 75,
  "rl_duplicate_stderr": "rl-developer-memory MCP parent process already has active instance. parent_pid=36551. active_pids=[36553]",
  "pgrep_lines": [
    "36553 /home/mehmet/infra/rl-developer-memory/.venv/bin/python -m rl_developer_memory.server"
  ]
}
```

Interpretation:
- first instance stayed alive
- second same-parent spawn was rejected with **exit 75**
- process table showed **max 1 rl-developer-memory instance** during the controlled proof window

## Live host cleanup + check
After removing the stale pre-patch rl-developer-memory process and leaving the config-enabled instance running, the exact runtime check was:

```bash
pgrep -af "codex_issue_memory.server|rl_developer_memory.server" | grep -v '/bin/bash -c'
```

Observed stable output after a second check:
```text
36899 /home/mehmet/infra/codex-issue-memory/.venv/bin/python -m codex_issue_memory.server
36900 /home/mehmet/infra/rl-developer-memory/.venv/bin/python -m rl_developer_memory.server
```

RL conclusion:
- no duplicate `rl_developer_memory.server` process remained
- surviving live process carried the new parent-singleton env from `~/.codex/config.toml:267-269`

## Residual note
- The stale live duplicate was a **pre-patch / pre-config** survivor. Runtime proof required removing it once; after that, the live set stabilized at one process.
