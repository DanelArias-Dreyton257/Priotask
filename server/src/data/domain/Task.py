from datetime import datetime
from typing import Optional


class Task:

    def __init__(self, name: str, deadline: datetime, expected_duration_h: float, importance: int,
                 task_type: str = "", task_subtype: str = "", task_id: Optional[int] = None,
                 user_id: Optional[int] = None, done: bool = False,
                 completed_at: Optional[datetime] = None,
                 recurrence_unit: Optional[str] = None, recurrence_interval: Optional[int] = None,
                 recurrence_end_date: Optional[datetime] = None):
        self.name = name
        self.deadline = deadline
        self.expected_duration_h = expected_duration_h
        self.importance = importance
        # Used only as lexicographic tie-breakers when prioritizing (see spec eq. 5).
        self.task_type = task_type
        self.task_subtype = task_subtype
        # Persistence fields: unset (None) until the task has been stored.
        self.task_id = task_id
        self.user_id = user_id
        self.done = done
        self.completed_at = completed_at
        # Phase 11: when recurrence_unit is set, completing this task spawns
        # the next occurrence (see TaskManager.mark_done) advanced by
        # recurrence_interval recurrence_units, stopping once that next
        # deadline would fall after recurrence_end_date.
        self.recurrence_unit = recurrence_unit
        self.recurrence_interval = recurrence_interval
        self.recurrence_end_date = recurrence_end_date

    def __repr__(self):
        return (f"Task(task_id={self.task_id}, name={self.name}, deadline={self.deadline}, "
                f"expected_duration_h={self.expected_duration_h}, importance={self.importance}, "
                f"task_type={self.task_type}, task_subtype={self.task_subtype}, "
                f"done={self.done}, completed_at={self.completed_at}, "
                f"recurrence_unit={self.recurrence_unit}, recurrence_interval={self.recurrence_interval}, "
                f"recurrence_end_date={self.recurrence_end_date})")

    def get_time_until_deadline(self):
        return (self.deadline - datetime.now()).total_seconds()
