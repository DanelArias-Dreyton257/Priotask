from datetime import datetime


class Task:

    def __init__(self, name: str, deadline: datetime, expected_duration_h: float, importance: int,
                 task_type: str = "", task_subtype: str = ""):
        self.name = name
        self.deadline = deadline
        self.expected_duration_h = expected_duration_h
        self.importance = importance
        # Used only as lexicographic tie-breakers when prioritizing (see spec eq. 5).
        self.task_type = task_type
        self.task_subtype = task_subtype

    def __repr__(self):
        return (f"Task(name={self.name}, deadline={self.deadline}, "
                f"expected_duration_h={self.expected_duration_h}, importance={self.importance}, "
                f"task_type={self.task_type}, task_subtype={self.task_subtype})")

    def get_time_until_deadline(self):
        return (self.deadline - datetime.now()).total_seconds()
