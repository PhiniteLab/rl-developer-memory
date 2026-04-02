from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.benchmarks import run_runtime_diagnostics


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_runtime_diagnostics_integrity_and_rerank(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rl-developer-memory-runtime-diagnostics-test-") as temp_dir:
            base = Path(temp_dir)
            os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(base / "share")
            os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(base / "share" / "rl_developer_memory.sqlite3")
            os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(base / "state")
            os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(base / "share" / "backups")
            os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(base / "state" / "log")
            app = RLDeveloperMemoryApp()
            report = run_runtime_diagnostics(app, repeats=1)
            self.assertEqual(report["taxonomy"]["positive_failures"], [])
            self.assertEqual(report["taxonomy"]["negative_failures"], [])
            self.assertTrue(report["session_feedback_rerank_ok"])
            self.assertEqual(report["integrity_check"], "ok")
            self.assertEqual(report["consolidation"]["distinct_pattern_ids"], 1)
            self.assertEqual(report["consolidation"]["distinct_variant_ids"], 1)


if __name__ == "__main__":
    unittest.main()
