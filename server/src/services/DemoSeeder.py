"""
Seeds a demo admin user with a varied set of tasks, for the publicly deployed
instance (Render wipes priotask.db on every redeploy/idle spin-up, since the
free tier has no persistent disk). Every deadline is computed relative to
"now", and kept at least a day out, so open tasks never render as overdue --
this is meant to look like an ongoing project when shown to someone, not to
exercise edge cases (scripts/seed_demo_data.py already covers that locally).
"""
from datetime import datetime, timedelta

from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager

DEMO_USERNAME = "admin"
DEMO_PASSWORD = "adminadmin"
DEMO_EMAIL = "admin@priotask.local"


def seed_demo_data(users: UserManager, tasks: TaskManager) -> None:
    user = users.get_user_by_username(DEMO_USERNAME)
    if user is None:
        user = users.create_user(DEMO_USERNAME, DEMO_PASSWORD, DEMO_EMAIL)
    elif tasks.get_tasks_for_user(user.user_id):
        return  # already seeded, leave it as-is

    now = datetime.now()
    open_tasks = [
        dict(name="Pay upcoming invoice", deadline=now + timedelta(days=1),
             expected_duration_h=1.0, importance=9, task_type="finance"),
        dict(name="Water the plants", deadline=now + timedelta(days=1),
             expected_duration_h=0.25, importance=1, task_type="chore"),
        dict(name="Prepare client presentation", deadline=now + timedelta(days=1),
             expected_duration_h=3.0, importance=8, task_type="work", task_subtype="presentation"),
        dict(name="Fix leaking faucet", deadline=now + timedelta(days=2),
             expected_duration_h=1.5, importance=4, task_type="chore", task_subtype="repair"),
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
        dict(name="Weekly team sync", deadline=now + timedelta(days=4),
             expected_duration_h=1.0, importance=4, task_type="work", task_subtype="meeting",
             recurrence_unit="week", recurrence_interval=1),
    ]
    for fields in open_tasks:
        tasks.create_task(user_id=user.user_id, **fields)

    in_progress = tasks.create_task(
        user_id=user.user_id, name="Write blog post", deadline=now + timedelta(days=7),
        expected_duration_h=5.0, importance=5, task_type="personal", task_subtype="writing",
    )
    tasks.log_hours(in_progress.task_id, 2.0)

    # Already-completed tasks so the Prioritizer window has real completion
    # history to train on; hidden by default (only shown with "Show completed").
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
