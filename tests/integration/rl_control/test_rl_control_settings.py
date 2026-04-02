from __future__ import annotations

from rl_developer_memory.settings import Settings


def test_rl_control_settings_from_env(monkeypatch, tmp_path) -> None:
    base = tmp_path
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_HOME", str(base / "share"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_DB_PATH", str(base / "share" / "rl_developer_memory.sqlite3"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_STATE_DIR", str(base / "state"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_BACKUP_DIR", str(base / "share" / "backups"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_LOG_DIR", str(base / "state" / "log"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_ENABLE_RL_CONTROL", "1")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_DOMAIN_MODE", "RL-Control")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_ENABLE_THEORY_AUDIT", "true")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_ENABLE_EXPERIMENT_AUDIT", "yes")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_STRICT_PROMOTION", "0")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_REVIEW_GATED_PROMOTION", "0")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET", "4")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT", "5")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT", "7")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS", "24")

    settings = Settings.from_env()

    assert settings.enable_rl_control is True
    assert settings.domain_mode == "rl_control"
    assert settings.enable_theory_audit is True
    assert settings.enable_experiment_audit is True
    assert settings.rl_strict_promotion is False
    assert settings.rl_review_gated_promotion is False
    assert settings.rl_candidate_warning_budget == 4
    assert settings.rl_required_seed_count == 5
    assert settings.rl_production_min_seed_count == 7
    assert settings.rl_max_artifact_refs == 24
