from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rl_developer_memory.app import RLDeveloperMemoryApp
from rl_developer_memory.backup import BackupManager
from rl_developer_memory.benchmarks import seed_rl_control_reporting_memory
from rl_developer_memory.maintenance import cmd_doctor, cmd_recommended_config, cmd_rl_audit_health
from rl_developer_memory.storage import RLDeveloperMemoryStore


class Phase6RLAuditOpsTests(unittest.TestCase):
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
        "RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE",
        "RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH",
    )

    def setUp(self) -> None:
        self._env_backup = {key: os.environ.get(key) for key in self._ENV_KEYS}
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-phase6-rl-ops-")
        base = Path(self.temp_dir.name)
        self.data_root = base / "share"
        self.state_root = base / "state"
        self.codex_home = base / ".codex"
        os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(self.data_root)
        os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(self.data_root / "rl_developer_memory.sqlite3")
        os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(self.state_root)
        os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(self.data_root / "backups")
        os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(self.state_root / "log")
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_DOMAIN_MODE"] = "hybrid"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_ENABLE_CALIBRATION_PROFILE"] = "1"
        os.environ["RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH"] = str(self.state_root / "calibration_profile.json")
        store = RLDeveloperMemoryStore.from_env()
        store.initialize()
        Path(os.environ["RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH"]).write_text(
            json.dumps({"global": {"accept_threshold": 0.68, "weak_threshold": 0.40, "ambiguity_margin": 0.09}}),
            encoding="utf-8",
        )
        BackupManager.from_env().create_backup()
        app = RLDeveloperMemoryApp(store=store)
        seed_rl_control_reporting_memory(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_recommended_config_emits_rl_control_shadow_profile(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_recommended_config(mode="shadow", fmt="json", max_instances=0, profile="rl-control-shadow")
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["profile"], "rl-control-shadow")
        self.assertEqual(payload["env"]["RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL"], "1")
        self.assertEqual(payload["env"]["RL_DEVELOPER_MEMORY_DOMAIN_MODE"], "hybrid")
        self.assertEqual(payload["env"]["RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT"], "1")
        self.assertEqual(payload["env"]["RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT"], "1")

    def test_rl_audit_health_reports_pending_reviews_and_findings(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_rl_audit_health(window_days=30, limit=10)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["enabled"])
        self.assertGreaterEqual(payload["patterns"]["total"], 2)
        self.assertGreaterEqual(payload["review_queue"]["pending"], 2)
        self.assertGreaterEqual(payload["findings"]["total"], 0)

    def test_doctor_passes_for_registered_rl_shadow_profile(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        install_root = Path(self.temp_dir.name) / "install"
        install_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "scripts/register_codex.py",
                "--install-root",
                str(install_root),
                "--data-root",
                str(self.data_root),
                "--state-root",
                str(self.state_root),
                "--codex-home",
                str(self.codex_home),
                "--enable-rl-control",
                "--rl-rollout-mode",
                "shadow",
            ],
            cwd=repo_root,
            check=True,
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cmd_doctor(mode="shadow", max_instances=0, codex_home=str(self.codex_home), profile="rl-control-shadow")
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["errors"], 0)


if __name__ == "__main__":
    unittest.main()
