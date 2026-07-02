"""
CRUD layer between UserDAO and the domain. Owns user creation (PBKDF2-HMAC-
SHA256 password hashing), lookup, email/password updates (Phase 13), Google
account creation/linking (v1.1), and domain<->DTO mapping.
"""
import hashlib
import hmac
import os
import re
import sqlite3
from typing import Optional, Tuple

from server.src.data.db.UserDAO import UserDAO
from server.src.data.domain.User import User
from server.src.data.dto.UserDTO import UserDTO

PBKDF2_ITERATIONS = 200_000
_MIN_USERNAME_LEN = 3


class UserManager:
    """CRUD layer between UserDAO (raw rows) and the rest of the app (User/UserDTO)."""

    def __init__(self, dao: Optional[UserDAO] = None):
        self.dao = dao or UserDAO()

    @staticmethod
    def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return digest, salt

    def _row_to_domain(self, row: sqlite3.Row) -> User:
        return User(
            username=row["username"],
            password_hash=row["password_hash"],
            email=row["email"],
            user_id=row["user_id"],
            password_salt=row["password_salt"],
            google_sub=row["google_sub"],
        )

    def _domain_to_dto(self, user: User) -> UserDTO:
        return UserDTO(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            has_password=user.password_hash is not None,
            google_linked=user.google_sub is not None,
        )

    def create_user(self, username: str, password: str, email: str) -> UserDTO:
        password_hash, password_salt = self._hash_password(password)
        user_id = self.dao.add_user(username, password_hash, password_salt, email)
        user = User(username, password_hash, email, user_id=user_id, password_salt=password_salt)
        return self._domain_to_dto(user)

    def get_user_by_username(self, username: str) -> Optional[UserDTO]:
        row = self.dao.get_user(username)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[UserDTO]:
        row = self.dao.get_user_by_id(user_id)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def verify_password(self, username: str, password: str) -> bool:
        row = self.dao.get_user(username)
        # A Google-only account has no local password to verify against.
        if row is None or row["password_hash"] is None:
            return False
        digest, _ = self._hash_password(password, row["password_salt"])
        return hmac.compare_digest(digest, row["password_hash"])

    def update_email(self, user_id: int, email: str) -> Optional[UserDTO]:
        self.dao.update_email(user_id, email)
        return self.get_user_by_id(user_id)

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Verifies `current_password` against the stored hash before replacing it; returns
        False (no-op) if the user is unknown or the current password doesn't match."""
        row = self.dao.get_user_by_id(user_id)
        if row is None or row["password_hash"] is None:
            return False
        digest, _ = self._hash_password(current_password, row["password_salt"])
        if not hmac.compare_digest(digest, row["password_hash"]):
            return False
        password_hash, password_salt = self._hash_password(new_password)
        self.dao.update_password(user_id, password_hash, password_salt)
        return True

    def delete_user(self, username: str) -> None:
        self.dao.delete_user(username)

    def delete_user_by_id(self, user_id: int) -> None:
        self.dao.delete_user_by_id(user_id)

    def get_user_by_google_sub(self, google_sub: str) -> Optional[UserDTO]:
        row = self.dao.get_user_by_google_sub(google_sub)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        row = self.dao.get_user_by_email(email)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def create_google_user(self, email: str, google_sub: str) -> UserDTO:
        """Creates an account for a first-time Google sign-in. No local
        password is set; the username is derived from the email address."""
        username = self._generate_username_from_email(email)
        user_id = self.dao.add_google_user(username, email, google_sub)
        user = User(username, None, email, user_id=user_id, google_sub=google_sub)
        return self._domain_to_dto(user)

    def link_google_account(self, user_id: int, google_sub: str) -> Optional[UserDTO]:
        """Attaches a Google identity to an existing (password-based) account,
        so it can be logged into either way going forward."""
        self.dao.set_google_sub(user_id, google_sub)
        return self.get_user_by_id(user_id)

    def _generate_username_from_email(self, email: str) -> str:
        local_part = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@", 1)[0]).lower()
        base = local_part.ljust(_MIN_USERNAME_LEN, "0")
        username = base
        suffix = 2
        while self.get_user_by_username(username) is not None:
            username = f"{base}{suffix}"
            suffix += 1
        return username
