import unittest
from datetime import datetime, timedelta

from server.src.data.db.DB import DB
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager

REFERENCE = datetime(2026, 1, 1)


class TaskManagerTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        self.manager = TaskManager(TaskDAO(self.db))
        # tasks.user_id is a foreign key, so tests need real users on file.
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.other_user_id = users.create_user("bob", "s3cret", "bob@example.com").user_id

    def tearDown(self):
        self.db.close()

    def test_create_task_assigns_task_id(self):
        dto = self.manager.create_task(
            user_id=self.user_id, name="write report", deadline=REFERENCE + timedelta(days=2),
            expected_duration_h=4.0, importance=5, task_type="work", task_subtype="writing",
        )
        self.assertIsNotNone(dto.task_id)
        self.assertEqual(dto.user_id, self.user_id)
        self.assertEqual(dto.name, "write report")
        self.assertEqual(dto.expected_duration_h, 4.0)
        self.assertEqual(dto.importance, 5)
        self.assertFalse(dto.done)
        self.assertIsNone(dto.completed_at)

    def test_get_task_round_trips_fields(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="read book", deadline=REFERENCE + timedelta(days=5),
            expected_duration_h=2.5, importance=3,
        )
        fetched = self.manager.get_task(created.task_id)
        self.assertEqual(fetched, created)

    def test_get_task_returns_none_when_missing(self):
        self.assertIsNone(self.manager.get_task(999))

    def test_get_tasks_for_user_only_returns_own_tasks(self):
        self.manager.create_task(user_id=self.user_id, name="a", deadline=REFERENCE, expected_duration_h=1.0, importance=1)
        self.manager.create_task(user_id=self.other_user_id, name="b", deadline=REFERENCE, expected_duration_h=1.0, importance=1)
        tasks = self.manager.get_tasks_for_user(self.user_id)
        self.assertEqual([t.name for t in tasks], ["a"])

    def test_update_task_persists_changes(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="draft", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        self.manager.update_task(
            created.task_id, name="final", deadline=REFERENCE + timedelta(days=1),
            expected_duration_h=2.0, importance=9, task_type="work", task_subtype="review",
        )
        updated = self.manager.get_task(created.task_id)
        self.assertEqual(updated.name, "final")
        self.assertEqual(updated.importance, 9)
        self.assertEqual(updated.task_type, "work")

    def test_mark_done_sets_done_and_completed_at(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="task", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        completed_at = REFERENCE + timedelta(days=1)
        self.manager.mark_done(created.task_id, completed_at)
        done_task = self.manager.get_task(created.task_id)
        self.assertTrue(done_task.done)
        self.assertEqual(done_task.completed_at, completed_at.isoformat())

    def test_delete_task_removes_it(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="temp", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        self.manager.delete_task(created.task_id)
        self.assertIsNone(self.manager.get_task(created.task_id))


if __name__ == "__main__":
    unittest.main()
