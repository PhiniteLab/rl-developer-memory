# 06_lifecycle_changes

## Effective behavior
1. **Duplicate reject is parent-scoped when enabled**
   - parent lock path: `src/rl_developer_memory/lifecycle.py:188-191`
   - acquisition: `src/rl_developer_memory/lifecycle.py:241-258`
   - start-path enforcement: `src/rl_developer_memory/lifecycle.py:568-577`
   - duplicate exit code remains configured reuse signal (`75`): `src/rl_developer_memory/server.py:332-336`

2. **Lifecycle monitor now owns shutdown triggers**
   - monitor loop: `src/rl_developer_memory/lifecycle.py:387-422`
   - shutdown request funnel: `src/rl_developer_memory/lifecycle.py:352-385`
   - order is:
     - reap stale slots
     - parent death check
     - stdin EOF check
     - idle timeout check

3. **Idle timeout tracks last observed activity**
   - activity timestamp: `src/rl_developer_memory/lifecycle.py:149-151`, `287-293`
   - idle threshold from settings: `src/rl_developer_memory/settings.py:127-132`
   - aggregate exposure: `src/rl_developer_memory/lifecycle.py:542-551`, `700-703`

4. **Parent death now triggers clean shutdown path**
   - parent PID captured at start: `src/rl_developer_memory/lifecycle.py:148`
   - parent liveness check: `src/rl_developer_memory/lifecycle.py:316-318`
   - shutdown reason: `parent-death`

5. **stdin EOF now triggers clean shutdown path**
   - passive stdio polling without consuming protocol bytes: `src/rl_developer_memory/lifecycle.py:294-314`
   - shutdown reason: `stdin-eof`
   - server main suppresses lifecycle-owned `KeyboardInterrupt`: `src/rl_developer_memory/server.py:340-346`

6. **Stale slot recovery only reclaims dead PID slots**
   - stale predicate: `src/rl_developer_memory/lifecycle.py:320-324`
   - cleanup writeback: `src/rl_developer_memory/lifecycle.py:325-350`
   - no DB/backups/session cleanup was added

7. **Aggregate status now persists shutdown reason after stop**
   - latest slot fallback: `src/rl_developer_memory/lifecycle.py:427-440`
   - aggregate builder fallback: `src/rl_developer_memory/lifecycle.py:527-556`
   - read API fallback: `src/rl_developer_memory/lifecycle.py:659-713`
