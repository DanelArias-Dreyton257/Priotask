from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskDTO:
    """Wire-format view of a Task: deadline/completed_at as ISO 8601 strings, no behavior."""
    task_id: Optional[int]
    user_id: int
    name: str
    deadline: str
    expected_duration_h: float
    importance: int
    task_type: str = ""
    task_subtype: str = ""
    done: bool = False
    completed_at: Optional[str] = None
