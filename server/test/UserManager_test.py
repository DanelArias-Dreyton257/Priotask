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

    def test_delete_user_by_id_removes_it(self):
        created = self.manager.create_user("julia", "s3cret", "julia@example.com")
        self.manager.delete_user_by_id(created.user_id)
        self.assertIsNone(self.manager.get_user_by_id(created.user_id))

    def test_create_user_has_password_true_and_not_google_linked(self):
        dto = self.manager.create_user("kate", "s3cret", "kate@example.com")
        self.assertTrue(dto.has_password)
        self.assertFalse(dto.google_linked)

    # --- v1.1: Sign in with Google ---

    def test_create_google_user_derives_username_from_email(self):
        dto = self.manager.create_google_user("newperson@example.com", "google-sub-1")
        self.assertEqual(dto.username, "newperson")
        self.assertEqual(dto.email, "newperson@example.com")
        self.assertFalse(dto.has_password)
        self.assertTrue(dto.google_linked)

    def test_create_google_user_dedupes_username_collisions(self):
        self.manager.create_user("sameuser", "s3cret", "sameuser@other.com")
        dto = self.manager.create_google_user("sameuser@example.com", "google-sub-2")
        self.assertNotEqual(dto.username, "sameuser")
        self.assertTrue(dto.username.startswith("sameuser"))

    def test_get_user_by_google_sub_returns_matching_user(self):
        created = self.manager.create_google_user("gperson@example.com", "google-sub-3")
        fetched = self.manager.get_user_by_google_sub("google-sub-3")
        self.assertEqual(fetched.user_id, created.user_id)

    def test_get_user_by_google_sub_returns_none_when_missing(self):
        self.assertIsNone(self.manager.get_user_by_google_sub("no-such-sub"))

    def test_get_user_by_email_returns_matching_user(self):
        created = self.manager.create_user("liam", "s3cret", "liam@example.com")
        fetched = self.manager.get_user_by_email("liam@example.com")
        self.assertEqual(fetched.user_id, created.user_id)

    def test_link_google_account_marks_user_google_linked(self):
        created = self.manager.create_user("mia", "s3cret", "mia@example.com")
        linked = self.manager.link_google_account(created.user_id, "google-sub-4")
        self.assertTrue(linked.google_linked)
        self.assertTrue(linked.has_password)
        self.assertEqual(self.manager.get_user_by_google_sub("google-sub-4").user_id, created.user_id)

    def test_verify_password_returns_false_for_google_only_account(self):
        self.manager.create_google_user("nopass@example.com", "google-sub-5")
        self.assertFalse(self.manager.verify_password("nopass", "anything"))

    def test_change_password_returns_false_for_google_only_account(self):
        created = self.manager.create_google_user("nopass2@example.com", "google-sub-6")
        changed = self.manager.change_password(created.user_id, "anything", "new-password")
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
