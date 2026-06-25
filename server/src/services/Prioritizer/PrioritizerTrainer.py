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
    task to work on": done tasks are positives, scored at the moment they
    were completed; the user's still-open tasks are negatives, scored as of
    now. That's not a true snapshot of every task that was on the table at
    each completion - the schema from Phase 2 doesn't keep that history -
    but it's the signal available without adding an event log.
    """

    def __init__(self, task_manager: Optional[TaskManager] = None, network: Optional[PrioritizerNetwork] = None):
        self.task_manager = task_manager or TaskManager()
        self.network = network or PrioritizerNetwork()

    def _build_examples(self, user_id: int) -> List[TrainingExample]:
        tasks = self.task_manager.get_domain_tasks_for_user(user_id)
        now = datetime.now()
        examples: List[TrainingExample] = []
        for task in tasks:
            if task.done and task.completed_at is not None:
                examples.append((task, task.completed_at, 1))
            elif not task.done:
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
