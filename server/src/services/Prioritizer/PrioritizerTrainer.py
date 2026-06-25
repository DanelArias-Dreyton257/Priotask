from datetime import datetime
from typing import List, Optional

from server.src.services.Prioritizer.PrioritizerNetwork import PrioritizerNetwork, TrainingExample
from server.src.services.TaskManager import TaskManager

# Need at least this many examples, with both labels present, before a fit
# is worth running - an all-positive or all-negative batch can't teach the
# network anything.
MIN_EXAMPLES = 4


class PrioritizerTrainer:
    """
    Builds the Phase 6 training set from a user's task history and fits
    PrioritizerNetwork on it. The label approximates "the user picked this
    task to work on": for each past completion, the completed task is a
    positive example and the tasks still open at that exact moment (Phase 7's
    `CompletionSnapshot`, captured by `TaskManager.mark_done`) are negatives,
    both scored as of that completion's timestamp. Currently still-open tasks
    are also added as negatives scored as of now - that signal stays valid
    even before any completion history exists (e.g. a brand-new account).
    """

    def __init__(self, task_manager: Optional[TaskManager] = None, network: Optional[PrioritizerNetwork] = None):
        self.task_manager = task_manager or TaskManager()
        self.network = network or PrioritizerNetwork()

    def _build_examples(self, user_id: int) -> List[TrainingExample]:
        tasks_by_id = {task.task_id: task for task in self.task_manager.get_domain_tasks_for_user(user_id)}
        examples: List[TrainingExample] = []

        for snapshot in self.task_manager.get_completion_snapshots(user_id):
            completed_task = tasks_by_id.get(snapshot.completed_task_id)
            if completed_task is not None:
                examples.append((completed_task, snapshot.completed_at, 1))
            for open_task_id in snapshot.open_task_ids:
                open_task = tasks_by_id.get(open_task_id)
                if open_task is not None:
                    examples.append((open_task, snapshot.completed_at, 0))

        now = datetime.now()
        for task in tasks_by_id.values():
            if not task.done:
                examples.append((task, now, 0))

        return examples

    def train(self, user_id: int) -> bool:
        """Fits the user's network and returns True, or returns False (no-op)
        if there isn't enough signal yet to train on."""
        examples = self._build_examples(user_id)
        if len(examples) < MIN_EXAMPLES or len({label for _, _, label in examples}) < 2:
            return False
        self.network.fit(user_id, examples)
        return True
