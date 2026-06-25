from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.PrioritizerService import PrioritizerService

DEFAULT_AVAILABLE_HOURS_TODAY = 6.0
DEFAULT_PLAN_WEEK_DAYS = 7
EPSILON = 1e-9


@dataclass
class PlanEntry:
    """One line of today's plan: where a task ranks and how many hours it gets."""
    rank: int
    task: Task
    score: float
    recommended_hours_today: float


@dataclass
class DayPlan:
    """One day of a multi-day plan (Phase 9): the same `plan()` output for
    that day, plus the tasks due that day and the diagnostics (eq. 6) for the
    day's eligible tasks, used by the client as a per-day load indicator."""
    date: datetime
    entries: List[PlanEntry]
    diagnostics: Dict[str, float]
    deadlines: List[Task]
    available_hours: float


class DailyPlanner:
    """
    Turns the ranking signal v_i (PrioritizerService) into a user-facing time
    budget for today, per Phase 3 of the roadmap:
    - Only not-done tasks with remaining effort are eligible.
    - Each eligible task gets a share of `available_hours_today` proportional
      to its score, capped by its own remaining effort (water-filling: hours
      freed by capped tasks are redistributed among the rest).
    - Overdue tasks are water-filled first against the full budget, so a glut
      of current tasks can never starve them; whatever is left over is then
      water-filled among the current (not-yet-due) tasks.
    """

    def __init__(self, service: Optional[PrioritizerService] = None):
        self.service = service or PrioritizerService()

    @staticmethod
    def _is_overdue(task: Task, reference_date: datetime) -> bool:
        return task.deadline <= reference_date

    @staticmethod
    def _water_fill(pairs: List[Tuple[Task, float]], budget: float) -> Dict[Task, float]:
        """Distribute `budget` across `pairs` proportionally to score, capped by
        each task's remaining effort, redistributing freed budget until the
        budget is exhausted or every task is fully covered."""
        allocated = {task: 0.0 for task, _ in pairs}
        active = [(task, score) for task, score in pairs if score > 0]
        remaining_budget = budget

        while remaining_budget > EPSILON and active:
            total_weight = sum(score for _, score in active)
            if total_weight <= 0:
                break

            shares = {task: remaining_budget * (score / total_weight) for task, score in active}
            capped = [
                (task, score) for task, score in active
                if shares[task] >= task.expected_duration_h - allocated[task] - EPSILON
            ]

            if not capped:
                for task, _ in active:
                    allocated[task] += shares[task]
                remaining_budget = 0.0
                break

            capped_tasks = {task for task, _ in capped}
            for task, _ in capped:
                give = task.expected_duration_h - allocated[task]
                allocated[task] += give
                remaining_budget -= give
            active = [(task, score) for task, score in active if task not in capped_tasks]

        return allocated

    def plan(
        self,
        tasks: List[Task],
        available_hours_today: float = DEFAULT_AVAILABLE_HOURS_TODAY,
        reference_date: Optional[datetime] = None,
    ) -> List[PlanEntry]:
        reference_date = reference_date or datetime.now()
        eligible = [task for task in tasks if not task.done and task.expected_duration_h > 0]
        ranked = self.service.rank(eligible, reference_date)

        overdue = [pair for pair in ranked if self._is_overdue(pair[0], reference_date)]
        current = [pair for pair in ranked if not self._is_overdue(pair[0], reference_date)]

        overdue_hours = self._water_fill(overdue, available_hours_today)
        leftover_budget = available_hours_today - sum(overdue_hours.values())
        current_hours = self._water_fill(current, leftover_budget)

        hours_by_task = {**overdue_hours, **current_hours}
        return [
            PlanEntry(rank=i + 1, task=task, score=score, recommended_hours_today=hours_by_task[task])
            for i, (task, score) in enumerate(ranked)
        ]

    @staticmethod
    def _clone_task(task: Task) -> Task:
        """A by-value copy of `task`, so `plan_week` can carry remaining
        effort forward day by day without mutating the caller's tasks."""
        return Task(
            task.name, task.deadline, task.expected_duration_h, task.importance,
            task.task_type, task.task_subtype, task_id=task.task_id, user_id=task.user_id,
            done=task.done, completed_at=task.completed_at,
        )

    def plan_week(
        self,
        tasks: List[Task],
        days: int = DEFAULT_PLAN_WEEK_DAYS,
        available_hours_today: float = DEFAULT_AVAILABLE_HOURS_TODAY,
        reference_date: Optional[datetime] = None,
    ) -> List[DayPlan]:
        """Generalizes `plan()` across `days` simulated days: each day's
        recommended hours are subtracted from that task's remaining effort
        before ranking the next day, so a task that gets fully covered today
        no longer competes for budget tomorrow (carrying the existing
        water-filling logic forward instead of re-deriving it per day)."""
        reference_date = reference_date or datetime.now()
        not_done = [task for task in tasks if not task.done]
        working_tasks = [self._clone_task(task) for task in not_done]

        day_plans = []
        for day_index in range(days):
            day_date = reference_date + timedelta(days=day_index)
            entries = self.plan(working_tasks, available_hours_today, day_date)
            diagnostics = self.service.diagnostics([entry.task for entry in entries], day_date)
            deadlines = [task for task in not_done if task.deadline.date() == day_date.date()]

            # Snapshot each entry's task before it's mutated below for the
            # next day's carry-forward - otherwise this day's PlanEntry would
            # retroactively show the task as done once a later day fully
            # covers its remaining effort (PlanEntry.task is the same
            # working_tasks object, not a copy).
            snapshot_entries = [
                PlanEntry(rank=entry.rank, task=self._clone_task(entry.task),
                          score=entry.score, recommended_hours_today=entry.recommended_hours_today)
                for entry in entries
            ]
            day_plans.append(DayPlan(
                date=day_date, entries=snapshot_entries, diagnostics=diagnostics,
                deadlines=deadlines, available_hours=available_hours_today,
            ))

            hours_by_task = {entry.task: entry.recommended_hours_today for entry in entries}
            for task in working_tasks:
                used = hours_by_task.get(task)
                if used:
                    task.expected_duration_h = max(0.0, task.expected_duration_h - used)
                    if task.expected_duration_h <= EPSILON:
                        task.done = True

        return day_plans
