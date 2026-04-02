from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RegisterCodexTests(unittest.TestCase):
    def test_register_codex_installs_coexistence_guidance_in_agents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-codex-guidance-") as temp_dir:
            base = Path(temp_dir)
            subprocess.run(
                [
                    sys.executable,
                    "scripts/register_codex.py",
                    "--install-root",
                    str(base / "install"),
                    "--data-root",
                    str(base / "share"),
                    "--state-root",
                    str(base / "state"),
                    "--codex-home",
                    str(base / ".codex"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )
            agents_text = (base / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("RL Developer Memory workflow", agents_text)
            self.assertIn("RL/control/experiment-related failures", agents_text)
            self.assertIn("issue_memory", agents_text)
            self.assertIn("dual-write only when both scopes are genuinely useful", agents_text)

    def test_register_codex_keeps_rl_flags_absent_by_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-codex-default-") as temp_dir:
            base = Path(temp_dir)
            subprocess.run(
                [
                    sys.executable,
                    "scripts/register_codex.py",
                    "--install-root",
                    str(base / "install"),
                    "--data-root",
                    str(base / "share"),
                    "--state-root",
                    str(base / "state"),
                    "--codex-home",
                    str(base / ".codex"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )
            config_text = (base / ".codex" / "config.toml").read_text(encoding="utf-8")
            self.assertNotIn('RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"', config_text)

    def test_register_codex_can_write_rl_active_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-codex-rl-") as temp_dir:
            base = Path(temp_dir)
            subprocess.run(
                [
                    sys.executable,
                    "scripts/register_codex.py",
                    "--install-root",
                    str(base / "install"),
                    "--data-root",
                    str(base / "share"),
                    "--state-root",
                    str(base / "state"),
                    "--codex-home",
                    str(base / ".codex"),
                    "--enable-rl-control",
                    "--rl-rollout-mode",
                    "active",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )
            config_text = (base / ".codex" / "config.toml").read_text(encoding="utf-8")
            self.assertIn('RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL = "1"', config_text)
            self.assertIn('RL_DEVELOPER_MEMORY_DOMAIN_MODE = "rl_control"', config_text)
            self.assertIn('RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT = "1"', config_text)
            self.assertIn('RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT = "1"', config_text)


if __name__ == "__main__":
    unittest.main()
