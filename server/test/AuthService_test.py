import unittest

from server.src.data.db.DB import DB
from server.src.data.db.SessionDAO import SessionDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.AuthService import AuthService
from server.src.services.UserManager import UserManager


class AuthServiceTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        user_manager = UserManager(UserDAO(self.db))
        session_dao = SessionDAO(self.db)
        self.auth = AuthService(user_manager, session_dao)
        user_manager.create_user("alice", "s3cret!!", "alice@example.com")

    def tearDown(self):
        self.db.close()

    def test_login_with_correct_credentials_returns_token(self):
        token = self.auth.login("alice", "s3cret!!")
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)

    def test_login_with_wrong_password_returns_none(self):
        self.assertIsNone(self.auth.login("alice", "wrong"))

    def test_login_with_unknown_user_returns_none(self):
        self.assertIsNone(self.auth.login("nobody", "s3cret!!"))

    def test_login_persists_session_to_db(self):
        token = self.auth.login("alice", "s3cret!!")
        row = self.auth.session_dao.get_session(token)
        self.assertIsNotNone(row)
        self.assertIn("expires_at", row.keys())

    def test_resolve_token_returns_user_id(self):
        token = self.auth.login("alice", "s3cret!!")
        user_id = self.auth.resolve_token(token)
        self.assertIsNotNone(user_id)
        self.assertIsInstance(user_id, int)

    def test_resolve_unknown_token_returns_none(self):
        self.assertIsNone(self.auth.resolve_token("not-a-real-token"))

    def test_resolve_expired_token_returns_none(self):
        token = self.auth.login("alice", "s3cret!!")
        # Force expiry to the past.
        self.auth.session_dao.update_expires_at(token, "2000-01-01T00:00:00+00:00")
        self.assertIsNone(self.auth.resolve_token(token))

    def test_resolve_expired_token_removes_it_from_db(self):
        token = self.auth.login("alice", "s3cret!!")
        self.auth.session_dao.update_expires_at(token, "2000-01-01T00:00:00+00:00")
        self.auth.resolve_token(token)
        self.assertIsNone(self.auth.session_dao.get_session(token))

    def test_logout_removes_session(self):
        token = self.auth.login("alice", "s3cret!!")
        self.auth.logout(token)
        self.assertIsNone(self.auth.resolve_token(token))

    def test_resolve_slides_expiry(self):
        token = self.auth.login("alice", "s3cret!!")
        before = self.auth.session_dao.get_session(token)["expires_at"]
        self.auth.resolve_token(token)
        after = self.auth.session_dao.get_session(token)["expires_at"]
        # After a resolve the stored expiry must be >= the one set at login.
        self.assertGreaterEqual(after, before)

    def test_revoke_user_removes_all_sessions(self):
        token_a = self.auth.login("alice", "s3cret!!")
        token_b = self.auth.login("alice", "s3cret!!")
        user_id = self.auth.resolve_token(token_a)
        self.auth.revoke_user(user_id)
        self.assertIsNone(self.auth.session_dao.get_session(token_a))
        self.assertIsNone(self.auth.session_dao.get_session(token_b))

    def test_multiple_logins_produce_independent_tokens(self):
        token_a = self.auth.login("alice", "s3cret!!")
        token_b = self.auth.login("alice", "s3cret!!")
        self.assertNotEqual(token_a, token_b)
        # Both are valid simultaneously.
        self.assertIsNotNone(self.auth.resolve_token(token_a))
        self.assertIsNotNone(self.auth.resolve_token(token_b))


if __name__ == "__main__":
    unittest.main()
