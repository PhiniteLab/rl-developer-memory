from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "scripts" / "mcp_reuse_harness.py"


pytest.importorskip("mcp.server.fastmcp", reason="requires installed MCP runtime dependency for end-to-end launch")


def test_mcp_reuse_harness_reports_expected_contract() -> None:
    proc = subprocess.run(
        [sys.executable, str(HARNESS), "--json", "--timeout", "10"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
    payload = json.loads(proc.stdout)
    verdict = payload["verdict"]
    assert verdict["main_started"] is True
    assert verdict["subagent_resolved_to_main"] is True
    assert verdict["duplicate_launch_rejected"] is True
    assert verdict["reuse_signal_emitted"] is True
    assert verdict["duplicate_preserved_single_owner_slot"] is True
    assert verdict["distinct_main_conversations_coexist"] is True
    assert sorted(verdict["active_owner_keys"]) == sorted(
        [payload["main_thread"], payload["sibling_main_thread"]]
    )
    assert payload["preferred_owner_key_env"] == "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY"

    resolution = payload["subagent_resolution"]
    assert resolution["owner_key_env"] == "CODEX_THREAD_ID"
    assert resolution["owner_key"] == payload["main_thread"]
    assert resolution["owner_role"] == "subagent"

    duplicate = payload["duplicate_launch"]
    assert duplicate["returncode"] == payload["duplicate_exit_code_expected"] == 75
