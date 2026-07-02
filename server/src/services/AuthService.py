import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Tuple

from server.src.data.db.SessionDAO import SessionDAO
from server.src.services.UserManager import UserManager

EXPIRY_DAYS = int(os.environ.get("PRIOTASK_SESSION_EXPIRY_DAYS", "7"))

GoogleVerifier = Callable[[str, str], dict]


def _default_google_verifier(id_token_str: str, client_id: str) -> dict:
    """Verifies a Google ID token's signature/audience/expiry against
    Google's public certs, returning its claims. Raises ValueError (via
    google-auth) on any invalid token."""
    from google.auth.transport import requests as google_requests  # lazy: optional dep
    from google.oauth2 import id_token as google_id_token

    return google_id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)


class AuthService:
    """
    Issues and resolves bearer tokens for the API (Phase 4). Phase 15 moves
    from an in-memory dict to a `sessions` DB table (SessionDAO) so tokens
    survive server restarts. Sliding expiry: each successful resolve extends
    the token's lifetime by EXPIRY_DAYS (configurable via
    PRIOTASK_SESSION_EXPIRY_DAYS, default 7). revoke_user() purges all
    sessions for a given user, used when an account is deleted.

    v1.1 adds login_with_google(): verifies a Google ID token (via an
    injectable `google_verifier`, real Google network calls swapped out in
    tests) and issues the same kind of session token as password login,
    creating or linking a local account as needed.
    """

    def __init__(self, user_manager: Optional[UserManager] = None,
                 session_dao: Optional[SessionDAO] = None,
                 google_client_id: Optional[str] = None,
                 google_verifier: Optional[GoogleVerifier] = None):
        self.user_manager = user_manager or UserManager()
        self.session_dao = session_dao or SessionDAO()
        self.google_client_id = google_client_id or os.environ.get("PRIOTASK_GOOGLE_CLIENT_ID")
        self.google_verifier = google_verifier or _default_google_verifier

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _expiry(self) -> str:
        return (self._now() + timedelta(days=EXPIRY_DAYS)).isoformat()

    def _issue_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        self.session_dao.add_session(token, user_id, self._expiry())
        self.session_dao.cleanup_expired(self._now().isoformat())
        return token

    def login(self, username: str, password: str) -> Optional[str]:
        if not self.user_manager.verify_password(username, password):
            return None
        user = self.user_manager.get_user_by_username(username)
        return self._issue_session(user.user_id)

    def login_with_google(self, id_token_str: str) -> Optional[Tuple[str, str]]:
        """Returns (token, username) on success. None if Google sign-in isn't
        configured, the token fails verification, or its email is unverified."""
        if not self.google_client_id:
            return None
        try:
            claims = self.google_verifier(id_token_str, self.google_client_id)
        except Exception:
            # Boundary validating an external, attacker-controlled token: any
            # failure (bad signature, expired, malformed, network error
            # fetching Google's certs) is just "not a valid credential".
            return None

        google_sub = claims.get("sub")
        email = claims.get("email")
        if not google_sub or not email or not claims.get("email_verified"):
            return None

        user = self.user_manager.get_user_by_google_sub(google_sub)
        if user is None:
            user = self.user_manager.get_user_by_email(email)
            user = (self.user_manager.link_google_account(user.user_id, google_sub) if user
                    else self.user_manager.create_google_user(email, google_sub))

        token = self._issue_session(user.user_id)
        return token, user.username

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
