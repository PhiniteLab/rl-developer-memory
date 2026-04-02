#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

CONFIG_BEGIN = "# >>> rl-developer-memory >>>"
CONFIG_END = "# <<< rl-developer-memory <<<"
AGENTS_BEGIN = "<!-- >>> rl-developer-memory >>> -->"
AGENTS_END = "<!-- <<< rl-developer-memory <<< -->"  # replaced below


def replace_block(text: str, begin: str, end: str, new_block: str) -> str:
    if begin in text and end in text:
        prefix = text.split(begin, 1)[0]
        suffix = text.split(end, 1)[1]
        return prefix + new_block + suffix
    if text and not text.endswith("\n"):
        text += "\n"
    return text + ("\n" if text else "") + new_block


def main() -> None:
    parser = argparse.ArgumentParser(description="Register Codex MCP config and AGENTS instructions.")
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--codex-home", required=True)
    parser.add_argument("--enable-rl-control", action="store_true")
    parser.add_argument("--rl-rollout-mode", choices=("shadow", "active"), default="shadow")
    args = parser.parse_args()

    install_root = Path(args.install_root).expanduser().resolve()
    data_root = Path(args.data_root).expanduser().resolve()
    state_root = Path(args.state_root).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()

    codex_home.mkdir(parents=True, exist_ok=True)

    config_path = codex_home / "config.toml"
    config_path.touch(exist_ok=True)
    config_text = config_path.read_text(encoding="utf-8")

    rl_env_lines = ""
    shadow_mode_flag = "1"
    if args.enable_rl_control:
        domain_mode = "hybrid" if args.rl_rollout_mode == "shadow" else "rl_control"
        shadow_mode_flag = "1" if args.rl_rollout_mode == "shadow" else "0"
        rl_env_lines = f"""RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"
RL_DEVELOPER_MEMORY_DOMAIN_MODE = "{domain_mode}"
RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT = "1"
RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT = "1"
RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION = "1"
RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION = "1"
RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET = "2"
RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT = "3"
RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT = "5"
RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS = "12"
"""

    config_block = f"""{CONFIG_BEGIN}
[mcp_servers.rl_developer_memory]
command = "{install_root / ".venv" / "bin" / "python"}"
args = ["-m", "rl_developer_memory.server"]
cwd = "{install_root}"
startup_timeout_sec = 15
tool_timeout_sec = 25
enabled = true
required = false
[mcp_servers.rl_developer_memory.env]
RL_DEVELOPER_MEMORY_HOME = "{data_root}"
RL_DEVELOPER_MEMORY_DB_PATH = "{data_root / "rl_developer_memory.sqlite3"}"
RL_DEVELOPER_MEMORY_STATE_DIR = "{state_root}"
RL_DEVELOPER_MEMORY_BACKUP_DIR = "{data_root / "backups"}"
RL_DEVELOPER_MEMORY_LOG_DIR = "{state_root / "log"}"
RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR = "{state_root / "run"}"
RL_DEVELOPER_MEMORY_SERVER_DUPLICATE_EXIT_CODE = "75"
RL_DEVELOPER_MEMORY_SERVER_REQUIRE_OWNER_KEY = "1"
RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV = "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"
RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY = "1"
RL_DEVELOPER_MEMORY_ENFORCE_SINGLE_MCP_INSTANCE = "0"
RL_DEVELOPER_MEMORY_MAX_MCP_INSTANCES = "0"
RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT = "1"
RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT_SHADOW_MODE = "{shadow_mode_flag}"
RL_DEVELOPER_MEMORY_ENABLE_PREFERENCE_RULES = "1"
RL_DEVELOPER_MEMORY_ENABLE_REDACTION = "1"
RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE = "1"
RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH = "{state_root / "calibration_profile.json"}"
{rl_env_lines}# Prefer explicit RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY injection per main conversation.
# Current Codex runtimes may also derive the main-conversation key from CODEX_THREAD_ID session lineage.
# Optional diagnostics: RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE=main|subagent
# Do not set RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY to a static literal in config.toml.
{CONFIG_END}
"""
    config_text = replace_block(config_text, CONFIG_BEGIN, CONFIG_END, config_block)
    config_path.write_text(config_text, encoding="utf-8")

    agents_path = codex_home / "AGENTS.md"
    agents_path.touch(exist_ok=True)
    agents_text = agents_path.read_text(encoding="utf-8")

    agents_begin = "<!-- >>> rl-developer-memory >>> -->"
    agents_end = "<!-- <<< rl-developer-memory <<< -->"
    agents_block = f"""{agents_begin}

## RL Developer Memory workflow

- For RL/control/experiment-related failures, call the `rl_developer_memory` MCP server **first**.
- Treat `issue_memory` as a fallback and secondary source for general non-RL failures.
- Start with:
  - `issue_match(error_text=..., command=..., file_path=..., project_scope=...)`
- Only fall back to `issue_memory` if either:
  - RL query is ambiguous/abstain for the current scope, or
  - no RL match is returned for this failure pattern.
- Keep writes explicit and separated:
  - Write RL/experiment-specific, strategy, or policy-relevant lessons to `rl_developer_memory` with `issue_record_resolution`.
  - Write general reusable engineering lessons to `issue_memory` with `issue_record_resolution`.
  - Do dual-write only when both scopes are genuinely useful for the same fix.
- For stable reuse, prefer short normalized excerpts and compact `project_scope` values:
  - repo-specific path/config/import issues → repo-scoped scope,
  - broad recurring engineering patterns → global scope.
- Read only the top one or two matches first. Call `issue_get` only if ambiguous.
- Keep writes compact:
  - canonical symptom
  - root cause class
  - canonical fix
  - prevention rule
  - verification steps
- Never dump long raw logs into memory; prefer a short normalized excerpt.

{agents_end}
"""
    agents_text = replace_block(agents_text, agents_begin, agents_end, agents_block)
    agents_path.write_text(agents_text, encoding="utf-8")


if __name__ == "__main__":
    main()
