from __future__ import annotations

import logging
import math
from pathlib import Path

import pytest

from rl_developer_memory.settings import Settings


def _configure_base_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "share"
    state = tmp_path / "state"
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_HOME", str(home))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_DB_PATH", str(home / "rl_developer_memory.sqlite3"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_STATE_DIR", str(state))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_BACKUP_DIR", str(home / "backups"))
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_LOG_DIR", str(state / "log"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    for key in (
        "CODEX_THREAD_ID",
        "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY",
        "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_KEY_ENV",
        "RL_DEVELOPER_MEMORY_MAIN_CONVERSATION_ROLE",
        "RL_DEVELOPER_MEMORY_SERVER_ALLOW_SYNTHETIC_OWNER_KEY",
        "RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY",
        "RL_DEVELOPER_MEMORY_SERVER_OWNER_KEY_ENV",
        "RL_DEVELOPER_MEMORY_SERVER_OWNER_ROLE",
        "RL_DEVELOPER_MEMORY_MCP_OWNER_KEY",
        "RL_DEVELOPER_MEMORY_MCP_OWNER_KEY_ENV",
        "RL_DEVELOPER_MEMORY_MCP_OWNER_ROLE",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    ("env_name", "env_value", "field_name", "expected"),
    [
        ("RL_DEVELOPER_MEMORY_SERVER_PARENT_INSTANCE_IDLE_TIMEOUT_SECONDS", "not-an-int", "server_parent_instance_idle_timeout_seconds", 0),
        ("RL_DEVELOPER_MEMORY_SESSION_TTL_SECONDS", "not-an-int", "session_ttl_seconds", 21600),
        ("RL_DEVELOPER_MEMORY_MATCH_ACCEPT_THRESHOLD", "not-a-float", "match_accept_threshold", 0.68),
    ],
)
def test_invalid_numeric_env_values_fall_back_to_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    env_name: str,
    env_value: str,
    field_name: str,
    expected: int | float,
) -> None:
    _configure_base_env(monkeypatch, tmp_path)
    monkeypatch.setenv(env_name, env_value)

    with caplog.at_level(logging.WARNING):
        settings = Settings.from_env()

    actual = getattr(settings, field_name)
    if isinstance(expected, float):
        assert math.isclose(actual, expected)
    else:
        assert actual == expected
    assert env_name in caplog.text


def test_strict_read_only_disables_dense_cache_and_telemetry_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_STRICT_READ_ONLY", "1")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_ENABLE_DENSE_CACHE_WRITES", "1")
    monkeypatch.setenv("RL_DEVELOPER_MEMORY_ENABLE_TELEMETRY_WRITES", "1")

    settings = Settings.from_env()

    assert settings.strict_read_only is True
    assert settings.enable_dense_cache_writes is False
    assert settings.enable_telemetry_writes is False
