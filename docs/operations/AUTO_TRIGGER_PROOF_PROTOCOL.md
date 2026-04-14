# Auto-trigger proof protocol

This runbook is the **recommended first test** for new installations, new Codex setups, and any environment where you want to prove that:

- prompt routing is working,
- skill and tool selection is sensible,
- the MCP server is reachable,
- the live runtime state changes when expected,
- failure and abstention cases behave safely,
- and duplicate/reuse ownership rules still hold.

Use this document before deeper rollout work.

## Before you start

This runbook assumes:

- you are inside a **live Codex session**,
- the `rl_developer_memory` MCP server is already **registered and reachable**,
- and the environment has already passed a basic install check.

If you have not yet done a basic runtime check, run these first:

```bash
PYTHONPATH=src .venv/bin/python -m rl_developer_memory.maintenance smoke
PYTHONPATH=src .venv/bin/python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
```

This protocol is heavier than a quick smoke test. It is intended to prove **routing + MCP + runtime effects**, not just installation.

### Safety note

Use **synthetic test data** while running this proof. Do not store real secrets, private tokens, raw `.env` excerpts, or sensitive local paths during feedback and write-back prompts.

## Purpose

This protocol is designed to prove the end-to-end chain:

1. **user prompt**
2. **routing / skill selection**
3. **tool selection**
4. **MCP execution when needed**
5. **observable runtime effect**

It also proves the opposite case:

- prompts that should **not** trigger MCP or repo tooling do **not** do so.

## Evidence standard

For a prompt to count as **proved**, collect three layers of evidence:

1. **Routing evidence**
   - expected skill or workflow appears in the transcript
   - expected tool call appears in the transcript

2. **MCP evidence**
   - the tool returns live fields such as `pid`, `db_path`, `decision`, `retrieval_event_id`, or metrics

3. **End-to-end effect**
   - state-changing prompts cause a measurable delta
   - non-state prompts do **not** cause an unwanted delta

### Proof levels

- **Level A — direct proof**
  - transcript tool call
  - live MCP response
  - measurable post-state effect

- **Level B — strong proof**
  - transcript tool call
  - live MCP response
  - effect is plausible but not fully state-diffed

- **Level C — weak proof**
  - only narrative or indirect reasoning
  - not enough for a “verified” claim

- **Level F — failed**
  - wrong trigger, wrong tool, missing effect, or unsafe behavior

## Baseline snapshot

Before running the 10 prompts, capture a baseline.

### MCP baseline

Run:

- `issue_health`
- `issue_metrics(window_days=30)`
- `issue_recent(limit=5)`

These are **MCP tool calls inside Codex**, not plain shell commands.

### CLI baseline

Run:

```bash
PYTHONPATH=src .venv/bin/python -m rl_developer_memory.maintenance server-status
PYTHONPATH=src .venv/bin/python -m rl_developer_memory.maintenance doctor --mode shadow --max-instances 0
```

### Record these fields

- `retrieval.total`
- `retrieval.by_mode.match`
- `retrieval.by_mode.search`
- `feedback.counts`
- `review_queue.pending`
- `server.pid`
- `server.owner_key_env`
- `server.active_count`

### Baseline acceptance

The baseline is acceptable when:

- MCP health is good
- the server is running
- the active DB path is on the local Linux/WSL filesystem
- there is no fatal configuration error

## Execution rule

For **every** prompt in this protocol, use:

1. **pre-snapshot**
2. **prompt execution**
3. **post-snapshot**

This is required so you can prove whether a tool call had a real effect.

## The 10-prompt proof matrix

Use the following prompts as written, or with only minimal wording changes.

| ID | Real prompt | Expected skill / workflow | Expected tool or MCP tool | Expected MCP effect | Failure condition | Target result |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | “Translate this into English: ‘Bellek sunucusu çalışıyor mu?’” | none | none | none | any unnecessary repo or MCP tool call | PASS |
| 2 | “Şimdi repomu detaylıca anla ve analiz et.” | `core-repo-audit`, `core-task-classifier` | repo inspection / routing only | none | missing repo-audit flow or unnecessary memory lookup | PASS |
| 3 | “Şimdi bunu detaylıca test et. Özellikle skill tetiklenmesi, MCP’nin çalışması ve canlı performansı doğrula.” | `core-task-classifier`, `python-quality-gate` | shell validation + MCP health/metrics | health and metrics become part of the answer | only narrative answer with no real validation | PASS |
| 4 | “`ModuleNotFoundError: No module named requests` alıyorum. Önce bellekte benzeri var mı bak.” | memory routing | `issue_match` | retrieval counter increases; `retrieval_event_id` appears | no MCP lookup or fabricated answer | PASS |
| 5 | “Aynı sorunu farklı sözcüklerle tekrar soruyorum; önceki kaydı aç.” | memory routing | `issue_match`, then `issue_get` if needed | detailed candidate retrieval | details are invented without `issue_get` when required | PASS |
| 6 | “`Segmentation fault in custom JPEG decoder after native image resize` için bellekte uygun bir şey var mı?” | memory routing | `issue_match` | likely `abstain` or low-confidence outcome | fake confident match | PASS |
| 7 | “Bu repo için rollout güvenliğinde neyi tekrar etmemeliyim? Önce guardrail’leri getir.” | prevention routing | `issue_guardrails`, optionally `issue_list_preferences` | prevention-oriented result, not generic search | wrong tool family or no prevention lookup | PASS |
| 8 | “Az önce önerdiğin candidate işe yaramadı. Bunu negatif feedback olarak işle ve tekrar dene.” | feedback routing | `issue_feedback` then `issue_match` | reranking or clearer abstention in the same session | feedback never recorded or no follow-up retrieval | PASS |
| 9 | “Sorunu doğruladım: yanlış virtualenv yüzünden import bozuluyormuş. Bunu reusable fix olarak kaydet.” | write-back routing | `issue_record_resolution` | durable record becomes visible in recent/search/metrics | no write-back or unverified write-back | PASS |
| 10 | “Aktif DB yolunu `/mnt/c/...` altına koyarsam sistem doğru reddediyor mu? Test et.” | validation routing | shell or regression test | explicit fail-fast guard | no rejection or unclear error | PASS |

## Prompt-by-prompt evidence template

Copy this block for each prompt:

```md
## Prompt <ID>
- Prompt:
- Expected skill / workflow:
- Expected tool:
- Expected MCP effect:
- Pre-snapshot:
- Post-snapshot:
- Actual tool chain:
- Actual MCP response:
- Metrics delta:
- Failure observed:
- Proof level: A / B / C / F
- Final result: PASS / FAIL / INCERTAIN
```

## Shared failure criteria

Mark the prompt as **failed** if any of the following happens.

### Routing failures

- expected skill or workflow is missing
- a no-tool prompt triggers unnecessary repo or MCP activity
- a real failure prompt avoids MCP lookup when lookup was requested

### Tool failures

- the wrong MCP tool is called
- the expected MCP tool is not called
- feedback or write-back happens in the wrong order

### Effect failures

- `issue_match` is called but the retrieval counters do not move
- `issue_feedback` is called but no same-session effect can be observed
- `issue_record_resolution` succeeds nominally but no durable visibility appears afterward
- a guardrail prompt returns no prevention-oriented output

### Safety failures

- raw secrets or sensitive local paths are written durably
- unverified fixes are stored as reusable memory
- a prompt that should abstain is forced into a misleading confident answer

## Log and trace checklist

Use this checklist for each prompt.

### Transcript checklist

- [ ] expected skill or workflow is visible
- [ ] expected tool call is visible
- [ ] the final explanation matches the actual tool evidence

### MCP checklist

- [ ] `issue_health` is healthy when relevant
- [ ] `retrieval_event_id` appears for `issue_match`
- [ ] `issue_metrics` confirms the expected delta
- [ ] `issue_feedback` has a visible follow-up effect
- [ ] `issue_record_resolution` has a visible durable effect

### Runtime checklist

- [ ] `server-status` shows a running server
- [ ] `owner_key_env` is sensible for the active environment
- [ ] `active_count` is plausible
- [ ] duplicate/reuse rules remain intact

### CLI checklist

- [ ] exit code is correct
- [ ] warnings are recorded, not hidden
- [ ] negative-path tests fail in the expected way
- [ ] temporary directories are isolated when used

### Evidence integrity checklist

- [ ] pre-snapshot collected
- [ ] prompt executed
- [ ] post-snapshot collected
- [ ] proof level labeled honestly

## Recommended run order

Run the prompts in this order:

1. Prompt 1 — no-tool control
2. Prompt 2 — analysis-only control
3. Prompt 10 — negative config guard
4. Prompt 4 — real failure lookup
5. Prompt 6 — abstain case
6. Prompt 7 — guardrails
7. Prompt 8 — feedback and rerank
8. Prompt 9 — durable write-back
9. Prompt 3 — full validation request
10. Prompt 5 — follow-up continuity check

This order helps you detect:

- false positive triggering first,
- then positive MCP behavior,
- then reranking and write-back discipline.

## Final verdict rule

### VERIFIED

You may call the auto-trigger chain **verified** when:

- at least **8 of 10** prompts pass
- at least **6** of those passes are **Level A**
- Prompt 1 and Prompt 10 behave correctly as controls
- Prompt 4, Prompt 8, and Prompt 9 show real MCP effects
- no safety failure occurs

### PARTIALLY VERIFIED

Use this when:

- 6–7 prompts pass, or
- too many results are only Level B, or
- the core chain works but control prompts are weak

### NOT VERIFIED

Use this when:

- two or more critical prompts fail
- state deltas cannot be confirmed
- wrong or unnecessary tool triggering is common

## Final report template

```md
# Auto-trigger proof run summary

- Run date:
- Repo:
- Baseline MCP health:
- Baseline retrieval total:
- Final retrieval total:
- Final feedback delta:
- Final recent/search verification:
- Duplicate/reuse status:
- Warning list:
- Critical failures:

## Prompt results
| ID | Result | Proof level | Notes |
| --- | --- | --- | --- |
| 1 | PASS | A | ... |
| 2 | PASS | A | ... |
| 3 | PASS | B | ... |

## Final verdict
- Auto-trigger chain: VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED
- MCP runtime: VERIFIED / NOT VERIFIED
- Write-back discipline: VERIFIED / NOT VERIFIED
- Negative guard behavior: VERIFIED / NOT VERIFIED
```

## Related documents

- [../OPERATIONS.md](../OPERATIONS.md)
- [../VALIDATION_MATRIX.md](../VALIDATION_MATRIX.md)
- [../USAGE.md](../USAGE.md)
- [../ROLLOUT.md](../ROLLOUT.md)
- [../SKILL_INSTALL_SYNC.md](../SKILL_INSTALL_SYNC.md)
