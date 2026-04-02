---
name: rl-developer-memory-self-learning
description: Use this skill after a real RL/control failure signal or a verified reusable fix, so retrieval, guardrails, feedback, and write-back stay compact, scoped, and disciplined.
---

# Purpose

Use the `rl_developer_memory` MCP server as a **compact RL-aware failure-memory layer**.

This skill is a **specialized companion** to broader RL engineering work:
- retrieval-first when a real failure appears
- guardrail lookup when policy/scope reminders are needed
- verified write-back when a reusable RL/control lesson is proven

It is **not** the primary skill for general RL architecture or theorem-to-code design.

## Trigger criteria

Trigger this skill when:
- a command fails
- a stack trace appears
- a test or smoke run fails
- a rollout mismatch appears
- a theory/code inconsistency appears
- a verified RL/control/experiment fix might deserve durable memory

## Non-trigger criteria

Do **not** use this skill for:
- generic planning with no real failure signal
- casual RL discussion
- broad architecture work before any failure or guardrail need exists
- saving speculative ideas, temporary workarounds, or unverified fixes

## Retrieval workflow

1. Identify the shortest stable failure excerpt.
2. Call `issue_match` first with:
   - `error_text`
   - `command`
   - `file_path`
   - `project_scope`
3. Read only the top one or two candidates first.
4. Use `issue_get` only if ambiguity remains.
5. Use `issue_guardrails` when prevention rules, policy reminders, or scope guidance are needed.

## Scope workflow

- use `project_scope` for repo-specific RL/control issues
- use `global` for broadly reusable engineering lessons
- use `user_scope` for stable user/team preferences

Do not promote transient session reactions directly into durable memory.

## Write-back workflow

Only call `issue_record_resolution` when all of the following are true:
- the symptom is real
- the fix is specific
- the fix was validated
- the lesson is reusable
- the stored summary is redacted and compact

Prefer compact fields:
- canonical symptom
- canonical fix
- prevention rule
- verification steps

## Hygiene rules

Never write these to durable memory:
- raw secrets or tokens
- private env dumps
- sensitive local absolute paths
- long noisy logs
- speculative hypotheses
- one-off typo fixes

## Token discipline

- prefer short error excerpts over full logs
- prefer `issue_match` over `issue_get`
- read only the top one or two candidates unless ambiguity forces more
- keep write-backs normalized and short

## Delivery format

State:
- whether memory was queried
- which scope was used
- whether guardrails were consulted
- whether feedback or write-back happened
- what validation justified any durable write
