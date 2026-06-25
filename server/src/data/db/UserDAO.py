import sqlite3
from typing import List, Optional

from server.src.data.db.DB import DB


class UserDAO(object):
    def __init__(self, db: Optional[DB] = None):
        self.db = db or DB().connect()

    def add_user(self, username: str, password_hash: bytes, password_salt: bytes, email: str) -> int:
        cursor = self.db.execute(
            "INSERT INTO users (username, password_hash, password_salt, email) VALUES (?, ?, ?, ?)",
            (username, password_hash, password_salt, email),
        )
        return cursor.lastrowid

    def get_user(self, username: str) -> Optional[sqlite3.Row]:
        query = "SELECT * FROM users WHERE username = ?"
        return self.db.execute(query, (username,)).fetchone()

    def get_users(self) -> List[sqlite3.Row]:
        query = "SELECT * FROM users"
        return self.db.execute(query).fetchall()

    def delete_user(self, username: str) -> None:
        self.db.execute("DELETE FROM users WHERE username = ?", (username,))
