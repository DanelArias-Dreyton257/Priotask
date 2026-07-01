import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from server.src.data.db.SessionDAO import SessionDAO
from server.src.services.UserManager import UserManager

EXPIRY_DAYS = int(os.environ.get("PRIOTASK_SESSION_EXPIRY_DAYS", "7"))


class AuthService:
    """
    Issues and resolves bearer tokens for the API (Phase 4). Phase 15 moves
    from an in-memory dict to a `sessions` DB table (SessionDAO) so tokens
    survive server restarts. Sliding expiry: each successful resolve extends
    the token's lifetime by EXPIRY_DAYS (configurable via
    PRIOTASK_SESSION_EXPIRY_DAYS, default 7). revoke_user() purges all
    sessions for a given user, used when an account is deleted.
    """

    def __init__(self, user_manager: Optional[UserManager] = None,
                 session_dao: Optional[SessionDAO] = None):
        self.user_manager = user_manager or UserManager()
        self.session_dao = session_dao or SessionDAO()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _expiry(self) -> str:
        return (self._now() + timedelta(days=EXPIRY_DAYS)).isoformat()

    def login(self, username: str, password: str) -> Optional[str]:
        if not self.user_manager.verify_password(username, password):
            return None
        user = self.user_manager.get_user_by_username(username)
        token = secrets.token_urlsafe(32)
        self.session_dao.add_session(token, user.user_id, self._expiry())
        self.session_dao.cleanup_expired(self._now().isoformat())
        return token

    def logout(self, token: str) -> None:
        self.session_dao.delete_session(token)

    def resolve_token(self, token: str) -> Optional[int]:
        row = self.session_dao.get_session(token)
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < self._now():
            self.session_dao.delete_session(token)
            return None
        self.session_dao.update_expires_at(token, self._expiry())
        return row["user_id"]

    def revoke_user(self, user_id: int) -> None:
        self.session_dao.delete_sessions_for_user(user_id)
