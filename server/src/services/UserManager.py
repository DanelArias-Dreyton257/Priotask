import hashlib
import hmac
import os
import sqlite3
from typing import Optional, Tuple

from server.src.data.db.UserDAO import UserDAO
from server.src.data.domain.User import User
from server.src.data.dto.UserDTO import UserDTO

PBKDF2_ITERATIONS = 200_000


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
        )

    def _domain_to_dto(self, user: User) -> UserDTO:
        return UserDTO(user_id=user.user_id, username=user.username, email=user.email)

    def create_user(self, username: str, password: str, email: str) -> UserDTO:
        password_hash, password_salt = self._hash_password(password)
        user_id = self.dao.add_user(username, password_hash, password_salt, email)
        user = User(username, password_hash, email, user_id=user_id, password_salt=password_salt)
        return self._domain_to_dto(user)

    def get_user_by_username(self, username: str) -> Optional[UserDTO]:
        row = self.dao.get_user(username)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def verify_password(self, username: str, password: str) -> bool:
        row = self.dao.get_user(username)
        if row is None:
            return False
        digest, _ = self._hash_password(password, row["password_salt"])
        return hmac.compare_digest(digest, row["password_hash"])

    def delete_user(self, username: str) -> None:
        self.dao.delete_user(username)
