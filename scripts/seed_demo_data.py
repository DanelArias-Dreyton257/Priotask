#!/usr/bin/env python
"""
Seeds the database with an admin/admin user and a varied set of demo tasks
(overdue, due today, due this week/month, different efforts/importances/
types, a couple already completed, one partially logged) so the UI can be
exercised manually without registering and typing tasks by hand.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO  # noqa: E402
from server.src.data.db.DB import DB  # noqa: E402
from server.src.data.db.TaskDAO import TaskDAO  # noqa: E402
from server.src.data.db.UserDAO import UserDAO  # noqa: E402
from server.src.services.TaskManager import TaskManager  # noqa: E402
from server.src.services.UserManager import UserManager  # noqa: E402

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminadmin"
ADMIN_EMAIL = "admin@priotask.local"


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "priotask.db"
    db = DB(db_path).connect()
    users = UserManager(UserDAO(db))
    tasks = TaskManager(TaskDAO(db), CompletionSnapshotDAO(db))

    user = users.get_user_by_username(ADMIN_USERNAME)
    if user is None:
        user = users.create_user(ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL)
        print(f"Created user '{ADMIN_USERNAME}' (password: '{ADMIN_PASSWORD}').")
    else:
        print(f"User '{ADMIN_USERNAME}' already exists, reusing it.")

    if tasks.get_tasks_for_user(user.user_id):
        print(f"'{ADMIN_USERNAME}' already has tasks, leaving them as-is.")
        print("Run scripts/reset_db.sh first if you want a clean reseed.")
        db.close()
        return

    now = datetime.now()
    open_tasks = [
        dict(name="Pay overdue invoice", deadline=now - timedelta(days=1),
             expected_duration_h=1.0, importance=9, task_type="finance"),
        dict(name="Water the plants", deadline=now,
             expected_duration_h=0.25, importance=1, task_type="chore"),
        dict(name="Fix leaking faucet", deadline=now + timedelta(days=2),
             expected_duration_h=1.5, importance=4, task_type="chore", task_subtype="repair"),
        dict(name="Prepare client presentation", deadline=now + timedelta(days=1),
             expected_duration_h=3.0, importance=8, task_type="work", task_subtype="presentation"),
        dict(name="Submit quarterly report", deadline=now + timedelta(days=3),
             expected_duration_h=5.0, importance=7, task_type="work", task_subtype="report"),
        dict(name="Refactor billing module", deadline=now + timedelta(days=5),
             expected_duration_h=8.0, importance=5, task_type="work", task_subtype="engineering"),
        dict(name="Renew passport", deadline=now + timedelta(days=10),
             expected_duration_h=2.0, importance=6, task_type="personal"),
        dict(name="Study for certification exam", deadline=now + timedelta(days=14),
             expected_duration_h=10.0, importance=9, task_type="study", task_subtype="exam"),
        dict(name="Plan birthday party", deadline=now + timedelta(days=20),
             expected_duration_h=4.0, importance=3, task_type="personal", task_subtype="event"),
        dict(name="Read 'Atomic Habits'", deadline=now + timedelta(days=30),
             expected_duration_h=6.0, importance=2, task_type="personal", task_subtype="reading"),
        # Recurring (Phase 11): completing this spawns its next occurrence a
        # week later instead of just marking it done, demoing the "Repeats"
        # control/badge without needing to create one by hand.
        dict(name="Weekly team sync", deadline=now + timedelta(days=4),
             expected_duration_h=1.0, importance=4, task_type="work", task_subtype="meeting",
             recurrence_unit="week", recurrence_interval=1),
    ]
    for fields in open_tasks:
        tasks.create_task(user_id=user.user_id, **fields)

    # Some progress already logged, to show partial completion (Phase 7) in the UI.
    in_progress = tasks.create_task(
        user_id=user.user_id, name="Write blog post", deadline=now + timedelta(days=7),
        expected_duration_h=5.0, importance=5, task_type="personal", task_subtype="writing",
    )
    tasks.log_hours(in_progress.task_id, 2.0)

    # A few already-completed tasks, so PrioritizerTrainer (Phase 6/7) has real
    # completion history to learn from once /api/prioritizer/train is triggered.
    done_tasks = [
        dict(name="Submit timesheet", deadline=now - timedelta(days=4),
             expected_duration_h=0.5, importance=4, task_type="work", completed_days_ago=5),
        dict(name="Renew gym membership", deadline=now - timedelta(days=1),
             expected_duration_h=0.5, importance=2, task_type="personal", completed_days_ago=2),
        dict(name="Weekly grocery shopping", deadline=now - timedelta(hours=12),
             expected_duration_h=1.0, importance=3, task_type="chore", completed_days_ago=1),
    ]
    for fields in done_tasks:
        completed_days_ago = fields.pop("completed_days_ago")
        created = tasks.create_task(user_id=user.user_id, **fields)
        tasks.mark_done(created.task_id, now - timedelta(days=completed_days_ago))

    total = len(open_tasks) + 1 + len(done_tasks)
    print(f"Seeded {total} tasks for '{ADMIN_USERNAME}' "
          f"({len(done_tasks)} already done, 1 partially logged).")
    print(f"Log in at the client with username '{ADMIN_USERNAME}' / password '{ADMIN_PASSWORD}'.")
    db.close()


if __name__ == "__main__":
    main()
