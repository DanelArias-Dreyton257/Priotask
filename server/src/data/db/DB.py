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
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
"""


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
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()
        return self

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
