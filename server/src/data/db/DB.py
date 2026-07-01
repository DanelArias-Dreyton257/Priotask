import sqlite3
from typing import Any, Sequence

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    password_salt BLOB NOT NULL,
    email TEXT NOT NULL
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


class DB:
    """
    Thin sqlite3 wrapper: owns the connection, applies the schema on connect,
    and returns rows as sqlite3.Row so callers can read columns by name
    instead of relying on positional order.
    """

    def __init__(self, db_path: str = "priotask.db"):
        self.db_path = db_path
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> "DB":
        # check_same_thread=False: Flask's dev server (and most WSGI servers)
        # handle each request on its own thread, but this DB instance is a
        # single connection shared across all of them.
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self._migrate_tasks_recurrence_columns()
        self.connection.commit()
        return self

    def _migrate_tasks_recurrence_columns(self) -> None:
        existing = {row["name"] for row in self.connection.execute("PRAGMA table_info(tasks)")}
        for column, sql_type in _TASKS_RECURRENCE_COLUMNS.items():
            if column not in existing:
                self.connection.execute(f"ALTER TABLE tasks ADD COLUMN {column} {sql_type}")

    def execute(self, query: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(query, params)
        self.connection.commit()
        return cursor

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "DB":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
