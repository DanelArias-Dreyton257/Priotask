from datetime import datetime

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.PrioritizerModel import PrioritizerModel


class PrioritizerNetwork(PrioritizerModel):
    """
    Future work: a small per-user neural network, trained on the user's task
    selections, that learns to replace/adjust FormulaPrioritizer's scores.
    Its weights are meant to be persisted in the database per user.
    """

    def score(self, task: Task, reference_date: datetime) -> float:
        raise NotImplementedError("PrioritizerNetwork is not implemented yet.")
