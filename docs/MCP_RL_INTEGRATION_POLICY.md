# RL MCP integration policy

This document defines how to use the `rl_developer_memory` MCP surface inside an RL/control
development workflow without breaking runtime posture, memory quality, or redaction hygiene.

It is a **workflow contract**, not a second runtime authority. The live MCP registration source of
truth remains `~/.codex/config.toml`.

## Runtime invariants

- Live runtime authority: **`~/.codex/config.toml` only**
- Preferred owner-key env: **`RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY`**
- Owner-key posture: **required**
- Duplicate exit code **`75`**: treat as **reuse**, not crash
- Global total instance cap logic: **`0`**
- Default rollout posture: **shadow**
- Active DB path: local Linux/WSL path only, never `/mnt/c/...`
- Secret hygiene: no unredacted secrets, tokens, env excerpts, or sensitive local paths in memory

---

## 1) Decision policy

Use the MCP surface as a staged policy, not as a blind logging system.

### A. Before implementation expands

Use `issue_match` when any of the following is true:
- a compile/import/type error appears
- a runtime error appears
- a flaky test pattern is suspected
- a seed instability or variance problem appears
- a rollout mismatch appears
- a theorem/code inconsistency appears
- a similar repo-local failure pattern may already exist

Recommended query shape:
- shortest stable `error_text`
- `command` if known
- `file_path` if known
- `project_scope` when repo-specific
- `session_id` if you want local reranking memory

### B. After `issue_match`

- **`match`**  
  Inspect the top result first. Use `issue_get` only if details are needed.

- **`ambiguous`**  
  Read only the top one or two candidates with `issue_get`, then use `issue_guardrails`.

- **`abstain`**  
  Continue fresh debugging. Do not force a memory write just because no hit exists.

### C. When to use `issue_guardrails`

Use `issue_guardrails` when:
- you need prevention rules before editing
- you need preference overlays
- you need a “what should I avoid repeating?” reminder
- you are in RL/control-sensitive work and want scope-aware caution

### D. During iteration

Use `issue_feedback` after a **meaningful** attempt:
- candidate helped → positive feedback
- candidate was wrong → negative feedback
- keep weak, local reactions session-scoped via `session_id`

Do **not** call feedback for every trivial thought; call it when a candidate materially affected the next action.

### E. After verification

Use `issue_record_resolution` only after:
- the failure is real
- the fix is specific
- the fix passed validation
- the resolution is reusable
- the summary is redacted

---

## 2) RL development lifecycle placement

The recommended lifecycle is:

1. **Problem framing / reproduction**
   - reproduce the failure or identify the decision point
   - call `issue_match`

2. **Candidate review**
   - if needed, call `issue_get`
   - if useful, call `issue_guardrails`

3. **Implementation / experiment**
   - make the smallest defensible change
   - keep validation local and repo-native

4. **Validation**
   - compile/import/type/test/smoke/benchmark/theory checks as relevant

5. **Feedback**
   - call `issue_feedback` for accepted/rejected candidate usefulness

6. **Write-back**
   - call `issue_record_resolution` only for verified reusable fixes

This same flow applies to:
- algorithm development
- experiment orchestration
- theorem/code work
- rollout validation
- benchmark/reporting work

---

## 3) Scope policy

Choose scope deliberately.

### `project_scope`
Use for repo-specific issues, such as:
- local package layout/import problems
- RL backbone config schema issues
- theorem-to-code sync issues
- rollout/doctor/reuse harness mismatches
- benchmark/reporting payload issues
- checkpoint/resume or local scripts in this repo

Recommended repo scope:
- `project_scope="rl-developer-memory"`

### `global`
Use for broadly reusable engineering patterns, such as:
- wrong interpreter / wrong virtualenv
- common Python packaging mistakes
- generic SQLite lock mitigation
- general CI/lint/type-check lessons

### `user_scope`
Use for stable user-specific preferences, such as:
- prefers small additive patches
- prefers pyright before pytest
- avoids heavyweight dependencies
- wants shadow-first rollout discipline
- favors theorem/code sync before RL promotion

Rule of thumb:
- repo-specific behavior → `project_scope`
- reusable engineering lesson → `global`
- personal or team style/tuning preference → `user_scope`

---

## 4) Preference and session policy

There are two different memory layers:

### A. Durable preference layer
Use:
- `issue_set_preference`
- `issue_list_preferences`

Store only stable preferences, for example:
- coding style
- validation order
- preferred strategy family
- avoid-strategy rules
- review strictness

Use `user_scope` for personal defaults and `project_scope` when a repo-specific style should be shared.

### B. Session layer
Use:
- `session_id` on `issue_match`
- `session_id` on `issue_feedback`

Use session memory for:
- temporary candidate reranking
- within-debug-session accept/reject signals
- local false-positive suppression

Do **not** promote raw session reactions directly into durable issue patterns.

---

## 5) Write-back policy

Only verified fixes should enter durable memory.

## Minimum write-back gate

All must be true:
- the failure or issue is real
- the symptom is stable enough to describe compactly
- the fix is specific and reproducible
- relevant validation passed
- the scope decision is explicit
- the stored content is redacted

## Never write back

Do **not** store:
- secrets, tokens, auth headers, private keys
- raw `.env` excerpts
- unredacted local machine paths when avoidable
- noisy one-off logs
- speculative hypotheses
- temporary hacks
- unverified “maybe fixed it” notes
- single-run flake noise without confirmed pattern

## Required resolution shape

A durable resolution should contain:
- canonical symptom
- root cause class
- canonical fix
- prevention rule
- verification steps
- selected scope

---

## 6) Error-family write-back rules

### Compile / import / type errors
Write to memory when:
- deterministic
- fix is clear and reusable
- validated by lint/type/import/test path

Typical scope:
- repo-specific import path issue → `project_scope`
- generic interpreter/venv lesson → `global`

### Runtime errors
Write when:
- reproducible enough
- root cause is isolated
- post-fix smoke/test/command passes

### Flaky tests
Write only when:
- flakiness is confirmed, not just suspected
- source is classified
- mitigation is validated across reruns

Do **not** store a single unexplained flake as durable memory.

### Seed instability / variance issues
Write when:
- instability exceeds a defined threshold
- mitigation is tested across multiple seeds or equivalent bounded evidence
- the stored lesson is reusable beyond one exact run

### Rollout mismatch
Examples:
- shadow vs active posture misuse
- owner-key mismatch
- duplicate exit `75` misclassified as crash
- instance-cap expectation mismatch

Write when:
- doctor/harness/runtime evidence confirms the mismatch
- corrected behavior is verified

### Theory inconsistency
Examples:
- theorem/code sync mismatch
- missing assumptions
- wrong audit hook for theorem claim

Write when:
- sync validator or theory audit fails for a real reason
- fix is validated by sync/test path

---

## 7) Redaction policy

Before any durable write:

Redact or generalize:
- tokens
- credentials
- private URLs
- exact local usernames when unnecessary
- sensitive absolute paths
- raw env var dumps

Prefer:
- normalized symptom excerpts
- relative file paths
- compact canonical summaries

Good:
- `ModuleNotFoundError under project venv mismatch`
- `checkpoint root incorrectly pointed to /mnt/c path`

Bad:
- full shell history
- copied `.env`
- raw stack trace with secrets or private paths

---

## 8) Example usage flows

### Flow A — compile/import failure

1. `issue_match(error_text=..., command=..., file_path=..., project_scope="rl-developer-memory")`
2. if ambiguous → `issue_get(...)`
3. implement fix
4. validate with `ruff` / `pyright` / targeted tests
5. `issue_feedback(...)`
6. if reusable and verified → `issue_record_resolution(...)`

### Flow B — seed instability

1. observe unstable returns or large variance
2. `issue_match(error_text="seed instability / return variance spike", project_scope="rl-developer-memory")`
3. `issue_guardrails(...)` for prevention rules
4. run multi-seed or bounded reproducibility check
5. `issue_feedback(...)`
6. store only if mitigation is verified and not one-off noise

### Flow C — rollout mismatch

1. detect owner-key / duplicate / rollout posture mismatch
2. `issue_match(error_text=..., command="doctor or harness command", project_scope="rl-developer-memory")`
3. validate with doctor / reuse harness
4. `issue_feedback(...)`
5. record durable fix only if mismatch is confirmed and corrected

### Flow D — theorem inconsistency

1. theorem/code sync or audit failure appears
2. `issue_match(error_text=..., file_path="docs/THEORY_TO_CODE.md" or related module, project_scope="rl-developer-memory")`
3. inspect top match or guardrails
4. fix registry/doc/audit mismatch
5. validate with theorem sync script + tests
6. store only verified reusable pattern

---

## 9) Recommended short contract for contributors

When working on RL code in this repo:
- query memory before expanding work on a real failure
- keep retrieval compact and scoped
- use session memory for local ranking, durable memory for verified lessons
- keep shadow posture as default
- respect owner-key and reuse semantics
- never write secrets or noisy logs into memory
- write back only verified reusable fixes
