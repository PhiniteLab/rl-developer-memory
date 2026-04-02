from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rl_developer_memory.app import RLDeveloperMemoryApp


class RLControlAuditHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-rlc-audit-hardening-")
        base = Path(self.temp_dir.name)
        os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(base / "share")
        os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(base / "share" / "rl_developer_memory.sqlite3")
        os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(base / "state")
        os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(base / "share" / "backups")
        os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(base / "state" / "log")
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_DOMAIN_MODE"] = "rl_control"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT"] = "1"
        self.app = RLDeveloperMemoryApp()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_experiment_audit_hardening_blocks_high_tier_without_baselines(self) -> None:
        stored = self.app.issue_record_resolution(
            title="Validated request without baseline manifest should be blocked",
            raw_error="The SAC run looked stable but the report omitted baseline details.",
            canonical_fix="Persist baseline identities and normalization settings before promoting the run.",
            prevention_rule="Validated promotions require baseline comparison metadata and reproducibility context.",
            project_scope="rl-lab",
            domain="rl_control",
            memory_kind="experiment_pattern",
            problem_family="safe_rl",
            algorithm_family="sac",
            runtime_stage="train",
            run_manifest_json={
                "algorithm_family": "sac",
                "runtime_stage": "train",
                "seed_count": 4,
                "train_env_id": "Train-v1",
                "eval_env_id": "Eval-v1",
            },
            metrics_json={
                "return_mean": 250.0,
                "constraint_violation_rate": 0.0,
            },
            validation_json={
                "seed_count": 4,
                "baseline_comparison": True,
                "validation_tier": "validated",
            },
        )

        self.assertEqual(stored["promotion"]["status"], "blocked")
        self.assertIn("missing-baseline-comparison", stored["promotion"]["blockers"])
        self.assertIsNone(stored["review_item"])
        self.assertEqual(stored["validation_tier"], "observed")

        fetched = self.app.issue_get(pattern_id=int(stored["pattern_id"]))
        summaries = [item["summary"] for item in fetched["audit_findings"]]
        self.assertTrue(any("baseline_comparison" in summary and "baseline_names" in summary for summary in summaries))
        self.assertTrue(any("normalization settings" in summary for summary in summaries))
        self.assertTrue(any("tracking_rmse" in summary for summary in summaries))

    def test_theory_audit_hardening_surfaces_boundary_and_review_gaps(self) -> None:
        stored = self.app.issue_record_resolution(
            title="HJB claim missing boundary conditions",
            raw_error="The HJB proof writes the stationarity condition but omits the terminal boundary condition.",
            canonical_fix="Add the terminal boundary condition and state the proof assumptions explicitly.",
            prevention_rule="All HJB patterns must capture terminal or boundary conditions before reuse.",
            project_scope="theory-lab",
            domain="rl_control",
            memory_kind="theory_pattern",
            problem_family="hjb",
            theorem_claim_type="hjb_optimality",
            problem_profile_json={
                "problem_family": "hjb",
                "dynamics_class": "nonlinear_ct",
                "assumptions": ["smooth value function", "compact input set"],
                "theorem_claim_type": "hjb_optimality",
                "lyapunov_candidate": "V(x)",
            },
            validation_json={
                "validation_tier": "candidate",
            },
        )

        self.assertEqual(stored["validation_tier"], "candidate")
        fetched = self.app.issue_get(pattern_id=int(stored["pattern_id"]))
        summaries = [item["summary"] for item in fetched["audit_findings"]]
        self.assertTrue(any("terminal or boundary assumptions" in summary for summary in summaries))
        self.assertTrue(any("without explicit theory_reviewed evidence" in summary for summary in summaries))


if __name__ == "__main__":
    unittest.main()
