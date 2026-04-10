"""Unit tests for rl_developer_memory.backup module."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from rl_developer_memory.backup import BackupManager, BackupResult, utc_stamp


@pytest.fixture()
def backup_env(tmp_path: Path):
    """Create a minimal Settings-like environment with a real SQLite database."""
    db_path = tmp_path / "data" / "test.sqlite3"
    db_path.parent.mkdir(parents=True)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE issues (id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO issues VALUES (1, 'test issue')")
    conn.commit()
    conn.close()

    class FakeSettings:
        def __init__(self) -> None:
            self.db_path = db_path
            self.backup_dir = backup_dir
            self.windows_backup_target: Path | None = None
            self.local_backup_keep = 5
            self.mirror_backup_keep = 3
            self.hostname = "test-host"

        def ensure_dirs(self) -> None:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    return FakeSettings()


class TestUtcStamp:
    def test_format(self) -> None:
        stamp = utc_stamp()
        assert len(stamp) == 15  # YYYYMMDD_HHMMSS
        assert stamp[8] == "_"


class TestBackupResult:
    def test_to_dict(self) -> None:
        result = BackupResult(
            local_path="/tmp/a.sqlite3",
            mirror_path=None,
            sha256="abc",
            created_at_utc="2024-01-01T00:00:00",
            bytes=1024,
        )
        d = result.to_dict()
        assert d["sha256"] == "abc"
        assert d["mirror_path"] is None


class TestCreateBackup:
    def test_creates_backup_file(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        assert Path(result.local_path).exists()
        assert result.sha256
        assert result.bytes > 0

    def test_manifest_written(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        manifest_path = Path(result.local_path).with_suffix(".json")
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["sha256"] == result.sha256

    def test_missing_db_raises(self, backup_env) -> None:
        backup_env.db_path = Path("/nonexistent/db.sqlite3")
        manager = BackupManager(backup_env)
        with pytest.raises(FileNotFoundError):
            manager.create_backup()


class TestListBackups:
    def test_empty_dir(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        assert manager.list_backups() == []

    def test_lists_created_backup(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        manager.create_backup()
        rows = manager.list_backups()
        assert len(rows) == 1
        assert rows[0]["verified"] is True


class TestVerifyBackup:
    def test_valid_backup(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        verification = manager.verify_backup(result.local_path)
        assert verification["verified"] is True

    def test_tampered_backup(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        backup_path = Path(result.local_path)
        # Append garbage to change the hash
        with open(backup_path, "ab") as f:
            f.write(b"tampered")
        verification = manager.verify_backup(result.local_path)
        assert verification["verified"] is False

    def test_missing_backup_raises(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        with pytest.raises(FileNotFoundError):
            manager.verify_backup("/nonexistent/backup.sqlite3")


class TestRestoreBackup:
    def test_restore_replaces_db(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        # Modify the live DB
        conn = sqlite3.connect(backup_env.db_path)
        conn.execute("INSERT INTO issues VALUES (2, 'extra')")
        conn.commit()
        conn.close()
        # Restore from backup — should lose the extra row
        manager.restore_backup(result.local_path, create_safety_backup=False)
        conn = sqlite3.connect(backup_env.db_path)
        count = conn.execute("SELECT count(*) FROM issues").fetchone()[0]
        conn.close()
        assert count == 1

    def test_restore_creates_safety_backup(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        restore_info = manager.restore_backup(result.local_path, create_safety_backup=True)
        assert restore_info["safety_backup"] is not None

    def test_restore_invalid_manifest_raises(self, backup_env) -> None:
        manager = BackupManager(backup_env)
        result = manager.create_backup()
        backup_path = Path(result.local_path)
        with open(backup_path, "ab") as f:
            f.write(b"tampered")
        with pytest.raises(ValueError, match="verification failed"):
            manager.restore_backup(result.local_path)


class TestPrune:
    def test_prunes_old_backups(self, backup_env) -> None:
        backup_env.local_backup_keep = 2
        manager = BackupManager(backup_env)
        for _ in range(4):
            manager.create_backup()
        remaining = list(backup_env.backup_dir.glob("rl_developer_memory_*.sqlite3"))
        assert len(remaining) <= 2
