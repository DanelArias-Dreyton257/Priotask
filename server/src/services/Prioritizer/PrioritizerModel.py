from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

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
