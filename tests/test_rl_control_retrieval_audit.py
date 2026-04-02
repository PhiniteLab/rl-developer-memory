from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest

from rl_developer_memory.app import RLDeveloperMemoryApp


class RLControlRetrievalAuditTests(unittest.TestCase):
    _ENV_KEYS = (
        "RL_DEVELOPER_MEMORY_HOME",
        "RL_DEVELOPER_MEMORY_DB_PATH",
        "RL_DEVELOPER_MEMORY_STATE_DIR",
        "RL_DEVELOPER_MEMORY_BACKUP_DIR",
        "RL_DEVELOPER_MEMORY_LOG_DIR",
        "RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL",
        "RL_DEVELOPER_MEMORY_DOMAIN_MODE",
        "RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT",
        "RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT",
        "RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION",
        "RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT",
    )

    def setUp(self) -> None:
        self._env_backup = {key: os.environ.get(key) for key in self._ENV_KEYS}
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-rlc-retrieval-")
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
        os.environ["RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION"] = "0"
        os.environ["RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT"] = "3"
        self.app = RLDeveloperMemoryApp()
        self._record_patterns()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _record_patterns(self) -> None:
        self.theory_record = self.app.issue_record_resolution(
            title="HJB boundary condition mismatch in nonlinear regulation proof",
            raw_error="Bellman residual stays nonzero because terminal boundary condition is omitted in the HJB derivation.",
            canonical_fix="State the terminal boundary condition explicitly and align the discrete Bellman residual with the continuous-time HJB objective.",
            prevention_rule="Every HJB claim must record terminal or boundary conditions and the continuous/discrete convention.",
            project_scope="rl-lab",
            domain="rl_control",
            tags="hjb,bellman,lyapunov",
            memory_kind="theory_pattern",
            problem_family="hjb",
            theorem_claim_type="hjb_optimality",
            algorithm_family="mpc",
            runtime_stage="design",
            problem_profile_json={
                "problem_family": "hjb",
                "system_name": "inverted_pendulum",
                "dynamics_class": "nonlinear_ct",
                "assumptions": ["smooth value function", "compact input set", "terminal boundary condition"],
                "theorem_claim_type": "hjb_optimality",
                "lyapunov_candidate": "V(x)",
            },
            validation_json={
                "validation_tier": "theory_reviewed",
                "theory_reviewed": True,
                "reviewed_by": "proof-reviewer",
            },
            patch_summary="Added the missing terminal condition and re-derived the stationarity condition.",
            resolution_notes="Reviewed against the continuous-time HJB form.",
        )
        self.experiment_record = self.app.issue_record_resolution(
            title="SAC quadrotor critic instability under saturation",
            raw_error="critic loss became nan after action saturation during training",
            canonical_fix="Clamp normalized actions and use target smoothing before critic updates.",
            prevention_rule="Record action bounds and actuator saturation contracts in the run manifest.",
            project_scope="rl-lab",
            domain="rl_control",
            tags="sac,quadrotor,safe-rl",
            memory_kind="experiment_pattern",
            problem_family="safe_rl",
            theorem_claim_type="uub",
            algorithm_family="sac",
            runtime_stage="train",
            problem_profile_json={
                "problem_family": "safe_rl",
                "system_name": "quadrotor",
                "task_name": "tracking",
                "dynamics_class": "nonlinear_dt",
                "assumptions": ["bounded disturbance", "bounded reference"],
                "theorem_claim_type": "uub",
                "lyapunov_candidate": "V(x)=x^T P x",
            },
            run_manifest_json={
                "algorithm_family": "sac",
                "runtime_stage": "train",
                "seed_count": 2,
                "train_env_id": "QuadrotorTrackingTrain-v1",
                "eval_env_id": "QuadrotorTrackingEval-v1",
                "baseline_names": ["mpc", "pid"],
                "action_bounds": [-1.0, 1.0],
            },
            metrics_json={
                "return_mean": 245.0,
                "return_std": 12.5,
                "tracking_rmse": 0.18,
                "control_effort": 0.31,
                "constraint_violation_rate": 0.02,
            },
            validation_json={
                "seed_count": 2,
                "baseline_comparison": True,
                "validation_tier": "candidate",
            },
            sim2real_profile_json={"stage": "sil", "latency_ms": 6.0},
            patch_summary="Added target policy smoothing and explicit action clamp in critic target path.",
            resolution_notes="Validated in SIL with actuator saturation active.",
        )

    def test_rl_control_search_prioritizes_theory_pattern_and_reports_domain_audit(self) -> None:
        result = self.app.issue_search(
            query="HJB Bellman boundary condition optimality proof for nonlinear control",
            project_scope="rl-lab",
            limit=3,
        )

        self.assertEqual(result["patterns"][0]["pattern_id"], self.theory_record["pattern_id"])
        self.assertEqual(result["patterns"][0]["memory_kind"], "theory_pattern")
        self.assertEqual(result["patterns"][0]["problem_family"], "hjb")
        self.assertEqual(result["patterns"][0]["theorem_claim_type"], "hjb_optimality")

        audit = result["read_only_audit"]
        self.assertTrue(audit["enabled"])
        self.assertEqual(audit["query_domain_profile"]["memory_kind_hint"], "theory_pattern")
        self.assertEqual(audit["query_domain_profile"]["problem_family_hint"], "hjb")
        self.assertEqual(audit["query_domain_profile"]["theorem_claim_type_hint"], "hjb_optimality")
        self.assertEqual(audit["matches"][0]["pattern_id"], self.theory_record["pattern_id"])
        self.assertEqual(audit["matches"][0]["severity"], "clean")
        self.assertIn("rl-theorem-claim:hjb_optimality", audit["matches"][0]["compatibility_reasons"])
        self.assertIn("rl-problem-family:hjb", audit["matches"][0]["rank_reasons"])

    def test_rl_control_match_exposes_read_only_audit_without_false_iss_trigger(self) -> None:
        result = self.app.issue_match(
            error_text="SAC quadrotor training critic saturation seed issue",
            project_scope="rl-lab",
            limit=2,
        )

        self.assertTrue(result["matches"])
        top_match = result["matches"][0]
        self.assertEqual(top_match["pattern_id"], self.experiment_record["pattern_id"])
        self.assertEqual(top_match["memory_kind"], "experiment_pattern")
        self.assertEqual(top_match["algorithm_family"], "sac")
        self.assertEqual(top_match["runtime_stage"], "train")

        audit = result["read_only_audit"]
        self.assertTrue(audit["enabled"])
        self.assertEqual(audit["query_domain_profile"]["theorem_claim_type_hint"], "none")
        self.assertEqual(audit["query_domain_profile"]["memory_kind_hint"], "experiment_pattern")
        self.assertEqual(audit["matches"][0]["pattern_id"], self.experiment_record["pattern_id"])

        finding_summaries = [item["summary"] for item in audit["matches"][0]["findings"]]
        self.assertTrue(any("seed_count is below the recommended threshold" in summary for summary in finding_summaries))
        self.assertNotEqual(audit["query_domain_profile"]["theorem_claim_type_hint"], "iss")

    def test_rl_control_search_reports_sim2real_mismatch_as_read_only_warning(self) -> None:
        result = self.app.issue_search(
            query="quadrotor hardware deployment sac saturation",
            project_scope="rl-lab",
            limit=3,
        )

        self.assertTrue(result["patterns"])
        self.assertEqual(result["patterns"][0]["pattern_id"], self.experiment_record["pattern_id"])

        audit = result["read_only_audit"]
        self.assertTrue(audit["enabled"])
        self.assertEqual(audit["query_domain_profile"]["memory_kind_hint"], "sim2real_pattern")
        self.assertEqual(audit["query_domain_profile"]["runtime_stage_hint"], "deployment")
        self.assertEqual(audit["query_domain_profile"]["sim2real_stage_hint"], "hardware")
        self.assertEqual(audit["matches"][0]["severity"], "warning")

        finding_summaries = [item["summary"] for item in audit["matches"][0]["findings"]]
        self.assertTrue(any("runtime-stage 'train'" in summary for summary in finding_summaries))
        self.assertTrue(any("sim2real-stage 'sil'" in summary for summary in finding_summaries))
        self.assertTrue(any("seed_count is below the recommended threshold" in summary for summary in finding_summaries))


if __name__ == "__main__":
    unittest.main()
