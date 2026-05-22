from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import resources
from typing import Any

_logger = logging.getLogger(__name__)

__all__ = ["MigrationAsset", "MigrationError", "MigrationRunner", "SchemaState", "inspect_schema"]

MIGRATION_NAME_RE = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$", re.IGNORECASE)
DROP_STATEMENT_RE = re.compile(
    r"\bDROP\s+(?P<object_type>TABLE|TRIGGER|INDEX|VIEW)\s+"
    r"(?:IF\s+EXISTS\s+)?(?P<object_name>(?:\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*))?)",
    re.IGNORECASE,
)
SQL_COMMENT_RE = re.compile(r"(--[^\n]*(?:\n|$)|/\*.*?\*/)", re.DOTALL)
SAFE_DROP_TABLES = frozenset({"contextual_bandit_state", "ranker_state"})
ARCHIVE_MANIFEST_TABLE = "migration_archive_manifests"


class MigrationError(RuntimeError):
    """Raised when schema migrations are inconsistent or invalid."""


@dataclass(frozen=True, slots=True)
class MigrationAsset:
    version: int
    name: str
    resource_name: str
    checksum: str
    sql: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SchemaState:
    current_version: int
    applied_count: int
    migrations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DropStatement:
    object_type: str
    object_name: str


class MigrationRunner:
    """Discover and apply packaged SQL migrations."""

    def __init__(self, package: str = "rl_developer_memory") -> None:
        self.package = package

    def list_migrations(self) -> list[MigrationAsset]:
        sql_dir = resources.files(self.package).joinpath("sql")
        assets: list[MigrationAsset] = []
        for entry in sql_dir.iterdir():
            if not entry.is_file():
                continue
            match = MIGRATION_NAME_RE.match(entry.name)
            if not match:
                continue
            sql = entry.read_text(encoding="utf-8")
            assets.append(
                MigrationAsset(
                    version=int(match.group("version")),
                    name=match.group("name"),
                    resource_name=entry.name,
                    checksum=sha256(sql.encode("utf-8")).hexdigest(),
                    sql=sql,
                )
            )
        assets.sort(key=lambda item: item.version)
        if not assets:
            raise MigrationError("No SQL migrations were discovered")
        return assets

    @staticmethod
    def ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def ensure_archive_manifest_table(conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ARCHIVE_MANIFEST_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_version INTEGER NOT NULL,
                migration_name TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_name TEXT NOT NULL,
                object_existed INTEGER NOT NULL CHECK(object_existed IN (0, 1)),
                object_sql TEXT NOT NULL DEFAULT '',
                row_count INTEGER,
                archived_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{ARCHIVE_MANIFEST_TABLE}_migration
                ON {ARCHIVE_MANIFEST_TABLE}(migration_version, object_type, object_name)
            """
        )

    @staticmethod
    def _has_schema_migrations_table(conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        return row is not None

    def applied_migrations(self, conn: sqlite3.Connection, *, create_if_missing: bool = True) -> list[dict[str, Any]]:
        if create_if_missing:
            self.ensure_schema_migrations_table(conn)
        elif not self._has_schema_migrations_table(conn):
            return []
        rows = conn.execute(
            "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def schema_state(self, conn: sqlite3.Connection) -> SchemaState:
        applied = self.applied_migrations(conn, create_if_missing=False)
        current_version = max((int(row["version"]) for row in applied), default=0)
        return SchemaState(
            current_version=current_version,
            applied_count=len(applied),
            migrations=applied,
        )

    def apply_all(self, conn: sqlite3.Connection, *, target_version: int | None = None) -> list[MigrationAsset]:
        self.ensure_schema_migrations_table(conn)
        migrations = self.list_migrations()
        applied_rows = self.applied_migrations(conn)
        applied_by_version = {int(row["version"]): row for row in applied_rows}

        executed: list[MigrationAsset] = []
        for migration in migrations:
            if target_version is not None and migration.version > target_version:
                break

            existing = applied_by_version.get(migration.version)
            if existing is not None:
                if str(existing["checksum"]) != migration.checksum:
                    raise MigrationError(
                        f"Migration checksum mismatch for version {migration.version}: "
                        f"database has {existing['checksum']}, package has {migration.checksum}"
                    )
                continue

            _logger.info("Applying migration %d: %s", migration.version, migration.name)
            try:
                self._apply_one(conn, migration)
            except MigrationError:
                raise
            except sqlite3.Error as exc:
                _logger.error("Migration %d failed: %s", migration.version, exc)
                raise MigrationError(
                    f"Failed to apply migration {migration.version} ({migration.name}): {exc}"
                ) from exc
            executed.append(migration)

        if executed:
            _logger.info("Applied %d migration(s), now at version %d", len(executed), executed[-1].version)
        return executed

    def _apply_one(self, conn: sqlite3.Connection, migration: MigrationAsset) -> None:
        if conn.in_transaction:
            raise MigrationError(
                "MigrationRunner.apply_all requires a connection with no active transaction; "
                f"refusing to apply migration {migration.version}"
            )

        drops = self._drop_statements(migration.sql)
        try:
            conn.execute("BEGIN IMMEDIATE")
            if drops:
                self._validate_drop_policy(conn, migration, drops)
                self._archive_drop_manifests(conn, migration, drops)
            self._execute_sql_script(conn, migration.sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    self._utc_now_iso(),
                ),
            )
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise

    @staticmethod
    def _execute_sql_script(conn: sqlite3.Connection, sql: str) -> None:
        pending = ""
        for char in sql:
            pending += char
            if not sqlite3.complete_statement(pending):
                continue
            statement = pending.strip()
            pending = ""
            if statement:
                conn.execute(statement)

        if pending.strip() and not MigrationRunner._comment_only(pending):
            raise MigrationError("Migration SQL ended with an incomplete statement")

    @staticmethod
    def _comment_only(sql: str) -> bool:
        return not SQL_COMMENT_RE.sub("", sql).strip()

    @staticmethod
    def _drop_statements(sql: str) -> list[DropStatement]:
        sql_without_comments = MigrationRunner._strip_comments_and_string_literals(sql)
        return [
            DropStatement(
                object_type=match.group("object_type").upper(),
                object_name=MigrationRunner._normalize_object_name(match.group("object_name")),
            )
            for match in DROP_STATEMENT_RE.finditer(sql_without_comments)
        ]

    @staticmethod
    def _strip_comments_and_string_literals(sql: str) -> str:
        """Return SQL with comments and single-quoted literals blanked out.

        This is intentionally small and conservative: DROP policy scanning must not
        be triggered by prose stored in string literals, while quoted identifiers
        remain visible for real DROP statements.
        """

        output: list[str] = []
        index = 0
        length = len(sql)
        while index < length:
            char = sql[index]
            next_char = sql[index + 1] if index + 1 < length else ""
            if char == "-" and next_char == "-":
                output.extend("  ")
                index += 2
                while index < length and sql[index] != "\n":
                    output.append(" ")
                    index += 1
                continue
            if char == "/" and next_char == "*":
                output.extend("  ")
                index += 2
                while index < length:
                    current = sql[index]
                    following = sql[index + 1] if index + 1 < length else ""
                    output.append("\n" if current == "\n" else " ")
                    index += 1
                    if current == "*" and following == "/":
                        output.append(" ")
                        index += 1
                        break
                continue
            if char == "'":
                output.append(" ")
                index += 1
                while index < length:
                    current = sql[index]
                    output.append("\n" if current == "\n" else " ")
                    index += 1
                    if current != "'":
                        continue
                    if index < length and sql[index] == "'":
                        output.append(" ")
                        index += 1
                        continue
                    break
                continue
            output.append(char)
            index += 1
        return "".join(output)

    @staticmethod
    def _normalize_object_name(raw_name: str) -> str:
        name = raw_name.strip().split(".")[-1].strip()
        if (
            (name.startswith('"') and name.endswith('"'))
            or (name.startswith("`") and name.endswith("`"))
            or (name.startswith("[") and name.endswith("]"))
        ):
            name = name[1:-1]
        return name.replace('""', '"').replace("``", "`").strip()

    @staticmethod
    def _validate_drop_policy(
        conn: sqlite3.Connection, migration: MigrationAsset, drops: list[DropStatement]
    ) -> None:
        for drop in drops:
            if drop.object_type != "TABLE":
                continue
            if drop.object_name in SAFE_DROP_TABLES:
                continue
            schema_row = MigrationRunner._sqlite_master_row(conn, drop.object_type, drop.object_name)
            object_sql = str(schema_row["sql"] or "") if schema_row is not None else ""
            if "CREATE VIRTUAL TABLE" in object_sql.upper() and drop.object_name.endswith("_fts"):
                continue
            raise MigrationError(
                "Unsafe DROP TABLE in migration "
                f"{migration.version} ({migration.name}): {drop.object_name}. "
                "Add an explicit safe-drop policy entry or replace the migration with a backup/archive-safe path."
            )

    @staticmethod
    def _archive_drop_manifests(
        conn: sqlite3.Connection, migration: MigrationAsset, drops: list[DropStatement]
    ) -> None:
        MigrationRunner.ensure_archive_manifest_table(conn)
        archived_at = MigrationRunner._utc_now_iso()
        for drop in drops:
            schema_row = MigrationRunner._sqlite_master_row(conn, drop.object_type, drop.object_name)
            object_sql = str(schema_row["sql"] or "") if schema_row is not None else ""
            row_count = MigrationRunner._row_count(conn, drop.object_name) if drop.object_type == "TABLE" and schema_row else None
            conn.execute(
                f"""
                INSERT INTO {ARCHIVE_MANIFEST_TABLE}(
                    migration_version,
                    migration_name,
                    object_type,
                    object_name,
                    object_existed,
                    object_sql,
                    row_count,
                    archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    drop.object_type,
                    drop.object_name,
                    1 if schema_row is not None else 0,
                    object_sql,
                    row_count,
                    archived_at,
                ),
            )

    @staticmethod
    def _sqlite_master_row(conn: sqlite3.Connection, object_type: str, object_name: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE type = ? AND name = ?",
            (object_type.lower(), object_name),
        ).fetchone()

    @staticmethod
    def _row_count(conn: sqlite3.Connection, table_name: str) -> int | None:
        try:
            row = conn.execute(f"SELECT COUNT(*) AS count FROM {MigrationRunner._quote_identifier(table_name)}").fetchone()
        except sqlite3.Error:
            return None
        return int(row["count"]) if row is not None else None

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def inspect_schema(conn: sqlite3.Connection) -> dict[str, Any]:
    """Convenience helper for callers that only need schema state."""
    return MigrationRunner().schema_state(conn).to_dict()
