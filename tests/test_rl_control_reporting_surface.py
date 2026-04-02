from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.benchmarks import seed_rl_control_reporting_memory


class RLControlReportingSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-rlc-reporting-")
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
        self.seeded = seed_rl_control_reporting_memory(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_issue_search_exposes_read_only_audit_summary_and_top_level_report(self) -> None:
        result = self.app.issue_search(
            query="SAC quadrotor tracking validated baselines normalized actions",
            project_scope="rl-lab",
            limit=3,
        )
        self.assertTrue(result["read_only_audit"]["enabled"])
        self.assertIn("summary", result["read_only_audit"])
        self.assertEqual(result["read_only_audit"]["summary"]["total_matches"], len(result["read_only_audit"]["matches"]))
        self.assertIn("audit_report", result)
        self.assertGreaterEqual(result["audit_report"]["total_matches"], 1)

    def test_issue_get_exposes_persisted_audit_report(self) -> None:
        bundle = self.app.issue_get(pattern_id=self.seeded["experiment_pattern_id"])
        self.assertTrue(bundle["audit_report"]["enabled"])
        self.assertEqual(bundle["audit_report"]["memory_kind"], "experiment_pattern")
        self.assertEqual(bundle["audit_report"]["promotion"]["requested_tier"], "validated")
        self.assertEqual(bundle["audit_report"]["promotion"]["applied_tier"], "candidate")
        self.assertTrue(bundle["audit_report"]["promotion"]["review_required"])
        self.assertGreaterEqual(bundle["audit_report"]["artifact_summary"]["total"], 1)

    def test_review_queue_and_resolve_expose_audit_reports(self) -> None:
        queue = self.app.issue_review_queue(status="pending", limit=10)
        self.assertTrue(queue["audit_report"]["enabled"])
        self.assertGreaterEqual(queue["audit_report"]["total_items"], 2)
        self.assertTrue(all(item.get("audit_report", {}).get("enabled") for item in queue["items"]))

        review_id = int(queue["items"][0]["id"])
        resolved = self.app.issue_review_resolve(review_id=review_id, decision="approve", note="Reviewed for reporting test.")
        self.assertTrue(resolved["found"])
        self.assertTrue(resolved["audit_report"]["enabled"])
        self.assertIn(resolved["audit_report"]["status"], {"approved", "rejected", "archived", "pending"})


if __name__ == "__main__":
    unittest.main()
