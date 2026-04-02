from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.storage import RLDeveloperMemoryStore


class RLControlStorageIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-rlc-storage-")
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
        self.store = RLDeveloperMemoryStore.from_env()
        self.app = RLDeveloperMemoryApp(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rl_control_schema_columns_exist(self) -> None:
        schema = self.store.schema_state()
        self.assertEqual(schema.current_version, 12)

        with self.store.managed_connection() as conn:
            pattern_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(issue_patterns)").fetchall()
            }
            variant_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(issue_variants)").fetchall()
            }
            episode_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(issue_episodes)").fetchall()
            }
            tables = {
                row["name"]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
            }

        self.assertTrue({"memory_kind", "problem_family", "theorem_claim_type", "validation_tier", "problem_profile_json", "validation_json"}.issubset(pattern_columns))
        self.assertTrue({"algorithm_family", "runtime_stage", "variant_profile_json", "sim2real_profile_json"}.issubset(variant_columns))
        self.assertTrue({"run_manifest_json", "metrics_json", "artifact_refs_json", "evidence_json"}.issubset(episode_columns))
        self.assertIn("audit_findings", tables)
        self.assertIn("artifact_references", tables)

    def test_issue_record_resolution_persists_rl_control_metadata_and_audits(self) -> None:
        stored = self.app.issue_record_resolution(
            title="SAC quadrotor critic instability under saturation",
            raw_error="critic loss became nan after action saturation during training",
            canonical_fix="Clamp normalized actions and use target smoothing before critic updates.",
            prevention_rule="Record action bounds and actuator saturation contracts in the run manifest.",
            project_scope="uav-lab",
            domain="rl_control",
            tags="sac,quadrotor,lyapunov",
            context="nonlinear quadrotor tracking with safety-aware reward",
            command="python train.py --algo sac --env QuadrotorTracking-v1",
            file_path="agents/sac/critic.py",
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
            variant_profile_json={
                "policy_head": "tanh",
                "critic_heads": 2,
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
                "theory_reviewed": True,
                "reviewed_by": "reviewer-A",
            },
            artifact_refs_json=[
                {
                    "kind": "tensorboard",
                    "uri": "runs/quad_sac_exp_01",
                    "description": "training curves",
                    "bytes": 4096,
                }
            ],
            sim2real_profile_json={"stage": "sil", "latency_ms": 6.0},
            patch_summary="Added target policy smoothing and explicit action clamp in critic target path.",
            resolution_notes="Validated in SIL with actuator saturation active.",
        )

        self.assertEqual(stored["memory_kind"], "experiment_pattern")
        self.assertEqual(stored["problem_family"], "safe_rl")
        self.assertEqual(stored["theorem_claim_type"], "uub")
        self.assertEqual(stored["algorithm_family"], "sac")
        self.assertEqual(stored["runtime_stage"], "train")
        self.assertEqual(stored["validation_tier"], "candidate")
        self.assertEqual(stored["promotion"]["requested_tier"], "theory_reviewed")
        self.assertTrue(stored["promotion"]["review_required"])
        self.assertIsNotNone(stored["review_item"])
        self.assertGreaterEqual(stored["audit_finding_count"], 1)
        self.assertEqual(stored["artifact_ref_count"], 1)

        fetched = self.app.issue_get(pattern_id=int(stored["pattern_id"]), include_examples=True)
        self.assertTrue(fetched["found"])
        pattern = fetched["pattern"]
        variant = fetched["variants"][0]
        episode = fetched["episodes"][0]
        artifact_ref = fetched["artifact_refs"][0]

        self.assertEqual(pattern["memory_kind"], "experiment_pattern")
        self.assertEqual(pattern["problem_family"], "safe_rl")
        self.assertEqual(pattern["theorem_claim_type"], "uub")
        self.assertEqual(pattern["validation_tier"], "candidate")
        self.assertEqual(pattern["validation_json"]["promotion_requested_tier"], "theory_reviewed")
        self.assertEqual(pattern["validation_json"]["promotion_status"], "pending_review")
        self.assertEqual(pattern["problem_profile_json"]["system_name"], "quadrotor")
        self.assertEqual(variant["algorithm_family"], "sac")
        self.assertEqual(variant["runtime_stage"], "train")
        self.assertEqual(variant["sim2real_profile_json"]["stage"], "sil")
        self.assertEqual(episode["run_manifest_json"]["seed_count"], 2)
        self.assertAlmostEqual(float(episode["metrics_json"]["tracking_rmse"]), 0.18)
        self.assertEqual(artifact_ref["kind"], "tensorboard")
        self.assertEqual(artifact_ref["uri"], "runs/quad_sac_exp_01")
        self.assertTrue(any(item["audit_type"] == "experiment" for item in fetched["audit_findings"]))
        self.assertTrue(any("seed_count" in item["summary"] for item in fetched["audit_findings"]))


if __name__ == "__main__":
    unittest.main()
