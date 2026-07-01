from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple

from server.src.data.domain.Task import Task


class PrioritizerModel(ABC):
    """
    Common interface for every prioritization strategy.

    Two implementations are expected to exist side by side:
    - FormulaPrioritizer: the closed-form model from the technical spec (no training).
    - PrioritizerNetwork: a per-user neural network trained from task selections (future work).
    """

    @abstractmethod
    def score(self, task: Task, reference_date: datetime) -> float:
        """Return the priority score v_i for a single task."""
        raise NotImplementedError

    def score_many(self, tasks: List[Task], reference_date: datetime) -> List[Tuple[Task, float]]:
        """Return (task, score) pairs for a list of tasks.

        Subclasses may override this to batch their predictions (e.g.
        PrioritizerNetwork batches the Keras model.predict() call). The
        default implementation falls back to calling score() per task.
        """
        return [(task, self.score(task, reference_date)) for task in tasks]
