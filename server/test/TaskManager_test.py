import unittest
from datetime import datetime, timedelta

from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO
from server.src.data.db.DB import DB
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager

REFERENCE = datetime(2026, 1, 1)


class TaskManagerTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        self.manager = TaskManager(TaskDAO(self.db), CompletionSnapshotDAO(self.db))
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

    def test_mark_done_snapshots_other_open_tasks(self):
        a = self.manager.create_task(
            user_id=self.user_id, name="a", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        b = self.manager.create_task(
            user_id=self.user_id, name="b", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        completed_at = REFERENCE + timedelta(days=1)

        self.manager.mark_done(a.task_id, completed_at)

        snapshots = self.manager.get_completion_snapshots(self.user_id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].completed_task_id, a.task_id)
        self.assertEqual(snapshots[0].completed_at, completed_at)
        self.assertEqual(snapshots[0].open_task_ids, [b.task_id])

    def test_mark_done_snapshot_excludes_other_users_tasks(self):
        mine = self.manager.create_task(
            user_id=self.user_id, name="mine", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        self.manager.create_task(
            user_id=self.other_user_id, name="theirs", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )

        self.manager.mark_done(mine.task_id, REFERENCE)

        snapshots = self.manager.get_completion_snapshots(self.user_id)
        self.assertEqual(snapshots[0].open_task_ids, [])

    def test_log_hours_reduces_remaining_duration(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="task", deadline=REFERENCE, expected_duration_h=4.0, importance=1,
        )
        updated = self.manager.log_hours(created.task_id, 1.5)
        self.assertEqual(updated.expected_duration_h, 2.5)
        self.assertFalse(updated.done)

    def test_log_hours_marks_done_when_remaining_reaches_zero(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="task", deadline=REFERENCE, expected_duration_h=2.0, importance=1,
        )
        completed_at = REFERENCE + timedelta(days=1)
        updated = self.manager.log_hours(created.task_id, 5.0, completed_at)
        self.assertEqual(updated.expected_duration_h, 0.0)
        self.assertTrue(updated.done)
        self.assertEqual(updated.completed_at, completed_at.isoformat())

    def test_log_hours_returns_none_when_missing(self):
        self.assertIsNone(self.manager.log_hours(999, 1.0))

    def test_create_task_persists_recurrence_fields(self):
        dto = self.manager.create_task(
            user_id=self.user_id, name="standup", deadline=REFERENCE, expected_duration_h=0.5,
            importance=2, recurrence_unit="day", recurrence_interval=1,
        )
        fetched = self.manager.get_task(dto.task_id)
        self.assertEqual(fetched.recurrence_unit, "day")
        self.assertEqual(fetched.recurrence_interval, 1)
        self.assertIsNone(fetched.recurrence_end_date)

    def test_mark_done_spawns_next_occurrence_daily(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="standup", deadline=REFERENCE, expected_duration_h=0.5,
            importance=2, recurrence_unit="day", recurrence_interval=1,
        )
        self.manager.mark_done(created.task_id, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        self.assertEqual(len(tasks), 2)
        spawned = next(t for t in tasks if t.task_id != created.task_id)
        self.assertEqual(spawned.name, "standup")
        self.assertFalse(spawned.done)
        self.assertEqual(spawned.deadline, (REFERENCE + timedelta(days=1)).isoformat())
        self.assertEqual(spawned.recurrence_unit, "day")

    def test_mark_done_spawns_next_occurrence_weekly_with_interval(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="laundry", deadline=REFERENCE, expected_duration_h=1.0,
            importance=2, recurrence_unit="week", recurrence_interval=2,
        )
        self.manager.mark_done(created.task_id, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        spawned = next(t for t in tasks if t.task_id != created.task_id)
        self.assertEqual(spawned.deadline, (REFERENCE + timedelta(weeks=2)).isoformat())

    def test_mark_done_spawns_next_occurrence_monthly_clamps_month_end(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="rent", deadline=datetime(2026, 1, 31),
            expected_duration_h=1.0, importance=2, recurrence_unit="month", recurrence_interval=1,
        )
        self.manager.mark_done(created.task_id, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        spawned = next(t for t in tasks if t.task_id != created.task_id)
        self.assertEqual(spawned.deadline, datetime(2026, 2, 28).isoformat())

    def test_mark_done_does_not_spawn_past_recurrence_end_date(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="standup", deadline=REFERENCE, expected_duration_h=0.5,
            importance=2, recurrence_unit="day", recurrence_interval=1,
            recurrence_end_date=REFERENCE,
        )
        self.manager.mark_done(created.task_id, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        self.assertEqual(len(tasks), 1)

    def test_mark_done_does_not_spawn_for_non_recurring_task(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="one-off", deadline=REFERENCE, expected_duration_h=1.0,
            importance=1,
        )
        self.manager.mark_done(created.task_id, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        self.assertEqual(len(tasks), 1)

    def test_log_hours_completing_recurring_task_also_spawns(self):
        created = self.manager.create_task(
            user_id=self.user_id, name="watering", deadline=REFERENCE, expected_duration_h=1.0,
            importance=1, recurrence_unit="day", recurrence_interval=1,
        )
        self.manager.log_hours(created.task_id, 1.0, REFERENCE)

        tasks = self.manager.get_tasks_for_user(self.user_id)
        self.assertEqual(len(tasks), 2)


if __name__ == "__main__":
    unittest.main()
