from __future__ import annotations

from rl_developer_memory.settings import Settings


def test_settings_invalid_numeric_env_values_fall_back(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_DB_PATH", str(tmp_path / "share" / "memory.sqlite3"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_BACKUP_DIR", str(tmp_path / "share" / "backups"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_LOG_DIR", str(tmp_path / "state" / "log"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR", str(tmp_path / "state" / "run"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_CALIBRATION_PROFILE_PATH", str(tmp_path / "state" / "calibration.json"))

    invalid_numeric_keys = [
        "RL_DEVELOPER_MEMORY_LOCAL_BACKUP_KEEP",
        "RL_DEVELOPER_MEMORY_MIRROR_BACKUP_KEEP",
        "RL_DEVELOPER_MEMORY_MATCH_ACCEPT_THRESHOLD",
        "RL_DEVELOPER_MEMORY_MATCH_WEAK_THRESHOLD",
        "RL_DEVELOPER_MEMORY_AMBIGUITY_MARGIN",
        "RL_DEVELOPER_MEMORY_SESSION_TTL_SECONDS",
        "RL_DEVELOPER_MEMORY_DENSE_EMBEDDING_DIM",
        "RL_DEVELOPER_MEMORY_DENSE_CANDIDATE_LIMIT",
        "RL_DEVELOPER_MEMORY_DENSE_SIMILARITY_FLOOR",
        "RL_DEVELOPER_MEMORY_STRATEGY_OVERLAY_SCALE",
        "RL_DEVELOPER_MEMORY_VARIANT_OVERLAY_SCALE",
        "RL_DEVELOPER_MEMORY_SAFE_OVERRIDE_MARGIN",
        "RL_DEVELOPER_MEMORY_MINIMUM_STRATEGY_EVIDENCE",
        "RL_DEVELOPER_MEMORY_STRATEGY_HALF_LIFE_DAYS",
        "RL_DEVELOPER_MEMORY_VARIANT_HALF_LIFE_DAYS",
        "RL_DEVELOPER_MEMORY_PREFERENCE_OVERLAY_SCALE",
        "RL_DEVELOPER_MEMORY_MAX_PREFERENCE_ADJUSTMENT",
        "RL_DEVELOPER_MEMORY_GUARDRAIL_LIMIT",
        "RL_DEVELOPER_MEMORY_TELEMETRY_RETENTION_DAYS",
        "RL_DEVELOPER_MEMORY_RESOLVED_REVIEW_RETENTION_DAYS",
        "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS",
        "RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_MONITOR_INTERVAL_SECONDS",
        "RL_DEVELOPER_MEMORY_ENV_JSON_MAX_CHARS",
        "RL_DEVELOPER_MEMORY_VERIFICATION_OUTPUT_MAX_CHARS",
        "RL_DEVELOPER_MEMORY_NOTE_MAX_CHARS",
        "RL_DEVELOPER_MEMORY_RL_CANDIDATE_WARNING_BUDGET",
        "RL_DEVELOPER_MEMORY_RL_REQUIRED_SEED_COUNT",
        "RL_DEVELOPER_MEMORY_RL_PRODUCTION_MIN_SEED_COUNT",
        "RL_DEVELOPER_MEMORY_RL_MAX_ARTIFACT_REFS",
    ]
    for key in invalid_numeric_keys:
        monkeypatch.setenv(key, "not-a-number")

    settings = Settings.from_env()

    assert settings.session_ttl_seconds == 21600
    assert settings.dense_embedding_dim == 192
    assert settings.match_accept_threshold == 0.68
    assert settings.server_parent_instance_idle_timeout_seconds == 0
