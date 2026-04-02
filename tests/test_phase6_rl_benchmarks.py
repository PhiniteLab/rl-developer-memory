from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.benchmarks import run_rl_control_reporting_benchmark


class Phase6RLBenchmarksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-phase6-rl-bench-")
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rl_control_reporting_benchmark_reports_full_surface_coverage(self) -> None:
        app = RLDeveloperMemoryApp()
        report = run_rl_control_reporting_benchmark(app, repeats=1)
        self.assertEqual(report["search_top1_accuracy"], 1.0)
        self.assertEqual(report["read_only_summary_coverage"], 1.0)
        self.assertEqual(report["pattern_audit_report_coverage"], 1.0)
        self.assertEqual(report["review_queue_report_coverage"], 1.0)
        self.assertTrue(report["rl_metrics_present"])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
