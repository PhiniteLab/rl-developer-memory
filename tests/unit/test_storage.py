from __future__ import annotations

import sqlite3
from typing import Any, cast

import pytest

from rl_developer_memory.storage import RLDeveloperMemoryStore


class _FakeConnection:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def execute(self, sql: str) -> None:
        return None


def _make_store(conn: _FakeConnection, *, retry_delays: tuple[float, ...] = ()) -> RLDeveloperMemoryStore:
    store = RLDeveloperMemoryStore.__new__(RLDeveloperMemoryStore)
    store_for_test = cast(Any, store)
    store_for_test._BUSY_RETRY_DELAYS = retry_delays
    store_for_test.connect = lambda: conn
    return store


def test_managed_connection_propagates_locked_error_without_generator_runtime_error() -> None:
    conn = _FakeConnection()
    store = _make_store(conn)

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        with store.managed_connection() as active_conn:
            assert active_conn is conn
            raise sqlite3.OperationalError("database is locked")

    assert conn.rollback_calls == 1
    assert conn.commit_calls == 0


def test_managed_connection_retries_begin_immediate_before_entering_context() -> None:
    class _RetryingBeginConnection(_FakeConnection):
        def __init__(self) -> None:
            super().__init__()
            self.begin_attempts = 0

        def execute(self, sql: str) -> None:
            if sql == "BEGIN IMMEDIATE;":
                self.begin_attempts += 1
                if self.begin_attempts == 1:
                    raise sqlite3.OperationalError("database is locked")

    conn = _RetryingBeginConnection()
    store = _make_store(conn, retry_delays=(0.0,))

    with store.managed_connection(immediate=True) as active_conn:
        assert active_conn is conn

    assert conn.begin_attempts == 2
    assert conn.rollback_calls == 0
    assert conn.commit_calls == 1
