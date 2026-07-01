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

    def get_user_by_id(self, user_id: int) -> Optional[sqlite3.Row]:
        query = "SELECT * FROM users WHERE user_id = ?"
        return self.db.execute(query, (user_id,)).fetchone()

    def get_users(self) -> List[sqlite3.Row]:
        query = "SELECT * FROM users"
        return self.db.execute(query).fetchall()

    def update_email(self, user_id: int, email: str) -> None:
        self.db.execute("UPDATE users SET email = ? WHERE user_id = ?", (email, user_id))

    def update_password(self, user_id: int, password_hash: bytes, password_salt: bytes) -> None:
        self.db.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? WHERE user_id = ?",
            (password_hash, password_salt, user_id),
        )

    def delete_user(self, username: str) -> None:
        self.db.execute("DELETE FROM users WHERE username = ?", (username,))

    def delete_user_by_id(self, user_id: int) -> None:
        self.db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
