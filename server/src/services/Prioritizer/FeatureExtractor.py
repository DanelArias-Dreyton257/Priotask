import math
from datetime import datetime
from typing import List, Optional

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FormulaPrioritizer import FormulaPrioritizer

# Fixed order: every learning PrioritizerModel (PrioritizerNetwork today,
# others later) trains and predicts on this exact vector, so persisted
# weights stay meaningful across runs.
FEATURE_ORDER = ["effort_days", "days_remaining", "importance", "urgency", "formula_score"]

# Normalization scales used by extract_normalized(). Each feature is squashed
# into roughly [-1, 1] using these domain-informed constants so no single
# feature can dominate gradient updates on tiny per-user datasets. The scales
# were chosen to place a "typical" task (8h effort, 7 days out, importance 5)
# near the middle of each feature's normalized range.
_EFFORT_SCALE = 10.0        # ~10 days of effort → 1.0
_DAYS_SCALE = 14.0          # ±14 days → ±~0.96
_URGENCY_SCALE = 10.0       # urgency of 10 → tanh(1) ≈ 0.76
_SCORE_SCALE = 100.0        # formula_score of 100 → tanh(1) ≈ 0.76


class FeatureExtractor:
    """
    Turns a Task into the numeric feature vector learning models consume.
    Reuses FormulaPrioritizer's own building blocks instead of recomputing
    them, so the formula and any learned correction stay consistent.

    extract() returns raw values (used by tests and diagnostics).
    extract_normalized() squashes each feature to roughly [-1, 1] so that
    differently-scaled inputs don't dominate gradient updates in the network.
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

    def normalize(self, features: List[float]) -> List[float]:
        """Squash raw features to ~[-1, 1] using fixed domain-informed scales."""
        effort_days, days_remaining, importance, urgency, formula_score = features
        return [
            min(effort_days / _EFFORT_SCALE, 3.0),      # cap at 3× typical max
            math.tanh(days_remaining / _DAYS_SCALE),
            importance / 10.0,                           # already [0.1, 1.0]
            math.tanh(urgency / _URGENCY_SCALE),
            math.tanh(formula_score / _SCORE_SCALE),
        ]

    def extract_normalized(self, task: Task, reference_date: datetime) -> List[float]:
        return self.normalize(self.extract(task, reference_date))
