from datetime import datetime
from typing import List, Optional

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FormulaPrioritizer import FormulaPrioritizer

# Fixed order: every learning PrioritizerModel (PrioritizerNetwork today,
# others later) trains and predicts on this exact vector, so persisted
# weights stay meaningful across runs.
FEATURE_ORDER = ["effort_days", "days_remaining", "importance", "urgency", "formula_score"]


class FeatureExtractor:
    """
    Turns a Task into the numeric feature vector learning models consume.
    Reuses FormulaPrioritizer's own building blocks instead of recomputing
    them, so the formula and any learned correction stay consistent.
    """

    def __init__(self, formula: Optional[FormulaPrioritizer] = None):
        self.formula = formula or FormulaPrioritizer()

    def extract(self, task: Task, reference_date: datetime) -> List[float]:
        return [
            self.formula.effort_days(task),
            self.formula.days_remaining(task, reference_date),
            float(task.importance),
            self.formula.urgency(task, reference_date),
            self.formula.score(task, reference_date),
        ]
