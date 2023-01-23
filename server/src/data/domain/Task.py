from datetime import datetime


class Task:

    def __init__(self, name: str, deadline: datetime, expected_duration_h: int, importance: int):
        self.name = name
        self.deadline = deadline
        self.expected_duration_h = expected_duration_h
        self.importance = importance

    def __repr__(self):
        return f"Task(name={self.name}, deadline={self.deadline}, expected_duration_h={self.expected_duration_h}, importance={self.importance})"

    def get_time_until_deadline(self):
        return (self.deadline - datetime.now()).total_seconds()
