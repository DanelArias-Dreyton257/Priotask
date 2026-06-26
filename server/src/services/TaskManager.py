import json
import sqlite3
from datetime import datetime
from typing import List, NamedTuple, Optional

from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.domain.Task import Task
from server.src.data.dto.TaskDTO import TaskDTO
from server.src.services.Recurrence import next_deadline


class CompletionSnapshot(NamedTuple):
    """A completion event plus the IDs of the other tasks that were still
    open at that moment - the real training signal PrioritizerTrainer needs,
    in place of its earlier done-vs-currently-open proxy (Phase 6/7)."""
    completed_task_id: int
    completed_at: datetime
    open_task_ids: List[int]


class TaskManager:
    """CRUD layer between TaskDAO (raw rows) and the rest of the app (Task/TaskDTO)."""

    def __init__(self, dao: Optional[TaskDAO] = None, snapshot_dao: Optional[CompletionSnapshotDAO] = None):
        self.dao = dao or TaskDAO()
        self.snapshot_dao = snapshot_dao or CompletionSnapshotDAO()

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
            recurrence_unit=row["recurrence_unit"],
            recurrence_interval=row["recurrence_interval"],
            recurrence_end_date=datetime.fromisoformat(row["recurrence_end_date"])
            if row["recurrence_end_date"] else None,
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
            recurrence_unit=task.recurrence_unit,
            recurrence_interval=task.recurrence_interval,
            recurrence_end_date=task.recurrence_end_date.isoformat() if task.recurrence_end_date else None,
        )

    def create_task(self, user_id: int, name: str, deadline: datetime, expected_duration_h: float,
                     importance: int, task_type: str = "", task_subtype: str = "",
                     recurrence_unit: Optional[str] = None, recurrence_interval: Optional[int] = None,
                     recurrence_end_date: Optional[datetime] = None) -> TaskDTO:
        task_id = self.dao.add_task(
            user_id, name, deadline.isoformat(), expected_duration_h, importance, task_type, task_subtype,
            recurrence_unit, recurrence_interval,
            recurrence_end_date.isoformat() if recurrence_end_date else None,
        )
        task = Task(name, deadline, expected_duration_h, importance, task_type, task_subtype,
                    task_id=task_id, user_id=user_id, recurrence_unit=recurrence_unit,
                    recurrence_interval=recurrence_interval, recurrence_end_date=recurrence_end_date)
        return self._domain_to_dto(task)

    def get_task(self, task_id: int) -> Optional[TaskDTO]:
        row = self.dao.get_task(task_id)
        return self._domain_to_dto(self._row_to_domain(row)) if row else None

    def get_domain_task(self, task_id: int) -> Optional[Task]:
        row = self.dao.get_task(task_id)
        return self._row_to_domain(row) if row else None

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
                     importance: int, task_type: str = "", task_subtype: str = "",
                     recurrence_unit: Optional[str] = None, recurrence_interval: Optional[int] = None,
                     recurrence_end_date: Optional[datetime] = None) -> None:
        self.dao.update_task(
            task_id, name, deadline.isoformat(), expected_duration_h, importance, task_type, task_subtype,
            recurrence_unit, recurrence_interval,
            recurrence_end_date.isoformat() if recurrence_end_date else None,
        )

    def mark_done(self, task_id: int, completed_at: Optional[datetime] = None) -> None:
        """Persist completion, snapshotting which other tasks were still open
        at this moment - the Phase 6 training signal for PrioritizerNetwork.
        If the task recurs (Phase 11), also spawns its next occurrence."""
        completed_at = completed_at or datetime.now()
        task = self.get_domain_task(task_id)
        if task is not None:
            open_ids = [
                t.task_id for t in self.get_tasks_for_user(task.user_id)
                if not t.done and t.task_id != task_id
            ]
            self.snapshot_dao.add_snapshot(
                task.user_id, task_id, completed_at.isoformat(), json.dumps(open_ids),
            )
        self.dao.mark_done(task_id, completed_at.isoformat())
        if task is not None and task.recurrence_unit:
            self._spawn_next_occurrence(task)

    def _spawn_next_occurrence(self, task: Task) -> Optional[TaskDTO]:
        upcoming = next_deadline(task.deadline, task.recurrence_unit, task.recurrence_interval or 1)
        if task.recurrence_end_date is not None and upcoming > task.recurrence_end_date:
            return None
        return self.create_task(
            task.user_id, task.name, upcoming, task.expected_duration_h, task.importance,
            task.task_type, task.task_subtype, task.recurrence_unit, task.recurrence_interval,
            task.recurrence_end_date,
        )

    def log_hours(self, task_id: int, hours_worked: float,
                   completed_at: Optional[datetime] = None) -> Optional[TaskDTO]:
        """Logs hours_worked against a task's remaining effort. If that
        brings the remaining effort to zero, the task is marked done (same
        completion signal/snapshot as mark_done)."""
        row = self.dao.get_task(task_id)
        if row is None:
            return None
        task = self._row_to_domain(row)
        remaining = max(0.0, task.expected_duration_h - hours_worked)
        self.dao.update_duration(task_id, remaining)
        if remaining <= 0 and not task.done:
            self.mark_done(task_id, completed_at)
        return self.get_task(task_id)

    def get_completion_snapshots(self, user_id: int) -> List[CompletionSnapshot]:
        rows = self.snapshot_dao.get_snapshots_for_user(user_id)
        return [
            CompletionSnapshot(
                completed_task_id=row["completed_task_id"],
                completed_at=datetime.fromisoformat(row["completed_at"]),
                open_task_ids=json.loads(row["open_task_ids"]),
            )
            for row in rows
        ]

    def delete_task(self, task_id: int) -> None:
        self.dao.delete_task(task_id)
