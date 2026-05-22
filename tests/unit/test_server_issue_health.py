from __future__ import annotations

from pathlib import Path

import rl_developer_memory.server as server_module


class _FakeCursor:
    def __init__(self, value: int) -> None:
        self._value = value

    def fetchone(self) -> tuple[int]:
        return (self._value,)


class _FakeConnection:
    def execute(self, sql: str) -> _FakeCursor:
        if "issue_patterns" in sql:
            return _FakeCursor(3)
        if "issue_variants" in sql:
            return _FakeCursor(7)
        raise AssertionError(f"unexpected query: {sql}")


class _FakeConnectionManager:
    def __enter__(self) -> _FakeConnection:
        return _FakeConnection()

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeStore:
    def managed_connection(self) -> _FakeConnectionManager:
        return _FakeConnectionManager()


class _FakeApp:
    def __init__(self) -> None:
        self.store = _FakeStore()


class _FakeLifecycleStatus:
    def to_dict(self) -> dict[str, object]:
        return {"running": False, "active_count": 0}


class _FakeSettings:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path


def test_issue_health_uses_pure_read_lifecycle_status(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    db_path.write_bytes(b"sqlite")
    settings = _FakeSettings(db_path)
    calls: list[bool] = []

    def fake_read_server_lifecycle_status(_settings, *, refresh_files: bool = False) -> _FakeLifecycleStatus:
        calls.append(refresh_files)
        return _FakeLifecycleStatus()

    monkeypatch.setattr(server_module, "get_settings", lambda: settings)
    monkeypatch.setattr(server_module, "get_app", lambda: _FakeApp())
    monkeypatch.setattr(server_module, "read_server_lifecycle_status", fake_read_server_lifecycle_status)

    result = server_module.issue_health()

    assert result["healthy"] is True
    assert result["db_path"] == str(db_path)
    assert result["db_bytes"] == len(b"sqlite")
    assert result["patterns"] == 3
    assert result["variants"] == 7
    assert result["lifecycle"] == {"running": False, "active_count": 0}
    assert calls == [False]
