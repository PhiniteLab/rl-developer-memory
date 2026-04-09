# 05_patch_map

## Scope
- Repo: `/home/mehmet/infra/rl-developer-memory`
- Goal: parent-scoped singleton + duplicate rejection + idle/parent/EOF shutdown + stale slot recovery
- Compatibility posture:
  - code default remains env-gated (`RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON` default off in code)
  - live enablement moved to `~/.codex/config.toml:267-269`
  - reuse harness keeps parent singleton disabled in test mode (`src/rl_developer_memory/mcp_reuse_harness.py:103-105`, `168-170`)

## Minimal patch points
1. `src/rl_developer_memory/settings.py:59,123-132,227-229`
   - added lifecycle env parsing:
     - `RL_DEVELOPER_MEMORY_SERVER_ENFORCE_PARENT_SINGLETON`
     - `RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS`
     - `RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS`
2. `src/rl_developer_memory/lifecycle.py:188-245,352-422,558-653`
   - duplicate guard, lifecycle monitor, shutdown controller, stale recovery, richer aggregate status
3. `src/rl_developer_memory/server.py:330-346`
   - suppress lifecycle-triggered `KeyboardInterrupt` while preserving real interrupts
4. `src/rl_developer_memory/mcp_reuse_harness.py:103-105,168-170`
   - keep legacy reuse contract by explicitly disabling parent singleton in harness env
5. `tests/integration/operations/test_phase6_server_lifecycle.py:255-509`
   - added lifecycle regression tests:
     - duplicate parent guard
     - stale slot cleanup
     - idle timeout
     - parent death
     - stdin EOF
6. `~/.codex/config.toml:267-269`
   - live host enablement for rl-developer-memory singleton/idle watchdog

## Change map by concern
- Duplicate guard: `lifecycle.py:188-245`, `558-581`
- Idle timeout: `lifecycle.py:352-422`
- Parent death: `lifecycle.py:352-422`
- Stdin EOF: `lifecycle.py:294-314`, `352-422`
- Stale slot cleanup: `lifecycle.py:325-350`
- Shutdown reason persistence: `lifecycle.py:427-556`, `659-713`
- Server main-loop compatibility: `server.py:340-346`
