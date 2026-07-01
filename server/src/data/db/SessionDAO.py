import sqlite3
from typing import Optional

from server.src.data.db.DB import DB


class SessionDAO:
    """
    Raw access to `sessions`: one row per active bearer token, storing the
    owning user_id and an ISO-8601 expiry timestamp. Used by AuthService
    (Phase 15) to persist sessions across server restarts and enforce a
    sliding expiry policy.
    """

    def __init__(self, db: Optional[DB] = None):
        self.db = db or DB().connect()

    def add_session(self, token: str, user_id: int, expires_at: str) -> None:
        self.db.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )

    def get_session(self, token: str) -> Optional[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()

    def update_expires_at(self, token: str, expires_at: str) -> None:
        self.db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?", (expires_at, token)
        )

    def delete_session(self, token: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def delete_sessions_for_user(self, user_id: int) -> None:
        self.db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def cleanup_expired(self, now: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
