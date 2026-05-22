from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rl_developer_memory.storage import RLDeveloperMemoryStore


class _FakeSettings:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def test_managed_connection_does_not_yield_again_after_locked_body_error(tmp_path: Path) -> None:
    store = RLDeveloperMemoryStore(_FakeSettings(tmp_path / "memory.sqlite3"))  # type: ignore[arg-type]

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        with store.managed_connection() as _conn:
            raise sqlite3.OperationalError("database is locked")
