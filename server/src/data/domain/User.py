from typing import Optional


class User:

    def __init__(self, username: str, password_hash: bytes, email: str,
                 user_id: Optional[int] = None, password_salt: Optional[bytes] = None):
        self.username = username
        # Never store plaintext passwords: password_hash/password_salt come
        # from UserManager's hashing, not from the raw password the user typed.
        self.password_hash = password_hash
        self.password_salt = password_salt
        self.email = email
        self.user_id = user_id

    def __repr__(self):
        return f"User(user_id={self.user_id}, username={self.username}, email={self.email})"
