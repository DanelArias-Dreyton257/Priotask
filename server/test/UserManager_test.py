import unittest

from server.src.data.db.DB import DB
from server.src.data.db.UserDAO import UserDAO
from server.src.services.UserManager import UserManager


class UserManagerTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        self.manager = UserManager(UserDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_create_user_assigns_user_id_and_never_returns_password(self):
        dto = self.manager.create_user("alice", "s3cret", "alice@example.com")
        self.assertIsNotNone(dto.user_id)
        self.assertEqual(dto.username, "alice")
        self.assertEqual(dto.email, "alice@example.com")
        self.assertNotIn("password", dto.__dict__)

    def test_password_is_not_stored_in_plaintext(self):
        self.manager.create_user("bob", "s3cret", "bob@example.com")
        row = self.manager.dao.get_user("bob")
        self.assertNotEqual(row["password_hash"], b"s3cret")

    def test_verify_password_accepts_correct_password(self):
        self.manager.create_user("carol", "correct-password", "carol@example.com")
        self.assertTrue(self.manager.verify_password("carol", "correct-password"))

    def test_verify_password_rejects_wrong_password(self):
        self.manager.create_user("dave", "correct-password", "dave@example.com")
        self.assertFalse(self.manager.verify_password("dave", "wrong-password"))

    def test_verify_password_rejects_unknown_user(self):
        self.assertFalse(self.manager.verify_password("ghost", "anything"))

    def test_get_user_by_username_returns_none_when_missing(self):
        self.assertIsNone(self.manager.get_user_by_username("nobody"))

    def test_get_user_by_id_returns_matching_user(self):
        created = self.manager.create_user("frank", "s3cret", "frank@example.com")
        fetched = self.manager.get_user_by_id(created.user_id)
        self.assertEqual(fetched.username, "frank")

    def test_get_user_by_id_returns_none_when_missing(self):
        self.assertIsNone(self.manager.get_user_by_id(999))

    def test_update_email_changes_stored_email(self):
        created = self.manager.create_user("grace", "s3cret", "old@example.com")
        updated = self.manager.update_email(created.user_id, "new@example.com")
        self.assertEqual(updated.email, "new@example.com")
        self.assertEqual(self.manager.get_user_by_id(created.user_id).email, "new@example.com")

    def test_change_password_with_correct_current_password_succeeds(self):
        created = self.manager.create_user("heidi", "old-password", "heidi@example.com")
        changed = self.manager.change_password(created.user_id, "old-password", "new-password")
        self.assertTrue(changed)
        self.assertTrue(self.manager.verify_password("heidi", "new-password"))
        self.assertFalse(self.manager.verify_password("heidi", "old-password"))

    def test_change_password_with_wrong_current_password_fails(self):
        created = self.manager.create_user("ivan", "old-password", "ivan@example.com")
        changed = self.manager.change_password(created.user_id, "wrong-password", "new-password")
        self.assertFalse(changed)
        self.assertTrue(self.manager.verify_password("ivan", "old-password"))

    def test_change_password_for_unknown_user_fails(self):
        self.assertFalse(self.manager.change_password(999, "anything", "new-password"))

    def test_delete_user_removes_it(self):
        self.manager.create_user("erin", "s3cret", "erin@example.com")
        self.manager.delete_user("erin")
        self.assertIsNone(self.manager.get_user_by_username("erin"))


if __name__ == "__main__":
    unittest.main()
