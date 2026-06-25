from datetime import datetime

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.PrioritizerModel import PrioritizerModel

SECONDS_PER_DAY = 86400.0
# Shifts the deadline back so a task is already considered overdue (d_i < 0)
# from the start of its due day, instead of only after midnight (see spec eq. 2).
DEADLINE_OFFSET_DAYS = 0.49


class FormulaPrioritizer(PrioritizerModel):
    """
    Closed-form prioritization model, implementing the equations from the
    technical spec (tareas_spec.pdf) with no learning involved.
    """

    def effort_days(self, task: Task) -> float:
        """h_i: estimated effort converted from hours to days (eq. 1)."""
        return task.expected_duration_h / 24.0

    def days_remaining(self, task: Task, reference_date: datetime) -> float:
        """d_i: days left until the deadline (eq. 2)."""
        return (task.deadline - reference_date).total_seconds() / SECONDS_PER_DAY - DEADLINE_OFFSET_DAYS

    def urgency(self, task: Task, reference_date: datetime) -> float:
        """r_i: urgency, split between the current and overdue regimes (eq. 3)."""
        h = self.effort_days(task)
        d = self.days_remaining(task, reference_date)
        if d > 0:
            return h / d
        return (2 + abs(d)) * h

    def score(self, task: Task, reference_date: datetime) -> float:
        """v_i = alpha_i * r_i (eq. 4)."""
        return task.importance * self.urgency(task, reference_date)
