import sqlite3
from typing import List, Optional

from server.src.data.db.DB import DB


class TaskDAO(object):
    def __init__(self, db: Optional[DB] = None):
        self.db = db or DB().connect()

    def add_task(self, user_id: int, name: str, deadline: str, expected_duration_h: float,
                 importance: int, task_type: str, task_subtype: str) -> int:
        cursor = self.db.execute(
            "INSERT INTO tasks (user_id, name, deadline, expected_duration_h, importance, "
            "task_type, task_subtype) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, deadline, expected_duration_h, importance, task_type, task_subtype),
        )
        return cursor.lastrowid

    def get_task(self, task_id: int) -> Optional[sqlite3.Row]:
        query = "SELECT * FROM tasks WHERE task_id = ?"
        return self.db.execute(query, (task_id,)).fetchone()

    def get_tasks_for_user(self, user_id: int) -> List[sqlite3.Row]:
        query = "SELECT * FROM tasks WHERE user_id = ?"
        return self.db.execute(query, (user_id,)).fetchall()

    def update_task(self, task_id: int, name: str, deadline: str, expected_duration_h: float,
                    importance: int, task_type: str, task_subtype: str) -> None:
        self.db.execute(
            "UPDATE tasks SET name = ?, deadline = ?, expected_duration_h = ?, importance = ?, "
            "task_type = ?, task_subtype = ? WHERE task_id = ?",
            (name, deadline, expected_duration_h, importance, task_type, task_subtype, task_id),
        )

    def mark_done(self, task_id: int, completed_at: str) -> None:
        self.db.execute(
            "UPDATE tasks SET done = 1, completed_at = ? WHERE task_id = ?",
            (completed_at, task_id),
        )

    def delete_task(self, task_id: int) -> None:
        self.db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
