import unittest
from datetime import datetime

from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO
from server.src.data.db.DB import DB
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.DemoSeeder import DEMO_USERNAME, seed_demo_data
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager


class DemoSeederTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        self.users = UserManager(UserDAO(self.db))
        self.tasks = TaskManager(TaskDAO(self.db), CompletionSnapshotDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_creates_demo_user_with_tasks(self):
        seed_demo_data(self.users, self.tasks)

        user = self.users.get_user_by_username(DEMO_USERNAME)
        self.assertIsNotNone(user)
        seeded_tasks = self.tasks.get_tasks_for_user(user.user_id)
        self.assertGreater(len(seeded_tasks), 0)

    def test_open_tasks_are_never_overdue(self):
        seed_demo_data(self.users, self.tasks)

        user = self.users.get_user_by_username(DEMO_USERNAME)
        now = datetime.now()
        open_tasks = [t for t in self.tasks.get_domain_tasks_for_user(user.user_id) if not t.done]
        self.assertGreater(len(open_tasks), 0)
        for task in open_tasks:
            self.assertGreater(task.deadline, now)

    def test_is_idempotent(self):
        seed_demo_data(self.users, self.tasks)
        user = self.users.get_user_by_username(DEMO_USERNAME)
        first_count = len(self.tasks.get_tasks_for_user(user.user_id))

        seed_demo_data(self.users, self.tasks)

        second_count = len(self.tasks.get_tasks_for_user(user.user_id))
        self.assertEqual(first_count, second_count)


if __name__ == "__main__":
    unittest.main()
