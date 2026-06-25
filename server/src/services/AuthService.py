import secrets
from typing import Dict, Optional

from server.src.services.UserManager import UserManager


class AuthService:
    """
    Issues and resolves bearer tokens for the API (Phase 4). Tokens are opaque,
    random strings kept in memory only (no expiry/persistence yet) and map
    1:1 to a user_id; restarting the server invalidates every session.
    """

    def __init__(self, user_manager: Optional[UserManager] = None):
        self.user_manager = user_manager or UserManager()
        self._tokens_by_user: Dict[int, str] = {}
        self._users_by_token: Dict[str, int] = {}

    def login(self, username: str, password: str) -> Optional[str]:
        if not self.user_manager.verify_password(username, password):
            return None
        user = self.user_manager.get_user_by_username(username)
        token = self._tokens_by_user.get(user.user_id)
        if token is None:
            token = secrets.token_urlsafe(32)
            self._tokens_by_user[user.user_id] = token
            self._users_by_token[token] = user.user_id
        return token

    def logout(self, token: str) -> None:
        user_id = self._users_by_token.pop(token, None)
        if user_id is not None:
            self._tokens_by_user.pop(user_id, None)

    def resolve_token(self, token: str) -> Optional[int]:
        return self._users_by_token.get(token)
