from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rl_developer_memory.app import RLDeveloperMemoryApp


class RLControlPromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-rlc-promotion-")
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
        os.environ["RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION"] = "1"
        self.app = RLDeveloperMemoryApp()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_approve_promotion_review_promotes_validation_tier(self) -> None:
        stored = self.app.issue_record_resolution(
            title="SAC tracking experiment qualifies for validated tier after review",
            raw_error="SAC training stabilized after target smoothing and normalized actions.",
            canonical_fix="Clamp actions, seed the replay buffer, and smooth critic targets.",
            prevention_rule="Every validated RL experiment must persist seeds, baselines, and normalization metadata.",
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
                "train_env_id": "QuadTrain-v1",
                "eval_env_id": "QuadEval-v1",
                "baseline_names": ["mpc", "pid"],
                "normalization": {"observations": True, "actions": True},
            },
            metrics_json={
                "return_mean": 310.0,
                "return_std": 8.0,
                "tracking_rmse": 0.09,
                "control_effort": 0.22,
                "constraint_violation_rate": 0.0,
                "crash_rate": 0.0,
            },
            validation_json={
                "seed_count": 4,
                "baseline_comparison": True,
                "validation_tier": "validated",
            },
        )

        self.assertEqual(stored["validation_tier"], "candidate")
        self.assertEqual(stored["promotion"]["requested_tier"], "validated")
        self.assertTrue(stored["promotion"]["review_required"])
        self.assertEqual(stored["promotion"]["status"], "pending_review")
        self.assertIsNotNone(stored["review_item"])
        self.assertEqual(stored["review_item"]["metadata_json"]["review_mode"], "promotion")

        pattern_before = self.app.issue_get(pattern_id=int(stored["pattern_id"]))
        self.assertEqual(pattern_before["pattern"]["validation_tier"], "candidate")
        self.assertEqual(pattern_before["variants"][0]["status"], "active")

        review_id = int(stored["review_item"]["id"])
        resolved = self.app.issue_review_resolve(review_id=review_id, decision="approve", note="Audit reviewed.")
        self.assertTrue(resolved["found"])
        self.assertEqual(resolved["item"]["status"], "approved")

        pattern_after = self.app.issue_get(pattern_id=int(stored["pattern_id"]))
        self.assertEqual(pattern_after["pattern"]["validation_tier"], "validated")
        self.assertEqual(pattern_after["pattern"]["validation_json"]["promotion_status"], "approved")
        self.assertEqual(pattern_after["variants"][0]["status"], "active")

    def test_reject_promotion_review_keeps_candidate_variant_active(self) -> None:
        stored = self.app.issue_record_resolution(
            title="HJB proof candidate pending formal proof review",
            raw_error="The HJB derivation now includes the missing boundary condition.",
            canonical_fix="Explicitly state the terminal boundary condition and reconcile the HJB residual.",
            prevention_rule="Theory-reviewed promotions must stay candidate-level until the proof review queue approves them.",
            project_scope="theory-lab",
            domain="rl_control",
            memory_kind="theory_pattern",
            problem_family="hjb",
            theorem_claim_type="hjb_optimality",
            problem_profile_json={
                "problem_family": "hjb",
                "dynamics_class": "nonlinear_ct",
                "assumptions": ["smooth value function", "terminal boundary condition"],
                "theorem_claim_type": "hjb_optimality",
                "lyapunov_candidate": "V(x)",
            },
            validation_json={
                "theory_reviewed": True,
                "reviewed_by": "proof-reviewer",
                "validation_tier": "theory_reviewed",
            },
        )

        self.assertEqual(stored["validation_tier"], "candidate")
        self.assertIsNotNone(stored["review_item"])
        self.assertEqual(stored["review_item"]["metadata_json"]["review_mode"], "promotion")

        review_id = int(stored["review_item"]["id"])
        resolved = self.app.issue_review_resolve(review_id=review_id, decision="reject", note="Keep as candidate.")
        self.assertTrue(resolved["found"])
        self.assertEqual(resolved["item"]["status"], "rejected")

        bundle = self.app.issue_get(pattern_id=int(stored["pattern_id"]))
        self.assertEqual(bundle["pattern"]["validation_tier"], "candidate")
        self.assertEqual(bundle["pattern"]["validation_json"]["promotion_status"], "rejected")
        self.assertEqual(bundle["variants"][0]["status"], "active")


if __name__ == "__main__":
    unittest.main()
