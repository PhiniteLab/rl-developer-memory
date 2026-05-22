from __future__ import annotations

import json
import multiprocessing
import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest

import rl_developer_memory.backup as backup_module
from rl_developer_memory.backup import BackupManager


@pytest.fixture()
def backup_env(tmp_path: Path) -> Any:
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

    return cast(Any, FakeSettings())


class _WorkerSettings:
    def __init__(self, db_path: Path, backup_dir: Path) -> None:
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.windows_backup_target: Path | None = None
        self.local_backup_keep = 5
        self.mirror_backup_keep = 3
        self.hostname = "test-host"

    def ensure_dirs(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)


def _create_backup_worker(
    db_path: str,
    backup_dir: str,
    stamp: str,
    start_event: Any,
    result_queue: Any,
) -> None:
    backup_module.utc_stamp = lambda: stamp
    manager = BackupManager(cast(Any, _WorkerSettings(Path(db_path), Path(backup_dir))))
    if not start_event.wait(timeout=10):
        result_queue.put({"error": "start timeout"})
        return
    try:
        result = manager.create_backup()
        manifest = json.loads(Path(result.local_path).with_suffix(".json").read_text(encoding="utf-8"))
        verification = manager.verify_backup(result.local_path)
    except Exception as exc:  # pragma: no cover - surfaced in parent assertions
        result_queue.put({"error": f"{type(exc).__name__}: {exc}"})
        return
    result_queue.put(
        {
            "local_path": result.local_path,
            "manifest_local_path": manifest["local_path"],
            "manifest_source_db": manifest["source_db"],
            "verified": verification["verified"],
        }
    )


def test_same_second_backups_use_unique_filenames(backup_env, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = BackupManager(backup_env)
    monkeypatch.setattr("rl_developer_memory.backup.utc_stamp", lambda: "20260522_120000")

    first = manager.create_backup()
    second = manager.create_backup()

    assert first.local_path != second.local_path
    assert Path(first.local_path).name == "rl_developer_memory_20260522_120000.sqlite3"
    assert Path(second.local_path).name == "rl_developer_memory_20260522_120000_0001.sqlite3"
    assert Path(second.local_path).exists()


def test_same_second_backups_are_unique_across_processes(backup_env) -> None:
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("concurrent backup collision test requires fork start method")

    ctx = multiprocessing.get_context("fork")
    start_event = ctx.Event()
    result_queue = ctx.Queue()
    stamp = "20260522_120000"
    worker_count = 4
    processes = [
        ctx.Process(
            target=_create_backup_worker,
            args=(str(backup_env.db_path), str(backup_env.backup_dir), stamp, start_event, result_queue),
        )
        for _ in range(worker_count)
    ]

    for process in processes:
        process.start()
    start_event.set()

    results = [result_queue.get(timeout=15) for _ in processes]

    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0

    errors = [item["error"] for item in results if "error" in item]
    assert errors == []

    local_paths = [Path(str(item["local_path"])) for item in results]
    assert len({path.name for path in local_paths}) == worker_count
    assert {path.name for path in local_paths} == {
        "rl_developer_memory_20260522_120000.sqlite3",
        "rl_developer_memory_20260522_120000_0001.sqlite3",
        "rl_developer_memory_20260522_120000_0002.sqlite3",
        "rl_developer_memory_20260522_120000_0003.sqlite3",
    }
    assert all(path.exists() for path in local_paths)
    assert all(item["verified"] is True for item in results)
    assert {str(backup_env.db_path)} == {str(item["manifest_source_db"]) for item in results}
    assert {str(path) for path in local_paths} == {str(item["manifest_local_path"]) for item in results}
