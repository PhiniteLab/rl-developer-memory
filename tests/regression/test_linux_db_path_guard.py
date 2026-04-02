import os

import pytest

from rl_developer_memory.settings import Settings


@pytest.fixture(autouse=True)
def _restore_env():
    original = os.environ.get("RL_DEVELOPER_MEMORY_DB_PATH")
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("RL_DEVELOPER_MEMORY_DB_PATH", None)
        else:
            os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = original


def test_settings_reject_active_db_under_mnt_c(tmp_path) -> None:
    os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = "/mnt/c/temp/rl_developer_memory.sqlite3"
    with pytest.raises(ValueError):
        Settings.from_env()
