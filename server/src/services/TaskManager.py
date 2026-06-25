import sqlite3
from datetime import datetime
from typing import List, Optional

from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.domain.Task import Task
from server.src.data.dto.TaskDTO import TaskDTO


class TaskManager:
    """CRUD layer between TaskDAO (raw rows) and the rest of the app (Task/TaskDTO)."""

    def __init__(self, dao: Optional[TaskDAO] = None):
        self.dao = dao or TaskDAO()

    def _row_to_domain(self, row: sqlite3.Row) -> Task:
        return Task(
            name=row["name"],
            deadline=datetime.fromisoformat(row["deadline"]),
            expected_duration_h=row["expected_duration_h"],
            importance=row["importance"],
            task_type=row["task_type"],
            task_subtype=row["task_subtype"],
            task_id=row["task_id"],
            user_id=row["user_id"],
            done=bool(row["done"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    def _domain_to_dto(self, task: Task) -> TaskDTO:
        return TaskDTO(
            task_id=task.task_id,
            user_id=task.user_id,
            name=task.name,
            deadline=task.deadline.isoformat(),
            expected_duration_h=task.expected_duration_h,
            importance=task.importance,
            task_type=task.task_type,
            task_subtype=task.task_subtype,
            done=task.done,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )

    def create_task(self, user_id: int, name: str, deadline: datetime, expected_duration_h: float,
                     importance: int, task_type: str = "", task_subtype: str = "") -> TaskDTO:
        task_id = self.dao.add_task(
            user_id, name, deadline.isoformat(), expected_duration_h, importance, task_type, task_subtype,
        )
        task = Task(name, deadline, expected_duration_h, importance, task_type, task_subtype,
                    task_id=task_id, user_id=user_id)
        return self._domain_to_dto(task)

    def get_task(self, task_id: int) -> Optional[TaskDTO]:
        row = self.dao.get_task(task_id)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def get_tasks_for_user(self, user_id: int) -> List[TaskDTO]:
        rows = self.dao.get_tasks_for_user(user_id)
        return [self._domain_to_dto(self._row_to_domain(row)) for row in rows]

    def get_domain_tasks_for_user(self, user_id: int) -> List[Task]:
        """Like get_tasks_for_user, but returns Task domain objects (e.g. for DailyPlanner)."""
        rows = self.dao.get_tasks_for_user(user_id)
        return [self._row_to_domain(row) for row in rows]

    def to_dto(self, task: Task) -> TaskDTO:
        return self._domain_to_dto(task)

    def update_task(self, task_id: int, name: str, deadline: datetime, expected_duration_h: float,
                     importance: int, task_type: str = "", task_subtype: str = "") -> None:
        self.dao.update_task(
            task_id, name, deadline.isoformat(), expected_duration_h, importance, task_type, task_subtype,
        )

    def mark_done(self, task_id: int, completed_at: Optional[datetime] = None) -> None:
        """Persist completion. Needed later as the Phase 6 training signal for PrioritizerNetwork."""
        completed_at = completed_at or datetime.now()
        self.dao.mark_done(task_id, completed_at.isoformat())

    def delete_task(self, task_id: int) -> None:
        self.dao.delete_task(task_id)
