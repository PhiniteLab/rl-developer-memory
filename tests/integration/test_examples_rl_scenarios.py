from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "EXAMPLES" / "run_rl_scenarios.py"


def test_rl_scenario_demo_routes_hard_buggy_code_to_correct_fixes(tmp_path: Path) -> None:
    output_json = tmp_path / "rl_scenarios_metrics.json"
    output_markdown = tmp_path / "rl_scenarios_summary.md"
    env = os.environ.copy()
    src_root = str(ROOT / "src")
    env["PYTHONPATH"] = src_root if not env.get("PYTHONPATH") else src_root + os.pathsep + env["PYTHONPATH"]
    proc = subprocess.run([sys.executable, str(SCRIPT), "--output-json", str(output_json), "--output-markdown", str(output_markdown)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["summary"]["status"] == "passed"
    assert payload["summary"]["buggy_cases"] >= 10
    assert payload["summary"]["fixed_cases"] >= 2
    assert payload["summary"]["total_cases"] >= 12
    assert payload["summary"]["buggy_detection_recall"] == 1.0
    assert payload["summary"]["fixed_non_trigger_rate"] == 1.0
    assert payload["summary"]["routing_accuracy"] == 1.0
    assert payload["summary"]["mean_issue_match_latency_ms"] > 0.0
    assert payload["summary"]["mean_score_uplift_after_feedback"] >= 0.0
    assert payload["transport"]["mode"] == "mcp_stdio"
    assert "issue_match" in payload["transport"]["tool_names"]
    assert "issue_feedback" in payload["transport"]["tool_names"]
    cases = {case["case_id"]: case for case in payload["cases"]}
    buggy_case_ids = ["q_learning_bug", "dqn_target_network_bug", "n_step_return_bug", "ppo_clip_objective_bug", "gae_terminal_mask_bug", "actor_critic_bug", "sac_alpha_sign_bug", "td3_target_smoothing_bug", "td3_policy_delay_bug", "vtrace_importance_weight_bug"]
    for case_id in buggy_case_ids:
        case = cases[case_id]
        assert case["failure"]["failed"] is True, case_id
        assert case["mcp_triggered"] is True, case_id
        assert case["mcp_match"]["decision"]["status"] == "match", case_id
        assert case["route_ok"] is True, case_id
    assert "target-network" in cases["dqn_target_network_bug"]["issue_get"]["canonical_fix"].lower()
    assert "minimum" in cases["ppo_clip_objective_bug"]["issue_get"]["canonical_fix"].lower()
    assert "target_entropy" in cases["sac_alpha_sign_bug"]["issue_get"]["canonical_fix"]
    assert "policy_delay" in cases["td3_policy_delay_bug"]["issue_get"]["canonical_fix"]
    assert "importance weights" in cases["vtrace_importance_weight_bug"]["issue_get"]["canonical_fix"].lower()
    for case_id in ["q_learning_fixed", "actor_critic_fixed"]:
        case = cases[case_id]
        assert case["failure"]["failed"] is False, case_id
        assert case["mcp_triggered"] is False, case_id
        assert case["route_ok"] is True, case_id
