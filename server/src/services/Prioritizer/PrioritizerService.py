from datetime import datetime
from typing import Dict, List, Optional, Tuple

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FormulaPrioritizer import FormulaPrioritizer
from server.src.services.Prioritizer.PrioritizerModel import PrioritizerModel


class PrioritizerService:
    """
    Entry point for prioritization. Delegates the per-task score (v_i) to a
    PrioritizerModel (FormulaPrioritizer for now, PrioritizerNetwork later) and
    handles the model-agnostic parts of the spec: ordering (eq. 5) and the
    diagnostics panel (eq. 6).
    """

    def __init__(self, model: Optional[PrioritizerModel] = None):
        self.model = model or FormulaPrioritizer()

    def _scores(self, tasks: List[Task], reference_date: datetime) -> List[Tuple[Task, float]]:
        return [(task, self.model.score(task, reference_date)) for task in tasks]

    def rank(self, tasks: List[Task], reference_date: Optional[datetime] = None) -> List[Tuple[Task, float]]:
        """pi = argsort(v, desc; Tipo, Sub-tipo, Nombre, asc) (eq. 5)."""
        reference_date = reference_date or datetime.now()
        scored = self._scores(tasks, reference_date)
        return sorted(
            scored,
            key=lambda pair: (-pair[1], pair[0].task_type, pair[0].task_subtype, pair[0].name),
        )

    def diagnostics(self, tasks: List[Task], reference_date: Optional[datetime] = None) -> Dict[str, float]:
        """Mean, population std and sum of {v_i}, plus the V/4 and V/8 session-load thresholds (eq. 6)."""
        reference_date = reference_date or datetime.now()
        values = [score for _, score in self._scores(tasks, reference_date)]
        n = len(values)
        if n == 0:
            return {"mean": 0.0, "std": 0.0, "sum": 0.0, "threshold_quarter": 0.0, "threshold_eighth": 0.0}

        total = sum(values)
        mean = total / n
        variance = sum((v - mean) ** 2 for v in values) / n
        return {
            "mean": mean,
            "std": variance ** 0.5,
            "sum": total,
            "threshold_quarter": total / 4,
            "threshold_eighth": total / 8,
        }
