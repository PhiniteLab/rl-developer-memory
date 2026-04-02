# Codex RL agent operating model

This guide defines a **token-conscious, owner-key-safe, MCP-aware working model** for RL development in this repository.

It is an **operating model**, not a second runtime authority. Live runtime authority remains **`~/.codex/config.toml`**.

## Goals

- turn a single high-level RL request into a disciplined multi-phase workflow
- keep analysis, planning, coding, validation, stabilization, documentation, and memory write-back connected
- preserve owner-key / reuse / shadow-rollout posture
- reduce token waste and context bloat
- keep durable memory high-signal and verified

## Runtime invariants

These invariants are non-negotiable for Codex-driven RL work in this repo:

- live runtime authority: **`~/.codex/config.toml` only**
- owner-key posture: **required**
- preferred main-conversation owner key: **`RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`**
- duplicate exit code **`75`** means **reuse**, not crash
- global max instance cap logic: **`0`**
- default rollout posture: **shadow**
- active SQLite DB path must stay on local Linux/WSL storage, not `/mnt/c/...`
- secrets, tokens, env excerpts, and sensitive local paths must be redacted before durable storage

---

## 1) Recommended agent roles

Use the smallest role set that safely covers the task.

| Role | Responsibility | Typical outputs | May write code? |
|---|---|---|---|
| Main orchestrator | Owns scope, plan gate, sequencing, owner-key continuity, final decision, and final report | short plan, merged patch intent, final decision | yes |
| Explorer | Maps repo paths, commands, entrypoints, risk zones, existing contracts | bounded repo map, file list, command list | no |
| Router | Classifies task family, risk, validation depth, and required workflow | plan gate, validation depth, role routing | no |
| Refactorer | Implements a bounded patch in an assigned write scope | focused code/doc edits | yes |
| Validator | Runs quality gates and classifies failures clearly | pass/fail matrix, failing command excerpts | no |
| Reviewer | Independent correctness pass; looks for gaps, regressions, and docs/code drift | review findings, accept/revise signal | no |
| RL auditor (optional, at most one) | Reviews RL/control-specific assumptions, stability, metrics, theory/code, and rollout posture | RL risk findings, audit summary | usually no |

### Default role set

For most RL development tasks:
1. **Explorer**
2. **Router**
3. **Refactorer**
4. **Validator**
5. **Reviewer**

Add **RL auditor** only when the task materially touches:
- algorithm design
- reward/objective changes
- theorem-to-code mapping
- stabilization logic
- promotion or rollout policy

---

## 2) Phase-by-phase orchestration flow

### Phase 0 — kickoff
Run **Explorer + Router in parallel**.

Outputs should stay compact:
- repo delta only
- relevant files only
- relevant commands only
- explicit risk notes only

### Phase 1 — short plan gate
The main orchestrator writes a short plan before edits:
- task classification
- minimal write scope
- validation depth
- whether RL auditor is needed
- what is parallel vs serial

No meaningful implementation should start before this gate.

### Phase 2 — bounded implementation
Use **one refactorer** by default.

Use multiple refactorers only when:
- write scopes are disjoint
- the next local step is not blocked on one of them
- merge order is obvious

### Phase 3 — validation
Use **validator** after edits are merged or a bounded patch is ready.

Minimum expected order for Python work:
1. syntax/import sanity
2. `ruff check .`
3. `pyright`
4. `python -m pytest`
5. `python -m rl_developer_memory.maintenance smoke`
6. domain-specific smoke / benchmark / doctor / harness checks as needed
7. `python -m build`

### Phase 4 — review
Use **reviewer** after validation results are known.

Reviewer checks:
- correctness and regressions
- docs/code/CLI/MCP sync
- owner-key / rollout / DB-path posture drift
- whether the patch stayed bounded

### Phase 5 — memory and wrap-up
The main orchestrator decides whether memory interaction is needed.

Durable memory write-back is **post-validation only**.
Subagents should not directly promote speculative fixes into durable memory.

---

## 3) Main conversation / subagent / MCP reuse model

## Main conversation contract

Treat one user request as one orchestration root.
The **main conversation** owns:
- final plan gate
- final patch intent
- final validation matrix
- final write-back decision

## Owner-key model

- the main conversation should prefer **`RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`**
- subagents must resolve to the same main-conversation owner key
- duplicate launches that hit the same owner should be interpreted as **reuse**, with exit code **`75`**
- a duplicate launch must not create a second stateful owner slot

## MCP reuse policy

Use the MCP runtime as a shared, conversation-owned surface:
- subagents may consult the same runtime indirectly through the owner-key model
- durable write-back should be coordinated by the main orchestrator after validation
- session-scoped ranking memory may be used during debugging, but should not become durable memory automatically

---

## 4) Parallel vs sequential work policy

### Safe to parallelize

- Explorer + Router
- multiple read-only repo inspections
- docs drafting while implementation is still being planned
- disjoint implementation tasks with clearly separated file ownership
- test planning or benchmark reading that does not block the next code step

### Keep sequential

- plan gate -> implementation
- implementation merge -> validation
- validation -> review
- review -> durable memory write-back
- shadow-readiness evidence -> active rollout recommendation

### Do not parallelize

- two agents editing the same file group
- durable memory write-back from multiple agents
- validation against code that is still changing under another agent
- rollout promotion decisions before validation evidence is complete

---

## 5) MCP usage points in the RL lifecycle

Use `rl_developer_memory` as a disciplined failure-and-preference surface.

| RL lifecycle point | MCP action |
|---|---|
| before debugging expands after a real failure | `issue_match` |
| top hit is ambiguous | `issue_get` for top 1-2 only |
| before editing when prevention rules matter | `issue_guardrails` |
| after a meaningful accepted/rejected candidate | `issue_feedback` |
| only after validated, reusable resolution | `issue_record_resolution` |
| stable user/team style preferences | `issue_set_preference` / `issue_list_preferences` |

### Important rule

Do **not** query or write issue memory just because work is happening.
Use it when there is a real failure, ambiguity, prevention need, or a verified reusable lesson.

---

## 6) Token-efficient prompt design

The default prompt shape should be short, structured, and bounded.

## Recommended prompt envelope

Use this shape when delegating to subagents:

```text
Goal:
Scope:
Non-goals:
Files or surfaces to inspect:
Expected output shape:
Constraints:
```

### Good delegation example

```text
Goal: classify validation depth for a bounded RL trainer patch.
Scope: tests/, trainers/, experiments/ only.
Non-goals: do not edit files.
Expected output shape: 5 bullets max with commands.
Constraints: respect owner-key/shadow/live-authority posture.
```

### Prompt rules that reduce token burn

- ask for **file paths and decisions**, not long prose
- ask for **top risks only**, not exhaustive repo summaries
- ask for **diff-ready recommendations**, not large rewrites
- include **non-goals** to prevent wandering
- bound the expected answer shape (`3 bullets`, `1 table`, `5 files max`)
- avoid pasting large logs; provide normalized error excerpts instead
- avoid forwarding full conversation history when a short summary is enough

---

## 7) Summary, checkpoint, and task decomposition strategy

Large RL tasks should not carry full context from start to finish.

## Phase summary rule

At the end of each phase, produce a compact checkpoint with:
- what changed
- what evidence matters
- what remains blocked
- which files now matter
- next command or next decision

### Suggested checkpoint template

```text
Phase:
What changed:
Evidence:
Open risks:
Files in scope:
Next step:
```

## Decomposition strategy

Break large RL work into units such as:
- algorithm contract
- trainer/runtime stabilization
- theory/audit mapping
- experiment config/runner
- rollout/validation/promotion
- docs and memory policy

Each unit should have:
- one owner
- bounded files
- one explicit done-criterion
- one validation slice

## Context hygiene rules

- do not restate repo-wide policy docs in full; link or summarize
- carry forward only the **delta** from the previous phase
- convert long logs into short normalized excerpts
- record stable facts once, then refer to them by summary
- prefer one strong doc link over re-pasting policy text

---

## 8) Minimum safe orchestration contract for RL work

A Codex-led RL task should satisfy this minimum contract:

1. **Inspect first**
   - explorer + router kickoff
2. **Plan before edits**
   - short plan gate recorded
3. **Bound the write scope**
   - no opportunistic rewrites
4. **Respect runtime posture**
   - live authority, owner-key, duplicate 75, shadow default, Linux DB path
5. **Validate before claims**
   - lint/type/test/smoke/build, plus RL-specific checks when relevant
6. **Review before promotion**
   - independent pass for correctness and drift
7. **Write memory only after proof**
   - verified reusable lessons only
8. **Prefer no-go to weak active rollout**
   - active rollout recommendation requires clean shadow evidence and manageable review backlog

### RL-specific extra checks

Use RL-specific validation when relevant:
- `python -m rl_developer_memory.maintenance smoke-learning`
- `python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0`
- `python -m rl_developer_memory.maintenance doctor --mode shadow --profile rl-control-shadow`
- `python -m rl_developer_memory.maintenance e2e-mcp-reuse-harness --json`
- `python -m rl_developer_memory.maintenance benchmark-rl-control-reporting`
- `python scripts/release_acceptance.py --json`

---

## 9) Practical workflow examples

## Example A — bounded trainer fix

- Explorer: identify trainer/checkpoint/diagnostics files
- Router: classify as bugfix + RL runtime validation
- Refactorer: patch trainer and tests
- Validator: run core gate + targeted smoke
- Reviewer: check rollback/determinism/docs sync
- Main orchestrator: decide whether a reusable failure lesson should be written back

## Example B — new RL algorithm skeleton

- Explorer: inspect algorithms/agents/networks/theory/config/tests
- Router: classify as feature + RL auditor needed
- Refactorer: implement algorithm skeleton and config/docs/tests
- RL auditor: verify objective/stability/theory hooks
- Validator: run core gate + smoke-learning + theorem/code sync
- Reviewer: check boundedness and extension safety

## Example C — rollout hardening

- Explorer: inspect release_acceptance, maintenance, rollout docs, ownership docs
- Router: classify as operational hardening
- Refactorer: patch readiness/reporting/docs/tests
- Validator: run doctor/harness/benchmark/release_acceptance
- Reviewer: confirm active recommendation stayed conservative

---

## 10) Recommended repo touch points

For this repository, the most useful lightweight changes are:
- keep this guide in `docs/`
- link it from `docs/README.md` and root `README.md`
- reference it from `AGENTS.md` without duplicating the full policy
- mention it in `docs/DEVELOPMENT.md` so contributors know where the orchestration contract lives

This keeps the guidance discoverable without turning the repo into a second runtime authority.
