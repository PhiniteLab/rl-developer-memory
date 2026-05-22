from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.benchmarks import run_dense_bandit_benchmark, seed_dense_bandit_memory


class DenseRetrievalBanditTests(unittest.TestCase):
    _ENV_KEYS = (
        "RL_DEVELOPER_MEMORY_HOME",
        "RL_DEVELOPER_MEMORY_DB_PATH",
        "RL_DEVELOPER_MEMORY_STATE_DIR",
        "RL_DEVELOPER_MEMORY_BACKUP_DIR",
        "RL_DEVELOPER_MEMORY_LOG_DIR",
        "RL_DEVELOPER_MEMORY_ENABLE_DENSE_RETRIEVAL",
        "RL_DEVELOPER_MEMORY_ENABLE_DENSE_CACHE_WRITES",
        "RL_DEVELOPER_MEMORY_ENABLE_TELEMETRY_WRITES",
        "RL_DEVELOPER_MEMORY_STRICT_READ_ONLY",
        "RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT",
    )

    def setUp(self) -> None:
        self._env_backup = {key: os.environ.get(key) for key in self._ENV_KEYS}
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-dense-bandit-")
        base = Path(self.temp_dir.name)
        os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(base / "share")
        os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(base / "share" / "rl_developer_memory.sqlite3")
        os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(base / "state")
        os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(base / "share" / "backups")
        os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(base / "state" / "log")
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_DENSE_RETRIEVAL"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_STRATEGY_BANDIT"] = "1"
        self.app = RLDeveloperMemoryApp()
        seed_dense_bandit_memory(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_dense_retrieval_surfaces_dense_reason_for_paraphrase_queries(self) -> None:
        result = self.app.issue_match(
            error_text=(
                "active runtime uses an incompatible base checkpoint for the low-rank "
                "adapter during local llm warm start"
            ),
            file_path="llm/lora/load_adapter.py",
            command="python train_lora.py --resume adapter.ckpt",
            repo_name="llm-lab",
            project_scope="global",
            limit=3,
        )
        self.assertTrue(result["matches"])
        self.assertEqual(result["matches"][0]["title"], "LoRA adapter checkpoint rank mismatch")
        self.assertIn("dense-retrieval", result["matches"][0]["why"])

        with self.app.store.managed_connection() as conn:
            embedding_count = conn.execute(
                "SELECT COUNT(*) AS count FROM embeddings WHERE object_type = 'variant'"
            ).fetchone()["count"]
        self.assertGreater(int(embedding_count), 0)

    def test_dense_retrieval_can_skip_embedding_cache_writes(self) -> None:
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_DENSE_CACHE_WRITES"] = "0"
        app = RLDeveloperMemoryApp()
        seed_dense_bandit_memory(app)

        with app.store.managed_connection() as conn:
            embedding_count_before = conn.execute(
                "SELECT COUNT(*) AS count FROM embeddings"
            ).fetchone()["count"]

        result = app.issue_match(
            error_text=(
                "active runtime uses an incompatible base checkpoint for the low-rank "
                "adapter during local llm warm start"
            ),
            file_path="llm/lora/load_adapter.py",
            command="python train_lora.py --resume adapter.ckpt",
            repo_name="llm-lab",
            project_scope="global",
            limit=3,
        )

        self.assertTrue(result["matches"])
        self.assertEqual(result["matches"][0]["title"], "LoRA adapter checkpoint rank mismatch")
        self.assertIn("dense-retrieval", result["matches"][0]["why"])

        with app.store.managed_connection() as conn:
            embedding_count_after = conn.execute(
                "SELECT COUNT(*) AS count FROM embeddings"
            ).fetchone()["count"]
        self.assertEqual(int(embedding_count_after), int(embedding_count_before))

    def test_strict_read_only_disables_dense_cache_and_telemetry_writes(self) -> None:
        os.environ["RL_DEVELOPER_MEMORY_STRICT_READ_ONLY"] = "1"
        app = RLDeveloperMemoryApp()
        seed_dense_bandit_memory(app)

        with app.store.managed_connection() as conn:
            embedding_count_before = conn.execute(
                "SELECT COUNT(*) AS count FROM embeddings"
            ).fetchone()["count"]
            retrieval_event_count_before = conn.execute(
                "SELECT COUNT(*) AS count FROM retrieval_events"
            ).fetchone()["count"]
            retrieval_candidate_count_before = conn.execute(
                "SELECT COUNT(*) AS count FROM retrieval_candidates"
            ).fetchone()["count"]

        result = app.issue_match(
            error_text=(
                "active runtime uses an incompatible base checkpoint for the low-rank "
                "adapter during local llm warm start"
            ),
            file_path="llm/lora/load_adapter.py",
            command="python train_lora.py --resume adapter.ckpt",
            repo_name="llm-lab",
            project_scope="global",
            limit=3,
        )

        self.assertTrue(result["matches"])
        self.assertIsNone(result["retrieval_event_id"])

        with app.store.managed_connection() as conn:
            embedding_count_after = conn.execute(
                "SELECT COUNT(*) AS count FROM embeddings"
            ).fetchone()["count"]
            retrieval_event_count_after = conn.execute(
                "SELECT COUNT(*) AS count FROM retrieval_events"
            ).fetchone()["count"]
            retrieval_candidate_count_after = conn.execute(
                "SELECT COUNT(*) AS count FROM retrieval_candidates"
            ).fetchone()["count"]
        self.assertEqual(int(embedding_count_after), int(embedding_count_before))
        self.assertEqual(int(retrieval_event_count_after), int(retrieval_event_count_before))
        self.assertEqual(int(retrieval_candidate_count_after), int(retrieval_candidate_count_before))

    def test_strategy_bandit_promotes_verified_second_candidate(self) -> None:
        first = self.app.issue_match(
            error_text="ModuleNotFoundError: No module named requests",
            project_scope="global",
            session_id="bandit-before",
            repo_name="tooling-lab",
            limit=3,
        )
        self.assertEqual(first["decision"]["status"], "ambiguous")
        second_candidate_pattern = int(first["matches"][1]["pattern_id"])

        feedback = self.app.issue_feedback(
            retrieval_event_id=int(first["retrieval_event_id"]),
            feedback_type="fix_verified",
            candidate_rank=2,
            notes="Positive strategy-bandit training for second candidate.",
        )
        self.assertIsNotNone(feedback["bandit"])
        assert feedback["bandit"] is not None
        self.assertEqual(feedback["bandit"]["policy"], "conservative_hierarchical_thompson")
        self.assertTrue(feedback["bandit"]["global_update_applied"])

        second = self.app.issue_match(
            error_text="ModuleNotFoundError: No module named requests",
            project_scope="global",
            session_id="bandit-after",
            repo_name="tooling-lab",
            limit=3,
        )
        self.assertTrue(second["matches"])
        self.assertEqual(int(second["matches"][0]["pattern_id"]), second_candidate_pattern)
        self.assertIn("strategy-bandit-safe-override", second["matches"][0]["why"])

    def test_dense_bandit_benchmark_summary(self) -> None:
        report = run_dense_bandit_benchmark(self.app, repeats=2)
        self.assertGreaterEqual(float(report["dense_top1_accuracy"]), 1.0)
        self.assertGreater(float(report["dense_reason_rate"]), 0.0)
        self.assertTrue(report["bandit"]["promoted_second_candidate"])


if __name__ == "__main__":
    unittest.main()
