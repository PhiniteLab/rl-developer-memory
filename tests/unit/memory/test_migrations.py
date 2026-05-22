from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from rl_developer_memory.migrations import MigrationAsset, MigrationError, MigrationRunner
from rl_developer_memory.storage import RLDeveloperMemoryStore


def _asset(version: int, name: str, sql: str) -> MigrationAsset:
    import hashlib

    return MigrationAsset(
        version=version,
        name=name,
        resource_name=f"{version:03d}_{name}.sql",
        checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        sql=sql,
    )


class StaticMigrationRunner(MigrationRunner):
    def __init__(self, migrations: list[MigrationAsset]) -> None:
        super().__init__()
        self._migrations = migrations

    def list_migrations(self) -> list[MigrationAsset]:
        return list(self._migrations)


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rl-developer-memory-migrate-")
        base = Path(self.temp_dir.name)
        os.environ["RL_DEVELOPER_MEMORY_HOME"] = str(base / "share")
        os.environ["RL_DEVELOPER_MEMORY_DB_PATH"] = str(base / "share" / "rl_developer_memory.sqlite3")
        os.environ["RL_DEVELOPER_MEMORY_STATE_DIR"] = str(base / "state")
        os.environ["RL_DEVELOPER_MEMORY_BACKUP_DIR"] = str(base / "share" / "backups")
        os.environ["RL_DEVELOPER_MEMORY_LOG_DIR"] = str(base / "state" / "log")
        self.store = RLDeveloperMemoryStore.from_env()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialize_applies_v2_foundation(self) -> None:
        self.store.initialize()
        schema = self.store.schema_state()
        self.assertEqual(schema.current_version, 13)
        self.assertEqual(schema.applied_count, 12)

        with self.store.managed_connection() as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                ).fetchall()
            }

        self.assertIn("issue_patterns", tables)
        self.assertIn("issue_examples", tables)
        self.assertIn("issue_variants", tables)
        self.assertIn("issue_episodes", tables)
        self.assertIn("retrieval_events", tables)
        self.assertIn("feedback_events", tables)
        self.assertIn("session_memory", tables)
        self.assertIn("app_metadata", tables)
        self.assertNotIn("contextual_bandit_state", tables)
        self.assertNotIn("ranker_state", tables)
        self.assertIn("strategy_stats", tables)
        self.assertIn("variant_stats", tables)
        self.assertIn("preference_rules", tables)
        self.assertIn("review_queue", tables)
        self.assertIn("audit_findings", tables)
        self.assertIn("artifact_references", tables)

    def test_v1_to_v2_migration_preserves_existing_records(self) -> None:
        self.store.migrate(target_version=1)
        self.assertEqual(self.store.schema_state().current_version, 1)

        pattern = self.store.create_pattern(
            {
                "title": "Legacy sqlite cwd issue",
                "project_scope": "global",
                "domain": "python",
                "error_family": "sqlite_error",
                "root_cause_class": "cwd_relative_path_bug",
                "canonical_symptom": "sqlite file not found outside repo root",
                "canonical_fix": "Resolve the path relative to __file__.",
                "prevention_rule": "Do not depend on cwd for DB paths.",
                "verification_steps": "Run from repo root and a foreign cwd.",
                "tags": ["sqlite", "cwd"],
                "signature": "global|sqlite_error|cwd_relative_path_bug|sqlite-path",
            }
        )
        example = self.store.add_example(
            pattern_id=int(pattern["id"]),
            raw_error="FileNotFoundError: contractsDatabase.sqlite3",
            normalized_error="filenotfounderror path_contractsdatabase.sqlite3",
            command="python -m app.main",
            file_path="services/db_loader.py",
            verified_fix="Resolve the path relative to __file__.",
        )
        self.assertGreater(int(example["id"]), 0)

        upgraded = self.store.migrate()
        self.assertEqual(upgraded.current_version, 13)

        bundle = self.store.get_pattern(int(pattern["id"]), include_examples=True)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle.pattern["title"], "Legacy sqlite cwd issue")
        self.assertEqual(len(bundle.examples), 1)

        with self.store.managed_connection() as conn:
            app_meta = conn.execute(
                "SELECT value FROM app_metadata WHERE key = 'schema_generation'"
            ).fetchone()
            self.assertIsNotNone(app_meta)
            self.assertEqual(app_meta["value"], "v2-foundation")

    def test_cleanup_migration_drops_retired_learning_state_on_upgrade(self) -> None:
        self.store.migrate(target_version=8)
        self.assertEqual(self.store.schema_state().current_version, 8)

        with self.store.managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO ranker_state(model_name, weights_json, bias, learning_rate, fit_count, updated_at)
                VALUES ('default', '{}', 0.0, 0.05, 3, '2026-03-29T00:00:00Z')
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contextual_bandit_state (
                    model_name TEXT PRIMARY KEY,
                    alpha REAL NOT NULL DEFAULT 0.20,
                    a_diag_json TEXT NOT NULL,
                    b_json TEXT NOT NULL,
                    pull_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO contextual_bandit_state(model_name, alpha, a_diag_json, b_json, pull_count, updated_at)
                VALUES ('variant_selector_linucb', 0.2, '{}', '{}', 4, '2026-03-29T00:00:00Z')
                """
            )

        upgraded = self.store.migrate()
        self.assertEqual(upgraded.current_version, 13)

        with self.store.managed_connection() as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                ).fetchall()
            }
            cleanup_meta = conn.execute(
                "SELECT value FROM app_metadata WHERE key = 'learning_state_cleanup'"
            ).fetchone()
            drop_manifests = {
                row["object_name"]: row
                for row in conn.execute(
                    """
                    SELECT object_name, object_existed, row_count
                    FROM migration_archive_manifests
                    WHERE migration_version = 9 AND object_type = 'TABLE'
                    """
                ).fetchall()
            }

        self.assertNotIn("ranker_state", tables)
        self.assertNotIn("contextual_bandit_state", tables)
        self.assertIsNotNone(cleanup_meta)
        assert cleanup_meta is not None
        self.assertEqual(cleanup_meta["value"], "dropped")
        self.assertEqual(drop_manifests["ranker_state"]["object_existed"], 1)
        self.assertEqual(drop_manifests["ranker_state"]["row_count"], 1)
        self.assertEqual(drop_manifests["contextual_bandit_state"]["object_existed"], 1)
        self.assertEqual(drop_manifests["contextual_bandit_state"]["row_count"], 1)

    def test_failed_migration_rolls_back_partial_schema_and_marker(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        runner = StaticMigrationRunner(
            [
                _asset(
                    1,
                    "partial_failure",
                    """
                    CREATE TABLE partially_created (
                        id INTEGER PRIMARY KEY
                    );
                    INSERT INTO partially_created(id) VALUES (1);
                    CREATE TABLE partially_created (
                        id INTEGER PRIMARY KEY
                    );
                    """,
                )
            ]
        )

        with self.assertRaises(MigrationError):
            runner.apply_all(conn)

        table_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'partially_created'"
        ).fetchone()
        applied_row = conn.execute("SELECT version FROM schema_migrations WHERE version = 1").fetchone()
        self.assertIsNone(table_row)
        self.assertIsNone(applied_row)
        conn.close()

    def test_migration_executor_accepts_multiple_statements_on_one_line(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        runner = StaticMigrationRunner(
            [
                _asset(
                    1,
                    "same_line_statements",
                    "CREATE TABLE same_line(id INTEGER PRIMARY KEY); INSERT INTO same_line(id) VALUES (1);",
                )
            ]
        )

        runner.apply_all(conn)

        row = conn.execute("SELECT id FROM same_line").fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["id"], 1)
        conn.close()

    def test_drop_table_migration_records_pre_drop_archive_manifest(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        runner = StaticMigrationRunner(
            [
                _asset(
                    1,
                    "create_retired_state",
                    """
                    CREATE TABLE ranker_state (
                        model_name TEXT PRIMARY KEY,
                        weights_json TEXT NOT NULL
                    );
                    INSERT INTO ranker_state(model_name, weights_json)
                    VALUES ('default', '{}');
                    """,
                ),
                _asset(
                    2,
                    "drop_retired_state",
                    "DROP TABLE IF EXISTS ranker_state;",
                ),
            ]
        )

        runner.apply_all(conn)

        dropped_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'ranker_state'"
        ).fetchone()
        manifest = conn.execute(
            """
            SELECT object_type, object_name, object_existed, object_sql, row_count
            FROM migration_archive_manifests
            WHERE migration_version = 2 AND object_name = 'ranker_state'
            """
        ).fetchone()

        self.assertIsNone(dropped_table)
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest["object_type"], "TABLE")
        self.assertEqual(manifest["object_existed"], 1)
        self.assertIn("CREATE TABLE ranker_state", manifest["object_sql"])
        self.assertEqual(manifest["row_count"], 1)
        conn.close()

    def test_unsafe_drop_table_policy_rejects_unarchived_data_table(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        runner = StaticMigrationRunner(
            [
                _asset(
                    1,
                    "create_data",
                    "CREATE TABLE important_data (id INTEGER PRIMARY KEY);",
                ),
                _asset(
                    2,
                    "unsafe_drop",
                    "DROP TABLE IF EXISTS important_data;",
                ),
            ]
        )

        with self.assertRaises(MigrationError):
            runner.apply_all(conn)

        retained_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'important_data'"
        ).fetchone()
        rejected_marker = conn.execute("SELECT version FROM schema_migrations WHERE version = 2").fetchone()
        self.assertIsNotNone(retained_table)
        self.assertIsNone(rejected_marker)
        conn.close()

    def test_drop_policy_ignores_drop_table_inside_string_literals(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        runner = StaticMigrationRunner(
            [
                _asset(
                    1,
                    "drop_text_literal",
                    """
                    CREATE TABLE notes (
                        id INTEGER PRIMARY KEY,
                        body TEXT NOT NULL
                    );
                    INSERT INTO notes(id, body)
                    VALUES (1, 'do not run DROP TABLE important_data; this is documentation only');
                    """,
                )
            ]
        )

        runner.apply_all(conn)

        row = conn.execute("SELECT body FROM notes WHERE id = 1").fetchone()
        marker = conn.execute("SELECT version FROM schema_migrations WHERE version = 1").fetchone()
        self.assertIsNotNone(row)
        self.assertIsNotNone(marker)
        assert row is not None
        self.assertIn("DROP TABLE important_data", row["body"])
        conn.close()


if __name__ == "__main__":
    unittest.main()
