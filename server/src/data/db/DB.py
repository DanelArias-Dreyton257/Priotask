import sqlite3
import threading
from typing import Any, Sequence

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB,
    password_salt BLOB,
    email TEXT NOT NULL,
    google_sub TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    deadline TEXT NOT NULL,
    expected_duration_h REAL NOT NULL,
    importance INTEGER NOT NULL,
    task_type TEXT NOT NULL DEFAULT '',
    task_subtype TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    recurrence_unit TEXT,
    recurrence_interval INTEGER,
    recurrence_end_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS model_weights (
    user_id INTEGER NOT NULL,
    model_type TEXT NOT NULL,
    payload BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, model_type),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS completion_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    completed_task_id INTEGER NOT NULL,
    completed_at TEXT NOT NULL,
    open_task_ids TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
"""

# Phase 11 (recurring tasks) added three columns to `tasks` after this project's only
# schema-creation path (CREATE TABLE IF NOT EXISTS, no migration system). An on-disk
# priotask.db created before this change won't get them from SCHEMA alone, so they're
# added here via ALTER TABLE, guarded by a PRAGMA check so it's a no-op on fresh DBs.
_TASKS_RECURRENCE_COLUMNS = {
    "recurrence_unit": "TEXT",
    "recurrence_interval": "INTEGER",
    "recurrence_end_date": "TEXT",
}

# v1.1 (Google sign-in) added a nullable `google_sub` column to `users`, plus
# relaxed `password_hash`/`password_salt` to nullable (Google-only accounts
# have no local password). SQLite's ALTER TABLE can add a column but can't
# drop a NOT NULL constraint, so only the new column is migrated here for an
# existing on-disk DB; one predating this change and still carrying the old
# NOT NULL constraint should be recreated with `./scripts/reset_db.sh`.


class _Result:
    """What DB.execute() returns: rows already fetched into memory (see the
    comment on DB._lock for why), plus the inserted row id if any. Covers
    every access pattern the DAOs actually use - .fetchone()/.fetchall()/
    .lastrowid - without holding the shared connection open past execute()."""

    __slots__ = ("_rows", "lastrowid")

    def __init__(self, rows: list, lastrowid: int | None):
        self._rows = rows
        self.lastrowid = lastrowid

    def fetchone(self) -> "sqlite3.Row | None":
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows


class DB:
    """
    Thin sqlite3 wrapper: owns the connection, applies the schema on connect,
    and returns rows as sqlite3.Row so callers can read columns by name
    instead of relying on positional order.
    """

    def __init__(self, db_path: str = "priotask.db"):
        self.db_path = db_path
        self.connection: sqlite3.Connection | None = None
        # check_same_thread=False (below) only disables Python's guard
        # against cross-thread use - it does not make sqlite3.Connection
        # safe for genuinely *concurrent* access. Flask's dev server runs
        # threaded by default, and this DB instance is a single connection
        # shared by every DAO, so two requests landing on different threads
        # at the same moment can corrupt each other's cursor state
        # (sqlite3.InterfaceError: "bad parameter or other API misuse").
        # This lock serializes all query execution to make that safe -
        # acceptable since sqlite only supports one writer at a time anyway.
        self._lock = threading.Lock()

    def connect(self) -> "DB":
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self._migrate_tasks_recurrence_columns()
        self._migrate_users_google_sub_column()
        self.connection.commit()
        return self

    def _migrate_tasks_recurrence_columns(self) -> None:
        existing = {row["name"] for row in self.connection.execute("PRAGMA table_info(tasks)")}
        for column, sql_type in _TASKS_RECURRENCE_COLUMNS.items():
            if column not in existing:
                self.connection.execute(f"ALTER TABLE tasks ADD COLUMN {column} {sql_type}")

    def _migrate_users_google_sub_column(self) -> None:
        existing = {row["name"] for row in self.connection.execute("PRAGMA table_info(users)")}
        if "google_sub" not in existing:
            self.connection.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub "
            "ON users (google_sub) WHERE google_sub IS NOT NULL"
        )

    def execute(self, query: str, params: Sequence[Any] = ()) -> _Result:
        with self._lock:
            cursor = self.connection.execute(query, params)
            self.connection.commit()
            return _Result(cursor.fetchall(), cursor.lastrowid)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "DB":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
